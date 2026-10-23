"""医生海报小程序码接口单元测试（内存 SQLite）

覆盖 GET /api/v1/marketing/poster-qrcode：
- 未配置小程序实例返回 404
- 实例 app_secret_ref 解析失败（变量缺失/格式不识别）视为未配置返回 404
- 配置实例（secret_ref 指向测试注入的环境变量）且 mock publisher 返回 b'png' 时，
  接口返回 base64 且 data.image 可解码
- scene 超过 32 字符时 publisher 提前抛错（不发起 HTTP）
- 未登录拒绝（401）

不真实调用微信 API（publisher 方法被 monkeypatch）。
"""
import base64
from uuid import uuid4

import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.infrastructure.wechat.miniapp_publisher import MiniappPublisher
from app.models.miniapp_platform import AppTemplate, MiniappInstance
from app.models.tenant import Tenant

# 测试专用环境变量名（secret_ref 指向它，由 monkeypatch 注入）
TEST_SECRET_ENV_VAR = "TEST_POSTER_WX_APP_SECRET"


async def _seed_template(db_session: AsyncSession) -> AppTemplate:
    """创建小程序模板（MiniappInstance.template_id 非空）"""
    template = AppTemplate(
        id=str(uuid4()),
        code=f"tpl-{uuid4().hex[:8]}",
        name="测试模板",
        status=1,
    )
    db_session.add(template)
    await db_session.commit()
    return template


async def _seed_instance(
    db_session: AsyncSession,
    tenant: Tenant,
    template: AppTemplate,
    app_secret_ref: str | None,
) -> MiniappInstance:
    """为租户创建一个启用的 MiniappInstance"""
    instance = MiniappInstance(
        id=str(uuid4()),
        tenant_id=tenant.id,
        template_id=template.id,
        name="测试小程序实例",
        app_id=f"wx-test-{uuid4().hex[:8]}",
        app_secret_ref=app_secret_ref,
        status=1,
    )
    db_session.add(instance)
    await db_session.commit()
    return instance


def _auth_headers(tenant: Tenant, token: str | None) -> dict:
    headers = {"X-Tenant-ID": tenant.id}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


@pytest.mark.asyncio
class TestPosterQrcodeApi:
    """患者端医生海报小程序码接口"""

    async def test_not_configured_instance_returns_404(
        self,
        async_client: AsyncClient,
        test_tenant: Tenant,
        test_user,
    ):
        """租户下没有任何启用实例时返回 404"""
        token = create_access_token({"sub": test_user.id, "type": "user"})
        resp = await async_client.get(
            "/api/v1/marketing/poster-qrcode?scene=doctor-123",
            headers=_auth_headers(test_tenant, token),
        )
        assert resp.status_code == status.HTTP_404_NOT_FOUND
        assert resp.json()["message"] == "小程序未配置，无法生成小程序码"

    async def test_unresolvable_secret_ref_returns_404(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        test_tenant: Tenant,
        test_user,
    ):
        """实例存在但 secret_ref 无法解析（变量缺失 / 格式不识别）时同样返回 404"""
        template = await _seed_template(db_session)
        await _seed_instance(db_session, test_tenant, template, app_secret_ref="env:DEFINITELY_NOT_SET_VAR_XYZ")
        # 格式不识别（非 env: 前缀）也视为未配置
        await _seed_instance(db_session, test_tenant, template, app_secret_ref="raw-plaintext-secret")

        token = create_access_token({"sub": test_user.id, "type": "user"})
        resp = await async_client.get(
            "/api/v1/marketing/poster-qrcode?scene=doctor-123",
            headers=_auth_headers(test_tenant, token),
        )
        assert resp.status_code == status.HTTP_404_NOT_FOUND
        assert resp.json()["message"] == "小程序未配置，无法生成小程序码"

    async def test_returns_base64_image(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        test_tenant: Tenant,
        test_user,
        monkeypatch,
    ):
        """配置实例 + 环境变量 Secret + mock publisher 返回 b'png' → 接口返回可解码 base64"""
        template = await _seed_template(db_session)
        await _seed_instance(
            db_session, test_tenant, template, app_secret_ref=f"env:{TEST_SECRET_ENV_VAR}"
        )
        monkeypatch.setenv(TEST_SECRET_ENV_VAR, "test-secret-value")

        captured: dict = {}

        async def fake_get_unlimited_wxacode(self, scene, page=None, access_token=None):
            captured["scene"] = scene
            captured["page"] = page
            captured["app_id"] = self.app_id
            captured["app_secret"] = self.app_secret
            return b"png"

        monkeypatch.setattr(MiniappPublisher, "get_unlimited_wxacode", fake_get_unlimited_wxacode)

        token = create_access_token({"sub": test_user.id, "type": "user"})
        resp = await async_client.get(
            "/api/v1/marketing/poster-qrcode?scene=doctor-123&page=pages/doctor/detail",
            headers=_auth_headers(test_tenant, token),
        )
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()["data"]
        # data.image 是 PNG 二进制的 base64 字符串，且可解码还原
        assert base64.b64decode(data["image"]) == b"png"
        # 透传给 publisher 的参数正确（未真实调用微信 API）
        assert captured["scene"] == "doctor-123"
        assert captured["page"] == "pages/doctor/detail"
        assert captured["app_id"].startswith("wx-test-")
        assert captured["app_secret"] == "test-secret-value"

    async def test_scene_over_32_chars_raises_before_http(self):
        """scene 超过 32 字符时 publisher 提前抛 ValueError，不发起 HTTP"""
        publisher = MiniappPublisher(app_id="wx-test", app_secret="secret")
        with pytest.raises(ValueError):
            await publisher.get_unlimited_wxacode(scene="a" * 33)

    async def test_requires_login(
        self,
        async_client: AsyncClient,
        test_tenant: Tenant,
    ):
        """未携带登录态返回 401"""
        resp = await async_client.get(
            "/api/v1/marketing/poster-qrcode?scene=doctor-123",
            headers=_auth_headers(test_tenant, None),
        )
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED
