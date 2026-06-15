import uuid

from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class ScheduleGenerationLog(Base):
    """排班生成日志模型"""
    __tablename__ = "schedule_generation_logs"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    template_id = Column(String(36), ForeignKey("schedule_templates.id", ondelete="CASCADE"), nullable=False, comment="排班规则ID")
    operator_id = Column(String(36), ForeignKey("admins.id", ondelete="SET NULL"), nullable=True, comment="操作人ID")
    operator_name = Column(String(100), nullable=True, comment="操作人姓名")
    action_type = Column(String(20), nullable=False, comment="操作类型: generate/delete/suspend")
    start_date = Column(Date, nullable=True, comment="开始日期")
    end_date = Column(Date, nullable=True, comment="结束日期")
    affected_count = Column(Integer, default=0, comment="影响的记录数")
    remark = Column(Text, nullable=True, comment="备注")
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    
    # 关联关系
    template = relationship("ScheduleTemplate", backref="generation_logs")
    operator = relationship("Admin", backref="schedule_operation_logs")

