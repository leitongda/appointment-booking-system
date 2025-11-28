from sqlalchemy import Column, String, Integer, Text, DateTime, Enum
from app.db.base import Base, TimestampMixin
import uuid
import enum


class MessageType(str, enum.Enum):
    """消息类型"""
    APPOINTMENT = "appointment"  # 预约通知
    CONSULTATION = "consultation"  # 就诊通知
    SCHEDULE = "schedule"  # 排班通知
    SYSTEM = "system"  # 系统通知
    STOP_CLINIC = "stop_clinic"  # 停诊通知


class Message(Base, TimestampMixin):
    """消息模型"""
    __tablename__ = "messages"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), nullable=False, index=True, comment="接收用户ID")
    user_type = Column(String(20), nullable=False, comment="用户类型: patient/doctor")
    title = Column(String(200), nullable=False, comment="消息标题")
    content = Column(Text, comment="消息内容")
    message_type = Column(String(20), default=MessageType.SYSTEM.value, comment="消息类型")
    related_id = Column(String(36), comment="关联业务ID")
    is_read = Column(Integer, default=0, comment="是否已读: 0-未读 1-已读")
    read_at = Column(DateTime, comment="阅读时间")
    
    # 额外数据，JSON格式存储
    extra_data = Column(Text, comment="额外数据(JSON)")


class MessageTemplate(Base, TimestampMixin):
    """消息模板"""
    __tablename__ = "message_templates"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    code = Column(String(50), unique=True, nullable=False, comment="模板编码")
    name = Column(String(100), nullable=False, comment="模板名称")
    message_type = Column(String(20), nullable=False, comment="消息类型")
    title_template = Column(String(200), nullable=False, comment="标题模板")
    content_template = Column(Text, nullable=False, comment="内容模板")
    description = Column(String(255), comment="模板说明")
    status = Column(Integer, default=1, comment="状态: 0-禁用 1-启用")
