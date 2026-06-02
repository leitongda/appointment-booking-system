"""MiniappPublisher 单元测试

覆盖小程序代码上传、提审、审核查询、发布、回滚、预览码获取等操作。
mock WechatTokenManager 和 httpx.AsyncClient，无外部依赖。
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch, mock_open

import httpx
import pytest

from app.infrastructure.wechat.miniapp_publisher import MiniappPublisher


# ==================== Fixtures ====================


@pytest.fixture
def publisher():
    """创建 MiniappPublisher 实例"""
    return MiniappPublisher(app_id="wx_test_appid", app_secret="wx_test_secret")


@pytest.fixture
def mock_token():
    """mock WechatTokenManager.get_access_token 返回固定 token"""
    with patch(
        "app.infrastructure.wechat.miniapp_publisher.WechatTokenManager.get_access_token",
        new_callable=AsyncMock,
        return_value="mock_access_token_123",
    ) as m:
        yield m


def _make_response(json_data=None, content=b"", status_code=200, content_type="application/json"):
    """构造 httpx.Response 的 mock 对象"""
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.json.return_value = json_data or {}
    resp.content = content
    resp.text = str(json_data) if json_data else ""
    resp.headers = {"content-type": content_type}
    return resp


# ==================== 1. 代码上传 ====================


class TestUploadCode:
    """upload_code 测试"""

    @pytest.mark.asyncio
    async def test_upload_code_success(self, publisher):
        """上传成功"""
        mock_process = AsyncMock()
        mock_process.communicate.return_value = (b"Upload success\n", b"")
        mock_process.returncode = 0

        with patch("asyncio.create_subprocess_exec", return_value=mock_process), \
             patch("os.path.isdir", return_value=True), \
             patch("os.path.isfile", return_value=True):
            result = await publisher.upload_code(
                project_path="/tmp/project",
                version="1.0.0",
                desc="test release",
            )

        assert result["success"] is True
        assert "Upload success" in result["output"]
        assert result["error"] is None

    @pytest.mark.asyncio
    async def test_upload_code_dir_not_found(self, publisher):
        """项目目录不存在"""
        with patch("os.path.isdir", return_value=False):
            result = await publisher.upload_code(
                project_path="/nonexistent/path",
                version="1.0.0",
                desc="test",
            )

        assert result["success"] is False
        assert "项目目录不存在" in result["error"]

    @pytest.mark.asyncio
    async def test_upload_code_config_not_found(self, publisher):
        """project.config.json 不存在"""
        with patch("os.path.isdir", return_value=True), \
             patch("os.path.isfile", return_value=False):
            result = await publisher.upload_code(
                project_path="/tmp/project",
                version="1.0.0",
                desc="test",
            )

        assert result["success"] is False
        assert "project.config.json 不存在" in result["error"]

    @pytest.mark.asyncio
    async def test_upload_code_nonzero_exit(self, publisher):
        """上传进程返回非零退出码"""
        mock_process = AsyncMock()
        mock_process.communicate.return_value = (b"", b"upload failed: network error")
        mock_process.returncode = 1

        with patch("asyncio.create_subprocess_exec", return_value=mock_process), \
             patch("os.path.isdir", return_value=True), \
             patch("os.path.isfile", return_value=True):
            result = await publisher.upload_code(
                project_path="/tmp/project",
                version="1.0.0",
                desc="test",
            )

        assert result["success"] is False
        assert "network error" in result["error"]

    @pytest.mark.asyncio
    async def test_upload_code_timeout(self, publisher):
        """上传超时"""
        mock_process = AsyncMock()
        mock_process.communicate.side_effect = asyncio.TimeoutError()
        mock_process.kill = MagicMock()

        with patch("asyncio.create_subprocess_exec", return_value=mock_process), \
             patch("os.path.isdir", return_value=True), \
             patch("os.path.isfile", return_value=True):
            result = await publisher.upload_code(
                project_path="/tmp/project",
                version="1.0.0",
                desc="test",
            )

        assert result["success"] is False
        assert "超时" in result["error"]
        mock_process.kill.assert_called_once()

    @pytest.mark.asyncio
    async def test_upload_code_ci_not_installed(self, publisher):
        """miniprogram-ci 未安装"""
        with patch("asyncio.create_subprocess_exec", side_effect=FileNotFoundError), \
             patch("os.path.isdir", return_value=True), \
             patch("os.path.isfile", return_value=True):
            result = await publisher.upload_code(
                project_path="/tmp/project",
                version="1.0.0",
                desc="test",
            )

        assert result["success"] is False
        assert "miniprogram-ci 未安装" in result["error"]

    @pytest.mark.asyncio
    async def test_upload_code_custom_appid(self, publisher):
        """使用自定义 appid"""
        mock_process = AsyncMock()
        mock_process.communicate.return_value = (b"ok", b"")
        mock_process.returncode = 0

        with patch("asyncio.create_subprocess_exec", return_value=mock_process) as mock_exec, \
             patch("os.path.isdir", return_value=True), \
             patch("os.path.isfile", return_value=True):
            await publisher.upload_code(
                project_path="/tmp/project",
                version="2.0.0",
                desc="test",
                appid="wx_custom_id",
            )

        # 验证命令中使用了自定义 appid
        call_args = mock_exec.call_args[0]
        assert "wx_custom_id" in call_args


# ==================== 2. 提交审核 ====================


class TestSubmitAudit:
    """submit_audit 测试"""

    @pytest.mark.asyncio
    async def test_submit_audit_success(self, publisher, mock_token):
        """提审成功"""
        resp = _make_response(json_data={"errcode": 0, "errmsg": "ok", "auditid": 12345})

        with patch("httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.post.return_value = resp
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = instance

            result = await publisher.submit_audit()

        assert result["errcode"] == 0
        assert result["auditid"] == 12345
        mock_token.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_submit_audit_with_token(self, publisher):
        """传入 access_token 时不调用 token manager"""
        resp = _make_response(json_data={"errcode": 0, "errmsg": "ok"})

        with patch("httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.post.return_value = resp
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = instance

            result = await publisher.submit_audit(access_token="my_token")

        assert result["errcode"] == 0
        # 验证传入的 token 参数
        _, kwargs = instance.post.call_args
        assert kwargs["params"]["access_token"] == "my_token"


# ==================== 3. 查询审核状态 ====================


class TestGetAuditStatus:
    """get_audit_status 测试"""

    @pytest.mark.asyncio
    async def test_get_audit_status_success(self, publisher, mock_token):
        """查询成功 - 审核通过"""
        resp = _make_response(json_data={
            "errcode": 0,
            "errmsg": "ok",
            "status": 0,
            "auditid": 12345,
        })

        with patch("httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.post.return_value = resp
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = instance

            result = await publisher.get_audit_status(auditid=12345)

        assert result["errcode"] == 0
        assert result["status"] == 0

    @pytest.mark.asyncio
    async def test_get_audit_status_rejected(self, publisher, mock_token):
        """查询成功 - 审核被拒"""
        resp = _make_response(json_data={
            "errcode": 0,
            "errmsg": "ok",
            "status": 1,
            "reason": "页面内容不合规",
        })

        with patch("httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.post.return_value = resp
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = instance

            result = await publisher.get_audit_status(auditid=12345)

        assert result["status"] == 1
        assert result["reason"] == "页面内容不合规"

    @pytest.mark.asyncio
    async def test_get_audit_status_pending(self, publisher, mock_token):
        """查询成功 - 审核中"""
        resp = _make_response(json_data={
            "errcode": 0,
            "errmsg": "ok",
            "status": 2,
        })

        with patch("httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.post.return_value = resp
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = instance

            result = await publisher.get_audit_status(auditid=99999)

        assert result["status"] == 2


# ==================== 4. 发布 ====================


class TestRelease:
    """release 测试"""

    @pytest.mark.asyncio
    async def test_release_success(self, publisher, mock_token):
        """发布成功"""
        resp = _make_response(json_data={"errcode": 0, "errmsg": "ok"})

        with patch("httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.post.return_value = resp
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = instance

            result = await publisher.release()

        assert result["errcode"] == 0

    @pytest.mark.asyncio
    async def test_release_with_token(self, publisher):
        """传入 access_token 时不调用 token manager"""
        resp = _make_response(json_data={"errcode": 0, "errmsg": "ok"})

        with patch("httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.post.return_value = resp
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = instance

            result = await publisher.release(access_token="direct_token")

        assert result["errcode"] == 0
        _, kwargs = instance.post.call_args
        assert kwargs["params"]["access_token"] == "direct_token"


# ==================== 5. 预览二维码 ====================


class TestGetPreviewQrcode:
    """get_preview_qrcode 测试"""

    @pytest.mark.asyncio
    async def test_get_preview_qrcode_success(self, publisher, mock_token):
        """获取二维码成功"""
        fake_png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
        resp = _make_response(content=fake_png, content_type="image/png")

        with patch("httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.get.return_value = resp
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = instance

            result = await publisher.get_preview_qrcode()

        assert isinstance(result, bytes)
        assert result == fake_png

    @pytest.mark.asyncio
    async def test_get_preview_qrcode_with_page_path(self, publisher, mock_token):
        """带 page_path 参数"""
        fake_png = b"\x89PNG" + b"\x00" * 50
        resp = _make_response(content=fake_png, content_type="image/png")

        with patch("httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.get.return_value = resp
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = instance

            result = await publisher.get_preview_qrcode(page_path="pages/index/index")

        assert result == fake_png
        _, kwargs = instance.get.call_args
        assert kwargs["params"]["path"] == "pages/index/index"

    @pytest.mark.asyncio
    async def test_get_preview_qrcode_api_error(self, publisher, mock_token):
        """API 返回 JSON 错误"""
        resp = _make_response(
            json_data={"errcode": 40001, "errmsg": "invalid credential"},
            content_type="application/json",
        )

        with patch("httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.get.return_value = resp
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = instance

            with pytest.raises(RuntimeError, match="获取体验版二维码失败"):
                await publisher.get_preview_qrcode()

    @pytest.mark.asyncio
    async def test_get_preview_qrcode_http_error(self, publisher, mock_token):
        """非 200 状态码"""
        resp = _make_response(status_code=404, content_type="image/png", content=b"")

        with patch("httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.get.return_value = resp
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = instance

            with pytest.raises(RuntimeError, match="HTTP 404"):
                await publisher.get_preview_qrcode()


# ==================== 6. 回滚 ====================


class TestRollback:
    """rollback 测试"""

    @pytest.mark.asyncio
    async def test_rollback_success(self, publisher, mock_token):
        """回滚成功"""
        resp = _make_response(json_data={"errcode": 0, "errmsg": "ok"})

        with patch("httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.post.return_value = resp
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = instance

            result = await publisher.rollback()

        assert result["errcode"] == 0

    @pytest.mark.asyncio
    async def test_rollback_with_token(self, publisher):
        """传入 access_token 时不调用 token manager"""
        resp = _make_response(json_data={"errcode": 0, "errmsg": "ok"})

        with patch("httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.post.return_value = resp
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = instance

            result = await publisher.rollback(access_token="direct_token")

        assert result["errcode"] == 0
        _, kwargs = instance.post.call_args
        assert kwargs["params"]["access_token"] == "direct_token"


# ==================== 7. Token 错误 ====================


class TestTokenError:
    """token 获取失败场景"""

    @pytest.mark.asyncio
    async def test_submit_audit_token_error(self, publisher):
        """token 获取失败时 submit_audit 传播异常"""
        with patch(
            "app.infrastructure.wechat.miniapp_publisher.WechatTokenManager.get_access_token",
            new_callable=AsyncMock,
            side_effect=Exception("Redis 连接失败"),
        ):
            with pytest.raises(Exception, match="Redis 连接失败"):
                await publisher.submit_audit()

    @pytest.mark.asyncio
    async def test_get_audit_status_token_error(self, publisher):
        """token 获取失败时 get_audit_status 传播异常"""
        with patch(
            "app.infrastructure.wechat.miniapp_publisher.WechatTokenManager.get_access_token",
            new_callable=AsyncMock,
            side_effect=Exception("token expired"),
        ):
            with pytest.raises(Exception, match="token expired"):
                await publisher.get_audit_status(auditid=12345)

    @pytest.mark.asyncio
    async def test_release_token_error(self, publisher):
        """token 获取失败时 release 传播异常"""
        with patch(
            "app.infrastructure.wechat.miniapp_publisher.WechatTokenManager.get_access_token",
            new_callable=AsyncMock,
            side_effect=Exception("token expired"),
        ):
            with pytest.raises(Exception, match="token expired"):
                await publisher.release()

    @pytest.mark.asyncio
    async def test_rollback_token_error(self, publisher):
        """token 获取失败时 rollback 传播异常"""
        with patch(
            "app.infrastructure.wechat.miniapp_publisher.WechatTokenManager.get_access_token",
            new_callable=AsyncMock,
            side_effect=Exception("token expired"),
        ):
            with pytest.raises(Exception, match="token expired"):
                await publisher.rollback()

    @pytest.mark.asyncio
    async def test_get_preview_qrcode_token_error(self, publisher):
        """token 获取失败时 get_preview_qrcode 传播异常"""
        with patch(
            "app.infrastructure.wechat.miniapp_publisher.WechatTokenManager.get_access_token",
            new_callable=AsyncMock,
            side_effect=Exception("token expired"),
        ):
            with pytest.raises(Exception, match="token expired"):
                await publisher.get_preview_qrcode()


# ==================== 8. 微信 API 错误响应 ====================


class TestApiErrorResponse:
    """微信 API 返回 errcode != 0 的错误场景"""

    @pytest.mark.asyncio
    async def test_submit_audit_errcode_not_zero(self, publisher, mock_token):
        """提审失败 - errcode 不为 0"""
        resp = _make_response(json_data={
            "errcode": 87013,
            "errmsg": "resp data format error hint",
        })

        with patch("httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.post.return_value = resp
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = instance

            result = await publisher.submit_audit()

        assert result["errcode"] == 87013
        assert "resp data format error" in result["errmsg"]

    @pytest.mark.asyncio
    async def test_get_audit_status_errcode_not_zero(self, publisher, mock_token):
        """查询审核状态失败"""
        resp = _make_response(json_data={
            "errcode": 87014,
            "errmsg": "audit id not found",
        })

        with patch("httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.post.return_value = resp
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = instance

            result = await publisher.get_audit_status(auditid=99999)

        assert result["errcode"] == 87014

    @pytest.mark.asyncio
    async def test_release_errcode_not_zero(self, publisher, mock_token):
        """发布失败"""
        resp = _make_response(json_data={
            "errcode": 87015,
            "errmsg": "release fail, please audit first",
        })

        with patch("httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.post.return_value = resp
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = instance

            result = await publisher.release()

        assert result["errcode"] == 87015

    @pytest.mark.asyncio
    async def test_rollback_errcode_not_zero(self, publisher, mock_token):
        """回滚失败"""
        resp = _make_response(json_data={
            "errcode": 87016,
            "errmsg": "revert code release fail",
        })

        with patch("httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.post.return_value = resp
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = instance

            result = await publisher.rollback()

        assert result["errcode"] == 87016

    @pytest.mark.asyncio
    async def test_invalid_token_response(self, publisher, mock_token):
        """token 无效导致微信返回 40001"""
        resp = _make_response(json_data={
            "errcode": 40001,
            "errmsg": "invalid credential, access_token is invalid or not expired",
        })

        with patch("httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.post.return_value = resp
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = instance

            result = await publisher.submit_audit()

        assert result["errcode"] == 40001
        assert "invalid" in result["errmsg"]
