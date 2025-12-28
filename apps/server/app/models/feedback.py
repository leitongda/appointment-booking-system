from sqlalchemy import Column, String, Integer, Text, DateTime
from app.db.base import Base, AuditMixin
import uuid
import enum


class FeedbackType(str, enum.Enum):
    """反馈类型"""
    SUGGESTION = "suggestion"  # 建议
    COMPLAINT = "complaint"  # 投诉
    BUG = "bug"  # 问题反馈
    OTHER = "other"  # 其他


class FeedbackStatus(str, enum.Enum):
    """反馈状态"""
    PENDING = "pending"  # 待处理
    PROCESSING = "processing"  # 处理中
    RESOLVED = "resolved"  # 已解决
    CLOSED = "closed"  # 已关闭


class Feedback(Base, AuditMixin):
    """用户反馈模型"""
    __tablename__ = "feedbacks"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), nullable=False, index=True, comment="用户ID")
    user_type = Column(String(20), default="patient", comment="用户类型: patient/doctor")
    feedback_type = Column(String(20), default=FeedbackType.SUGGESTION.value, comment="反馈类型")
    title = Column(String(200), nullable=False, comment="反馈标题")
    content = Column(Text, nullable=False, comment="反馈内容")
    images = Column(Text, comment="图片URL列表(JSON)")
    contact = Column(String(50), comment="联系方式")
    status = Column(String(20), default=FeedbackStatus.PENDING.value, comment="状态")
    
    # 处理信息
    handler_id = Column(String(36), comment="处理人ID")
    reply = Column(Text, comment="回复内容")
    handled_at = Column(DateTime, comment="处理时间")
