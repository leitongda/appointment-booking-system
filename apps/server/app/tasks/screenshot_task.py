"""
定期网页截图任务
- 用 Python playwright（同步 API）在固定 Docker 环境内渲染 admin 核心页面
- 注入 admin token（直传 SCREENSHOT_TOKEN 或账号密码登录获取），逐页截图
- 整批截图通过 asyncio 桥接一次性 upload_bytes 到对象存储，返回汇总结果

部署注意：容器内需执行
    playwright install chromium --with-deps
否则任务会在 chromium.launch 时抛出 "Executable doesn't exist"。
"""
import asyncio
import json
import logging
import os
import re
from datetime import datetime
from typing import Any

from app.celery_app import celery_app
from app.infrastructure.storage import get_storage

logger = logging.getLogger(__name__)

# admin 前端 localStorage key（与 @hospital/shared STORAGE_KEYS 一致）
_ADMIN_TOKEN_KEY = "hospital_token"
_ADMIN_TENANT_KEY = "hospital_current_tenant_id"

# 默认截图目标页面（admin 核心路由）；可用 SCREENSHOT_PAGES 覆盖（逗号分隔）
_DEFAULT_PAGES = [
    "/dashboard",
    "/patient",
    "/appointment",
    "/schedule/calendar",
    "/medical-services",
]

# 视口尺寸
_VIEWPORT = {"width": 1920, "height": 1080}

# 单页 goto 超时（毫秒）
_NAV_TIMEOUT_MS = 30_000

# storage folder
_STORAGE_FOLDER = "admin-screenshots"


def _slugify(path: str) -> str:
    """把路由路径转成文件名安全的 slug：/schedule/calendar -> schedule-calendar"""
    slug = re.sub(r"[^a-zA-Z0-9/-]", "", path).strip("/")
    return slug.replace("/", "-") or "root"


def _get_config() -> dict[str, Any]:
    """从环境变量读取截图配置。未配置时返回空 pages 列表，任务直接跳过。"""
    base_url = (os.environ.get("SCREENSHOT_ADMIN_BASE_URL") or "").rstrip("/")
    token = os.environ.get("SCREENSHOT_TOKEN") or ""
    account = os.environ.get("SCREENSHOT_ACCOUNT") or ""
    password = os.environ.get("SCREENSHOT_PASSWORD") or ""
    api_base = (os.environ.get("SCREENSHOT_API_BASE_URL") or "").rstrip("/")
    tenant_id = os.environ.get("SCREENSHOT_TENANT_ID") or ""

    pages_env = os.environ.get("SCREENSHOT_PAGES")
    if pages_env is not None and pages_env.strip():
        pages = [p.strip() for p in pages_env.split(",") if p.strip()]
    else:
        pages = list(_DEFAULT_PAGES)

    return {
        "base_url": base_url,
        "token": token,
        "account": account,
        "password": password,
        "api_base": api_base,
        "tenant_id": tenant_id,
        "pages": pages,
    }


