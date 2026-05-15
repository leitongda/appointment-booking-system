"""API 契约测试

验证新旧服务的响应格式完全一致（JSON 结构、字段名、camelCase 序列化）。
"""
import pytest
from datetime import datetime

from app.modules.unified_message.schemas import (
    MessageResponse,
    MessageListResponse,
    UnreadCountResponse,
    SendResult,
    NotificationEvent,
)
from app.schemas.message import (
    MessageResponse as OldMessageResponse,
    MessageListResponse as OldMessageListResponse,
    UnreadCountResponse as OldUnreadCountResponse,
)


class TestMessageResponseContract:
    """验证新旧 MessageResponse 字段完全一致"""

    def test_field_names_match(self):
        """字段名必须完全一致"""
        new_fields = set(MessageResponse.model_fields.keys())
        old_fields = set(OldMessageResponse.model_fields.keys())
        assert new_fields == old_fields, (
            f"字段不一致: 新增={new_fields - old_fields}, 缺失={old_fields - new_fields}"
        )

    def test_camel_case_serialization(self):
        """序列化输出必须是 camelCase"""
        resp = MessageResponse(
            id="msg-1",
            store_id="store-1",
            user_id="user-1",
            user_type="patient",
            title="测试",
            content="内容",
            message_type="appointment",
            related_id="appt-1",
            is_read=0,
            read_at=None,
            created_at=datetime(2026, 5, 14, 10, 0, 0),
        )
        data = resp.model_dump(by_alias=True)

        # camelCase 字段
        assert "storeId" in data
        assert "userId" in data
        assert "userType" in data
        assert "messageType" in data
        assert "relatedId" in data
        assert "isRead" in data
        assert "readAt" in data
        assert "createdAt" in data

        # 不应包含 snake_case
        assert "store_id" not in data
        assert "user_id" not in data
        assert "is_read" not in data
        assert "created_at" not in data

    def test_null_fields_serialize_correctly(self):
        """None 值应序列化为 null（不是 undefined）"""
        resp = MessageResponse(id="msg-1")
        data = resp.model_dump(by_alias=True)

        assert data["id"] == "msg-1"
        assert data["storeId"] is None
        assert data["userId"] is None
        assert data["isRead"] == 0  # 默认值


class TestMessageListResponseContract:
    """验证新旧 MessageListResponse 字段完全一致"""

    def test_field_names_match(self):
        new_fields = set(MessageListResponse.model_fields.keys())
        old_fields = set(OldMessageListResponse.model_fields.keys())
        assert new_fields == old_fields


class TestUnreadCountResponseContract:
    """验证新旧 UnreadCountResponse 字段完全一致"""

    def test_field_names_match(self):
        new_fields = set(UnreadCountResponse.model_fields.keys())
        old_fields = set(OldUnreadCountResponse.model_fields.keys())
        assert new_fields == old_fields

    def test_camel_case_serialization(self):
        resp = UnreadCountResponse(
            total=10,
            appointment=3,
            consultation=1,
            schedule=2,
            system=2,
            stop_clinic=1,
            feedback=1,
        )
        data = resp.model_dump(by_alias=True)

        assert data["total"] == 10
        assert data["appointment"] == 3
        assert data["consultation"] == 1
        assert data["schedule"] == 2
        assert data["system"] == 2
        assert data["stopClinic"] == 1  # camelCase
        assert data["feedback"] == 1

        # snake_case 不应出现
        assert "stop_clinic" not in data

    def test_default_values(self):
        resp = UnreadCountResponse()
        data = resp.model_dump(by_alias=True)
        assert data["total"] == 0
        assert data["appointment"] == 0
        assert data["stopClinic"] == 0


class TestNotificationEventContract:
    """验证 NotificationEvent 字段兼容性"""

    def test_camel_case_serialization(self):
        event = NotificationEvent(
            tenant_id="t1",
            store_id="s1",
            recipient_id="u1",
            recipient_type="patient",
            recipient_phone="13800138000",
            recipient_email="test@example.com",
            recipient_openid="openid-123",
            template_code="appointment_success",
            variables={"key": "value"},
            message_type="appointment",
            related_id="appt-1",
            channels=["sms", "in_app"],
            priority=1,
            title="测试",
            content="内容",
            extra_data={"extra": "data"},
        )
        data = event.model_dump(by_alias=True)

        assert data["tenantId"] == "t1"
        assert data["storeId"] == "s1"
        assert data["recipientId"] == "u1"
        assert data["recipientType"] == "patient"
        assert data["recipientPhone"] == "13800138000"
        assert data["recipientEmail"] == "test@example.com"
        assert data["recipientOpenid"] == "openid-123"
        assert data["templateCode"] == "appointment_success"
        assert data["messageType"] == "appointment"
        assert data["relatedId"] == "appt-1"
        assert data["extraData"] == {"extra": "data"}


class TestSendResultContract:
    """验证 SendResult 字段兼容性"""

    def test_camel_case_serialization(self):
        result = SendResult(
            success=True,
            group_id="g1",
            channels_attempted=2,
            channels_succeeded=1,
            channels_failed=1,
            error_message=None,
        )
        data = result.model_dump(by_alias=True)

        assert data["success"] is True
        assert data["groupId"] == "g1"
        assert data["channelsAttempted"] == 2
        assert data["channelsSucceeded"] == 1
        assert data["channelsFailed"] == 1
        assert data["errorMessage"] is None
