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

    chief_complaint: Optional[str] = Field(None, max_length=500, description="主诉")
    present_illness: Optional[str] = Field(None, description="现病史")
    past_history: Optional[str] = Field(None, description="既往史")
    allergy_history: Optional[str] = Field(None, description="过敏史")
    physical_exam: Optional[str] = Field(None, description="体格检查")
    auxiliary_exam: Optional[str] = Field(None, description="辅助检查")
    diagnosis: Optional[str] = Field(None, description="诊断")
    treatment: Optional[str] = Field(None, description="治疗方案")
    prescription: Optional[str] = Field(None, description="处方")
    advice: Optional[str] = Field(None, description="医嘱")
    total_fee: Optional[Decimal] = Field(None, description="总费用")
    status: Optional[int] = Field(None, ge=1, le=2, description="状态 1草稿 2已完成")


class MedicalRecordResponse(BaseModel):
    """病历响应"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
        by_alias=True,
    )

    id: str = Field(..., description="病历ID")
    record_no: Optional[str] = Field(None, description="病历编号")
    appointment_id: Optional[str] = Field(None, description="预约ID")
    patient_id: Optional[str] = Field(None, description="患者ID")
    patient_name: Optional[str] = Field(None, description="患者姓名")
    patient_phone: Optional[str] = Field(None, description="患者手机号")
    patient_gender: Optional[int] = Field(None, description="患者性别")
    doctor_id: Optional[str] = Field(None, description="医生ID")
    doctor_name: Optional[str] = Field(None, description="医生姓名")
    department_id: Optional[str] = Field(None, description="科室ID")
    department_name: Optional[str] = Field(None, description="科室名称")
    chief_complaint: Optional[str] = Field(None, description="主诉")
    present_illness: Optional[str] = Field(None, description="现病史")
    past_history: Optional[str] = Field(None, description="既往史")
    allergy_history: Optional[str] = Field(None, description="过敏史")
    physical_exam: Optional[str] = Field(None, description="体格检查")
    auxiliary_exam: Optional[str] = Field(None, description="辅助检查")
    diagnosis: Optional[str] = Field(None, description="诊断")
    treatment: Optional[str] = Field(None, description="治疗方案")
    prescription: Optional[str] = Field(None, description="处方")
    advice: Optional[str] = Field(None, description="医嘱")
    total_fee: Optional[float] = Field(0, description="总费用")
    status: Optional[int] = Field(None, description="状态 1草稿 2已完成")
    visit_date: Optional[datetime] = Field(None, description="就诊时间")
    created_at: Optional[datetime] = Field(None, description="创建时间")
    updated_at: Optional[datetime] = Field(None, description="更新时间")


class MedicalRecordListResponse(BaseModel):
    """病历列表响应（简化版）"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
        by_alias=True,
    )

    id: str = Field(..., description="病历ID")
    record_no: Optional[str] = Field(None, description="病历编号")
    patient_name: Optional[str] = Field(None, description="患者姓名")
    doctor_name: Optional[str] = Field(None, description="医生姓名")
    department_name: Optional[str] = Field(None, description="科室名称")
    diagnosis: Optional[str] = Field(None, description="诊断")
    visit_date: Optional[datetime] = Field(None, description="就诊时间")
    status: Optional[int] = Field(None, description="状态")
    created_at: Optional[datetime] = Field(None, description="创建时间")

