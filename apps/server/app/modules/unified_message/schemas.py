"""统一消息中心请求/响应模式

与现有 API 契约 100% 兼容（字段名、null vs 缺失、时间格式）。
"""
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.core.config import settings


# ---------------------------------------------------------------------------
# 枚举
# ---------------------------------------------------------------------------

class NotificationEventType(str, Enum):
    """通知事件类型"""
    APPOINTMENT_SUCCESS = "appointment.success"
    APPOINTMENT_REMINDER_24H = "appointment.reminder.24h"
    APPOINTMENT_REMINDER_1H = "appointment.reminder.1h"
    APPOINTMENT_CANCELLED = "appointment.cancelled"
    SCHEDULE_CHANGE = "schedule.change"
    SCHEDULE_STOP = "schedule.stop"
    STOP_CLINIC = "stop_clinic"
    SYSTEM = "system"


class NotificationStatus(str, Enum):
    """通知状态"""
    PENDING = "pending"
    PARTIAL = "partial"
    SENT = "sent"
    FAILED = "failed"


class DeliveryStatus(str, Enum):
    """投递状态"""
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    PERMANENTLY_FAILED = "permanently_failed"


class ChannelType(str, Enum):
    """渠道类型"""
    IN_APP = "in_app"
    SMS = "sms"
    EMAIL = "email"
    WECHAT = "wechat"
    WEBSOCKET = "websocket"


