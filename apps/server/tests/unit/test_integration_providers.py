"""第三方平台 Provider 单元测试。

验证三个 Provider（Dingtalk/Wecom/Feishu）的核心 HTTP 调用逻辑：
- access_token 获取（成功/失败/配置缺失）
- 工作消息发送（成功/缺 agent_id/失败）
- 群机器人消息（加签算法/发送）
- OAuth code 换用户信息

HTTP 调用通过 mock httpx.AsyncClient 隔离，不依赖真实网络。
"""
import base64
import hashlib
import hmac
import time
import urllib.parse
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.infrastructure.integrations.dingtalk.provider import DingtalkProvider
from app.infrastructure.integrations.feishu.provider import FeishuProvider
from app.infrastructure.integrations.wecom.provider import WecomProvider
from app.models.integration import Integration


# ============================================================
# 测试辅助：构造 Integration 对象 + mock httpx
# ============================================================

def make_integration(
    provider: str = "dingtalk",
    app_id: str | None = "test_app_id",
    app_secret_ref: str | None = "env:TEST_SECRET",
    webhook_url: str | None = None,
    webhook_secret_ref: str | None = None,
    extra_config: dict | None = None,
) -> Integration:
    """构造测试用 Integration 对象（不落库）。"""
    return Integration(
        id=str(uuid4()),
        tenant_id="test-tenant",
        provider=provider,
        name="测试集成",
        app_id=app_id,
        app_secret_ref=app_secret_ref,
        webhook_url=webhook_url,
        webhook_secret_ref=webhook_secret_ref,
        extra_config=extra_config,
        status=1,
    )


class MockHttpResponse:
    """模拟 httpx.Response。"""

    def __init__(self, json_data: dict, status_code: int = 200):
        self._json = json_data
        self.status_code = status_code
        self.text = str(json_data)

    def json(self):
        return self._json


class MockAsyncClient:
    """模拟 httpx.AsyncClient，按 URL 模式返回预设响应。

    用法:
        with patch_httpx({"gettoken": MockHttpResponse({"access_token": "xxx", "errcode": 0})}):
            token = await provider._fetch_access_token(integration)
    """

    def __init__(self, responses: dict[str, MockHttpResponse] | None = None):
        self._responses = responses or {}
        self.requests: list[dict] = []  # 记录所有请求用于断言

    def _match(self, url: str) -> MockHttpResponse | None:
        for pattern, resp in self._responses.items():
            if pattern in url:
                return resp
        return MockHttpResponse({"errcode": -1, "errmsg": "no mock"})

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None

    async def get(self, url, **kwargs):
        self.requests.append({"method": "GET", "url": url, **kwargs})
        return self._match(url)

    async def post(self, url, **kwargs):
        self.requests.append({"method": "POST", "url": url, **kwargs})
        return self._match(url)


def patch_httpx(responses: dict[str, MockHttpResponse]):
    """patch httpx.AsyncClient，返回 MockAsyncClient。"""
    mock_client = MockAsyncClient(responses)
    return patch(
        "app.infrastructure.integrations.dingtalk.provider.httpx.AsyncClient",
        return_value=mock_client,
    ), mock_client


def patch_httpx_for(provider_module: str, responses: dict[str, MockHttpResponse]):
    """patch 指定 provider 模块的 httpx.AsyncClient，返回 context manager。

    用法:
        with patch_httpx_for(module, {"gettoken": resp}) as client:
            await provider._fetch_access_token(integration)
        # client.requests[-1] 可断言请求
    """
    mock_client = MockAsyncClient(responses)

    class HttpxPatch:
        def __init__(self):
            self._patcher = patch(f"{provider_module}.httpx.AsyncClient", return_value=mock_client)
            self.client = mock_client

        def __enter__(self):
            self._patcher.start()
            return self.client

        def __exit__(self, *args):
            self._patcher.stop()

    return HttpxPatch()


def patch_redis_token(token: str | None = None):
    """mock Redis token 缓存（避免真实 Redis 调用）。"""
    return patch(
        "app.infrastructure.integrations.base.RedisCache.get_integration_token",
        new_callable=AsyncMock,
        return_value=token,
    )


