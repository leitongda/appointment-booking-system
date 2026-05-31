"""反馈相关枚举"""
from enum import Enum


class FeedbackType(str, Enum):
    """反馈类型

    来源: models/feedback.py + schemas/feedback.py
    """
    SUGGESTION = "suggestion"  # 建议
    COMPLAINT = "complaint"    # 投诉
    BUG = "bug"               # 问题反馈
    OTHER = "other"            # 其他


class FeedbackStatus(str, Enum):
    """反馈状态

    来源: models/feedback.py + schemas/feedback.py
    """
    PENDING = "pending"          # 待处理
    PROCESSING = "processing"    # 处理中
    RESOLVED = "resolved"        # 已解决
    CLOSED = "closed"            # 已关闭
