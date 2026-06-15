"""通用枚举"""
from enum import Enum

# ---------- schemas/store_visit_type_config.py ----------

class TimeUnit(str, Enum):
    """时间单位

    来源: schemas/store_visit_type_config.py
    """
    HOURS = "hours"  # 小时
    DAYS = "days"    # 天


class VisitScope(str, Enum):
    """复诊范围

    来源: schemas/store_visit_type_config.py
    """
    SAME_DOCTOR = "same_doctor"          # 同医生
    SAME_DEPARTMENT = "same_department"  # 同科室
    SAME_STORE = "same_store"            # 同门店


# ---------- schemas/behavior_log.py ----------

class Platform(str, Enum):
    """平台枚举

    来源: schemas/behavior_log.py
    """
    ADMIN = "admin"      # 管理后台
    H5 = "h5"            # H5页面
    MINIAPP = "miniapp"  # 小程序


class BehaviorEventType(str, Enum):
    """行为事件类型

    来源: schemas/behavior_log.py
    命名为 BehaviorEventType 以与 core/events.py EventType 区分。
    """
    PAGE_VIEW = "page_view"  # 页面访问
    PAGE_LEAVE = "page_leave"  # 页面离开
    CLICK = "click"            # 点击
    SEARCH = "search"          # 搜索
    CUSTOM = "custom"          # 自定义事件


# ---------- schemas/follow_up.py ----------

class TaskStatus(str, Enum):
    """任务状态

    来源: schemas/follow_up.py
    """
    PENDING = "pending"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    OVERDUE = "overdue"


class PatientCondition(str, Enum):
    """患者状况

    来源: schemas/follow_up.py
    """
    IMPROVED = "improved"
    STABLE = "stable"
    WORSENED = "worsened"


class SelfReportStatus(str, Enum):
    """自报告状态

    来源: schemas/follow_up.py
    """
    PENDING = "pending"
    REVIEWED = "reviewed"


# ---------- schemas/extra_quota.py ----------

class ExtraQuotaType(str, Enum):
    """加号类型

    来源: schemas/extra_quota.py
    """
    NORMAL = "normal"                   # 普通加号
    SPECIAL = "special"                 # 特殊加号
    GREEN_CHANNEL = "green_channel"     # 绿色通道


class ApprovalStatus(str, Enum):
    """审批状态

    来源: schemas/extra_quota.py
    """
    PENDING = "pending"       # 待审批
    APPROVED = "approved"     # 已批准
    REJECTED = "rejected"     # 已拒绝
    CANCELLED = "cancelled"   # 已取消


# ---------- models/email_template.py + schemas/email_template.py ----------

class EmailTemplateType(str, Enum):
    """邮件模板类型

    来源: models/email_template.py + schemas/email_template.py
    """
    APPOINTMENT_CONFIRM = "appointment_confirm"       # 预约确认
    APPOINTMENT_REMIND = "appointment_remind"          # 就诊提醒
    APPOINTMENT_CANCEL = "appointment_cancel"          # 预约取消
    STOP_CLINIC = "stop_clinic"                        # 停诊通知（旧）
    CUSTOM = "custom"                                  # 自定义
    APPOINTMENT_CREATED = "appointment_created"        # 新预约通知
    APPOINTMENT_CANCELLED = "appointment_cancelled"    # 预约取消通知
    CHECKIN = "checkin"                                # 签到通知
    CALL_PATIENT = "call_patient"                      # 叫号通知
    VISIT_COMPLETED = "visit_completed"                # 就诊完成通知
    NO_SHOW = "no_show"                                # 爽约通知
    SCHEDULE_SUSPENDED = "schedule_suspended"           # 停诊通知


# ---------- tasks/notification_task.py ----------

class ReminderLevel(str, Enum):
    """提醒级别

    来源: tasks/notification_task.py
    """
    LEVEL_24H = "24h"
    LEVEL_2H = "2h"
    LEVEL_30MIN = "30min"
