'''
Author: Lei TongDa ebian123@qq.com
Date: 2026-01-05 23:11:43
LastEditors: Lei TongDa ebian123@qq.com
LastEditTime: 2026-02-04 15:46:38
FilePath: /appointment-booking-system/apps/server/app/models/schedule.py
Description:

Copyright (c) 2026 by ${git_name_email}, All Rights Reserved.
'''
from sqlalchemy import Column, String, Integer, Date, Time, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from app.db.base import Base, AuditMixin
import uuid

class Schedule(Base, AuditMixin):
    __tablename__ = "schedules"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    doctor_id = Column(String(36), ForeignKey("doctors.id"), nullable=False)
    # 租户关联（多租户支持）
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=True, index=True, comment="租户ID")
    store_id = Column(String(36), ForeignKey("stores.id"), nullable=True, comment="门店ID")
    template_id = Column(String(36), ForeignKey("schedule_templates.id"), nullable=True, comment="来源模板ID")
    shift_type_id = Column(String(36), ForeignKey("shift_types.id"), nullable=True, comment="班次类型ID")
    schedule_date = Column(Date, nullable=False)
    time_slot = Column(String(10), nullable=True, comment="时段: AM/PM/morning/afternoon/evening，可为空（自定义排班可通过start_time计算）")
    start_time = Column(Time)
    end_time = Column(Time)
    start_at = Column(DateTime(timezone=True), nullable=True, comment="开始时间(带时区)")
    end_at = Column(DateTime(timezone=True), nullable=True, comment="结束时间(带时区)")
    timezone = Column(String(50), nullable=True, default="Asia/Shanghai", comment="时区")
    total_slots = Column(Integer, default=10)  # 总号源
    booked_slots = Column(Integer, default=0)  # 已预约数
    appointment_type = Column(String(20), default="normal", comment="预约类型: urgent/normal/expert/medical_insurance/self_pay")
    status = Column(Integer, default=1)  # 0停诊 1正常

    # 关联关系
    tenant = relationship("Tenant", back_populates="schedules")
    doctor = relationship("Doctor", back_populates="schedules")
    store = relationship("Store", backref="schedules")
    template = relationship("ScheduleTemplate", back_populates="schedules")
    appointments = relationship("Appointment", back_populates="schedule")
