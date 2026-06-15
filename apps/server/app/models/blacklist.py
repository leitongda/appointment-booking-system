"""黑名单模型"""
import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.db.base import AuditMixin, Base


class Blacklist(Base, AuditMixin):
    """黑名单表"""
    __tablename__ = "blacklists"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=True, index=True, comment="租户ID")
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True, comment="用户ID，可选")
    store_id = Column(String(36), ForeignKey("stores.id"), nullable=True, comment="门店ID，可选，不选则针对所有门店")
    keyword = Column(String(50), comment="手机号或身份证关键词")
    reason = Column(String(500), comment="黑名单原因/备注")
    no_show_count = Column(Integer, default=0, comment="爽约次数（自动触发时记录）")
    source = Column(Integer, default=1, comment="来源: 1手动添加 2自动触发")
    expire_at = Column(DateTime, comment="解禁时间")
    released_at = Column(DateTime, comment="实际解禁时间")
    status = Column(Integer, default=1, comment="状态: 1生效 0已解禁")
    
    # 关联关系
    tenant = relationship("Tenant")
    user = relationship("User", foreign_keys=[user_id])
    store = relationship("Store", foreign_keys=[store_id])
