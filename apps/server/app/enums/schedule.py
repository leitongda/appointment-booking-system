"""排班相关枚举"""
from enum import Enum


class AppointmentType(str, Enum):
    """预约类型

    来源: schemas/schedule_template.py
    """
    URGENT = "urgent"                    # 加急
    NORMAL = "normal"                    # 普通
    EXPERT = "expert"                    # 专家
    MEDICAL_INSURANCE = "medical_insurance"  # 医保
    SELF_PAY = "self_pay"                # 自费


class ScheduleMode(str, Enum):
    """排班方式

    来源: schemas/schedule_template.py
    """
    WEEKLY = "weekly"              # 每周循环
    MONTH_WEEK_1 = "month_week_1"  # 每月第一周
    MONTH_WEEK_2 = "month_week_2"  # 每月第二周
    MONTH_WEEK_3 = "month_week_3"  # 每月第三周
    MONTH_WEEK_4 = "month_week_4"  # 每月第四周
    MONTH_WEEK_5 = "month_week_5"  # 每月第五周
    YEAR_ODD_WEEK = "year_odd_week"   # 本年奇数周
    YEAR_EVEN_WEEK = "year_even_week"  # 本年偶数周


class ActionType(str, Enum):
    """操作类型

    来源: schemas/schedule_generation_log.py
    """
    GENERATE = "generate"  # 生成排班
    DELETE = "delete"      # 删除排班
    SUSPEND = "suspend"    # 批量停诊


class RequestType(str, Enum):
    """申请类型

    来源: models/leave_request.py + schemas/leave_request.py
    """
    STOP_CLINIC = "stop_clinic"          # 停诊申请
    SCHEDULE_CHANGE = "schedule_change"  # 调班申请


class RequestStatus(str, Enum):
    """申请状态

    来源: models/leave_request.py + schemas/leave_request.py
    """
    PENDING = "pending"      # 待审核
    APPROVED = "approved"    # 已通过
    REJECTED = "rejected"    # 已拒绝
    CANCELLED = "cancelled"  # 已取消


class Period(str, Enum):
    """时段

    来源: schemas/leave_request.py
    """
    MORNING = "morning"      # 上午
    AFTERNOON = "afternoon"  # 下午
    EVENING = "evening"      # 晚上
    ALL = "all"              # 全天


class SuspensionProcessingStatus(str, Enum):
    """排班暂停处理状态"""
    PENDING = "pending"        # 待处理
    PROCESSING = "processing"  # 处理中
    COMPLETED = "completed"    # 已完成
    FAILED = "failed"          # 处理失败
