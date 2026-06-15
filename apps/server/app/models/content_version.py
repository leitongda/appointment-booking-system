"""内容版本历史模型"""
import uuid

from sqlalchemy import Column, String, Text

from app.db.base import Base, TimestampMixin


class ContentVersion(Base, TimestampMixin):
    """内容版本快照，记录每次更新前的状态"""
    __tablename__ = "content_versions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    content_type = Column(String(20), nullable=False, index=True, comment="内容类型: news/notice/banner")
    content_id = Column(String(36), nullable=False, index=True, comment="内容ID")
    operator_id = Column(String(36), nullable=True, comment="操作人ID")
    snapshot = Column(Text, nullable=False, comment="更新前的 JSON 快照")
