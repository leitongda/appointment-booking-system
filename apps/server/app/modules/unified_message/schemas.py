"""统一消息中心请求/响应模式

与现有 API 契约 100% 兼容（字段名、null vs 缺失、时间格式）。
"""
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.core.config import settings
from app.enums.notification import (  # noqa: F401 — re-export
    ChannelType,
    DeliveryStatus,
    NotificationEventType,
    NotificationStatus,
    Priority,
    RuleType,
    StrategyType,
)

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
    store_id: str | None = Field(None, description="门店ID")
    recipient_id: str = Field(..., description="接收用户ID")
    recipient_type: str = Field(..., description="用户类型: patient/doctor/admin")
    recipient_phone: str | None = Field(None, description="手机号")
    recipient_email: str | None = Field(None, description="邮箱")
    recipient_openid: str | None = Field(None, description="微信 OpenID")
    template_code: str = Field(..., description="模板代码")
    variables: dict[str, Any] = Field(default_factory=dict, description="模板变量")
    message_type: str = Field(..., description="消息类型")
    related_id: str | None = Field(None, description="关联业务ID")
    channels: list[str] | None = Field(None, description="指定渠道列表")
    priority: int = Field(0, description="优先级 0/1/2")
    title: str | None = Field(None, description="消息标题")
    content: str | None = Field(None, description="消息内容")
    extra_data: dict[str, Any] | None = Field(None, description="额外数据")


class SendResult(BaseModel):
    """单次发送结果"""
    model_config = _CAMEL_CONFIG

    success: bool = Field(..., description="是否成功")
    group_id: str | None = Field(None, description="通知组ID")
    channels_attempted: int = Field(0, description="尝试渠道数")
    channels_succeeded: int = Field(0, description="成功渠道数")
    channels_failed: int = Field(0, description="失败渠道数")
    error_message: str | None = Field(None, description="错误信息")


class BatchSendResult(BaseModel):
    """批量发送结果"""
    model_config = _CAMEL_CONFIG

    total: int = Field(0, description="总数")
    succeeded: int = Field(0, description="成功数")
    failed: int = Field(0, description="失败数")
    results: list[SendResult] = Field(default_factory=list, description="各条结果")


# ---------------------------------------------------------------------------
# 查询相关（与旧 API 兼容）
# ---------------------------------------------------------------------------

class MessageQuery(BaseModel):
    """消息查询参数"""
    model_config = _CAMEL_CONFIG

    message_type: str | None = Field(None, description="消息类型")
    is_read: int | None = Field(None, description="是否已读")
    page: int = Field(1, ge=1)
    page_size: int = Field(10, ge=1, le=settings.MAX_PAGE_SIZE)


class MessageResponse(BaseModel):
    """消息响应（与旧 MessageResponse 字段完全一致）"""
    model_config = _CAMEL_CONFIG

    id: str
    store_id: str | None = None
    user_id: str | None = None
    user_type: str | None = None
    title: str | None = None
    content: str | None = None
    message_type: str | None = None
    related_id: str | None = None
    is_read: int | None = 0
    read_at: datetime | None = None
    created_at: datetime | None = None


class MessageListResponse(BaseModel):
    """消息列表响应（与旧 MessageListResponse 字段完全一致）"""
    model_config = _CAMEL_CONFIG

    id: str
    store_id: str | None = None
    title: str | None = None
    content: str | None = None
    message_type: str | None = None
    is_read: int | None = 0
    created_at: datetime | None = None


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
    event_type: str | None = None
    subject_template: str | None = None
    html_template: str | None = None
    text_template: str | None = None
    wechat_template_id: str | None = None
    wechat_template_mapping: dict[str, Any] | None = None
    variables_schema: dict[str, Any] | None = None
    status: int = Field(1, ge=0, le=1)


class UnifiedTemplateResponse(BaseModel):
    """统一模板响应"""
    model_config = _CAMEL_CONFIG

    id: str
    tenant_id: str | None = None
    code: str | None = None
    name: str | None = None
    message_type: str | None = None
    event_type: str | None = None
    subject_template: str | None = None
    html_template: str | None = None
    text_template: str | None = None
    wechat_template_id: str | None = None
    wechat_template_mapping: dict[str, Any] | None = None
    variables_schema: dict[str, Any] | None = None
    status: int | None = 1
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ChannelStrategyCreate(BaseModel):
    """创建渠道策略"""
    model_config = _CAMEL_CONFIG

    event_type: str
    channels: list[str]
    strategy: str = Field("fallback")
    dedup_window_seconds: int = Field(0)
    priority: str = Field("medium")
    quiet_hours_exempt: bool = Field(False)
    status: int = Field(1, ge=0, le=1)


class ChannelStrategyResponse(BaseModel):
    """渠道策略响应"""
    model_config = _CAMEL_CONFIG

    id: str
    tenant_id: str | None = None
    event_type: str | None = None
    channels: list[str] | None = None
    strategy: str | None = None
    dedup_window_seconds: int | None = 0
    priority: str | None = None
    quiet_hours_exempt: bool | None = False
    status: int | None = 1
    created_at: datetime | None = None
    updated_at: datetime | None = None


class RecipientRuleCreate(BaseModel):
    """创建接收人规则"""
    model_config = _CAMEL_CONFIG

    name: str = Field(..., max_length=100)
    rule_type: str
    rule_config: dict[str, Any]
    event_type: str | None = None
    status: int = Field(1, ge=0, le=1)


class RecipientRuleResponse(BaseModel):
    """接收人规则响应"""
    model_config = _CAMEL_CONFIG

    id: str
    tenant_id: str | None = None
    name: str | None = None
    rule_type: str | None = None
    rule_config: dict[str, Any] | None = None
    event_type: str | None = None
    status: int | None = 1
    created_at: datetime | None = None
    updated_at: datetime | None = None
