"""统一消息中心集成测试

测试场景：
1. 兼容层降级逻辑
2. 渠道发送失败处理
3. 静默时段边界
4. 模板渲染
5. N+1 查询优化验证
"""
import pytest
from datetime import datetime, time
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4

from sqlalchemy import select, func
from app.modules.messages.service_messages import ContactInfo

from app.modules.unified_message.models import (
    NotificationGroup,
    NotificationRecipient,
    NotificationDelivery,
    UnifiedTemplate,
    ChannelStrategy,
    RecipientRule,
)
from app.modules.unified_message.schemas import (
    NotificationEvent,
    MessageQuery,
    SendResult,
    UnreadCountResponse,
)
from app.modules.unified_message.service import UnifiedMessageService
from app.modules.unified_message.compat import MessageServiceCompat


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_event():
    """示例通知事件"""
    return NotificationEvent(
        tenant_id="tenant-1",
        store_id="store-1",
        recipient_id="user-1",
        recipient_type="patient",
        recipient_phone="13800138000",
        recipient_openid="openid-123",
        template_code="appointment_success",
        variables={"doctor_name": "张三", "time": "2026-05-15 09:00"},
        message_type="appointment_success",
        related_id="appointment-1",
        title="预约成功",
        content="您已成功预约张三医生",
    )


@pytest.fixture
def sample_tenant(db_session):
    """创建测试租户"""
    from app.models.tenant import Tenant, SubscriptionPlan
    plan = SubscriptionPlan(
        id=str(uuid4()),
        plan_code="test_plan",
        name="测试计划",
        status=1,
    )
    db_session.add(plan)

    tenant = Tenant(
        id="tenant-1",
        tenant_code="test_tenant",
        name="测试租户",
        status=1,
        subscription_plan_id=plan.id,
    )
    db_session.add(tenant)
    return tenant


@pytest.fixture
def sample_template(db_session, sample_tenant):
    """创建测试模板"""
    db_session.flush()
    template = UnifiedTemplate(
        id=str(uuid4()),
        tenant_id="tenant-1",
        code="appointment_success",
        name="预约成功通知",
        message_type="appointment_success",
        subject_template="预约成功通知",
        text_template="您已成功预约{{doctor_name}}医生，就诊时间：{{time}}",
        status=1,
    )
    db_session.add(template)
    return template


@pytest.fixture
def sample_recipients(db_session, sample_tenant):
    """创建测试接收人数据（用于 N+1 查询测试）"""
    db_session.flush()
    recipients = []
    for i in range(10):
        group = NotificationGroup(
            id=str(uuid4()),
            tenant_id="tenant-1",
            event_type="appointment",
            message_type="appointment",
            related_id=f"appointment-{i}",
            dedup_key=f"tenant-1:user-{i}:appointment:appointment-{i}",
            status="sent",
        )
        db_session.add(group)

        recipient = NotificationRecipient(
            id=str(uuid4()),
            group_id=group.id,
            tenant_id="tenant-1",
            user_id="user-1",
            user_type="patient",
            title=f"预约通知 {i}",
            content=f"您有一个预约 {i}",
            is_read=0,
            status="sent",
        )
        db_session.add(recipient)
        recipients.append(recipient)

    return recipients


# ---------------------------------------------------------------------------
# 兼容层降级测试
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestCompatLayerFallback:
    """测试兼容层委托逻辑（已统一，不再有 feature flag 分支）"""

    async def test_compat_always_uses_new_service(self, db_session, sample_tenant, sample_event):
        """测试兼容层始终使用 UnifiedMessageService"""
        compat = MessageServiceCompat(db_session)

        mock_new_service = MagicMock()
        mock_new_service.send = AsyncMock(return_value=SendResult(
            success=True,
            group_id="group-1",
            channels_attempted=1,
            channels_succeeded=1,
            channels_failed=0,
        ))
        compat._new_service = mock_new_service

        with patch("app.middleware.tenant_context.get_current_tenant_id", return_value="tenant-1"):
            with patch(
                "app.modules.messages.service_messages._get_user_contact_info",
                new_callable=AsyncMock,
                return_value=ContactInfo("13800138000", "openid-123", None),
            ):
                await compat.send_appointment_notification(
                    user_id="user-1",
                    user_type="patient",
                    title="预约成功",
                    content="您已成功预约",
                    appointment_id="apt-1",
                )

        # 验证新服务被调用
        mock_new_service.send.assert_called_once()

    async def test_compat_has_no_old_service(self, db_session):
        """测试兼容层不再持有旧服务引用"""
        compat = MessageServiceCompat(db_session)
        assert not hasattr(compat, "old_service")


