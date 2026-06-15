import uuid

from sqlalchemy import Column, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from app.db.base import AuditMixin, Base


class DoctorBookingSetting(Base, AuditMixin):
    """医生预约设置模型"""
    __tablename__ = "doctor_booking_settings"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True, comment="租户ID")
    store_id = Column(String(36), ForeignKey("stores.id"), nullable=False, comment="门店ID")
    doctor_id = Column(String(36), ForeignKey("doctors.id"), nullable=False, comment="医生ID")
    booking_start_offset = Column(Integer, default=0, comment="预约开始偏移天数，0表示当天，n表示n+1天后开始")
    booking_range_days = Column(Integer, default=14, comment="预约范围天数，1-90天")
    release_time = Column(String(5), default="00:00", comment="放号时间 HH:mm格式")
    status = Column(Integer, default=1, comment="状态: 0禁用 1启用")

    # 唯一约束：同一门店同一医生只能有一条设置
    __table_args__ = (
        UniqueConstraint('store_id', 'doctor_id', name='uix_store_doctor'),
    )

    # 关联关系
    tenant = relationship("Tenant", backref="doctor_booking_settings")
    store = relationship("Store", backref="doctor_booking_settings")
    doctor = relationship("Doctor", backref="booking_settings")
