from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List, Any
from datetime import datetime
from enum import Enum
from app.core.config import settings


def to_camel(string: str) -> str:
    components = string.split('_')
    return components[0] + ''.join(x.title() for x in components[1:])


class NotificationChannel(str, Enum):
    """通知通道"""
    SMS = "sms"
    EMAIL = "email"
    IN_APP = "in_app"
    WECHAT = "wechat"


class NotificationStatus(str, Enum):
    """通知状态"""
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    PERMANENTLY_FAILED = "permanently_failed"


class NotificationLogCreate(BaseModel):
    """创建通知日志"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    channel: NotificationChannel = Field(..., description="通知通道")
    message_type: Optional[str] = Field(None, max_length=30, description="消息类型")
    title: Optional[str] = Field(None, max_length=200, description="消息标题")
    content: Optional[str] = Field(None, description="消息内容")
    recipient: str = Field(..., max_length=200, description="接收人标识")
    user_id: Optional[str] = Field(None, description="接收用户ID")
    user_type: Optional[str] = Field(None, max_length=20, description="用户类型")
    related_id: Optional[str] = Field(None, description="关联业务ID")
    tenant_id: Optional[str] = Field(None, description="租户ID")
    store_id: Optional[str] = Field(None, description="门店ID")
    extra_data: Optional[dict] = Field(None, description="额外数据")


class NotificationLogResponse(BaseModel):
    """通知日志响应"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
        by_alias=True,
    )

    id: str
    tenant_id: Optional[str] = None
    store_id: Optional[str] = None
    user_id: Optional[str] = None
    user_type: Optional[str] = None
    channel: Optional[str] = None
    message_type: Optional[str] = None
    title: Optional[str] = None
    content: Optional[str] = None
    status: Optional[str] = None
    error_message: Optional[str] = None
    recipient: Optional[str] = None
    related_id: Optional[str] = None
    retry_count: Optional[int] = None
    max_retries: Optional[int] = None
    next_retry_at: Optional[datetime] = None
    sent_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    extra_data: Optional[dict] = None


class NotificationLogQuery(BaseModel):
    """通知日志查询参数"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    channel: Optional[NotificationChannel] = Field(None, description="通知通道")
    status: Optional[NotificationStatus] = Field(None, description="发送状态")
    message_type: Optional[str] = Field(None, description="消息类型")
    user_id: Optional[str] = Field(None, description="用户ID")
    store_id: Optional[str] = Field(None, description="门店ID")
    start_date: Optional[datetime] = Field(None, description="开始日期")
    end_date: Optional[datetime] = Field(None, description="结束日期")
    page: int = Field(1, ge=1)
    page_size: int = Field(10, ge=1, le=settings.MAX_PAGE_SIZE)


class NotificationLogStats(BaseModel):
    """通知日志统计"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        by_alias=True,
    )

    total: int = 0
    sent: int = 0
    failed: int = 0
    pending: int = 0
    failure_rate: float = 0.0
    by_channel: dict = Field(default_factory=dict)
    by_type: dict = Field(default_factory=dict)


class NotificationUsageStats(BaseModel):
    """通知用量统计"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        by_alias=True,
    )

    period: dict
    total: int
    by_channel: dict = Field(default_factory=dict)
    by_type: dict = Field(default_factory=dict)
    by_status: dict = Field(default_factory=dict)
    daily_trend: list = Field(default_factory=list)


class NotificationQuotaInfo(BaseModel):
    """通知配额信息"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        by_alias=True,
    )

    tenant_id: str
    quotas: dict = Field(default_factory=dict)
    usage: dict = Field(default_factory=dict)
    remaining: dict = Field(default_factory=dict)
    usage_percent: dict = Field(default_factory=dict)
    period_start: str
    period_end: str


class NotificationQuotaUpdate(BaseModel):
    """通知配额更新"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    sms_monthly_limit: Optional[int] = None
    email_monthly_limit: Optional[int] = None
    wechat_monthly_limit: Optional[int] = None
    in_app_monthly_limit: Optional[int] = None
