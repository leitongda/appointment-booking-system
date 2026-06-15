"""统一枚举定义 -- 所有 enum 的单一来源。

分类规则：
- enums/ ：Python Enum/StrEnum/IntEnum 类型定义
- constants/ ：dict、tuple、list 等非 Enum 常量

使用方式：
    from app.enums.message import MessageType
    from app.enums.notification import NotificationChannel
"""

# appointment
from app.enums.appointment import CheckinMethod

# approval
from app.enums.approval import ApprovalInstanceStatus

# core (events + websocket + auth)
from app.enums.core import EventType, RoleType, WSMessageType

# feedback
from app.enums.feedback import FeedbackStatus, FeedbackType

# freelance
from app.enums.freelance import (
    FreelanceAccountPlatform,
    FreelanceAccountType,
    FreelanceInteractionType,
    FreelanceSettlementStatus,
    FreelanceTaskStatus,
)

# general
from app.enums.general import (
    ApprovalStatus,
    BehaviorEventType,
    EmailTemplateType,
    ExtraQuotaType,
    PatientCondition,
    Platform,
    ReminderLevel,
    SelfReportStatus,
    TaskStatus,
    TimeUnit,
    VisitScope,
)

# message
from app.enums.message import MessageType

# notification (schemas/notification.py + schemas/notification_log.py + modules/unified_message)
from app.enums.notification import (
    ChannelType,
    DeliveryStatus,
    NotificationChannel,
    NotificationEventType,
    NotificationLogStatus,
    NotificationPriority,
    NotificationStatus,
    Priority,
    RuleType,
    StrategyType,
)

# payment
from app.enums.payment import PaymentStatus, RefundStatus

# schedule
from app.enums.schedule import (
    ActionType,
    AppointmentType,
    Period,
    RequestStatus,
    RequestType,
    ScheduleMode,
    SuspensionProcessingStatus,
)

# support_ticket
from app.enums.support_ticket import (
    SupportTicketPriority,
    SupportTicketStatus,
    SupportTicketType,
)

__all__ = [
    # appointment
    "CheckinMethod",
    # schedule
    "ActionType",
    "AppointmentType",
    "Period",
    "RequestStatus",
    "RequestType",
    "ScheduleMode",
    "SuspensionProcessingStatus",
    # message
    "MessageType",
    # feedback
    "FeedbackStatus",
    "FeedbackType",
    # notification
    "ChannelType",
    "DeliveryStatus",
    "NotificationChannel",
    "NotificationEventType",
    "NotificationLogStatus",
    "NotificationPriority",
    "NotificationStatus",
    "Priority",
    "RuleType",
    "StrategyType",
    # support_ticket
    "SupportTicketPriority",
    "SupportTicketStatus",
    "SupportTicketType",
    # general
    "ApprovalStatus",
    "BehaviorEventType",
    "EmailTemplateType",
    "ExtraQuotaType",
    "PatientCondition",
    "Platform",
    "ReminderLevel",
    "SelfReportStatus",
    "TaskStatus",
    "TimeUnit",
    "VisitScope",
    # core
    "EventType",
    "RoleType",
    "WSMessageType",
    # freelance
    "FreelanceAccountPlatform",
    "FreelanceAccountType",
    "FreelanceInteractionType",
    "FreelanceSettlementStatus",
    "FreelanceTaskStatus",
    # payment
    "PaymentStatus",
    "RefundStatus",
    # approval
    "ApprovalInstanceStatus",
]
