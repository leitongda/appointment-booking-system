import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import PlainTextResponse

from app.api.v1 import main_router, deprecated_router
from app.api.v2 import build_v2_router
from app.core.config import settings
from app.core.logging import setup_logging
from app.core.redis import close_redis, get_redis
from app.core.websocket import ws_manager
from app.middleware.response import UnifiedResponseMiddleware
from app.middleware.exception import register_exception_handlers
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.request_log import RequestLogMiddleware
from app.middleware.operation_log import OperationLogMiddleware
from app.middleware.security_headers import SecurityHeadersMiddleware
from app.middleware.tenant_context import TenantContextMiddleware
from app.middleware.prometheus_metrics import PrometheusMetricsMiddleware, get_metrics_response
from app.middleware.deprecation import DeprecationMiddleware, DeprecatedEndpoint
from app.db.session import AsyncSessionLocal, engine
from app.tasks.blacklist_task import auto_release_blacklist
from app.modules.amap.router import close_amap_client

# 初始化日志系统
setup_logging(
    log_level=settings.LOG_LEVEL,
    log_dir=settings.LOG_DIR,
    app_name="hospital",
    json_format=settings.LOG_JSON_FORMAT,
    console_output=True,
    file_output=True
)

logger = logging.getLogger(__name__)

# 后台任务控制
_background_tasks = []


async def blacklist_auto_release_task():
    """黑名单自动解禁定时任务（每小时执行一次）"""
    while True:
        try:
            await asyncio.sleep(3600)  # 每小时执行一次
            async with AsyncSessionLocal() as db:
                released = await auto_release_blacklist(db)
                if released:
                    logger.info(f"自动解禁黑名单用户 {len(released)} 人")
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"黑名单自动解禁任务出错: {e}")


async def warmup_connections():
    """预热数据库和 Redis 连接池
    
    在应用启动时建立连接，避免首次请求时的连接延迟
    """
    try:
        # 预热 PostgreSQL 连接池
        logger.info("正在预热数据库连接池...")
        async with AsyncSessionLocal() as session:
            from sqlalchemy import text
            await session.execute(text("SELECT 1"))
        logger.info("✅ 数据库连接池预热完成")
    except Exception as e:
        logger.error(f"❌ 数据库连接池预热失败: {e}")
    
    try:
        # 预热 Redis 连接
        logger.info("正在预热 Redis 连接...")
        redis = await get_redis()
        await redis.ping()
        logger.info("✅ Redis 连接预热完成")
    except Exception as e:
        logger.error(f"❌ Redis 连接预热失败: {e}")


async def ensure_super_admin_exists():
    """确保系统中存在超级管理员
    
    系统启动时检查，如果没有超级管理员则记录警告日志。
    生产环境中应通过初始化脚本创建超级管理员。
    """
    from sqlalchemy import select, func
    from app.models.admin import Admin, Role
    
    try:
        async with AsyncSessionLocal() as session:
            # 检查是否存在 SUPER_ADMIN 角色
            role_result = await session.execute(
                select(Role).where(Role.code == "SUPER_ADMIN")
            )
            super_role = role_result.scalar_one_or_none()
            
            if not super_role:
                logger.warning("⚠️  系统中不存在 SUPER_ADMIN 角色，请运行初始化脚本: python scripts/init_roles.py")
                return
            
            # 检查是否有超级管理员账号
            admin_count = await session.scalar(
                select(func.count(Admin.id))
                .join(Role)
                .where(Role.code == "SUPER_ADMIN", Admin.status == 1)
            )
            
            if not admin_count or admin_count == 0:
                logger.warning("⚠️  系统中不存在有效的超级管理员账号，请运行初始化脚本: python scripts/init_data.py")
            else:
                logger.info(f"✅ 超级管理员检查通过（共 {admin_count} 个有效超管账号）")
    except Exception as e:
        logger.error(f"❌ 超级管理员检查失败: {e}")


