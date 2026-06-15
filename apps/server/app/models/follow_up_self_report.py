"""患者自报告模型"""
import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import relationship

from app.db.base import AuditMixin, Base


class FollowUpSelfReport(Base, AuditMixin):
    """患者自报告表 — 血压/血糖/症状等自我监测数据"""
    __tablename__ = "follow_up_self_reports"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=True, index=True, comment="租户ID")

    # 关联信息
    task_id = Column(String(36), ForeignKey("follow_up_tasks.id"), nullable=True, index=True, comment="关联随访任务ID")
    patient_id = Column(String(36), ForeignKey("patients.id"), nullable=False, index=True, comment="报告人ID")

    # 报告信息
    report_date = Column(DateTime, nullable=False, comment="测量/报告时间")

    # 体征数据
    systolic_bp = Column(Integer, nullable=True, comment="收缩压 (mmHg)")
    diastolic_bp = Column(Integer, nullable=True, comment="舒张压 (mmHg)")
    blood_glucose = Column(Numeric(5, 1), nullable=True, comment="血糖 (mmol/L)")
    heart_rate = Column(Integer, nullable=True, comment="心率 (次/分)")
    temperature = Column(Numeric(4, 1), nullable=True, comment="体温 (°C)")

    # 症状与感受
    symptoms = Column(Text, nullable=True, comment="症状描述")
    patient_condition = Column(String(20), nullable=True, comment="自我感受: improved/stable/worsened")
    notes = Column(Text, nullable=True, comment="备注")
    attachments = Column(Text, nullable=True, comment="附件JSON数组")

    # 审核状态
    status = Column(String(20), nullable=False, default="pending", comment="状态: pending/reviewed")
    reviewed_at = Column(DateTime, nullable=True, comment="审核时间")
    reviewed_by = Column(String(36), nullable=True, comment="审核医生ID")

    # 软删除
    deleted_at = Column(DateTime, nullable=True, comment="软删除时间")

    # 关系
    patient = relationship("Patient", backref="self_reports")
    task = relationship("FollowUpTask", backref="self_reports")
