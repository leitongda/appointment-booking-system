"""通知偏好检查 — 统一实现

替代 service_messages.py 和 dispatcher.py 中的重复实现。
"""
import logging
from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# 渠道字段映射
CHANNEL_FIELD_MAP = {
    "in_app": "in_app_enabled",
    "sms": "sms_enabled",
    "wechat": "wechat_enabled",
    "email": "email_enabled",
    "websocket": "in_app_enabled",  # WebSocket 复用站内信偏好
}

# 消息类型字段映射
TYPE_FIELD_MAP = {
    "appointment": "appointment_enabled",
    "appointment_success": "appointment_enabled",
    "appointment_reminder": "reminder_enabled",
    "appointment_cancelled": "appointment_enabled",
    "schedule": "reminder_enabled",
    "stop_clinic": "stop_clinic_enabled",
    "system": "system_enabled",
    "consultation": "consultation_enabled",
    "feedback": "feedback_enabled",
    "queue_call": "appointment_enabled",
}


async def check_notification_preference(
    db: AsyncSession,
    user_id: str,
    user_type: str,
    channel: str,
    message_type: str,
) -> bool:
    """检查用户是否启用了该渠道和消息类型的通知

    Args:
        db: 异步数据库会话
        user_id: 用户 ID
        user_type: 用户类型 (patient/doctor/admin)
        channel: 渠道名 (in_app/sms/wechat/email/websocket)
        message_type: 消息类型 (appointment/schedule/system/...)

    Returns:
        True 表示允许发送，False 表示用户已禁用。默认返回 True。
    """
    try:
        channel_col = CHANNEL_FIELD_MAP.get(channel)
        type_col = TYPE_FIELD_MAP.get(message_type)
        if not channel_col or not type_col:
            return True

        stmt = text(
            f"SELECT {channel_col}, {type_col} "
            f"FROM notification_preferences "
            f"WHERE user_id = :uid AND user_type = :utype "
            f"LIMIT 1"
        )
        result = await db.execute(stmt, {"uid": user_id, "utype": user_type})
        row = result.first()
        if row is None:
            return True  # 未设置偏好，默认允许
        return bool(row[0]) and bool(row[1])
    except Exception as e:
        logger.error(f"检查通知偏好失败: {e}", exc_info=True)
        return True  # 出错时默认允许


async def get_user_preferences(
    db: AsyncSession,
    user_id: str,
    user_type: str,
) -> Optional[dict]:
    """获取用户的完整通知偏好设置

    Returns:
        偏好字典，未设置时返回 None
    """
    try:
        stmt = text(
            "SELECT sms_enabled, email_enabled, wechat_enabled, in_app_enabled, "
            "appointment_enabled, reminder_enabled, stop_clinic_enabled, system_enabled, "
            "consultation_enabled, feedback_enabled, quiet_hours_start, quiet_hours_end "
            "FROM notification_preferences "
            "WHERE user_id = :uid AND user_type = :utype "
            "LIMIT 1"
        )
        result = await db.execute(stmt, {"uid": user_id, "utype": user_type})
        row = result.first()
        if row is None:
            return None

        return dict(zip(
            ["sms_enabled", "email_enabled", "wechat_enabled", "in_app_enabled",
             "appointment_enabled", "reminder_enabled", "stop_clinic_enabled",
             "system_enabled", "consultation_enabled", "feedback_enabled",
             "quiet_hours_start", "quiet_hours_end"],
            row,
        ))
    except Exception as e:
        logger.error(f"获取通知偏好失败: {e}", exc_info=True)
        return None
