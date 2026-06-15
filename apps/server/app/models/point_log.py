"""积分流水模型"""
import uuid

from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.db.base import AuditMixin, Base


class PointLog(Base, AuditMixin):
    """积分流水记录"""
    __tablename__ = "point_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=True, index=True, comment="租户ID")
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    change_amount = Column(Integer, nullable=False)  # 变更积分（正增负减）
    balance = Column(Integer, nullable=False)  # 变更后余额
    type = Column(Integer, default=4)  # 类型: 1消费 2充值 3赠送 4手动调整
    remark = Column(String(255))  # 备注
    operator_id = Column(String(36))  # 操作人ID
    
    # 关联关系
    user = relationship("User", back_populates="point_logs")