def _validate_production_config() -> None:
    """生产环境配置校验 — 启动时检查关键安全配置项

    检查项:
      1. SECRET_KEY 不为默认值
      2. DATABASE_URL 不指向 localhost
      3. DEBUG 为 False
      4. RATE_LIMIT_ENABLED 为 True

    不通过时输出 CRITICAL 日志，阻止不安全的生产部署。
    """
    if settings.ENVIRONMENT != "production":
        return

    violations: list[str] = []

    # SECRET_KEY 默认值检测（docker-compose 中的占位值 + 常见弱密钥）
    default_keys = {
        "your-secret-key-change-in-production",
        "secret",
        "change-me",
        "changeme",
    }
    if settings.SECRET_KEY.lower() in {k.lower() for k in default_keys} or len(settings.SECRET_KEY) < 16:
        violations.append("SECRET_KEY 使用默认值或长度不足 (<16 字符)")

    # DATABASE_URL 不应指向 localhost
    db_url_lower = settings.DATABASE_URL.lower()
    if "localhost" in db_url_lower or "127.0.0.1" in db_url_lower:
        violations.append("DATABASE_URL 指向 localhost/127.0.0.1，生产环境应使用远程数据库")

    # DEBUG 必须关闭
    if settings.DEBUG:
        violations.append("DEBUG=true，生产环境必须关闭调试模式")

    # 限流必须启用
    if not settings.RATE_LIMIT_ENABLED:
        violations.append("RATE_LIMIT_ENABLED=false，生产环境必须启用限流")

    if violations:
        for v in violations:
            logger.critical(f"CRITICAL 生产配置校验失败: {v}")
        logger.critical(
            "以上 {count} 项配置违规，请修正后重新启动".format(count=len(violations))
        )
    else:
        logger.info("生产环境配置校验通过")


def _init_sentry() -> None:
    """初始化 Sentry APM（仅当 SENTRY_DSN 非空时启用）"""
    if not settings.SENTRY_DSN:
        return

    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.logging import LoggingIntegration

    sentry_logging = LoggingIntegration(
        level=logging.INFO,        # 采集 INFO 及以上日志
        event_level=logging.ERROR,  # 仅将 ERROR 及以上发送为 Sentry 事件
    )

    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.ENVIRONMENT,
        traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
        integrations=[
            FastApiIntegration(),
            sentry_logging,
        ],
        send_default_pii=False,  # 不发送个人信息
    )
    logger.info(f"Sentry APM 已初始化 (dsn=***, traces_sample_rate={settings.SENTRY_TRACES_SAMPLE_RATE})")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期"""
    logger.info("="*50)
    logger.info(f"🚀 {settings.PROJECT_NAME} 启动中...")
    logger.info(f"   环境: {settings.ENVIRONMENT}")
    logger.info(f"   调试模式: {settings.DEBUG}")
    logger.info("="*50)

    # Sentry APM 初始化（仅当 DSN 非空时启用）
    _init_sentry()

    # 预热连接池（消除冷启动延迟）
    await warmup_connections()

    # 生产环境配置校验（安全检查）
    _validate_production_config()

    # 生产环境限流检查
    if settings.ENVIRONMENT == "production" and not settings.RATE_LIMIT_ENABLED:
        logger.critical(
            "生产环境中 RATE_LIMIT_ENABLED=false，拒绝启动。"
            "请在 .env 中设置 RATE_LIMIT_ENABLED=true"
        )
        import sys
        sys.exit(1)

    # 检查超级管理员是否存在
    await ensure_super_admin_exists()
    
    # 启动后台任务
    task = asyncio.create_task(blacklist_auto_release_task())
    _background_tasks.append(task)
    logger.info("后台定时任务已启动")
    
    # 启动 WebSocket 管理器
    await ws_manager.start()
    logger.info("WebSocket 管理器已启动")
    
    yield
    
    # 停止后台任务
    logger.info("正在关闭后台任务...")
    for task in _background_tasks:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
    
    # 停止 WebSocket 管理器
    await ws_manager.stop()
    logger.info("WebSocket 管理器已停止")
    
    # 关闭 Redis 连接
    await close_redis()
    logger.info("Redis 连接已关闭")

    # 关闭高德地图 HTTP 连接池
    await close_amap_client()
    logger.info("高德地图连接池已关闭")

    logger.info(f"👋 {settings.PROJECT_NAME} 已停止")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.PROJECT_NAME,
        description=_build_openapi_description(),
        version=settings.OPENAPI_VERSION,
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
        openapi_tags=_build_openapi_tags(),
        swagger_ui_parameters={"docExpansion": "none"},
        contact={"name": "技术支持"},
        license_info={"name": "私有协议"},
    )

    _configure_middlewares(app)
    register_exception_handlers(app)
    app.include_router(main_router, prefix=settings.API_V1_STR)
    app.include_router(deprecated_router, prefix=settings.API_V1_STR)
    # v2 路由注册点（当前为空，预留接口）
    v2_router = build_v2_router()
    app.include_router(v2_router, prefix=settings.API_V2_STR)
    _configure_static_mounts(app)
    _register_health_routes(app)
    _register_llms_routes(app)
    return app


def _build_openapi_tags():
    return [
        {
            "name": "认证",
            "description": "用户登录、注册、Token 刷新、微信授权等认证相关接口",
        },
        {
            "name": "用户",
            "description": "用户个人信息、密码修改、头像上传、就诊人管理",
        },
        {
            "name": "权限管理",
            "description": "管理员账号、角色、权限、操作日志等后台权限管理",
        },
        # 核心业务
        {
            "name": "预约",
            "description": "预约挂号、签到、叫号、取消、完成等预约全流程接口",
        },
        {
            "name": "排班",
            "description": "医生排班查询、批量创建、停诊、恢复等排班管理接口",
        },
        {
            "name": "排班模板",
            "description": "排班规则模板管理，支持按模板批量生成排班",
        },
        {
            "name": "自定义排班",
            "description": "不依赖模板的自定义排班管理",
        },
        {
            "name": "医生",
            "description": "医生信息查询、创建、更新、排序等管理接口",
        },
        {
            "name": "科室",
            "description": "科室信息查询、树形结构、医生绑定等管理接口",
        },
        {
            "name": "门店管理",
            "description": "多门店管理、门店配置、科室绑定、微信配置",
        },
        # 患者相关
        {
            "name": "就诊卡管理",
            "description": "患者就诊卡（家庭成员）的增删改查",
        },
        {
            "name": "患者管理",
            "description": "后台患者管理、黑名单、积分调整等",
        },
        {
            "name": "病历",
            "description": "病历记录的创建、查询、更新",
        },
        # 排班辅助
        {
            "name": "休息日设置",
            "description": "门店/医生休息日配置，休息日期间不可预约",
        },
        {
            "name": "停诊管理",
            "description": "临时停诊管理",
        },
        {
            "name": "停诊调班",
            "description": "医生停诊申请、调班申请的审核流程",
        },
        # 配置与设置
        {
            "name": "系统设置",
            "description": "预约规则、医院信息、微信/短信/邮件配置、时段配置等",
        },
        {
            "name": "诊费管理",
            "description": "诊费类型、全局模板、门店模板、医生诊费配置",
        },
        {
            "name": "医生预约设置",
            "description": "医生个性化预约限制配置",
        },
        {
            "name": "复诊规则配置",
            "description": "门店复诊判定规则配置（时间范围、判定范围）",
        },
        {
            "name": "规则管理",
            "description": "预约/签到/取消时间窗规则组管理",
        },
        {
            "name": "班次类型",
            "description": "班次类型定义（普通号、专家号等）",
        },
        # 内容与消息
        {
            "name": "内容管理",
            "description": "新闻公告、轮播图等内容管理",
        },
        {
            "name": "消息中心",
            "description": "站内消息发送、模板管理、已读状态",
        },
        {
            "name": "邮件模板",
            "description": "邮件通知模板管理",
        },
        {
            "name": "预约须知",
            "description": "预约须知内容配置",
        },
        {
            "name": "用户反馈",
            "description": "用户反馈、投诉建议的处理",
        },
        # 数据与统计
        {
            "name": "数据统计",
            "description": "预约统计、收入趋势、科室/医生排行等数据看板",
        },
        {
            "name": "用户行为分析",
            "description": "用户行为日志分析",
        },
        {
            "name": "审计日志",
            "description": "系统操作审计日志查询",
        },
        {
            "name": "数据导出",
            "description": "预约记录、统计数据导出",
        },
        {
            "name": "数据导入导出",
            "description": "批量数据导入导出",
        },
        # 其他
        {
            "name": "黑名单管理",
            "description": "患者黑名单管理，黑名单用户无法预约",
        },
        {
            "name": "用户收藏",
            "description": "用户收藏的医生",
        },
        {
            "name": "文件上传",
            "description": "图片上传、URL 转存",
        },
        {
            "name": "医生端",
            "description": "医生专属接口：今日预约、叫号队列、就诊操作",
        },
        {
            "name": "WebSocket",
            "description": "实时消息推送（叫号通知、签到通知等）",
        },
        # 多租户
        {
            "name": "租户管理",
            "description": "SaaS 多租户管理、订阅计划、用量统计（平台管理员）",
        },
    ]


def _build_openapi_description() -> str:
    return """
## 医院预约挂号系统 API

一套完整的医院预约挂号解决方案，支持多门店、多科室、多医生的排班预约管理。