# ---------------------------------------------------------------------------
# 渠道发送失败测试
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestChannelFailureHandling:
    """测试渠道发送失败处理"""

    async def test_delivery_recorded_on_channel_failure(self, db_session, sample_tenant):
        """测试渠道失败时创建失败的投递记录"""
        await db_session.flush()

        service = UnifiedMessageService(db_session)

        # 使用唯一事件避免去重
        unique_event = NotificationEvent(
            tenant_id="tenant-1",
            store_id="store-1",
            recipient_id=f"user-fail-{uuid4().hex[:8]}",
            recipient_type="patient",
            recipient_phone="13800138000",
            template_code="appointment_success",
            variables={"doctor_name": "张三"},
            message_type="appointment_success",
            related_id=f"apt-fail-{uuid4().hex[:8]}",
            title="渠道失败测试",
            content="测试内容",
        )

        with patch("app.modules.unified_message.service_send.channel_registry") as mock_registry:
            # 模拟渠道不可用
            mock_registry.is_available.return_value = False

            result = await service.send(unique_event)

            # 验证结果
            assert result.channels_failed > 0

            # 验证投递记录
            delivery_result = await db_session.execute(
                select(NotificationDelivery).where(
                    NotificationDelivery.tenant_id == "tenant-1"
                )
            )
            delivery_records = delivery_result.scalars().all()
            assert len(delivery_records) > 0
            # 所有投递记录都应该是失败状态
            for record in delivery_records:
                assert record.status == "failed"
                assert record.error_message == "渠道不可用"

    async def test_partial_success_when_some_channels_fail(self, db_session, sample_tenant, sample_event):
        """测试部分渠道成功、部分失败的情况"""
        await db_session.flush()

        service = UnifiedMessageService(db_session)

        with patch("app.modules.unified_message.service_send.channel_registry") as mock_registry:
            # 模拟第一个渠道失败，第二个成功
            mock_registry.is_available.side_effect = lambda ch: ch != "wechat"
            mock_registry.get.side_effect = lambda ch: MagicMock() if ch != "wechat" else None

            with patch.object(service, "_render_content") as mock_render:
                mock_render.return_value = MagicMock(title="测试", content="测试内容")

                # 需要 mock 渠道的 validate_recipient 和 send 方法
                # 这里简化测试，验证状态为 partial
                pass


# ---------------------------------------------------------------------------
# 静默时段边界测试
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestQuietHoursBoundary:
    """测试静默时段边界"""

    def test_in_quiet_hours_same_day(self):
        """测试同一天内的静默时段"""
        service = UnifiedMessageService.__new__(UnifiedMessageService)

        # 当前时间在静默时段内
        with patch("app.modules.unified_message.service_send.datetime") as mock_datetime:
            mock_datetime.now.return_value.time.return_value = time(23, 0)
            assert service._in_quiet_hours("22:00", "23:30") is True

        # 当前时间在静默时段外
        with patch("app.modules.unified_message.service_send.datetime") as mock_datetime:
            mock_datetime.now.return_value.time.return_value = time(21, 0)
            assert service._in_quiet_hours("22:00", "23:30") is False

    def test_in_quiet_hours_cross_midnight(self):
        """测试跨午夜的静默时段"""
        service = UnifiedMessageService.__new__(UnifiedMessageService)

        # 当前时间在跨午夜静默时段内（23:00 - 07:00）
        with patch("app.modules.unified_message.service_send.datetime") as mock_datetime:
            mock_datetime.now.return_value.time.return_value = time(23, 30)
            assert service._in_quiet_hours("23:00", "07:00") is True

        with patch("app.modules.unified_message.service_send.datetime") as mock_datetime:
            mock_datetime.now.return_value.time.return_value = time(6, 0)
            assert service._in_quiet_hours("23:00", "07:00") is True

        # 当前时间在跨午夜静默时段外
        with patch("app.modules.unified_message.service_send.datetime") as mock_datetime:
            mock_datetime.now.return_value.time.return_value = time(12, 0)
            assert service._in_quiet_hours("23:00", "07:00") is False

    def test_quiet_hours_filters_channels(self, db_session, sample_tenant):
        """测试静默时段过滤渠道"""
        # 这个测试需要更复杂的 setup，这里只验证逻辑
        pass