def patch_resolve_secret(secret: str = "decrypted_secret"):
    """mock secret 引用解析（patch 源头模块）。"""
    return patch(
        "app.common.secret_refs.resolve_secret_ref",
        return_value=secret,
    )


# ============================================================
# DingtalkProvider 测试
# ============================================================

class TestDingtalkProvider:
    """钉钉 Provider 测试。"""

    @pytest.fixture
    def provider(self):
        return DingtalkProvider()

    # ---- access_token ----

    async def test_fetch_access_token_success(self, provider):
        """成功获取 access_token。"""
        integration = make_integration("dingtalk", app_id="ding123")
        mock_resp = MockHttpResponse({"access_token": "token_abc", "errcode": 0})

        with patch_resolve_secret("real_secret"), \
             patch_httpx_for("app.infrastructure.integrations.dingtalk.provider", {"gettoken": mock_resp}):
            token = await provider._fetch_access_token(integration)
        assert token == "token_abc"

    async def test_fetch_access_token_missing_config(self, provider):
        """缺少 AppKey/AppSecret 时抛 ValueError。"""
        integration = make_integration("dingtalk", app_id=None, app_secret_ref=None)
        with pytest.raises(ValueError, match="配置不完整"):
            await provider._fetch_access_token(integration)

    async def test_fetch_access_token_api_error(self, provider):
        """钉钉 API 返回错误时抛 ValueError。"""
        integration = make_integration("dingtalk")
        mock_resp = MockHttpResponse({"errcode": 40001, "errmsg": "invalid appkey"})

        with patch_resolve_secret(), \
             patch_httpx_for("app.infrastructure.integrations.dingtalk.provider", {"gettoken": mock_resp}):
            with pytest.raises(ValueError, match="获取 access_token 失败"):
                await provider._fetch_access_token(integration)

    async def test_get_access_token_uses_cache(self, provider):
        """get_access_token 优先用 Redis 缓存。"""
        integration = make_integration("dingtalk", app_id="ding_cached")
        with patch_redis_token("cached_token"):
            token = await provider.get_access_token(integration)
        assert token == "cached_token"

    # ---- 工作消息 ----

    async def test_send_work_message_success(self, provider):
        """成功发送工作通知。"""
        integration = make_integration("dingtalk", extra_config={"agent_id": "999"})
        mock_resp = MockHttpResponse({"errcode": 0, "task_id": 123})

        with patch_redis_token("fake_token"), \
             patch_httpx_for("app.infrastructure.integrations.dingtalk.provider", {"asyncsend": mock_resp}) as client:
            ok = await provider.send_work_message(integration, "dt_user_1", "text", "测试消息")

        assert ok is True
        # 验证请求带了 access_token（通过 params 传递，非拼入 url）
        req = client.requests[-1]
        params = req.get("params", {})
        assert params.get("access_token") == "fake_token"

    async def test_send_work_message_no_agent_id(self, provider):
        """缺少 agent_id 时返回 False。"""
        integration = make_integration("dingtalk", extra_config={})
        with patch_redis_token("fake_token"):
            ok = await provider.send_work_message(integration, "dt_user_1", "text", "msg")
        assert ok is False

    async def test_send_work_message_api_failure(self, provider):
        """API 返回错误时返回 False。"""
        integration = make_integration("dingtalk", extra_config={"agent_id": "999"})
        mock_resp = MockHttpResponse({"errcode": 40001, "errmsg": "token失效"})

        with patch_redis_token("bad_token"), \
             patch_httpx_for("app.infrastructure.integrations.dingtalk.provider", {"asyncsend": mock_resp}):
            ok = await provider.send_work_message(integration, "dt_user_1", "text", "msg")
        assert ok is False

    # ---- 群机器人加签算法（纯函数，无需 mock HTTP）----

    def test_sign_webhook_url_without_secret(self, provider):
        """无 secret 时 URL 不变。"""
        url = "https://oapi.dingtalk.com/robot/send?access_token=xxx"
        signed = provider._sign_webhook_url(url, None)
        assert signed == url

    def test_sign_webhook_url_with_secret(self, provider):
        """有 secret 时追加 timestamp + sign 参数。"""
        url = "https://oapi.dingtalk.com/robot/send?access_token=xxx"
        secret = "SEC123456"
        signed = provider._sign_webhook_url(url, secret)
        # 应包含 timestamp 和 sign 参数
        assert "timestamp=" in signed
        assert "sign=" in signed
        # 验证签名算法正确性：parse_qs 自动 URL 解码，故 expected 用解码后的 base64
        parsed = urllib.parse.parse_qs(urllib.parse.urlparse(signed).query)
        timestamp = parsed["timestamp"][0]
        sign = parsed["sign"][0]
        # 复现算法验证（不编码，与 parse_qs 解码结果对齐）
        string_to_sign = f"{timestamp}\n{secret}"
        expected = base64.b64encode(
            hmac.new(secret.encode(), string_to_sign.encode(), hashlib.sha256).digest()
        ).decode()
        assert sign == expected

    async def test_send_robot_message_success(self, provider):
        """群机器人发送成功。"""
        mock_resp = MockHttpResponse({"errcode": 0})
        with patch_httpx_for("app.infrastructure.integrations.dingtalk.provider", {"robot/send": mock_resp}) as client:
            ok = await provider.send_robot_message(
                "https://oapi.dingtalk.com/robot/send?access_token=xxx",
                secret=None,
                msg_type="text",
                content="告警通知",
            )
        assert ok is True

    # ---- OAuth ----

    async def test_get_qrcode_login_url(self, provider):
        """生成扫码授权 URL。"""
        integration = make_integration("dingtalk", app_id="ding_app")
        url = await provider.get_qrcode_login_url(integration, "https://example.com/cb", "state123")
        assert "client_id=ding_app" in url
        assert "redirect_uri" in url
        assert "state=state123" in url

    async def test_get_user_info_by_code(self, provider):
        """OAuth code 换用户信息。"""
        integration = make_integration("dingtalk", app_id="ding_app")
        token_resp = MockHttpResponse({"accessToken": "uat_123"})
        info_resp = MockHttpResponse({"openId": "dt_open_1", "unionId": "dt_union_1", "nick": "张三"})

        with patch_resolve_secret(), \
             patch_httpx_for("app.infrastructure.integrations.dingtalk.provider", {
                 "userAccessToken": token_resp,
                 "contact/users/me": info_resp,
             }):
            user_info = await provider.get_user_info_by_code(integration, "auth_code_123")

        assert user_info["external_id"] == "dt_open_1"
        assert user_info["union_id"] == "dt_union_1"
        assert user_info["name"] == "张三"