def _login_for_token(context, api_base: str, account: str, password: str) -> str | None:
    """走 /admin/login 用账号密码换取 accessToken。

    admin 登录支持明文密码（encrypted=false），避开 RSA 加密路径。
    失败返回 None，由调用方决定是否继续。
    """
    import urllib.request

    url = f"{api_base}/admin/login"
    payload = json.dumps(
        {"username": account, "password": password, "encrypted": False}
    ).encode("utf-8")
    req = urllib.request.Request(  # noqa: S310 - 内网登录调用
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:  # noqa: S310 - 内网调用
            body = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        logger.error(f"[截图] 账号密码登录失败: {exc}")
        return None

    # 后端统一响应 {code, message, data}；data.accessToken
    data = body.get("data") if isinstance(body, dict) else None
    if isinstance(data, dict):
        token = data.get("accessToken") or data.get("access_token")
        if token:
            return str(token)
    logger.error(f"[截图] 登录响应未包含 accessToken: {body}")
    return None


@celery_app.task(
    name="app.tasks.screenshot_task.capture_admin_screenshots",
    time_limit=600,
    soft_time_limit=540,
)
def capture_admin_screenshots() -> dict:
    """定期截图 admin 核心页面并上传到对象存储。

    配置（环境变量）：
      - SCREENSHOT_ADMIN_BASE_URL: admin 前端基地址（必填），如 http://admin.local
      - SCREENSHOT_TOKEN: 直接注入的 admin token（优先）
      - SCREENSHOT_ACCOUNT / SCREENSHOT_PASSWORD: 账号密码登录拿 token（TOKEN 未设时用）
      - SCREENSHOT_API_BASE_URL: 登录接口基地址（如 http://api.local/api/v1）
      - SCREENSHOT_TENANT_ID: 注入的租户 ID（可选）
      - SCREENSHOT_PAGES: 逗号分隔的路由列表（可选，覆盖默认）

    返回：{success, captured:[{page, key, url}], failed:[{page, error}]}
    """
    cfg = _get_config()
    base_url = cfg["base_url"]
    pages = cfg["pages"]

    if not base_url:
        logger.warning("[截图] 未配置 SCREENSHOT_ADMIN_BASE_URL，任务跳过")
        return {"success": False, "skipped": True, "reason": "missing ADMIN_BASE_URL"}
    if not pages:
        logger.warning("[截图] 未配置截图页面列表，任务跳过")
        return {"success": False, "skipped": True, "reason": "no pages"}

    # 延迟 import，避免无 playwright 环境时 celery worker 启动失败
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        logger.error(f"[截图] 未安装 playwright: {exc}")
        return {"success": False, "skipped": True, "reason": "playwright not installed"}

    captured: list[dict] = []
    failed: list[dict] = []
    # 缓存内存中的截图字节，最后一次性 asyncio.run 上传整批
    pending_uploads: list[tuple[str, bytes]] = []

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(viewport=_VIEWPORT)

        # 先打开首页建立 origin，便于注入 localStorage
        try:
            seed_page = context.new_page()
            seed_page.goto(base_url, wait_until="domcontentloaded", timeout=_NAV_TIMEOUT_MS)
        except Exception as exc:
            logger.error(f"[截图] 打开 base_url={base_url} 失败: {exc}")
            browser.close()
            return {"success": False, "captured": [], "failed": [], "error": str(exc)}

        # 取得 token
        token = cfg["token"]
        if not token and cfg["account"] and cfg["password"] and cfg["api_base"]:
            token = _login_for_token(context, cfg["api_base"], cfg["account"], cfg["password"]) or ""

        if not token:
            logger.error("[截图] 无可用 token（SCREENSHOT_TOKEN 未设且账号密码登录失败/未配），任务终止")
            browser.close()
            return {
                "success": False,
                "captured": [],
                "failed": [{"page": p, "error": "no token"} for p in pages],
            }

        # 注入 token / tenantId
        try:
            seed_page.evaluate(f"localStorage.setItem('{_ADMIN_TOKEN_KEY}', '{token}');")
            if cfg["tenant_id"]:
                tid = cfg["tenant_id"]
                # 与 admin setStorage 字符串分支一致：存原始字符串（非 JSON），
                # 否则多出来的引号与 admin 自身存储格式不一致
                seed_page.evaluate(
                    f"localStorage.setItem('{_ADMIN_TENANT_KEY}', '{tid}');"
                )
        except Exception as exc:
            logger.error(f"[截图] 注入 token 失败: {exc}")
            browser.close()
            return {"success": False, "captured": [], "failed": [], "error": str(exc)}

        # 逐页截图，单页失败隔离
        now = datetime.utcnow()
        date_path = now.strftime("%Y%m%d")
        time_tag = now.strftime("%H%M%S")

        for path in pages:
            full_url = f"{base_url}{path}"
            try:
                page = context.new_page()
                page.goto(full_url, wait_until="networkidle", timeout=_NAV_TIMEOUT_MS)
                # 给 SPA 一点渲染时间
                page.wait_for_timeout(1500)
                png_bytes = page.screenshot(full_page=True, type="png")
                page.close()

                slug = _slugify(path)
                key = f"{_STORAGE_FOLDER}/{date_path}/{slug}_{time_tag}.png"
                pending_uploads.append((key, png_bytes))
                logger.info(f"[截图] 截图成功 page={path} size={len(png_bytes)}B")
            except Exception as exc:
                failed.append({"page": path, "error": str(exc)})
                logger.warning(f"[截图] 截图失败 page={path}: {exc}")

        browser.close()

    # 整批一次性上传（单个 asyncio.run 包裹一个协程，跑完所有 upload_bytes）
    if pending_uploads:
        try:
            storage = get_storage()

            async def _upload_all():
                results = []
                for key, data in pending_uploads:
                    res = await storage.upload_bytes(data, key, "image/png")
                    results.append((key, res.url))
                return results

            uploaded = asyncio.run(_upload_all())
            for (key, _), url in zip(pending_uploads, uploaded, strict=True):
                captured.append({"key": key, "url": url})
        except Exception as exc:
            logger.error(f"[截图] 对象存储批量上传失败（{len(pending_uploads)} 张丢失）: {exc}")
            failed.append({"page": "__upload__", "error": str(exc)})

    logger.info(
        f"[截图] 任务完成: 成功 {len(captured)} 张，失败 {len(failed)} 页"
    )
    return {
        "success": len(failed) == 0,
        "captured": captured,
        "failed": failed,
    }
