import uuid

from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.db.base import AuditMixin, Base


class StoreVisitTypeConfig(Base, AuditMixin):
    """门店复诊规则配置模型"""
    __tablename__ = "store_visit_type_configs"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    store_id = Column(String(36), ForeignKey("stores.id", ondelete="CASCADE"), 
                      nullable=False, unique=True, comment="门店ID")
    time_limit = Column(Integer, default=30, nullable=False, comment="复诊时间限制值")
    time_unit = Column(String(10), default="days", nullable=False, 
                       comment="时间单位：hours/days")
    scope = Column(String(20), default="same_doctor", nullable=False, 
                   comment="复诊范围：same_doctor/same_department/same_store")
    status = Column(Integer, default=1, comment="状态: 0禁用 1启用")
    
    # 关联关系
    store = relationship("Store", backref="visit_type_config")

