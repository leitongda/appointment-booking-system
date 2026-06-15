from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.config import settings
from app.enums.notification import NotificationChannel  # noqa: F401 — re-export
from app.enums.notification import NotificationLogStatus as NotificationStatus
from app.schemas.response import to_camel


class NotificationLogCreate(BaseModel):
    """创建通知日志"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    channel: NotificationChannel = Field(..., description="通知通道")
    message_type: str | None = Field(None, max_length=30, description="消息类型")
    title: str | None = Field(None, max_length=200, description="消息标题")
    content: str | None = Field(None, description="消息内容")
    recipient: str = Field(..., max_length=200, description="接收人标识")
    user_id: str | None = Field(None, description="接收用户ID")
    user_type: str | None = Field(None, max_length=20, description="用户类型")
    related_id: str | None = Field(None, description="关联业务ID")
    tenant_id: str | None = Field(None, description="租户ID")
    store_id: str | None = Field(None, description="门店ID")
    extra_data: dict | None = Field(None, description="额外数据")

class NotificationLogResponse(BaseModel):
    """通知日志响应"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
        by_alias=True,
    )

    id: str
    tenant_id: str | None = None
    store_id: str | None = None
    user_id: str | None = None
    user_type: str | None = None
    channel: str | None = None
    message_type: str | None = None
    title: str | None = None
    content: str | None = None
    status: str | None = None
    error_message: str | None = None
    recipient: str | None = None
    related_id: str | None = None
    retry_count: int | None = None
    max_retries: int | None = None
    next_retry_at: datetime | None = None
    sent_at: datetime | None = None
    created_at: datetime | None = None
    extra_data: dict | None = None

class NotificationLogQuery(BaseModel):
    """通知日志查询参数"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    channel: NotificationChannel | None = Field(None, description="通知通道")
    status: NotificationStatus | None = Field(None, description="发送状态")
    message_type: str | None = Field(None, description="消息类型")
    user_id: str | None = Field(None, description="用户ID")
    store_id: str | None = Field(None, description="门店ID")
    start_date: datetime | None = Field(None, description="开始日期")
    end_date: datetime | None = Field(None, description="结束日期")
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

    sms_monthly_limit: int | None = None
    email_monthly_limit: int | None = None
    wechat_monthly_limit: int | None = None
    in_app_monthly_limit: int | None = None
