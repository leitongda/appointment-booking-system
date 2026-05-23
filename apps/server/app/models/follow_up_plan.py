"""随访计划模型"""
import uuid
from sqlalchemy import Column, String, Integer, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base import Base, AuditMixin, TimestampMixin


class FollowUpPlan(Base, AuditMixin):
    """随访计划模板表"""
    __tablename__ = "follow_up_plans"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=True, index=True, comment="租户ID")
    name = Column(String(200), nullable=False, comment="计划名称")
    description = Column(Text, nullable=True, comment="计划描述")
    department_id = Column(String(36), ForeignKey("departments.id"), nullable=True, index=True, comment="科室ID，NULL=全局")
    diagnosis_code = Column(String(50), nullable=True, index=True, comment="诊断编码")
    diagnosis_name = Column(String(200), nullable=True, comment="诊断名称")
    status = Column(Integer, default=1, comment="状态 0=停用 1=启用")
    deleted_at = Column(DateTime, nullable=True, comment="软删除时间")

    # 关系
    department = relationship("Department", backref="follow_up_plans")
    steps = relationship("FollowUpPlanStep", backref="plan", cascade="all, delete-orphan", order_by="FollowUpPlanStep.step_order")


class FollowUpPlanStep(Base, TimestampMixin):
    """随访计划步骤表"""
    __tablename__ = "follow_up_plan_steps"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    plan_id = Column(String(36), ForeignKey("follow_up_plans.id", ondelete="CASCADE"), nullable=False, index=True, comment="计划ID")
    step_order = Column(Integer, nullable=False, comment="步骤顺序")
    name = Column(String(100), nullable=False, comment="步骤名称")
    days_after_visit = Column(Integer, nullable=False, comment="就诊后第几天")
    description = Column(Text, nullable=True, comment="步骤说明")
