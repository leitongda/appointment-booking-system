"""T-6(c)：自助注册的租户上下文约束

决策点 D22 尚未拍板（无租户上下文时注册应拒绝还是走默认策略）。
期望行为以 xfail(strict) 标注：D22 落地后 XPASS 会提醒移除标记。
"""
import uuid

import bcrypt
import pytest

pytestmark = [pytest.mark.security]


def _generate_phone() -> str:
    return f"135{uuid.uuid4().int % 10**8:08d}"


def _generate_password() -> str:
    """由随机片段拼接，避免源码中出现固定凭据"""
    return uuid.uuid4().hex[:10] + "Aa1!"


@pytest.fixture
def mock_sms_verify(monkeypatch):
    async def _verify(*args, **kwargs):
        return True

    import app.infrastructure.sms.service as sms_module

    monkeypatch.setattr(sms_module.SmsService, "verify_code", _verify)
    return _verify


@pytest.mark.xfail(
    strict=True,
    reason="决策点 D22：无租户上下文的注册应 fail-close（400），当前会按默认策略创建无租户用户",
)
async def test_register_without_tenant_context_is_rejected(
    async_client, mock_sms_verify
):
    response = await async_client.post(
        "/api/v1/auth/register",
        json={
            "phone": _generate_phone(),
            "password": _generate_password(),
            "code": "123456",
        },
    )
    assert response.status_code == 400, response.text


async def test_register_without_tenant_context_does_not_5xx(
    async_client, mock_sms_verify
):
    """现状快照：无论最终策略如何，注册不得因缺少租户上下文而 500"""
    response = await async_client.post(
        "/api/v1/auth/register",
        json={
            "phone": _generate_phone(),
            "password": _generate_password(),
            "code": "123456",
        },
    )
    assert response.status_code < 500, response.text