### 主要功能

| 模块 | 功能 |
|------|------|
| **预约管理** | 在线预约、签到、叫号、取消、爽约处理 |
| **排班管理** | 模板排班、自定义排班、停诊、休息日 |
| **患者管理** | 就诊卡、病历、积分、黑名单 |
| **权限管理** | 多角色、细粒度权限、操作日志 |
| **数据统计** | 预约趋势、收入统计、科室/医生排行 |

### 认证方式

- **JWT Token 认证**: 大部分接口需要在 Header 中携带 `Authorization: Bearer <token>`
- **微信登录**: 支持微信小程序授权登录
- **手机号登录**: 支持短信验证码登录

### 响应格式

所有接口返回统一格式：
```json
{
  "code": 0,
  "message": "success",
  "data": { ... }
}
```

### 错误码说明

| 错误码 | 说明 |
|--------|------|
| 0 | 成功 |
| 400 | 请求参数错误 |
| 401 | 未认证或 Token 过期 |
| 403 | 无权限 |
| 404 | 资源不存在 |
| 500 | 服务器内部错误 |
"""


def _configure_middlewares(app: FastAPI) -> None:
    # Starlette add_middleware 使用 insert(0)，build 时 reversed() 包装。
    # 因此最后注册的中间件在请求阶段最先执行（最靠近 app 层）。
    # 请求执行顺序：Prometheus -> TenantContext -> UnifiedResponse -> Deprecation -> OperationLog -> RequestLog -> RateLimit -> SecurityHeaders -> GZip -> CORS
    # 响应执行顺序：CORS -> GZip -> SecurityHeaders -> RateLimit -> RequestLog -> OperationLog -> Deprecation -> UnifiedResponse -> TenantContext -> Prometheus
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Tenant-ID", "X-Tenant-Code", "X-Request-ID", "Accept"],
    )
    # GZip 压缩 — 最小 1000 字节才压缩，避免小响应被压缩反而增大体积
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    app.add_middleware(
        SecurityHeadersMiddleware,
        hsts_enabled=settings.SECURITY_HSTS_ENABLED and not settings.DEBUG,
    )
    app.add_middleware(
        RateLimitMiddleware,
        requests_per_minute=settings.RATE_LIMIT_PER_MINUTE,
        requests_per_second=settings.RATE_LIMIT_PER_SECOND,
        enabled=settings.RATE_LIMIT_ENABLED,
    )
    app.add_middleware(RequestLogMiddleware)
    app.add_middleware(OperationLogMiddleware)
    app.add_middleware(DeprecationMiddleware)
    app.add_middleware(UnifiedResponseMiddleware)
    # 租户上下文中间件（最后注册 = 请求阶段最先执行），为限流/日志等下游中间件提供 tenant_id
    app.add_middleware(TenantContextMiddleware)
    # Prometheus 指标中间件（最外层，采集总请求耗时）
    app.add_middleware(PrometheusMetricsMiddleware)


def _configure_static_mounts(app: FastAPI) -> None:
    if settings.STORAGE_TYPE.lower() == "local":
        upload_dir = Path(settings.LOCAL_UPLOAD_DIR)
        upload_dir.mkdir(parents=True, exist_ok=True)
        # 使用带租户校验的文件服务替代直接 StaticFiles 挂载
        from app.middleware.tenant_context import get_current_tenant_id

        @app.get("/uploads/{file_path:path}", include_in_schema=False)
        async def _serve_upload_file(file_path: str):
            """带租户校验的本地文件访问端点。

            替代直接 StaticFiles 挂载，在返回文件前校验请求租户与文件所属租户是否匹配。
            租户文件的路径格式为 tenants/{tenant_id}/...，
            无租户上下文的公开请求（如患者端）允许访问。
            """
            from fastapi.responses import FileResponse as FR
            from starlette.responses import Response

            full_path = (upload_dir / file_path).resolve()

            # 防路径穿越
            if not str(full_path).startswith(str(upload_dir.resolve())):
                return Response(status_code=403)

            if not full_path.is_file():
                return Response(status_code=404)

            # 租户校验：从文件路径中提取 tenant_id，与请求上下文对比
            prefix = "tenants/"
            if file_path.startswith(prefix):
                remainder = file_path[len(prefix):]
                file_tenant_id = remainder.split("/", 1)[0] if "/" in remainder else remainder
                request_tenant_id = get_current_tenant_id()

                # 双方都有租户信息时必须匹配
                if file_tenant_id and request_tenant_id:
                    if str(file_tenant_id) != str(request_tenant_id):
                        return Response(status_code=403)

            # 推断 Content-Type
            ext = file_path.rsplit(".", 1)[-1].lower() if "." in file_path else ""
            mime_map = {
                "jpg": "image/jpeg", "jpeg": "image/jpeg",
                "png": "image/png", "gif": "image/gif",
                "webp": "image/webp", "svg": "image/svg+xml",
            }
            content_type = mime_map.get(ext, "application/octet-stream")

            return FR(
                path=str(full_path),
                media_type=content_type,
                headers={"Cache-Control": "public, max-age=86400"},
            )

        logger.info(f"文件服务已挂载（带租户校验）: /uploads -> {upload_dir}")


def _register_health_routes(app: FastAPI) -> None:
    import time as _time

    _start_time = _time.time()

    @app.get("/metrics", include_in_schema=False)
    async def prometheus_metrics():
        """Prometheus 指标端点"""
        return get_metrics_response()

    @app.get("/health", include_in_schema=False)
    async def health_check():
        """兼容旧端点，返回存活状态"""
        return {"status": "ok"}

    @app.get("/health/live", include_in_schema=False)
    async def liveness_probe():
        """存活探针 — 始终返回 200，Kubernetes liveness 用"""
        return {"status": "alive", "timestamp": _time.time()}

    @app.get("/health/ready", include_in_schema=False)
    async def readiness_probe():
        """就绪探针 — 检查 DB + Redis 可用性，Kubernetes readiness 用"""
        from sqlalchemy import text
        from app.db.session import async_session_maker

        checks = {}
        all_ok = True

        # 数据库检查
        try:
            async with async_session_maker() as db:
                await db.execute(text("SELECT 1"))
            checks["database"] = {"status": "ok"}
        except Exception as exc:
            checks["database"] = {"status": "error", "detail": str(exc)}
            all_ok = False

        # Redis 检查
        try:
            redis = await get_redis()
            await redis.ping()
            checks["redis"] = {"status": "ok"}
        except Exception as exc:
            checks["redis"] = {"status": "error", "detail": str(exc)}
            all_ok = False

        result = {
            "status": "ready" if all_ok else "not_ready",
            "checks": checks,
            "timestamp": _time.time(),
        }
        from starlette.responses import JSONResponse as _JR
        return _JR(content=result, status_code=200 if all_ok else 503)

    @app.get("/health/detailed", include_in_schema=False)
    async def detailed_health_check():
        """详细健康检查 — 包含 Celery、Redis 内存、DB 连接池、磁盘、运行时间"""
        import shutil
        from sqlalchemy import text
        from app.db.session import async_session_maker, engine

        uptime = _time.time() - _start_time
        checks = {
            "status": "ok",
            "environment": settings.ENVIRONMENT,
            "uptime_seconds": round(uptime, 1),
            "timestamp": _time.time(),
        }

        # --- 数据库 ---
        try:
            async with async_session_maker() as db:
                await db.execute(text("SELECT 1"))
            pool = engine.pool
            checks["database"] = {
                "status": "ok",
                "pool": {
                    "size": pool.size(),
                    "checked_in": pool.checkedin(),
                    "checked_out": pool.checkedout(),
                    "overflow": pool.overflow(),
                },
            }
        except Exception as exc:
            checks["database"] = {"status": "error", "detail": str(exc)}
            checks["status"] = "degraded"

        # --- Redis ---
        try:
            redis = await get_redis()
            await redis.ping()
            info = await redis.info("memory")
            checks["redis"] = {
                "status": "ok",
                "memory": {
                    "used_memory_human": info.get("used_memory_human", "N/A"),
                    "used_memory_peak_human": info.get("used_memory_peak_human", "N/A"),
                    "mem_fragmentation_ratio": info.get("mem_fragmentation_ratio", "N/A"),
                },
            }
        except Exception as exc:
            checks["redis"] = {"status": "error", "detail": str(exc)}
            checks["status"] = "degraded"

        # --- Celery ---
        try:
            from celery.app.control import Control
            from app.tasks.celery_app import celery_app as _celery

            ctrl = Control(_celery)
            inspect = ctrl.inspect(timeout=2)
            active = inspect.active() or {}
            stats = inspect.stats() or {}
            checks["celery"] = {
                "status": "ok",
                "workers": len(active),
                "active_tasks": sum(len(v) for v in active.values()),
                "worker_stats": {
                    name: {
                        "pool": s.get("pool", {}).get("implementation", "N/A"),
                        "rusage": s.get("rusage", {}),
                    }
                    for name, s in stats.items()
                },
            }
        except Exception as exc:
            checks["celery"] = {"status": "error", "detail": str(exc)}
            checks["status"] = "degraded"

        # --- 磁盘用量 ---
        try:
            usage = shutil.disk_usage("/")
            checks["disk"] = {
                "total_gb": round(usage.total / (1024**3), 2),
                "used_gb": round(usage.used / (1024**3), 2),
                "free_gb": round(usage.free / (1024**3), 2),
                "usage_percent": round(usage.used / usage.total * 100, 1),
            }
        except Exception as exc:
            checks["disk"] = {"status": "error", "detail": str(exc)}

        return checks


def _read_static_text(filename: str, fallback: str) -> str:
    static_dir = Path(__file__).parent / "static"
    file_path = static_dir / filename
    if file_path.exists():
        return file_path.read_text(encoding="utf-8")
    return fallback


def _register_llms_routes(app: FastAPI) -> None:
    static_dir = Path(__file__).parent / "static"

    @app.get("/llms.txt", response_class=PlainTextResponse, include_in_schema=False)
    async def get_llms_txt():
        return _read_static_text(
            "llms.txt",
            f"""# {settings.PROJECT_NAME}

