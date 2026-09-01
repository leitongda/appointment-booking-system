"""统一消息中心模块测试"""
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4

from sqlalchemy import select, func

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


# ---------------------------------------------------------------------------
# 模型测试
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestNotificationGroup:
    async def test_create_group(self, db_session, sample_tenant):
        """测试创建通知组"""
        await db_session.flush()

        group = NotificationGroup(
            id=str(uuid4()),
            tenant_id="tenant-1",
            event_type="appointment.success",
            message_type="appointment",
            dedup_key="tenant-1:user-1:appointment_success:appt-1",
            status="pending",
        )
        db_session.add(group)
        await db_session.commit()

        result = await db_session.execute(
            select(NotificationGroup).where(NotificationGroup.id == group.id)
        )
        saved = result.scalar_one()
        assert saved.tenant_id == "tenant-1"
        assert saved.event_type == "appointment.success"
        assert saved.status == "pending"

    async def test_dedup_key_unique(self, db_session, sample_tenant):
        """测试去重键唯一约束"""
        await db_session.flush()

        group1 = NotificationGroup(
            id=str(uuid4()),
            tenant_id="tenant-1",
            event_type="appointment.success",
            message_type="appointment",
            dedup_key="dedup-key-1",
            status="pending",
        )
        db_session.add(group1)
        await db_session.commit()

        group2 = NotificationGroup(
            id=str(uuid4()),
            tenant_id="tenant-1",
            event_type="appointment.success",
            message_type="appointment",
            dedup_key="dedup-key-1",  # 相同 dedup_key
            status="pending",
        )
        db_session.add(group2)
        with pytest.raises(Exception):  # IntegrityError
            await db_session.commit()
        await db_session.rollback()


@pytest.mark.asyncio
class TestNotificationRecipient:
    async def test_create_recipient(self, db_session, sample_tenant):
        """测试创建接收人"""
        await db_session.flush()

        group = NotificationGroup(
            id=str(uuid4()),
            tenant_id="tenant-1",
            event_type="appointment.success",
            message_type="appointment",
        )
        db_session.add(group)
        await db_session.flush()

        recipient = NotificationRecipient(
            id=str(uuid4()),
            group_id=group.id,
            tenant_id="tenant-1",
            user_id="user-1",
            user_type="patient",
            title="预约成功",
            content="测试内容",
            phone="13800138000",
            is_read=0,
        )
        db_session.add(recipient)
        await db_session.commit()

        result = await db_session.execute(
            select(NotificationRecipient).where(NotificationRecipient.id == recipient.id)
        )
        saved = result.scalar_one()
        assert saved.user_id == "user-1"
        assert saved.phone == "13800138000"
        assert saved.is_read == 0


@pytest.mark.asyncio
class TestUnifiedTemplate:
    async def test_tenant_code_unique(self, db_session, sample_tenant):
        """测试 (tenant_id, code) 联合唯一约束"""
        await db_session.flush()

        t1 = UnifiedTemplate(
            id=str(uuid4()),
            tenant_id="tenant-1",
            code="appointment_success",
            name="预约成功",
            message_type="appointment",
            text_template="预约成功",
        )
        db_session.add(t1)
        await db_session.commit()

        # 同租户同 code 应该冲突
        t2 = UnifiedTemplate(
            id=str(uuid4()),
            tenant_id="tenant-1",
            code="appointment_success",
            name="预约成功2",
            message_type="appointment",
            text_template="预约成功2",
        )
        db_session.add(t2)
        with pytest.raises(Exception):
            await db_session.commit()
        await db_session.rollback()

    async def test_different_tenants_same_code(self, db_session, sample_tenant):
        """测试不同租户可以使用相同 code"""
        await db_session.flush()

        t1 = UnifiedTemplate(
            id=str(uuid4()),
            tenant_id="tenant-1",
            code="appointment_success",
            name="预约成功",
            message_type="appointment",
        )
        db_session.add(t1)

        t2 = UnifiedTemplate(
            id=str(uuid4()),
            tenant_id="tenant-2",
            code="appointment_success",
            name="预约成功",
            message_type="appointment",
        )
        db_session.add(t2)
        await db_session.commit()  # 不应冲突


