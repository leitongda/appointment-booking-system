"""第三方集成通知渠道测试。

验证 BaseIntegrationChannel 的核心逻辑：
- 收件人外部 ID 解析（event 字段 → extra_data → IntegrationBinding 查询）
- validate_recipient 行为
- send 方法的降级链（企业应用消息 → 群机器人）
- 缺少配置时的安全跳过
"""
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.notifications.channels.integration_base import BaseIntegrationChannel
from app.infrastructure.notifications.channels.dingtalk import DingtalkChannel
from app.models.integration import Integration, IntegrationBinding
from app.schemas.notification import NotificationContent, NotificationEvent, NotificationPriority

# 直接复用真实的 DingtalkChannel（它就是 BaseIntegrationChannel 的子类），
# 避免定义带 __init__ 的测试类触发 pytest 收集警告。


@pytest.fixture
def channel(db_session: AsyncSession) -> DingtalkChannel:
    return DingtalkChannel(db_session)


def _make_event(
    tenant_id: str = "tenant-1",
    recipient_id: str = "user-1",
    extra_data: dict | None = None,
    dingtalk_id: str | None = None,
) -> NotificationEvent:
    return NotificationEvent(
        tenant_id=tenant_id,
        recipient_id=recipient_id,
        recipient_type="admin",
        message_type="system",
        template_code="test_template",
        recipient_dingtalk_id=dingtalk_id,
        extra_data=extra_data,
        priority=NotificationPriority.NORMAL,
    )


def _make_content() -> NotificationContent:
    return NotificationContent(title="测试标题", content="测试内容")


class TestResolveExternalId:
    """收件人外部 ID 解析逻辑。"""

    async def test_resolve_from_event_schema_field(self, channel, db_session):
        """优先从 event.recipient_dingtalk_id 字段解析。"""
        event = _make_event(dingtalk_id="dt_user_123")
        result = await channel._resolve_external_id(event)
        assert result == "dt_user_123"

    async def test_resolve_from_extra_data(self, channel, db_session):
        """其次从 extra_data 解析。"""
        event = _make_event(extra_data={"recipient_dingtalk_id": "dt_from_extra"})
        result = await channel._resolve_external_id(event)
        assert result == "dt_from_extra"

    async def test_resolve_from_binding_table(self, channel, db_session, test_tenant):
        """最后查 IntegrationBinding 表。"""
        binding = IntegrationBinding(
            id=str(uuid4()),
            tenant_id=test_tenant.id,
            user_id="admin-1",
            user_type="admin",
            provider="dingtalk",
            external_id="dt_binding_id",
        )
        db_session.add(binding)
        await db_session.commit()

        event = _make_event(tenant_id=test_tenant.id, recipient_id="admin-1")
        result = await channel._resolve_external_id(event)
        assert result == "dt_binding_id"

    async def test_resolve_returns_none_when_no_binding(self, channel, db_session, test_tenant):
        """无绑定时返回 None。"""
        event = _make_event(tenant_id=test_tenant.id, recipient_id="no-such-user")
        result = await channel._resolve_external_id(event)
        assert result is None

    async def test_event_field_takes_priority_over_extra_data(self, channel, db_session):
        """event schema 字段优先级高于 extra_data。"""
        event = _make_event(
            dingtalk_id="from_field",
            extra_data={"recipient_dingtalk_id": "from_extra"},
        )
        result = await channel._resolve_external_id(event)
        assert result == "from_field"


class TestValidateRecipient:
    """validate_recipient 行为。"""

    async def test_valid_when_external_id_resolved(self, channel, db_session):
        """能解析到 external_id 时返回有效。"""
        event = _make_event(dingtalk_id="dt_123")
        valid, error = await channel.validate_recipient(event)
        assert valid is True
        assert error is None
        # 应缓存到 extra_data
        assert event.extra_data["_external_id_dingtalk"] == "dt_123"

    async def test_invalid_when_no_external_id(self, channel, db_session, test_tenant):
        """无法解析时返回无效。"""
        event = _make_event(tenant_id=test_tenant.id, recipient_id="nobody")
        valid, error = await channel.validate_recipient(event)
        assert valid is False
        assert "未绑定" in error