> 医院挂号系统 API

- API 版本: 1.0.0
- 基础路径: {settings.API_V1_STR}
- Swagger 文档: /docs
- ReDoc 文档: /redoc
- OpenAPI JSON: {settings.API_V1_STR}/openapi.json

请运行 `python scripts/generate_llms_txt.py` 生成完整的 llms.txt 文件。
""",
        )

    @app.get("/llms-full.txt", response_class=PlainTextResponse, include_in_schema=False)
    async def get_llms_full_txt():
        return _read_static_text(
            "llms-full.txt",
            f"""# {settings.PROJECT_NAME}

> 医院挂号系统 API - 完整版

请运行 `python scripts/generate_llms_txt.py` 生成完整的 llms-full.txt 文件。

或者访问 OpenAPI 规范获取完整 API 定义:
- {settings.API_V1_STR}/openapi.json
""",
        )

    @app.get("/llms-en.txt", response_class=PlainTextResponse, include_in_schema=False)
    async def get_llms_en_txt():
        return _read_static_text(
            "llms-en.txt",
            f"""# {settings.PROJECT_NAME}

> Hospital Booking System API

Please run `python scripts/generate_llms_txt.py` to generate llms-en.txt file.
""",
        )

    @app.get("/llms-full-en.txt", response_class=PlainTextResponse, include_in_schema=False)
    async def get_llms_full_en_txt():
        return _read_static_text(
            "llms-full-en.txt",
            f"""# {settings.PROJECT_NAME}

