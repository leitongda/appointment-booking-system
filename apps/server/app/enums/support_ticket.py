"""工单相关枚举"""
from enum import Enum


class SupportTicketType(str, Enum):
    """工单类型

    来源: models/support_ticket.py + schemas/support_ticket.py
    """
    SUGGESTION = "suggestion"  # 建议
    COMPLAINT = "complaint"    # 投诉
    BUG = "bug"               # 缺陷
    OTHER = "other"            # 其他


class SupportTicketStatus(str, Enum):
    """工单状态

    来源: models/support_ticket.py + schemas/support_ticket.py
    """
    PENDING = "pending"          # 待处理
    PROCESSING = "processing"    # 处理中
    RESOLVED = "resolved"        # 已解决
    CLOSED = "closed"            # 已关闭


class SupportTicketPriority(str, Enum):
    """工单优先级

    来源: models/support_ticket.py + schemas/support_ticket.py
    """
    LOW = "low"        # 低
    MEDIUM = "medium"  # 中
    HIGH = "high"      # 高
    URGENT = "urgent"  # 紧急
