"""统一模板模型

从 app.modules.unified_message.models 移至此处，
消除 infrastructure.notifications.channels.wechat -> modules.unified_message.models 的反向依赖。
数据模型属于基础设施层（models），不属于业务模块层（modules）。
"""
import uuid

from sqlalchemy import (
    JSON,
    Column,
    Integer,
    String,
    Text,
    UniqueConstraint,
)

from app.db.base import Base, TimestampMixin


def _uuid() -> str:
    return str(uuid.uuid4())


class UnifiedTemplate(Base, TimestampMixin):
    """统一模板：所有渠道共享"""
    __tablename__ = "unified_templates"
    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_unified_template_tenant_code"),
    )

    id = Column(String(36), primary_key=True, default=_uuid)
    tenant_id = Column(String(36), nullable=False, index=True, comment="租户ID")
    code = Column(String(50), nullable=False, comment="模板编码: appointment_success")
    name = Column(String(100), nullable=False, comment="模板名称")
    message_type = Column(String(30), nullable=False, comment="消息类型")
    event_type = Column(String(50), nullable=True, comment="事件类型: appointment.success")
    # 各渠道模板内容
    subject_template = Column(String(200), nullable=True, comment="邮件主题模板")
    html_template = Column(Text, nullable=True, comment="邮件 HTML 模板")
    text_template = Column(Text, nullable=True, comment="短信/站内信纯文本模板")
    wechat_template_id = Column(String(50), nullable=True, comment="微信模板 ID")
    wechat_template_mapping = Column(JSON, nullable=True, comment="微信字段映射")
    # 第三方集成平台模板
    dingtalk_msg_template = Column(JSON, nullable=True, comment="钉钉工作通知消息体模板")
    wecom_msg_template = Column(JSON, nullable=True, comment="企业微信应用消息模板")
    feishu_msg_template = Column(JSON, nullable=True, comment="飞书消息模板")
    robot_msg_template = Column(Text, nullable=True, comment="群机器人通用 markdown 模板（三平台共用）")
    # 通用
    variables_schema = Column(JSON, nullable=True, comment="变量定义和默认值")
    status = Column(Integer, default=1, comment="状态: 0-禁用 1-启用")
