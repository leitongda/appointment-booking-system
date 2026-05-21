'''
Author: Lei TongDa ebian123@qq.com
Date: 2026-01-05 23:11:43
LastEditors: Lei TongDa ebian123@qq.com
LastEditTime: 2026-02-04 15:46:38
FilePath: /appointment-booking-system/apps/server/app/models/schedule.py
Description:

Copyright (c) 2026 by ${git_name_email}, All Rights Reserved.
'''
from sqlalchemy import Column, String, Integer, Date, Time, ForeignKey, DateTime, Index
from sqlalchemy.orm import relationship
from app.db.base import Base, AuditMixin
import uuid

class Schedule(Base, AuditMixin):
    __tablename__ = "schedules"

    # NOTE: 在 PG 中 start_time/end_time 为 NULL 时唯一索引不生效（NULL != NULL）。
    # 生产环境需通过应用层逻辑（规则引擎）保证同一医生同一时段不重复。
    __table_args__ = (
        Index('uix_schedule_doctor_date_time', 'doctor_id', 'schedule_date', 'start_time', 'end_time', unique=True),
    )

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    doctor_id = Column(String(36), ForeignKey("doctors.id"), nullable=False)
    # 租户关联（多租户支持）
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=True, index=True, comment="租户ID")
    store_id = Column(String(36), ForeignKey("stores.id"), nullable=True, comment="门店ID")
    template_id = Column(String(36), ForeignKey("schedule_templates.id"), nullable=True, comment="来源模板ID")
    shift_type_id = Column(String(36), ForeignKey("shift_types.id"), nullable=True, comment="班次类型ID")
    room_id = Column(String(36), ForeignKey("schedule_rooms.id"), nullable=True, index=True, comment="诊室ID")
    rule_set_id = Column(String(36), ForeignKey("rule_sets.id"), nullable=True, index=True, comment="关联规则组ID")
    schedule_date = Column(Date, nullable=False)
    time_slot = Column(String(10), nullable=True, comment="时段: AM/PM/morning/afternoon/evening，可为空（自定义排班可通过start_time计算）")
    start_time = Column(Time)
    end_time = Column(Time)
    start_at = Column(DateTime(timezone=True), nullable=True, comment="开始时间(带时区)")
    end_at = Column(DateTime(timezone=True), nullable=True, comment="结束时间(带时区)")
    timezone = Column(String(50), nullable=True, default="Asia/Shanghai", comment="时区")
    total_slots = Column(Integer, default=10)  # 总号源 (向后兼容, 自动由 quota 字段计算)
    booked_slots = Column(Integer, default=0)  # 已预约数
    appointment_type = Column(String(20), default="normal", comment="预约类型: urgent/normal/expert/medical_insurance/self_pay")
    status = Column(Integer, default=1)  # 0停诊 1正常 (legacy, 保持向后兼容)
    schedule_status = Column(
        String(20), default="published", nullable=False,
        comment="排班状态: draft/published/booking/full/suspended/finished/withdrawn（已包含原 publish_status 语义）",
    )

    # 号源拆分字段
    online_quota = Column(Integer, default=0, comment="线上号源")
    offline_quota = Column(Integer, default=0, comment="线下号源")
    reserved_quota = Column(Integer, default=0, comment="预留号源")
    extra_quota = Column(Integer, default=0, comment="加号号源")
    fee = Column(Integer, default=0, comment="挂号费(分)")

    @property
    def computed_total_slots(self) -> int:
        """由四类号源计算总号源数。"""
        return (
            (self.online_quota or 0)
            + (self.offline_quota or 0)
            + (self.reserved_quota or 0)
            + (self.extra_quota or 0)
        )

    def sync_total_slots(self):
        """将 total_slots 同步为 quota 字段之和。"""
        self.total_slots = self.computed_total_slots

    # 关联关系
    tenant = relationship("Tenant", back_populates="schedules")
    doctor = relationship("Doctor", back_populates="schedules")
    store = relationship("Store", backref="schedules")
    template = relationship("ScheduleTemplate", back_populates="schedules")
    appointments = relationship("Appointment", back_populates="schedule")
    room = relationship("ScheduleRoom", back_populates="schedules")
