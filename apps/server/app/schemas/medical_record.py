"""病历 Schema"""
from datetime import datetime
from decimal import Decimal

from pydantic import Field

from app.schemas.base import BaseRequestSchema, BaseSchema


class MedicalRecordCreate(BaseRequestSchema):
    """创建病历请求"""

    appointment_id: str = Field(..., description="预约ID")
    chief_complaint: str = Field(..., max_length=500, description="主诉")
    present_illness: str | None = Field(None, description="现病史")
    past_history: str | None = Field(None, description="既往史")
    allergy_history: str | None = Field(None, description="过敏史")
    family_history: str | None = Field(None, description="家族史")
    medication_history: str | None = Field(None, description="用药史")
    physical_exam: str | None = Field(None, description="体格检查")
    auxiliary_exam: str | None = Field(None, description="辅助检查")
    diagnosis: str = Field(..., description="诊断")
    treatment: str | None = Field(None, description="治疗方案")
    prescription: str | None = Field(None, description="处方")
    advice: str | None = Field(None, description="医嘱")
    total_fee: Decimal | None = Field(0, description="总费用")
    status: int = Field(1, ge=1, le=2, description="状态 1草稿 2已完成")
    visit_date: datetime | None = Field(None, description="就诊日期，不传则取当前时间")
    follow_up_plan_id: str | None = Field(None, description="随访计划ID，传入则自动生成随访任务")

class MedicalRecordUpdate(BaseRequestSchema):
    """更新病历请求"""

    chief_complaint: str | None = Field(None, max_length=500, description="主诉")
    present_illness: str | None = Field(None, description="现病史")
    past_history: str | None = Field(None, description="既往史")
    allergy_history: str | None = Field(None, description="过敏史")
    family_history: str | None = Field(None, description="家族史")
    medication_history: str | None = Field(None, description="用药史")
    physical_exam: str | None = Field(None, description="体格检查")
    auxiliary_exam: str | None = Field(None, description="辅助检查")
    diagnosis: str | None = Field(None, description="诊断")
    treatment: str | None = Field(None, description="治疗方案")
    prescription: str | None = Field(None, description="处方")
    advice: str | None = Field(None, description="医嘱")
    total_fee: Decimal | None = Field(None, description="总费用")
    status: int | None = Field(None, ge=1, le=2, description="状态 1草稿 2已完成")

class MedicalRecordResponse(BaseSchema):
    """病历响应"""

    id: str = Field(..., description="病历ID")
    record_no: str | None = Field(None, description="病历编号")
    appointment_id: str | None = Field(None, description="预约ID")
    patient_id: str | None = Field(None, description="患者ID")
    patient_name: str | None = Field(None, description="患者姓名")
    patient_phone: str | None = Field(None, description="患者手机号")
    patient_gender: int | None = Field(None, description="患者性别")
    doctor_id: str | None = Field(None, description="医生ID")
    doctor_name: str | None = Field(None, description="医生姓名")
    department_id: str | None = Field(None, description="科室ID")
    department_name: str | None = Field(None, description="科室名称")
    chief_complaint: str | None = Field(None, description="主诉")
    present_illness: str | None = Field(None, description="现病史")
    past_history: str | None = Field(None, description="既往史")
    allergy_history: str | None = Field(None, description="过敏史")
    family_history: str | None = Field(None, description="家族史")
    medication_history: str | None = Field(None, description="用药史")
    physical_exam: str | None = Field(None, description="体格检查")
    auxiliary_exam: str | None = Field(None, description="辅助检查")
    diagnosis: str | None = Field(None, description="诊断")
    treatment: str | None = Field(None, description="治疗方案")
    prescription: str | None = Field(None, description="处方")
    advice: str | None = Field(None, description="医嘱")
    total_fee: float | None = Field(0, description="总费用")
    status: int | None = Field(None, description="状态 1草稿 2已完成")
    visit_date: datetime | None = Field(None, description="就诊时间")
    created_at: datetime | None = Field(None, description="创建时间")
    updated_at: datetime | None = Field(None, description="更新时间")
    examination_reports: list | None = Field(None, description="检查报告列表")

class MedicalRecordListResponse(BaseSchema):
    """病历列表响应（简化版）"""

    id: str = Field(..., description="病历ID")
    record_no: str | None = Field(None, description="病历编号")
    patient_name: str | None = Field(None, description="患者姓名")
    doctor_name: str | None = Field(None, description="医生姓名")
    department_name: str | None = Field(None, description="科室名称")
    diagnosis: str | None = Field(None, description="诊断")
    visit_date: datetime | None = Field(None, description="就诊时间")
    status: int | None = Field(None, description="状态")
    created_at: datetime | None = Field(None, description="创建时间")
