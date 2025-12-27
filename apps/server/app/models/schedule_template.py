from sqlalchemy import Column, String, Integer, Time, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.db.base import Base, TimestampMixin
import uuid
import json


class ScheduleTemplate(Base, TimestampMixin):
    """排班模板模型"""
    __tablename__ = "schedule_templates"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False, comment="模板名称")
    store_id = Column(String(36), ForeignKey("stores.id"), nullable=False, comment="门店ID")
    doctor_id = Column(String(36), ForeignKey("doctors.id"), nullable=False, comment="医生ID")
    department_id = Column(String(36), ForeignKey("departments.id"), nullable=False, comment="科室ID")
    weekdays = Column(Text, nullable=False, comment="星期数组 JSON格式 [1,2,3,4,5]")
    appointment_type = Column(String(20), default="normal", comment="预约类型: urgent/normal/expert/medical_insurance/self_pay")
    start_time = Column(Time, nullable=False, comment="开始时间")
    end_time = Column(Time, nullable=False, comment="结束时间")
    slot_count = Column(Integer, nullable=False, default=1, comment="班次数量")
    slot_capacity = Column(Integer, default=10, comment="每班次人数")
    schedule_mode = Column(String(50), default="weekly", comment="排班方式")
    status = Column(Integer, default=1, comment="状态: 0禁用 1启用")
    
    @property
    def weekday_list(self) -> list:
        """获取星期列表"""
        if not self.weekdays:
            return []
        try:
            # 确保 weekdays 是字符串
            weekdays_str = str(self.weekdays) if not isinstance(self.weekdays, str) else self.weekdays
            if not weekdays_str.strip():
                return []
            return json.loads(weekdays_str)
        except (json.JSONDecodeError, TypeError, ValueError):
            # 兼容旧数据：如果是单个数字，转换为数组
            try:
                weekday_int = int(self.weekdays)
                return [weekday_int]
            except (ValueError, TypeError):
                return []
    
    @weekday_list.setter
    def weekday_list(self, value: list):
        """设置星期列表"""
        if isinstance(value, list):
            self.weekdays = json.dumps(value)
        else:
            self.weekdays = json.dumps([])
    
    # 关联关系
    store = relationship("Store", backref="schedule_templates")
    doctor = relationship("Doctor", backref="schedule_templates")
    department = relationship("Department", backref="schedule_templates")
    schedules = relationship("Schedule", back_populates="template")
