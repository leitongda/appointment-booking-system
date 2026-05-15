from sqlalchemy import Column, String, Boolean, DateTime, UniqueConstraint
from app.db.base import Base
import uuid
from datetime import datetime


class NotificationPreference(Base):
    __tablename__ = "notification_preferences"
    __table_args__ = (
        UniqueConstraint("user_id", "user_type", name="uq_notification_pref_user"),
    )

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), nullable=True, index=True, comment="租户ID")
    user_id = Column(String(36), nullable=False, index=True, comment="用户ID")
    user_type = Column(String(20), nullable=False, comment="用户类型: patient/doctor")
    appointment_enabled = Column(Boolean, default=True, comment="预约通知")
    reminder_enabled = Column(Boolean, default=True, comment="就诊提醒")
    queue_call_enabled = Column(Boolean, default=True, comment="叫号通知")
    stop_clinic_enabled = Column(Boolean, default=True, comment="停诊通知")
    system_enabled = Column(Boolean, default=True, comment="系统通知")
    consultation_enabled = Column(Boolean, default=True, comment="就诊通知")
    feedback_enabled = Column(Boolean, default=True, comment="反馈通知")
    sms_enabled = Column(Boolean, default=True, comment="短信通知")
    email_enabled = Column(Boolean, default=True, comment="邮件通知")
    wechat_enabled = Column(Boolean, default=True, comment="微信推送")
    in_app_enabled = Column(Boolean, default=True, comment="站内消息")
    quiet_hours_start = Column(String(5), nullable=True, comment="免打扰开始时间 HH:MM")
    quiet_hours_end = Column(String(5), nullable=True, comment="免打扰结束时间 HH:MM")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")