> Hospital Booking System API - Full Version

Please run `python scripts/generate_llms_txt.py` to generate llms-full-en.txt file.
""",
        )

    # 注册所有 llms-domain-*.txt 和 llms-workflow-*.txt 文件的路由（包括英文版本）
    seen_routes = set()
    for llms_file in sorted(static_dir.glob("llms-domain-*.txt")) + sorted(static_dir.glob("llms-workflow-*.txt")) + sorted(static_dir.glob("llms-domain-en-*.txt")) + sorted(static_dir.glob("llms-workflow-en-*.txt")):
        filename = llms_file.name
        route_path = f"/{filename}"

        # 避免重复注册
        if route_path in seen_routes:
            continue
        seen_routes.add(route_path)

        def _make_handler(fname: str):
            async def handler():
                return _read_static_text(fname, f"文件 {fname} 不存在，请运行 `python scripts/generate_llms_txt.py` 生成。")
            return handler

        app.add_api_route(
            route_path,
            _make_handler(filename),
            response_class=PlainTextResponse,
            include_in_schema=False,
        )

    # 注册语义描述文件路由
    @app.get("/llms-semantic.md", response_class=PlainTextResponse, include_in_schema=False)
    async def get_llms_semantic():
        return _read_static_text(
            "llms-semantic.md",
            "# Semantic Description\n\nPlease create llms-semantic.md file.",
        )

    @app.get("/llms-semantic-cn.md", response_class=PlainTextResponse, include_in_schema=False)
    async def get_llms_semantic_cn():
        return _read_static_text(
            "llms-semantic-cn.md",
            "# 语义描述\n\n请创建 llms-semantic-cn.md 文件。",
        )


app = create_app()
