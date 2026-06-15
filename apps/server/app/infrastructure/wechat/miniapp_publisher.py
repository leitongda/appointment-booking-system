"""微信小程序代码管理与发布客户端

封装小程序代码上传、审核、发布、回滚等操作。
使用 miniprogram-ci CLI 进行代码上传，httpx 调用微信管理端 API。
"""

import asyncio
import logging
import os

import httpx

from app.infrastructure.wechat.token_manager import WechatTokenManager

logger = logging.getLogger(__name__)


class MiniappPublisher:
    """微信小程序代码发布管理器

    封装微信小程序的代码上传、提交审核、发布、回滚、
    二维码预览等管理端 API 操作。
    """

    WECHAT_API_URL = "https://api.weixin.qq.com"
    # miniprogram-ci 上传超时（秒）
    UPLOAD_TIMEOUT = 300

    def __init__(self, app_id: str, app_secret: str) -> None:
        """初始化发布管理器

        Args:
            app_id: 小程序 AppID
            app_secret: 小程序 AppSecret
        """
        self.app_id = app_id
        self.app_secret = app_secret
        self._token_manager = WechatTokenManager

    async def _get_access_token(self) -> str:
        """获取当前小程序的 access_token"""
        return await self._token_manager.get_access_token(
            app_id=self.app_id,
            app_secret=self.app_secret,
        )

    # ------------------------------------------------------------------
    # 1. 代码上传（通过 miniprogram-ci CLI）
    # ------------------------------------------------------------------

    async def upload_code(
        self,
        project_path: str,
        version: str,
        desc: str,
        appid: str | None = None,
    ) -> dict:
        """通过 miniprogram-ci 上传小程序代码包

        前置条件: 需要安装 miniprogram-ci (npm i -g miniprogram-ci)，
        并配置小程序代码目录下的 project.config.json 或通过私钥文件认证。

        Args:
            project_path: 小程序代码目录路径（包含 project.config.json）
            version: 版本号，如 "1.0.0"
            desc: 版本描述
            appid: AppID（可选，默认使用实例 app_id）

        Returns:
            dict: {"success": bool, "output": str, "error": str | None}
        """
        effective_appid = appid or self.app_id
        logger.info(
            "[MiniappPublisher] 开始上传代码: appid=%s, version=%s, path=%s",
            effective_appid,
            version,
            project_path,
        )

        # 检查项目目录是否存在
        if not os.path.isdir(project_path):
            msg = f"项目目录不存在: {project_path}"
            logger.error("[MiniappPublisher] %s", msg)
            return {"success": False, "output": "", "error": msg}

        # 检查 project.config.json 是否存在
        config_path = os.path.join(project_path, "project.config.json")
        if not os.path.isfile(config_path):
            msg = f"project.config.json 不存在: {config_path}"
            logger.error("[MiniappPublisher] %s", msg)
            return {"success": False, "output": "", "error": msg}

        # 构造 miniprogram-ci 命令
        # miniprogram-ci upload --appid <appid> --pkgnma <path> --ver <version> --desc <desc>
        cmd = [
            "npx",
            "miniprogram-ci",
            "upload",
            "--appid",
            effective_appid,
            "--pkgnma",
            project_path,
            "--ver",
            version,
            "--desc",
            desc,
        ]

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=self.UPLOAD_TIMEOUT,
            )

            stdout_text = stdout.decode("utf-8", errors="replace") if stdout else ""
            stderr_text = stderr.decode("utf-8", errors="replace") if stderr else ""

            if process.returncode != 0:
                error_msg = stderr_text or stdout_text or f"进程退出码: {process.returncode}"
                logger.error(
                    "[MiniappPublisher] 代码上传失败: returncode=%s, stderr=%s",
                    process.returncode,
                    error_msg,
                )
                return {"success": False, "output": stdout_text, "error": error_msg}

            logger.info("[MiniappPublisher] 代码上传成功: version=%s", version)
            return {"success": True, "output": stdout_text, "error": None}

        except TimeoutError:
            msg = f"代码上传超时 ({self.UPLOAD_TIMEOUT}s)"
            logger.error("[MiniappPublisher] %s", msg)
            try:
                process.kill()
            except Exception:
                pass
            return {"success": False, "output": "", "error": msg}

        except FileNotFoundError:
            msg = "miniprogram-ci 未安装，请执行: npm i -g miniprogram-ci"
            logger.error("[MiniappPublisher] %s", msg)
            return {"success": False, "output": "", "error": msg}

    # ------------------------------------------------------------------
    # 2. 提交审核
    # ------------------------------------------------------------------

    async def submit_audit(
        self,
        access_token: str | None = None,
    ) -> dict:
        """提交小程序代码审核

        POST https://api.weixin.qq.com/wxa/submit_audit

        Args:
            access_token: 微信 access_token（可选，不传则自动获取）

        Returns:
            dict: 微信接口返回的完整响应体
        """
        token = access_token or await self._get_access_token()
        url = f"{self.WECHAT_API_URL}/wxa/submit_audit"

        async with httpx.AsyncClient(timeout=10.0, trust_env=False) as client:
            response = await client.post(
                url,
                params={"access_token": token},
                json={},
            )
            data = response.json()

        if data.get("errcode") != 0:
            logger.error(
                "[MiniappPublisher] 提交审核失败: errcode=%s, errmsg=%s",
                data.get("errcode"),
                data.get("errmsg"),
            )

        logger.info("[MiniappPublisher] submit_audit 结果: %s", data)
        return data

    # ------------------------------------------------------------------
    # 3. 查询审核状态
    # ------------------------------------------------------------------

    async def get_audit_status(
        self,
        auditid: int,
        access_token: str | None = None,
    ) -> dict:
        """查询指定审核单的审核状态

        POST https://api.weixin.qq.com/wxa/get_auditstatus

        Args:
            auditid: 审核单 ID（由 submit_audit 返回）
            access_token: 微信 access_token（可选，不传则自动获取）

        Returns:
            dict: 微信接口返回的完整响应体
                - auditid: 审核单 ID
                - status: 审核状态 (0=审核成功, 1=审核被拒绝, 2=审核中, 3=已撤回)
                - reason: 拒绝原因（如有）
                - ScreenShot: 截图（如有）
        """
        token = access_token or await self._get_access_token()
        url = f"{self.WECHAT_API_URL}/wxa/get_auditstatus"

        payload = {"auditid": auditid}

        async with httpx.AsyncClient(timeout=10.0, trust_env=False) as client:
            response = await client.post(
                url,
                params={"access_token": token},
                json=payload,
            )
            data = response.json()

        if data.get("errcode") != 0:
            logger.error(
                "[MiniappPublisher] 查询审核状态失败: errcode=%s, errmsg=%s",
                data.get("errcode"),
                data.get("errmsg"),
            )

        logger.info(
            "[MiniappPublisher] get_audit_status: auditid=%s, status=%s",
            auditid,
            data.get("status"),
        )
        return data

    # ------------------------------------------------------------------
    # 4. 发布已通过审核的代码
    # ------------------------------------------------------------------

    async def release(
        self,
        access_token: str | None = None,
    ) -> dict:
        """发布已审核通过的小程序代码

        POST https://api.weixin.qq.com/wxa/release

        Args:
            access_token: 微信 access_token（可选，不传则自动获取）

        Returns:
            dict: 微信接口返回的完整响应体
        """
        token = access_token or await self._get_access_token()
        url = f"{self.WECHAT_API_URL}/wxa/release"

        async with httpx.AsyncClient(timeout=10.0, trust_env=False) as client:
            response = await client.post(
                url,
                params={"access_token": token},
            )
            data = response.json()

        if data.get("errcode") != 0:
            logger.error(
                "[MiniappPublisher] 发布失败: errcode=%s, errmsg=%s",
                data.get("errcode"),
                data.get("errmsg"),
            )
        else:
            logger.info("[MiniappPublisher] 小程序发布成功")

        return data

    # ------------------------------------------------------------------
    # 5. 版本回滚
    # ------------------------------------------------------------------

    async def rollback(
        self,
        access_token: str | None = None,
    ) -> dict:
        """回滚小程序到上一个已发布的版本

        POST https://api.weixin.qq.com/wxa/revertcoderelease

        Args:
            access_token: 微信 access_token（可选，不传则自动获取）

        Returns:
            dict: 微信接口返回的完整响应体
        """
        token = access_token or await self._get_access_token()
        url = f"{self.WECHAT_API_URL}/wxa/revertcoderelease"

        async with httpx.AsyncClient(timeout=10.0, trust_env=False) as client:
            response = await client.post(
                url,
                params={"access_token": token},
            )
            data = response.json()

        if data.get("errcode") != 0:
            logger.error(
                "[MiniappPublisher] 版本回滚失败: errcode=%s, errmsg=%s",
                data.get("errcode"),
                data.get("errmsg"),
            )
        else:
            logger.info("[MiniappPublisher] 小程序版本回滚成功")

        return data

    # ------------------------------------------------------------------
    # 6. 获取体验版二维码
    # ------------------------------------------------------------------

    async def get_preview_qrcode(
        self,
        page_path: str | None = None,
        access_token: str | None = None,
    ) -> bytes:
        """获取小程序体验版二维码（预览二维码）

        GET https://api.weixin.qq.com/wxa/get_qrcode

        此接口返回的是 PNG 二维码图片的二进制数据。

        Args:
            page_path: 二维码携带的页面路径（可选），如 "pages/index/index"
            access_token: 微信 access_token（可选，不传则自动获取）

        Returns:
            bytes: 二维码 PNG 图片二进制数据

        Raises:
            RuntimeError: 获取二维码失败时抛出
        """
        token = access_token or await self._get_access_token()
        url = f"{self.WECHAT_API_URL}/wxa/get_qrcode"

        params = {"access_token": token}
        if page_path:
            params["path"] = page_path

        async with httpx.AsyncClient(timeout=30.0, trust_env=False) as client:
            response = await client.get(url, params=params)

        # 正常情况下返回图片二进制，失败时返回 JSON 错误
        content_type = response.headers.get("content-type", "")

        if "application/json" in content_type or "text/plain" in content_type:
            # 尝试解析为 JSON 错误
            try:
                error_data = response.json()
                raise RuntimeError(
                    f"获取体验版二维码失败: errcode={error_data.get('errcode')}, "
                    f"errmsg={error_data.get('errmsg')}"
                )
            except (ValueError, KeyError):
                raise RuntimeError(
                    f"获取体验版二维码失败: HTTP {response.status_code}, "
                    f"body={response.text[:500]}"
                )

        if response.status_code != 200:
            raise RuntimeError(
                f"获取体验版二维码失败: HTTP {response.status_code}"
            )

        logger.info(
            "[MiniappPublisher] 获取体验版二维码成功: %d bytes", len(response.content)
        )
        return response.content
