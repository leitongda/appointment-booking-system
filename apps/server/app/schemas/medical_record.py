"""病历 Schema"""
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from datetime import datetime, date
from decimal import Decimal


def to_camel(string: str) -> str:
    """将 snake_case 转换为 camelCase"""
    components = string.split('_')
    return components[0] + ''.join(x.title() for x in components[1:])


class MedicalRecordCreate(BaseModel):
    """创建病历请求"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )
    
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
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )
    
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
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
        by_alias=True,
    )
    
    id: str
    record_no: Optional[str] = None
    appointment_id: Optional[str] = None
    patient_id: Optional[str] = None
    patient_name: Optional[str] = None
    patient_phone: Optional[str] = None
    patient_gender: Optional[int] = None
    doctor_id: Optional[str] = None
    doctor_name: Optional[str] = None
    department_id: Optional[str] = None
    department_name: Optional[str] = None
    chief_complaint: Optional[str] = None
    present_illness: Optional[str] = None
    past_history: Optional[str] = None
    allergy_history: Optional[str] = None
    physical_exam: Optional[str] = None
    auxiliary_exam: Optional[str] = None
    diagnosis: Optional[str] = None
    treatment: Optional[str] = None
    prescription: Optional[str] = None
    advice: Optional[str] = None
    total_fee: Optional[float] = 0
    status: Optional[int] = None
    visit_date: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class MedicalRecordListResponse(BaseModel):
    """病历列表响应（简化版）"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
        by_alias=True,
    )
    
    id: str
    record_no: Optional[str] = None
    patient_name: Optional[str] = None
    doctor_name: Optional[str] = None
    department_name: Optional[str] = None
    diagnosis: Optional[str] = None
    visit_date: Optional[datetime] = None
    status: Optional[int] = None
    created_at: Optional[datetime] = None

