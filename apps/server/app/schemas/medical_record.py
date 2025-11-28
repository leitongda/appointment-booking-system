"""病历 Schema"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, date
from decimal import Decimal


class MedicalRecordCreate(BaseModel):
    """创建病历请求"""
    appointment_id: str = Field(..., description="预约ID")
    chief_complaint: str = Field(..., max_length=500, description="主诉")
    present_illness: Optional[str] = Field(None, description="现病史")
    past_history: Optional[str] = Field(None, description="既往史")
    allergy_history: Optional[str] = Field(None, description="过敏史")
    physical_exam: Optional[str] = Field(None, description="体格检查")
    auxiliary_exam: Optional[str] = Field(None, description="辅助检查")
    diagnosis: str = Field(..., description="诊断")
    treatment: Optional[str] = Field(None, description="治疗方案")
    prescription: Optional[str] = Field(None, description="处方")
    advice: Optional[str] = Field(None, description="医嘱")
    total_fee: Optional[Decimal] = Field(0, description="总费用")
    status: int = Field(2, ge=1, le=2, description="状态 1草稿 2已完成")


class MedicalRecordUpdate(BaseModel):
    """更新病历请求"""
    chief_complaint: Optional[str] = Field(None, max_length=500)
    present_illness: Optional[str] = None
    past_history: Optional[str] = None
    allergy_history: Optional[str] = None
    physical_exam: Optional[str] = None
    auxiliary_exam: Optional[str] = None
    diagnosis: Optional[str] = None
    treatment: Optional[str] = None
    prescription: Optional[str] = None
    advice: Optional[str] = None
    total_fee: Optional[Decimal] = None
    status: Optional[int] = Field(None, ge=1, le=2)


class MedicalRecordResponse(BaseModel):
    """病历响应"""
    id: str
    record_no: str
    appointment_id: str
    patient_id: str
    patient_name: Optional[str] = None
    patient_phone: Optional[str] = None
    patient_gender: Optional[int] = None
    doctor_id: str
    doctor_name: Optional[str] = None
    department_id: str
    department_name: Optional[str] = None
    chief_complaint: Optional[str] = None
    present_illness: Optional[str] = None
    past_history: Optional[str] = None
    allergy_history: Optional[str] = None
    physical_exam: Optional[str] = None
    auxiliary_exam: Optional[str] = None
    diagnosis: str
    treatment: Optional[str] = None
    prescription: Optional[str] = None
    advice: Optional[str] = None
    total_fee: Optional[float] = 0
    status: int
    visit_date: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class MedicalRecordListResponse(BaseModel):
    """病历列表响应（简化版）"""
    id: str
    record_no: str
    patient_name: Optional[str] = None
    doctor_name: Optional[str] = None
    department_name: Optional[str] = None
    diagnosis: str
    visit_date: Optional[datetime] = None
    status: int
    created_at: datetime

    class Config:
        from_attributes = True