# ============================================================
# WecomProvider 测试
# ============================================================

class TestWecomProvider:
    """企业微信 Provider 测试。"""

    WECOM_MODULE = "app.infrastructure.integrations.wecom.provider"

    @pytest.fixture
    def provider(self):
        return WecomProvider()

    async def test_fetch_access_token_success(self, provider):
        integration = make_integration("wecom", app_id="ww_corp_id")
        mock_resp = MockHttpResponse({"access_token": "wecom_token", "errcode": 0})

        with patch_resolve_secret(), \
             patch_httpx_for(self.WECOM_MODULE, {"gettoken": mock_resp}):
            token = await provider._fetch_access_token(integration)
        assert token == "wecom_token"

    async def test_fetch_access_token_missing_config(self, provider):
        integration = make_integration("wecom", app_id=None, app_secret_ref=None)
        with pytest.raises(ValueError, match="配置不完整"):
            await provider._fetch_access_token(integration)

    async def test_fetch_access_token_api_error(self, provider):
        integration = make_integration("wecom")
        mock_resp = MockHttpResponse({"errcode": 40013, "errmsg": "invalid corpid"})

        with patch_resolve_secret(), \
             patch_httpx_for(self.WECOM_MODULE, {"gettoken": mock_resp}):
            with pytest.raises(ValueError, match="获取 access_token 失败"):
                await provider._fetch_access_token(integration)

    async def test_send_work_message_success(self, provider):
        integration = make_integration("wecom", extra_config={"agent_id": "1000002"})
        mock_resp = MockHttpResponse({"errcode": 0})

        with patch_redis_token("wecom_token"), \
             patch_httpx_for(self.WECOM_MODULE, {"message/send": mock_resp}) as client:
            ok = await provider.send_work_message(integration, "wecom_user", "text", "测试")

        assert ok is True
        # 企业微信 access_token 通过 params 传递
        assert client.requests[-1].get("params", {}).get("access_token") == "wecom_token"

    async def test_send_work_message_no_agent_id(self, provider):
        integration = make_integration("wecom", extra_config={})
        with patch_redis_token("token"):
            ok = await provider.send_work_message(integration, "user", "text", "msg")
        assert ok is False

    async def test_send_robot_message_success(self, provider):
        mock_resp = MockHttpResponse({"errcode": 0})
        with patch_httpx_for(self.WECOM_MODULE, {"webhook/send": mock_resp}):
            ok = await provider.send_robot_message(
                "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx",
                secret=None,
                msg_type="markdown",
                content="## 告警\n内容",
            )
        assert ok is True

    async def test_robot_appends_key_param(self, provider):
        """群机器人 secret（即 key）应追加到 URL。"""
        mock_resp = MockHttpResponse({"errcode": 0})
        with patch_httpx_for(self.WECOM_MODULE, {"webhook/send": mock_resp}) as client:
            await provider.send_robot_message(
                "https://qyapi.weixin.qq.com/cgi-bin/webhook/send",
                secret="robot_key_123",
                msg_type="text",
                content="msg",
            )
        # 验证请求 URL 包含 key 参数
        assert "key=robot_key_123" in client.requests[-1]["url"]

    async def test_get_qrcode_login_url(self, provider):
        integration = make_integration("wecom", app_id="ww_corp", extra_config={"agent_id": "1000002"})
        url = await provider.get_qrcode_login_url(integration, "https://example.com/cb", "state456")
        assert "appid=ww_corp" in url
        assert "agentid=1000002" in url
        assert "state=state456" in url

    async def test_get_user_info_by_code(self, provider):
        integration = make_integration("wecom", app_id="ww_corp")
        userinfo_resp = MockHttpResponse({"errcode": 0, "userid": "wecom_uid", "open_userid": "open_1"})
        detail_resp = MockHttpResponse({"errcode": 0, "name": "李四", "mobile": "13800001234"})

        with patch_redis_token("wecom_token"), \
             patch_httpx_for(self.WECOM_MODULE, {
                 "getuserinfo": userinfo_resp,
                 "user/get": detail_resp,
             }):
            user_info = await provider.get_user_info_by_code(integration, "code_123")

        assert user_info["external_id"] == "wecom_uid"
        assert user_info["name"] == "李四"
        assert user_info["phone"] == "13800001234"