class TestSendLogic:
    """send 方法的降级与跳过逻辑。"""

    async def test_skip_when_no_integration_config(self, channel, db_session, test_tenant):
        """租户未配置集成时应返回 False（不报错）。"""
        event = _make_event(tenant_id=test_tenant.id, dingtalk_id="dt_123")
        result = await channel.send(event, _make_content())
        assert result is False

    async def test_send_via_work_message(self, channel, db_session, test_tenant):
        """配置了 app_id 时走企业应用消息。"""
        integration = Integration(
            id=str(uuid4()),
            tenant_id=test_tenant.id,
            provider="dingtalk",
            name="测试",
            app_id="dt_app",
            app_secret_ref="env:DT_SECRET",
            extra_config={"agent_id": "123"},
            status=1,
        )
        db_session.add(integration)
        await db_session.commit()

        event = _make_event(tenant_id=test_tenant.id, dingtalk_id="dt_user")

        # mock provider 的 send_work_message 返回成功
        mock_provider = MagicMock()
        mock_provider.get_access_token = AsyncMock(return_value="token")
        mock_provider.send_work_message = AsyncMock(return_value=True)

        with patch(
            "app.infrastructure.notifications.channels.integration_base.get_provider",
            return_value=mock_provider,
        ):
            result = await channel.send(event, _make_content())

        assert result is True
        mock_provider.send_work_message.assert_called_once()

    async def test_fallback_to_robot_when_work_message_fails(self, channel, db_session, test_tenant):
        """企业消息失败 + 配置了 webhook 时降级到群机器人。"""
        integration = Integration(
            id=str(uuid4()),
            tenant_id=test_tenant.id,
            provider="dingtalk",
            name="测试",
            app_id="dt_app",
            app_secret_ref="env:DT_SECRET",
            webhook_url="https://oapi.dingtalk.com/robot/send?access_token=xxx",
            status=1,
        )
        db_session.add(integration)
        await db_session.commit()

        event = _make_event(tenant_id=test_tenant.id, dingtalk_id="dt_user")

        mock_provider = MagicMock()
        mock_provider.get_access_token = AsyncMock(return_value="token")
        mock_provider.send_work_message = AsyncMock(return_value=False)  # 企业消息失败
        mock_provider.send_robot_message = AsyncMock(return_value=True)  # 机器人成功

        with patch(
            "app.infrastructure.notifications.channels.integration_base.get_provider",
            return_value=mock_provider,
        ), patch(
            "app.infrastructure.notifications.channels.integration_base.resolve_secret_ref",
            return_value=None,
        ):
            result = await channel.send(event, _make_content())

        assert result is True
        mock_provider.send_robot_message.assert_called_once()

    async def test_send_only_robot_when_no_app_id(self, channel, db_session, test_tenant):
        """未配置 app_id（仅 webhook）时直接走群机器人。"""
        integration = Integration(
            id=str(uuid4()),
            tenant_id=test_tenant.id,
            provider="dingtalk",
            name="测试",
            app_id=None,
            webhook_url="https://oapi.dingtalk.com/robot/send",
            status=1,
        )
        db_session.add(integration)
        await db_session.commit()

        event = _make_event(tenant_id=test_tenant.id, dingtalk_id="dt_user")

        mock_provider = MagicMock()
        mock_provider.send_robot_message = AsyncMock(return_value=True)

        with patch(
            "app.infrastructure.notifications.channels.integration_base.get_provider",
            return_value=mock_provider,
        ), patch(
            "app.infrastructure.notifications.channels.integration_base.resolve_secret_ref",
            return_value=None,
        ):
            result = await channel.send(event, _make_content())

        assert result is True
        mock_provider.send_robot_message.assert_called_once()

    async def test_returns_false_when_no_external_id(self, channel, db_session, test_tenant):
        """无法解析收件人时返回 False。"""
        event = _make_event(tenant_id=test_tenant.id, recipient_id="nobody", dingtalk_id=None)
        result = await channel.send(event, _make_content())
        assert result is False
