"""用户收藏模型"""
import uuid

from sqlalchemy import Column, ForeignKey, String, UniqueConstraint

from app.db.base import AuditMixin, Base


class UserFavorite(Base, AuditMixin):
    """用户收藏表"""
    __tablename__ = "user_favorites"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=True, index=True, comment="租户ID")
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, comment="用户ID")
    target_type = Column(String(20), nullable=False, comment="收藏类型: doctor/department")
    target_id = Column(String(36), nullable=False, comment="收藏目标ID")
    
    # 联合唯一约束：同一用户不能重复收藏同一目标
    __table_args__ = (
        UniqueConstraint('user_id', 'target_type', 'target_id', name='uq_user_favorite'),
    )

