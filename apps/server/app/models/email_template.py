from sqlalchemy import Column, String, Integer, Text, Enum
from app.db.base import Base, AuditMixin
import uuid
import enum


class EmailTemplateType(str, enum.Enum):
    """邮件模板类型"""
    APPOINTMENT_CONFIRM = "appointment_confirm"      # 预约确认
    APPOINTMENT_REMIND = "appointment_remind"         # 就诊提醒
    APPOINTMENT_CANCEL = "appointment_cancel"         # 预约取消
    STOP_CLINIC = "stop_clinic"                       # 停诊通知（旧）
    CUSTOM = "custom"                                 # 自定义
    # 事件钩子模板类型
    APPOINTMENT_CREATED = "appointment_created"       # 新预约通知
    APPOINTMENT_CANCELLED = "appointment_cancelled"   # 预约取消通知
    CHECKIN = "checkin"                               # 签到通知
    CALL_PATIENT = "call_patient"                     # 叫号通知
    VISIT_COMPLETED = "visit_completed"               # 就诊完成通知
    NO_SHOW = "no_show"                               # 爽约通知
    SCHEDULE_SUSPENDED = "schedule_suspended"          # 停诊通知


class EmailTemplate(Base, AuditMixin):
    """邮件模板模型"""
    __tablename__ = "email_templates"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), nullable=True, index=True, comment="租户ID")
    code = Column(String(50), unique=True, nullable=False, comment="模板编码")
    name = Column(String(100), nullable=False, comment="模板名称")
    template_type = Column(String(30), default=EmailTemplateType.CUSTOM.value, comment="模板类型")
    subject_template = Column(String(200), nullable=False, comment="邮件主题模板")
    content_template = Column(Text, nullable=False, comment="邮件内容模板(HTML)")
    description = Column(String(255), comment="模板说明")
    status = Column(Integer, default=1, comment="状态: 0-禁用 1-启用")