# ---------------------------------------------------------------------------
# 服务层测试
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestUnifiedMessageService:
    async def test_send_creates_group_and_recipient(self, db_session, sample_tenant, sample_event):
        """测试发送创建通知组和接收人"""
        await db_session.flush()

        service = UnifiedMessageService(db_session)

        # Mock Redis 去重
        with patch("app.modules.unified_message.service_send.get_redis") as mock_redis:
            mock_client = AsyncMock()
            mock_client.set.return_value = True  # 首次发送
            mock_redis.return_value = mock_client

            # Mock 渠道注册表
            with patch("app.modules.unified_message.service_send.channel_registry") as mock_registry:
                mock_registry.is_available.return_value = False  # 无可用渠道

                result = await service.send(sample_event)

                # 应该创建了通知组和接收人
                group_count = await db_session.execute(
                    select(func.count(NotificationGroup.id))
                )
                assert group_count.scalar() >= 1

                recipient_count = await db_session.execute(
                    select(func.count(NotificationRecipient.id))
                )
                assert recipient_count.scalar() >= 1

    async def test_dedup_blocks_duplicate(self, db_session, sample_tenant, sample_event):
        """测试去重拦截重复事件"""
        await db_session.flush()

        service = UnifiedMessageService(db_session)

        # Mock Redis 返回已存在
        with patch("app.modules.unified_message.service_send.get_redis") as mock_redis:
            mock_client = AsyncMock()
            mock_client.set.return_value = False  # 重复
            mock_redis.return_value = mock_client

            # 同时 mock DB 去重也返回已存在
            group = NotificationGroup(
                id=str(uuid4()),
                tenant_id="tenant-1",
                event_type="appointment_success",
                message_type="appointment_success",
                dedup_key=f"tenant-1:user-1:appointment_success:appointment-1",
            )
            db_session.add(group)
            await db_session.flush()

            result = await service.send(sample_event)
            assert result.success is True  # 去重视为成功
            assert result.channels_attempted == 0

    async def test_get_unread_count(self, db_session, sample_tenant):
        """测试获取未读消息数量"""
        await db_session.flush()

        # 创建通知组
        group = NotificationGroup(
            id=str(uuid4()),
            tenant_id="tenant-1",
            event_type="appointment.success",
            message_type="appointment",
        )
        db_session.add(group)
        await db_session.flush()

        # 创建未读接收人
        for i in range(3):
            recipient = NotificationRecipient(
                id=str(uuid4()),
                group_id=group.id,
                tenant_id="tenant-1",
                user_id="user-1",
                user_type="patient",
                title=f"消息 {i}",
                is_read=0,
            )
            db_session.add(recipient)

        # 创建已读接收人
        read_recipient = NotificationRecipient(
            id=str(uuid4()),
            group_id=group.id,
            tenant_id="tenant-1",
            user_id="user-1",
            user_type="patient",
            title="已读消息",
            is_read=1,
            read_at=datetime.utcnow(),
        )
        db_session.add(read_recipient)
        await db_session.commit()

        service = UnifiedMessageService(db_session)
        count = await service.get_unread_count("user-1", "patient")
        assert count.total == 3
        assert count.appointment == 3

    async def test_mark_as_read(self, db_session, sample_tenant):
        """测试标记已读"""
        await db_session.flush()

        group = NotificationGroup(
            id=str(uuid4()),
            tenant_id="tenant-1",
            event_type="system",
            message_type="system",
        )
        db_session.add(group)
        await db_session.flush()

        recipient = NotificationRecipient(
            id=str(uuid4()),
            group_id=group.id,
            tenant_id="tenant-1",
            user_id="user-1",
            user_type="patient",
            title="测试消息",
            is_read=0,
        )
        db_session.add(recipient)
        await db_session.commit()

        service = UnifiedMessageService(db_session)
        result = await service.mark_as_read(recipient.id, "user-1")
        assert result is True

        # 验证已读
        await db_session.refresh(recipient)
        assert recipient.is_read == 1
        assert recipient.read_at is not None

    async def test_mark_all_as_read(self, db_session, sample_tenant):
        """测试全部标记已读"""
        await db_session.flush()

        group = NotificationGroup(
            id=str(uuid4()),
            tenant_id="tenant-1",
            event_type="appointment.success",
            message_type="appointment",
        )
        db_session.add(group)
        await db_session.flush()

        for i in range(5):
            recipient = NotificationRecipient(
                id=str(uuid4()),
                group_id=group.id,
                tenant_id="tenant-1",
                user_id="user-1",
                user_type="patient",
                title=f"消息 {i}",
                is_read=0,
            )
            db_session.add(recipient)
        await db_session.commit()

        service = UnifiedMessageService(db_session)
        count = await service.mark_all_as_read("user-1", "patient")
        assert count == 5

    async def test_get_user_messages(self, db_session, sample_tenant):
        """测试获取用户消息列表"""
        await db_session.flush()

        group = NotificationGroup(
            id=str(uuid4()),
            tenant_id="tenant-1",
            event_type="appointment.success",
            message_type="appointment",
            related_id="appt-1",
        )
        db_session.add(group)
        await db_session.flush()

        for i in range(3):
            recipient = NotificationRecipient(
                id=str(uuid4()),
                group_id=group.id,
                tenant_id="tenant-1",
                user_id="user-1",
                user_type="patient",
                title=f"消息 {i}",
                content=f"内容 {i}",
                is_read=0,
            )
            db_session.add(recipient)
        await db_session.commit()

        service = UnifiedMessageService(db_session)
        query = MessageQuery(page=1, page_size=10)
        messages, total = await service.get_user_messages("user-1", "patient", query)

        assert total == 3
        assert len(messages) == 3
        assert messages[0]["title"] is not None


# ---------------------------------------------------------------------------
# Schema 测试
# ---------------------------------------------------------------------------

class TestSchemas:
    def test_notification_event_camel_case(self):
        """测试 NotificationEvent camelCase 序列化"""
        event = NotificationEvent(
            tenant_id="t1",
            recipient_id="u1",
            recipient_type="patient",
            template_code="test",
            message_type="system",
        )
        data = event.model_dump(by_alias=True)
        assert "tenantId" in data
        assert "recipientId" in data
        assert "recipientType" in data
        assert "templateCode" in data
        assert "messageType" in data

    def test_unread_count_response_defaults(self):
        """测试 UnreadCountResponse 默认值"""
        resp = UnreadCountResponse()
        assert resp.total == 0
        assert resp.appointment == 0
        assert resp.system == 0

    def test_send_result_schema(self):
        """测试 SendResult schema"""
        result = SendResult(
            success=True,
            group_id="g1",
            channels_attempted=2,
            channels_succeeded=1,
            channels_failed=1,
        )
        data = result.model_dump(by_alias=True)
        assert data["success"] is True
        assert data["groupId"] == "g1"
        assert data["channelsAttempted"] == 2
