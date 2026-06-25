"""
统一通知 Schema
"""
from typing import Any

from pydantic import BaseModel, Field

from app.enums.notification import (  # noqa: F401 — re-export
    NotificationChannel,
    NotificationPriority,
)


class NotificationEvent(BaseModel):
    """通知事件

    统一的通知事件数据结构，用于所有渠道的通知发送。
    """
    tenant_id: str = Field(..., description="租户ID")
    store_id: str | None = Field(None, description="门店ID")
    recipient_id: str = Field(..., description="接收用户ID")
    recipient_type: str = Field(..., description="接收用户类型: patient/doctor/admin")
    recipient_phone: str | None = Field(None, description="接收人手机号（短信需要）")
    recipient_email: str | None = Field(None, description="接收人邮箱（邮件需要）")
    recipient_openid: str | None = Field(None, description="接收人微信 OpenID（微信需要）")
    # 第三方集成平台收件人ID（可选，渠道内会自动查 IntegrationBinding）
    recipient_dingtalk_id: str | None = Field(None, description="接收人钉钉 userId")
    recipient_wecom_id: str | None = Field(None, description="接收人企业微信 userid")
    recipient_feishu_id: str | None = Field(None, description="接收人飞书 open_id")
    template_code: str = Field(..., description="模板代码")
    variables: dict[str, Any] = Field(default_factory=dict, description="模板变量")
    message_type: str = Field(..., description="消息类型: appointment/reminder/stop_clinic/system/consultation/feedback/queue_call")
    related_id: str | None = Field(None, description="关联业务ID")
    channels: list[str] | None = Field(None, description="指定渠道列表，None 表示使用默认渠道策略")
    priority: NotificationPriority = Field(default=NotificationPriority.NORMAL, description="通知优先级")
    title: str | None = Field(None, description="消息标题（可选，用于覆盖模板标题）")
    content: str | None = Field(None, description="消息内容（可选，用于覆盖模板内容）")
    extra_data: dict[str, Any] | None = Field(None, description="额外数据")


class NotificationContent(BaseModel):
    """渲染后的通知内容"""
    title: str = Field(..., description="消息标题")
    content: str = Field(..., description="消息内容")
    template_variables: dict[str, Any] = Field(default_factory=dict, description="模板变量")


class FallbackContext(BaseModel):
    """降级上下文

    记录通知渠道降级时的诊断信息，帮助调试和用户支持。
    """
    primary_channel: str = Field(..., description="首选渠道（降级前的目标渠道）")
    actual_channel: str = Field(..., description="实际发送成功的渠道")
    failed_channels: list[str] = Field(default_factory=list, description="降级过程中失败的渠道列表")
    fallback_reasons: dict[str, str] = Field(default_factory=dict, description="各失败渠道的降级原因，key=渠道名, value=原因")


class NotificationSendResult(BaseModel):
    """单条通知发送结果"""
    channel: str = Field(..., description="渠道名称")
    success: bool = Field(..., description="是否发送成功")
    error_message: str | None = Field(None, description="错误信息")
    is_fallback: bool = Field(default=False, description="是否为降级渠道发送")
    attempt_order: int = Field(default=0, description="在降级链中的尝试顺序（0=首选）")


class NotificationDispatchResult(BaseModel):
    """通知分发结果"""
    event: NotificationEvent = Field(..., description="原始事件")
    results: dict[str, NotificationSendResult] = Field(default_factory=dict, description="各渠道发送结果")
    total_channels: int = Field(default=0, description="尝试发送的渠道数")
    success_channels: int = Field(default=0, description="成功发送的渠道数")
    failed_channels: int = Field(default=0, description="发送失败的渠道数")
    skipped_channels: int = Field(default=0, description="因偏好/配置跳过的渠道数")
    fallback_context: FallbackContext | None = Field(None, description="降级上下文（仅在降级场景下有值）")
