import json
import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, Time
from sqlalchemy.orm import relationship

from app.db.base import AuditMixin, Base


class ScheduleTemplate(Base, AuditMixin):
    """排班模板模型"""
    __tablename__ = "schedule_templates"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False, comment="模板名称")
    # 租户关联（多租户支持）
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=True, index=True, comment="租户ID")
    store_id = Column(String(36), ForeignKey("stores.id"), nullable=False, comment="门店ID")
    doctor_id = Column(String(36), ForeignKey("doctors.id"), nullable=False, comment="医生ID")
    department_id = Column(String(36), ForeignKey("departments.id"), nullable=False, comment="科室ID")
    shift_type_id = Column(String(36), ForeignKey("shift_types.id"), nullable=True, index=True, comment="班次类型ID")
    rule_set_id = Column(String(36), ForeignKey("rule_sets.id"), nullable=True, index=True, comment="关联规则组ID")
    weekdays = Column(Text, nullable=False, comment="星期数组 JSON格式 [1,2,3,4,5]")
    appointment_type = Column(String(20), default="normal", comment="预约类型: urgent/normal/expert/medical_insurance/self_pay")
    start_time = Column(Time, nullable=False, comment="开始时间")
    end_time = Column(Time, nullable=False, comment="结束时间")
    slot_count = Column(Integer, nullable=False, default=1, comment="班次数量")
    slot_capacity = Column(Integer, nullable=False, default=10, comment="每班次人数")
    schedule_mode = Column(String(50), default="weekly", comment="排班方式")
    break_times = Column(Text, nullable=True, comment="排除时间段 JSON格式 [{startTime: '12:00', endTime: '13:30'}]")
    status = Column(Integer, default=1, comment="状态: 0禁用 1启用")
    last_generated_at = Column(DateTime, nullable=True, comment="上一次生成排班时间")

    # 关联关系
    tenant = relationship("Tenant", back_populates="schedule_templates")
    store = relationship("Store", backref="schedule_templates")
    doctor = relationship("Doctor", backref="schedule_templates")
    department = relationship("Department", backref="schedule_templates")
    shift_type = relationship("ShiftType", backref="schedule_templates")
    rule_set = relationship("RuleSet", backref="linked_schedule_templates")
    schedules = relationship("Schedule", back_populates="template")

    __table_args__ = (
        {'comment': '排班模板表（多租户支持）'},
    )

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
    
    @property
    def break_times_list(self) -> list:
        """获取排除时间段列表"""
        if not self.break_times:
            return []
        try:
            break_times_str = str(self.break_times) if not isinstance(self.break_times, str) else self.break_times
            if not break_times_str.strip():
                return []
            return json.loads(break_times_str)
        except (json.JSONDecodeError, TypeError, ValueError):
            return []
    
    @break_times_list.setter
    def break_times_list(self, value: list):
        """设置排除时间段列表"""
        if isinstance(value, list):
            self.break_times = json.dumps(value)
        else:
            self.break_times = None
