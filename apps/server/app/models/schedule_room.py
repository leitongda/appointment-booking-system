import uuid

from sqlalchemy import Column, ForeignKey, Index, Integer, String
from sqlalchemy.orm import relationship

from app.db.base import AuditMixin, Base


class ScheduleRoom(Base, AuditMixin):
    __tablename__ = "schedule_rooms"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True, comment="租户ID")
    store_id = Column(String(36), ForeignKey("stores.id"), nullable=False, index=True, comment="门店ID")
    name = Column(String(100), nullable=False, comment="诊室名称")
    room_number = Column(String(50), nullable=True, comment="房间号")
    floor = Column(String(20), nullable=True, comment="楼层")
    department_id = Column(String(36), ForeignKey("departments.id"), nullable=True, index=True, comment="所属科室")
    capacity = Column(Integer, default=1, comment="容量")
    status = Column(Integer, default=1, comment="状态 0禁用 1启用")
    remark = Column(String(500), nullable=True, comment="备注")

    # 关系
    tenant = relationship("Tenant")
    store = relationship("Store", backref="schedule_rooms")
    department = relationship("Department", backref="schedule_rooms")
    schedules = relationship("Schedule", back_populates="room")

    __table_args__ = (
        Index('uix_room_tenant_store_name', 'tenant_id', 'store_id', 'name', unique=True),
        {'comment': '诊室表'},
    )