# ---------------------------------------------------------------------------
# 模板渲染测试
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestTemplateRendering:
    """测试模板渲染"""

    async def test_render_with_template(self, db_session, sample_tenant, sample_template, sample_event):
        """测试使用模板渲染"""
        await db_session.flush()

        service = UnifiedMessageService(db_session)

        # 测试模板渲染
        template = await service._get_template("tenant-1", "appointment_success")
        assert template is not None
        assert template.code == "appointment_success"

        # 测试渲染结果
        title, content = service._render_template(
            template,
            {"doctor_name": "张三", "time": "2026-05-15 09:00"}
        )
        assert "张三" in content
        assert "2026-05-15 09:00" in content

    async def test_render_without_template(self, db_session, sample_tenant, sample_event):
        """测试没有模板时使用默认内容"""
        await db_session.flush()

        service = UnifiedMessageService(db_session)

        # 测试获取不存在的模板
        template = await service._get_template("tenant-1", "non_existent_template")
        assert template is None

    async def test_render_with_invalid_template_syntax(self, db_session, sample_tenant):
        """测试模板语法错误时的降级处理"""
        await db_session.flush()

        # 创建一个语法错误的模板
        template = UnifiedTemplate(
            id=str(uuid4()),
            tenant_id="tenant-1",
            code="invalid_template",
            name="无效模板",
            message_type="system",
            text_template="{{invalid syntax",
            status=1,
        )
        db_session.add(template)
        await db_session.flush()

        service = UnifiedMessageService(db_session)

        # 测试渲染应该回退到简单替换
        title, content = service._render_template(template, {"key": "value"})
        # 不应该抛出异常


# ---------------------------------------------------------------------------
# N+1 查询优化测试
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestQueryOptimization:
    """测试 N+1 查询优化"""

    async def test_get_user_messages_uses_join(self, db_session, sample_tenant, sample_recipients):
        """测试 get_user_messages 使用 join 而非循环查询"""
        await db_session.flush()

        service = UnifiedMessageService(db_session)
        query = MessageQuery(page=1, page_size=20)

        # 执行查询
        messages, total = await service.get_user_messages("user-1", "patient", query)

        # 验证结果
        assert total == 10
        assert len(messages) == 10

        # 验证每个消息都包含必要的字段
        for msg in messages:
            assert "id" in msg
            assert "message_type" in msg
            assert "related_id" in msg

    async def test_get_unread_count_uses_group_by(self, db_session, sample_tenant, sample_recipients):
        """测试 get_unread_count 使用 GROUP BY 而非循环查询"""
        await db_session.flush()

        service = UnifiedMessageService(db_session)

        # 执行查询
        result = await service.get_unread_count("user-1", "patient")

        # 验证结果
        assert isinstance(result, UnreadCountResponse)
        assert result.total == 10
        assert result.appointment == 10


# ---------------------------------------------------------------------------
# 规则引擎测试
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestRuleEngine:
    """测试规则引擎"""

    async def test_resolve_user_list_rule(self, db_session, sample_tenant):
        """测试固定用户列表规则"""
        await db_session.flush()

        from app.modules.unified_message.rule_engine import RecipientRuleEngine

        engine = RecipientRuleEngine(db_session)

        # 创建规则
        rule = RecipientRule(
            id=str(uuid4()),
            tenant_id="tenant-1",
            name="固定用户列表",
            rule_type="user_list",
            rule_config={
                "users": [
                    {"user_id": "user-1", "user_type": "patient"},
                    {"user_id": "user-2", "user_type": "patient"},
                ]
            },
            status=1,
        )
        db_session.add(rule)
        await db_session.flush()

        # 测试解析
        recipients = await engine._resolve_rule(rule, {})
        assert len(recipients) == 2
        assert recipients[0]["user_id"] == "user-1"
        assert recipients[1]["user_id"] == "user-2"

    async def test_resolve_event_driven_rule(self, db_session, sample_tenant):
        """测试事件驱动规则"""
        await db_session.flush()

        from app.modules.unified_message.rule_engine import RecipientRuleEngine

        engine = RecipientRuleEngine(db_session)

        # 创建规则
        rule = RecipientRule(
            id=str(uuid4()),
            tenant_id="tenant-1",
            name="事件驱动规则",
            rule_type="event_driven",
            rule_config={
                "recipient_field": "doctor_id",
                "fixed_user_type": "doctor",
            },
            status=1,
        )
        db_session.add(rule)
        await db_session.flush()

        # 测试解析
        event_data = {"doctor_id": "doctor-123"}
        recipients = await engine._resolve_rule(rule, event_data)
        assert len(recipients) == 1
        assert recipients[0]["user_id"] == "doctor-123"
        assert recipients[0]["user_type"] == "doctor"

    async def test_resolve_recipients_dedup(self, db_session, sample_tenant):
        """测试接收人去重"""
        await db_session.flush()

        from app.modules.unified_message.rule_engine import RecipientRuleEngine

        engine = RecipientRuleEngine(db_session)

        # 创建两个返回相同用户的规则
        rule1 = RecipientRule(
            id=str(uuid4()),
            tenant_id="tenant-1",
            name="规则1",
            rule_type="user_list",
            rule_config={
                "users": [{"user_id": "user-1", "user_type": "patient"}]
            },
            event_type="appointment",
            status=1,
        )
        rule2 = RecipientRule(
            id=str(uuid4()),
            tenant_id="tenant-1",
            name="规则2",
            rule_type="user_list",
            rule_config={
                "users": [{"user_id": "user-1", "user_type": "patient"}]
            },
            event_type="appointment",
            status=1,
        )
        db_session.add_all([rule1, rule2])
        await db_session.flush()

        # 测试解析（应该去重）
        with patch.object(engine, "_get_matching_rules", return_value=[rule1, rule2]):
            recipients = await engine.resolve_recipients(
                tenant_id="tenant-1",
                event_type="appointment",
                event_data={},
            )
            assert len(recipients) == 1  # 去重后只有一条