class Priority(str, Enum):
    """优先级"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class StrategyType(str, Enum):
    """渠道策略类型"""
    FALLBACK = "fallback"
    PARALLEL = "parallel"
    ALL = "all"


class RuleType(str, Enum):
    """接收人规则类型"""
    ROLE = "role"
    DEPARTMENT = "department"
    USER_LIST = "user_list"
    DYNAMIC = "dynamic"
    EVENT_DRIVEN = "event_driven"


# ---------------------------------------------------------------------------
# 通用配置
# ---------------------------------------------------------------------------

def _to_camel(s: str) -> str:
    parts = s.split("_")
    return parts[0] + "".join(x.title() for x in parts[1:])


_CAMEL_CONFIG = ConfigDict(
    alias_generator=_to_camel,
    populate_by_name=True,
    from_attributes=True,
    by_alias=True,
)


# ---------------------------------------------------------------------------
# 发送相关
# ---------------------------------------------------------------------------

class NotificationEvent(BaseModel):
    """统一通知事件（兼容旧 NotificationEvent，扩展新字段）"""
    model_config = _CAMEL_CONFIG

    tenant_id: str = Field(..., description="租户ID")
    store_id: Optional[str] = Field(None, description="门店ID")
    recipient_id: str = Field(..., description="接收用户ID")
    recipient_type: str = Field(..., description="用户类型: patient/doctor/admin")
    recipient_phone: Optional[str] = Field(None, description="手机号")
    recipient_email: Optional[str] = Field(None, description="邮箱")
    recipient_openid: Optional[str] = Field(None, description="微信 OpenID")
    template_code: str = Field(..., description="模板代码")
    variables: Dict[str, Any] = Field(default_factory=dict, description="模板变量")
    message_type: str = Field(..., description="消息类型")
    related_id: Optional[str] = Field(None, description="关联业务ID")
    channels: Optional[List[str]] = Field(None, description="指定渠道列表")
    priority: int = Field(0, description="优先级 0/1/2")
    title: Optional[str] = Field(None, description="消息标题")
    content: Optional[str] = Field(None, description="消息内容")
    extra_data: Optional[Dict[str, Any]] = Field(None, description="额外数据")


class SendResult(BaseModel):
    """单次发送结果"""
    model_config = _CAMEL_CONFIG

    success: bool = Field(..., description="是否成功")
    group_id: Optional[str] = Field(None, description="通知组ID")
    channels_attempted: int = Field(0, description="尝试渠道数")
    channels_succeeded: int = Field(0, description="成功渠道数")
    channels_failed: int = Field(0, description="失败渠道数")
    error_message: Optional[str] = Field(None, description="错误信息")


class BatchSendResult(BaseModel):
    """批量发送结果"""
    model_config = _CAMEL_CONFIG

    total: int = Field(0, description="总数")
    succeeded: int = Field(0, description="成功数")
    failed: int = Field(0, description="失败数")
    results: List[SendResult] = Field(default_factory=list, description="各条结果")


# ---------------------------------------------------------------------------
# 查询相关（与旧 API 兼容）
# ---------------------------------------------------------------------------

class MessageQuery(BaseModel):
    """消息查询参数"""
    model_config = _CAMEL_CONFIG

    message_type: Optional[str] = Field(None, description="消息类型")
    is_read: Optional[int] = Field(None, description="是否已读")
    page: int = Field(1, ge=1)
    page_size: int = Field(10, ge=1, le=settings.MAX_PAGE_SIZE)


class MessageResponse(BaseModel):
    """消息响应（与旧 MessageResponse 字段完全一致）"""
    model_config = _CAMEL_CONFIG

    id: str
    store_id: Optional[str] = None
    user_id: Optional[str] = None
    user_type: Optional[str] = None
    title: Optional[str] = None
    content: Optional[str] = None
    message_type: Optional[str] = None
    related_id: Optional[str] = None
    is_read: Optional[int] = 0
    read_at: Optional[datetime] = None
    created_at: Optional[datetime] = None


class MessageListResponse(BaseModel):
    """消息列表响应（与旧 MessageListResponse 字段完全一致）"""
    model_config = _CAMEL_CONFIG

    id: str
    store_id: Optional[str] = None
    title: Optional[str] = None
    content: Optional[str] = None
    message_type: Optional[str] = None
    is_read: Optional[int] = 0
    created_at: Optional[datetime] = None


class UnreadCountResponse(BaseModel):
    """未读消息数量（与旧 UnreadCountResponse 字段完全一致）"""
    model_config = _CAMEL_CONFIG

    total: int = 0
    appointment: int = 0
    consultation: int = 0
    schedule: int = 0
    system: int = 0
    stop_clinic: int = 0
    feedback: int = 0


# ---------------------------------------------------------------------------
# 模型 CRUD 相关
# ---------------------------------------------------------------------------

class UnifiedTemplateCreate(BaseModel):
    """创建统一模板"""
    model_config = _CAMEL_CONFIG

    code: str = Field(..., max_length=50)
    name: str = Field(..., max_length=100)
    message_type: str
    event_type: Optional[str] = None
    subject_template: Optional[str] = None
    html_template: Optional[str] = None
    text_template: Optional[str] = None
    wechat_template_id: Optional[str] = None
    wechat_template_mapping: Optional[Dict[str, Any]] = None
    variables_schema: Optional[Dict[str, Any]] = None
    status: int = Field(1, ge=0, le=1)


class UnifiedTemplateResponse(BaseModel):
    """统一模板响应"""
    model_config = _CAMEL_CONFIG

    id: str
    tenant_id: Optional[str] = None
    code: Optional[str] = None
    name: Optional[str] = None
    message_type: Optional[str] = None
    event_type: Optional[str] = None
    subject_template: Optional[str] = None
    html_template: Optional[str] = None
    text_template: Optional[str] = None
    wechat_template_id: Optional[str] = None
    wechat_template_mapping: Optional[Dict[str, Any]] = None
    variables_schema: Optional[Dict[str, Any]] = None
    status: Optional[int] = 1
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ChannelStrategyCreate(BaseModel):
    """创建渠道策略"""
    model_config = _CAMEL_CONFIG

    event_type: str
    channels: List[str]
    strategy: str = Field("fallback")
    dedup_window_seconds: int = Field(0)
    priority: str = Field("medium")
    quiet_hours_exempt: bool = Field(False)
    status: int = Field(1, ge=0, le=1)


class ChannelStrategyResponse(BaseModel):
    """渠道策略响应"""
    model_config = _CAMEL_CONFIG

    id: str
    tenant_id: Optional[str] = None
    event_type: Optional[str] = None
    channels: Optional[List[str]] = None
    strategy: Optional[str] = None
    dedup_window_seconds: Optional[int] = 0
    priority: Optional[str] = None
    quiet_hours_exempt: Optional[bool] = False
    status: Optional[int] = 1
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class RecipientRuleCreate(BaseModel):
    """创建接收人规则"""
    model_config = _CAMEL_CONFIG

    name: str = Field(..., max_length=100)
    rule_type: str
    rule_config: Dict[str, Any]
    event_type: Optional[str] = None
    status: int = Field(1, ge=0, le=1)


class RecipientRuleResponse(BaseModel):
    """接收人规则响应"""
    model_config = _CAMEL_CONFIG

    id: str
    tenant_id: Optional[str] = None
    name: Optional[str] = None
    rule_type: Optional[str] = None
    rule_config: Optional[Dict[str, Any]] = None
    event_type: Optional[str] = None
    status: Optional[int] = 1
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
