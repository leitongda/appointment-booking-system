"""
[已废弃] 自定义排班模型

数据已通过 Alembic 迁移 021_merge_custom_schedules 合并到 schedules 表。
schedules 表中 template_id IS NULL 的记录即为原自定义排班。

此文件仍保留的原因：
- custom_schedule_service.py 和 api/v1/custom_schedules.py 仍直接引用此模型
- 前端 admin 和 packages/api 仍引用相关 API 和类型
- 完全清理需要同步重构服务层、API 层和前端代码

TODO: 在下一次排班模块重构时一并清理此文件及相关代码。
"""
from sqlalchemy import Column, String, Integer, Date, Time, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base import Base, AuditMixin
import uuid


class CustomSchedule(Base, AuditMixin):
    """[已废弃] 自定义排班（单日排班）模型 - 数据已合并到 schedules 表"""
    __tablename__ = "custom_schedules"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    store_id = Column(String(36), ForeignKey("stores.id"), nullable=False, comment="门店ID")
    department_id = Column(String(36), ForeignKey("departments.id"), nullable=False, comment="科室ID")
    doctor_id = Column(String(36), ForeignKey("doctors.id"), nullable=False, comment="医生ID")
    schedule_date = Column(Date, nullable=False, comment="排班日期")
    start_time = Column(Time, nullable=False, comment="开始时间")
    end_time = Column(Time, nullable=False, comment="结束时间")
    appointment_type = Column(String(20), nullable=False, comment="预约类型: urgent/normal/expert/medical_insurance/self_pay")
    max_patients = Column(Integer, default=1, comment="预约人数（每个班次）")
    booked_count = Column(Integer, default=0, comment="已预约数")
    status = Column(Integer, default=1, comment="状态: 0停用 1启用")
    
    # 关联关系
    store = relationship("Store", backref="custom_schedules")
    department = relationship("Department", backref="custom_schedules")
    doctor = relationship("Doctor", backref="custom_schedules")