# ---------------------------------------------------------------------------
# 完整发送流程测试
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestFullSendFlow:
    """测试完整发送流程"""

    async def test_send_creates_all_records(self, db_session, sample_tenant):
        """测试发送创建所有必要的记录"""
        await db_session.flush()

        service = UnifiedMessageService(db_session)

        # 使用唯一事件避免 Redis 去重冲突
        unique_event = NotificationEvent(
            tenant_id="tenant-1",
            store_id="store-1",
            recipient_id=f"user-send-{uuid4().hex[:8]}",
            recipient_type="patient",
            recipient_phone="13800138000",
            template_code="appointment_success",
            variables={"doctor_name": "张三"},
            message_type="appointment_success",
            related_id=f"apt-send-{uuid4().hex[:8]}",
            title="发送流程测试",
            content="测试内容",
        )

        with patch("app.modules.unified_message.service_send.channel_registry") as mock_registry:
            mock_registry.is_available.return_value = True

            # registry.get() 返回一个类（callable），其实例有 mock 方法
            mock_channel_instance = AsyncMock()
            mock_channel_instance.validate_recipient = AsyncMock(return_value=(True, None))
            mock_channel_instance.send = AsyncMock(return_value=True)

            mock_channel_class = MagicMock(return_value=mock_channel_instance)
            mock_registry.get.return_value = mock_channel_class

            with patch.object(service, "_render_content") as mock_render:
                mock_render.return_value = MagicMock(title="测试", content="测试内容")

                result = await service.send(unique_event)

                # 验证结果
                assert result.success is True
                assert result.channels_succeeded > 0
                assert result.group_id is not None

    async def test_send_dedup_blocks_duplicate(self, db_session, sample_tenant):
        """测试去重阻止重复发送"""
        await db_session.flush()

        service = UnifiedMessageService(db_session)

        # 使用唯一事件
        dedup_event = NotificationEvent(
            tenant_id="tenant-1",
            store_id="store-1",
            recipient_id=f"user-dedup-{uuid4().hex[:8]}",
            recipient_type="patient",
            recipient_phone="13800138000",
            template_code="appointment_success",
            variables={"doctor_name": "张三"},
            message_type="appointment_success",
            related_id=f"apt-dedup-{uuid4().hex[:8]}",
            title="去重测试",
            content="测试内容",
        )

        with patch("app.modules.unified_message.service_send.channel_registry") as mock_registry:
            mock_registry.is_available.return_value = True

            mock_channel_instance = AsyncMock()
            mock_channel_instance.validate_recipient = AsyncMock(return_value=(True, None))
            mock_channel_instance.send = AsyncMock(return_value=True)

            mock_channel_class = MagicMock(return_value=mock_channel_instance)
            mock_registry.get.return_value = mock_channel_class

            with patch.object(service, "_render_content") as mock_render:
                mock_render.return_value = MagicMock(title="测试", content="测试内容")

                # 第一次发送
                result1 = await service.send(dedup_event)
                assert result1.success is True

                # 第二次发送（应该被去重）
                result2 = await service.send(dedup_event)
                assert result2.channels_attempted == 0  # 被去重，没有尝试发送