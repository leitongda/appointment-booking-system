import uuid

from sqlalchemy import Column, ForeignKey, Integer, String, Text, UniqueConstraint

from app.db.base import AuditMixin, Base
from app.enums.general import EmailTemplateType  # noqa: F401 — re-export for backward compat


class EmailTemplate(Base, AuditMixin):
    """邮件模板模型"""
    __tablename__ = "email_templates"
    __table_args__ = (
        UniqueConstraint("code", "tenant_id", name="uq_email_template_code_tenant"),
    )

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=True, index=True, comment="租户ID")
    code = Column(String(50), nullable=False, comment="模板编码")
    name = Column(String(100), nullable=False, comment="模板名称")
    template_type = Column(String(30), default=EmailTemplateType.CUSTOM.value, comment="模板类型")
    subject_template = Column(String(200), nullable=False, comment="邮件主题模板")
    content_template = Column(Text, nullable=False, comment="邮件内容模板(HTML)")
    description = Column(String(255), comment="模板说明")
    status = Column(Integer, default=1, comment="状态: 0-禁用 1-启用")