# ============================================================
# FeishuProvider 测试
# ============================================================

class TestFeishuProvider:
    """飞书 Provider 测试。"""

    FEISHU_MODULE = "app.infrastructure.integrations.feishu.provider"

    @pytest.fixture
    def provider(self):
        return FeishuProvider()

    async def test_fetch_access_token_success(self, provider):
        """飞书 token 字段为 tenant_access_token，错误码字段为 code。"""
        integration = make_integration("feishu", app_id="cli_app_id")
        mock_resp = MockHttpResponse({"code": 0, "tenant_access_token": "feishu_token"})

        with patch_resolve_secret(), \
             patch_httpx_for(self.FEISHU_MODULE, {"tenant_access_token": mock_resp}):
            token = await provider._fetch_access_token(integration)
        assert token == "feishu_token"

    async def test_fetch_access_token_missing_config(self, provider):
        integration = make_integration("feishu", app_id=None, app_secret_ref=None)
        with pytest.raises(ValueError, match="配置不完整"):
            await provider._fetch_access_token(integration)

    async def test_fetch_access_token_api_error(self, provider):
        integration = make_integration("feishu")
        mock_resp = MockHttpResponse({"code": 99991663, "msg": "invalid app_id"})

        with patch_resolve_secret(), \
             patch_httpx_for(self.FEISHU_MODULE, {"tenant_access_token": mock_resp}):
            with pytest.raises(ValueError, match="获取 tenant_access_token 失败"):
                await provider._fetch_access_token(integration)

    async def test_send_work_message_success(self, provider):
        integration = make_integration("feishu", app_id="cli_app")
        mock_resp = MockHttpResponse({"code": 0})

        with patch_redis_token("feishu_token"), \
             patch_httpx_for(self.FEISHU_MODULE, {"im/v1/messages": mock_resp}) as client:
            ok = await provider.send_work_message(integration, "fs_open_id", "text", "飞书测试")

        assert ok is True
        # 飞书消息通过 Bearer header 认证
        headers = client.requests[-1].get("headers", {})
        assert headers.get("Authorization") == "Bearer feishu_token"

    async def test_send_work_message_api_failure(self, provider):
        integration = make_integration("feishu")
        mock_resp = MockHttpResponse({"code": 99991668, "msg": "msg too long"})

        with patch_redis_token("feishu_token"), \
             patch_httpx_for(self.FEISHU_MODULE, {"im/v1/messages": mock_resp}):
            ok = await provider.send_work_message(integration, "fs_open_id", "text", "msg")
        assert ok is False

    async def test_send_robot_message_success(self, provider):
        mock_resp = MockHttpResponse({"StatusCode": 0})
        with patch_httpx_for(self.FEISHU_MODULE, {"robot": mock_resp}):
            ok = await provider.send_robot_message(
                "https://open.feishu.cn/open-apis/bot/v2/hook/xxx",
                secret=None,
                msg_type="text",
                content="飞书群消息",
            )
        assert ok is True

    async def test_send_robot_message_with_sign(self, provider):
        """加签时应带 timestamp + sign。"""
        mock_resp = MockHttpResponse({"StatusCode": 0})
        with patch_httpx_for(self.FEISHU_MODULE, {"bot/v2/hook": mock_resp}) as client:
            await provider.send_robot_message(
                "https://open.feishu.cn/open-apis/bot/v2/hook/xxx",
                secret="fs_encrypt_key",
                msg_type="text",
                content="signed msg",
            )
        # 验证请求体含 timestamp 和 sign
        import json
        body = client.requests[-1].get("json", {})
        assert "timestamp" in body
        assert "sign" in body

    async def test_get_qrcode_login_url(self, provider):
        integration = make_integration("feishu", app_id="cli_app")
        url = await provider.get_qrcode_login_url(integration, "https://example.com/cb", "state789")
        assert "app_id=cli_app" in url
        assert "state=state789" in url

    async def test_get_user_info_by_code(self, provider):
        integration = make_integration("feishu", app_id="cli_app")
        # 飞书 OAuth 流程：先用 tenant_access_token 鉴权，再换 user_access_token，再取 user_info
        tenant_token_resp = MockHttpResponse({"code": 0, "tenant_access_token": "tenant_fs"})
        uat_resp = MockHttpResponse({"code": 0, "data": {"access_token": "uat_fs"}})
        info_resp = MockHttpResponse({
            "code": 0,
            "data": {"open_id": "fs_open_1", "union_id": "fs_union_1", "name": "王五"},
        })

        with patch_resolve_secret(), \
             patch_httpx_for(self.FEISHU_MODULE, {
                 "tenant_access_token/internal": tenant_token_resp,
                 "authen/v1/access_token": uat_resp,
                 "user_info": info_resp,
             }):
            user_info = await provider.get_user_info_by_code(integration, "code_fs")

        assert user_info["external_id"] == "fs_open_1"
        assert user_info["union_id"] == "fs_union_1"
        assert user_info["name"] == "王五"
