"""核心事件和 WebSocket 枚举"""
from enum import Enum


class EventType(str, Enum):
    """业务事件类型

    来源: core/events.py
    """
    APPOINTMENT_CREATED = "appointment_created"       # 新预约
    APPOINTMENT_CANCELLED = "appointment_cancelled"   # 预约取消
    CHECKIN = "checkin"                               # 患者签到
    CALL_PATIENT = "call_patient"                     # 叫号
    VISIT_COMPLETED = "visit_completed"               # 就诊完成
    NO_SHOW = "no_show"                               # 爽约
    SCHEDULE_SUSPENDED = "schedule_suspended"          # 停诊


class WSMessageType(str, Enum):
    """WebSocket 消息类型

    来源: core/websocket.py
    """
    # 系统消息
    CONNECTED = "CONNECTED"              # 连接成功
    HEARTBEAT = "HEARTBEAT"              # 心跳
    ERROR = "ERROR"                      # 错误

    # 预约相关
    PATIENT_SIGNED_IN = "PATIENT_SIGNED_IN"          # 患者签到
    PATIENT_CALLED = "PATIENT_CALLED"                # 叫号
    PATIENT_PASSED = "PATIENT_PASSED"                # 过号
    PATIENT_RECALLED = "PATIENT_RECALLED"            # 重呼
    PATIENT_COMPLETED = "PATIENT_COMPLETED"          # 就诊完成
    PATIENT_NO_SHOW = "PATIENT_NO_SHOW"              # 爽约
    QUEUE_UPDATED = "QUEUE_UPDATED"                  # 队列更新
    NEW_APPOINTMENT = "NEW_APPOINTMENT"              # 新预约

    # 排班相关
    SCHEDULE_SUSPENDED = "SCHEDULE_SUSPENDED"                    # 排班停诊
    LEAVE_REQUEST_REVIEWED = "LEAVE_REQUEST_REVIEWED"           # 请假审核结果

    # 消息中心
    NEW_MESSAGE = "NEW_MESSAGE"                        # 新消息通知

    # 审批相关
    APPROVAL_PENDING = "APPROVAL_PENDING"              # 新待办
    APPROVAL_APPROVED = "APPROVAL_APPROVED"            # 审批通过
    APPROVAL_REJECTED = "APPROVAL_REJECTED"            # 审批拒绝
    APPROVAL_DELEGATED = "APPROVAL_DELEGATED"          # 审批转交
    APPROVAL_WITHDRAWN = "APPROVAL_WITHDRAWN"          # 审批撤回

    # 系统通知
    SYSTEM_MESSAGE = "SYSTEM_MESSAGE"                  # 系统消息


class RoleType(str, Enum):
    """角色类型枚举

    来源: common/auth_types.py
    """
    ADMIN = "admin"
    DOCTOR = "doctor"
    USER = "user"
    OPERATOR = "operator"
