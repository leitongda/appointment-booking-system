"""随访任务模型"""
import uuid
from sqlalchemy import Column, String, Integer, DateTime, Date, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.db.base import Base, AuditMixin


class FollowUpTask(Base, AuditMixin):
    """随访任务表"""
    __tablename__ = "follow_up_tasks"
    __table_args__ = (
        Index("idx_tasks_doctor_status_date", "doctor_id", "status", "scheduled_date"),
    )

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=True, index=True, comment="租户ID")
    task_no = Column(String(50), unique=True, nullable=False, comment="任务编号")

    # 关联信息
    patient_id = Column(String(36), ForeignKey("patients.id"), nullable=False, index=True, comment="患者ID")
    doctor_id = Column(String(36), ForeignKey("doctors.id"), nullable=False, index=True, comment="医生ID")
    department_id = Column(String(36), ForeignKey("departments.id"), nullable=False, index=True, comment="科室ID")
    appointment_id = Column(String(36), ForeignKey("appointments.id"), nullable=True, index=True, comment="预约ID")
    medical_record_id = Column(String(36), ForeignKey("medical_records.id"), nullable=True, index=True, comment="病历ID")

    # 计划关联
    plan_id = Column(String(36), ForeignKey("follow_up_plans.id"), nullable=True, index=True, comment="计划ID，NULL=手动创建")
    plan_step_id = Column(String(36), ForeignKey("follow_up_plan_steps.id"), nullable=True, comment="步骤ID")
    step_order = Column(Integer, nullable=True, comment="步骤顺序快照")

    # 任务信息
    scheduled_date = Column(Date, nullable=False, index=True, comment="计划随访日期")
    status = Column(String(20), nullable=False, default="pending", index=True, comment="状态: pending/completed/skipped/overdue")
    completed_at = Column(DateTime, nullable=True, comment="完成时间")
    completed_by = Column(String(36), nullable=True, comment="完成人")
    skip_reason = Column(String(500), nullable=True, comment="跳过原因")

    # 软删除
    deleted_at = Column(DateTime, nullable=True, comment="软删除时间")

    # 关系
    patient = relationship("Patient", backref="follow_up_tasks")
    doctor = relationship("Doctor", backref="follow_up_tasks")
    department = relationship("Department", backref="follow_up_tasks")
    appointment = relationship("Appointment", backref="follow_up_tasks")
    medical_record = relationship("MedicalRecord", backref="follow_up_tasks")
    plan = relationship("FollowUpPlan", backref="tasks")
    plan_step = relationship("FollowUpPlanStep", backref="tasks")
    records = relationship("FollowUpRecord", backref="task", foreign_keys="FollowUpRecord.task_id")
