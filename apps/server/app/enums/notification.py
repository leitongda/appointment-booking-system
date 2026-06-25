"""通知相关枚举"""
from enum import Enum

# ---------- schemas/notification.py ----------

class NotificationChannel(str, Enum):
    """通知渠道

    来源: schemas/notification.py
    """
    IN_APP = "in_app"
    SMS = "sms"
    WECHAT = "wechat"
    EMAIL = "email"
    WEBSOCKET = "websocket"


class NotificationPriority(int, Enum):
    """通知优先级

    来源: schemas/notification.py
    """
    NORMAL = 0
    IMPORTANT = 1
    URGENT = 2


# ---------- schemas/notification_log.py ----------

class NotificationLogStatus(str, Enum):
    """通知日志状态

    来源: schemas/notification_log.py
    命名为 NotificationLogStatus 以与 unified_message.NotificationStatus 区分。
    """
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    PERMANENTLY_FAILED = "permanently_failed"


# ---------- modules/unified_message/schemas.py ----------

class NotificationEventType(str, Enum):
    """通知事件类型

    来源: modules/unified_message/schemas.py
    """
    APPOINTMENT_SUCCESS = "appointment.success"
    APPOINTMENT_REMINDER_24H = "appointment.reminder.24h"
    APPOINTMENT_REMINDER_1H = "appointment.reminder.1h"
    APPOINTMENT_CANCELLED = "appointment.cancelled"
    SCHEDULE_CHANGE = "schedule.change"
    SCHEDULE_STOP = "schedule.stop"
    STOP_CLINIC = "stop_clinic"
    SYSTEM = "system"


class NotificationStatus(str, Enum):
    """通知状态

    来源: modules/unified_message/schemas.py
    """
    PENDING = "pending"
    PARTIAL = "partial"
    SENT = "sent"
    FAILED = "failed"


class DeliveryStatus(str, Enum):
    """投递状态

    来源: modules/unified_message/schemas.py
    """
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    PERMANENTLY_FAILED = "permanently_failed"


# Deprecated: use NotificationChannel instead. Kept for backward compatibility.
ChannelType = NotificationChannel


class Priority(str, Enum):
    """优先级

    来源: modules/unified_message/schemas.py
    """
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class StrategyType(str, Enum):
    """渠道策略类型

    来源: modules/unified_message/schemas.py
    """
    FALLBACK = "fallback"
    PARALLEL = "parallel"
    ALL = "all"


class RuleType(str, Enum):
    """接收人规则类型

    来源: modules/unified_message/schemas.py
    """
    ROLE = "role"
    DEPARTMENT = "department"
    USER_LIST = "user_list"
    DYNAMIC = "dynamic"
    EVENT_DRIVEN = "event_driven"
