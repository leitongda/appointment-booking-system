"""消息相关枚举"""
from enum import Enum


class MessageType(str, Enum):
    """消息类型

    来源: models/message.py + schemas/message.py
    """
    APPOINTMENT = "appointment"    # 预约通知
    CONSULTATION = "consultation"  # 就诊通知
    SCHEDULE = "schedule"          # 排班通知
    SYSTEM = "system"              # 系统通知
    STOP_CLINIC = "stop_clinic"    # 停诊通知
    FEEDBACK = "feedback"          # 反馈回复通知
    FOLLOW_UP = "follow_up"       # 随访通知
