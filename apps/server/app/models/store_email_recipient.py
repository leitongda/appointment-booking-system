"""门店邮件接收人模型"""
import uuid

from sqlalchemy import Column, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.db.base import AuditMixin, Base


class StoreEmailRecipient(Base, AuditMixin):
    """门店邮件接收人

    每个门店可绑定多个邮件接收人，每人可订阅不同的业务事件通知。
    event_types 以 JSON 数组形式存储，如 ["appointment_created", "checkin", "no_show"]
    """
    __tablename__ = "store_email_recipients"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    store_id = Column(String(36), ForeignKey("stores.id"), nullable=False, index=True, comment="门店ID")
    # 租户维度（p3a8）：经 store_id 回填
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=True, index=True,
                       comment="租户ID")
    name = Column(String(50), nullable=False, comment="接收人姓名")
    email = Column(String(100), nullable=False, comment="邮箱地址")
    event_types = Column(Text, comment="订阅事件类型(JSON数组)")
    status = Column(Integer, default=1, comment="状态: 0-禁用 1-启用")

    # 关联关系
    store = relationship("Store", backref="email_recipients", lazy="selectin")
