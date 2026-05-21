from sqlalchemy import Column, String, Integer, Text, DateTime, JSON
from app.db.base import Base
import uuid
from datetime import datetime


class NotificationLog(Base):
    __tablename__ = "notification_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), nullable=True, index=True, comment="租户ID")
    store_id = Column(String(36), nullable=True, index=True, comment="门店ID")
    user_id = Column(String(36), nullable=True, index=True, comment="接收用户ID")
    user_type = Column(String(20), nullable=True, comment="用户类型: patient/doctor/admin")
    channel = Column(String(20), nullable=False, index=True, comment="通知通道: sms/email/in_app/wechat")
    message_type = Column(String(30), nullable=True, comment="消息类型: appointment/schedule/system等")
    title = Column(String(200), nullable=True, comment="消息标题")
    content = Column(Text, nullable=True, comment="消息内容")
    status = Column(String(20), nullable=False, default="pending", index=True, comment="发送状态: pending/sent/failed")
    error_message = Column(Text, nullable=True, comment="错误信息")
    recipient = Column(String(200), nullable=True, comment="接收人标识: 手机号/邮箱/openid")
    related_id = Column(String(36), nullable=True, comment="关联业务ID")
    retry_count = Column(Integer, default=0, comment="重试次数")
    max_retries = Column(Integer, default=3, comment="最大重试次数")
    next_retry_at = Column(DateTime, nullable=True, comment="下次重试时间")
    sent_at = Column(DateTime, nullable=True, comment="实际发送时间")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    extra_data = Column(JSON, nullable=True, comment="额外数据")
    primary_channel = Column(String(20), nullable=True, comment="首选渠道（降级场景下记录原始目标渠道）")
    fallback_reason = Column(String(200), nullable=True, comment="降级原因（如: 渠道不可用/发送失败/API异常）")
    channel_attempt_order = Column(Integer, nullable=True, comment="当前渠道在降级链中的尝试顺序（0=首选渠道）")
