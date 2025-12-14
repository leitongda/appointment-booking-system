from pydantic import BaseModel, Field
from typing import Optional, List
from decimal import Decimal
from datetime import datetime


# ========== 诊费类型 Schema ==========

class ConsultationFeeTypeBase(BaseModel):
    name: str = Field(..., max_length=50, description="诊费类型名称")
    code: Optional[str] = Field(None, max_length=50, description="类型编码")
    description: Optional[str] = Field(None, max_length=255, description="描述")
    sort_order: int = Field(0, ge=0, description="排序")
    status: int = Field(1, ge=0, le=1, description="状态: 0禁用 1启用")


class ConsultationFeeTypeCreate(ConsultationFeeTypeBase):
    pass


class ConsultationFeeTypeUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=50)
    code: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = Field(None, max_length=255)
    sort_order: Optional[int] = Field(None, ge=0)
    status: Optional[int] = Field(None, ge=0, le=1)


class ConsultationFeeTypeResponse(ConsultationFeeTypeBase):
    id: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# ========== 诊费模板 Schema ==========

class ConsultationFeeTemplateBase(BaseModel):
    fee_type_id: str = Field(..., description="诊费类型ID")
    initial_fee: Decimal = Field(Decimal("0"), ge=0, description="初诊金额")
    follow_up_fee: Decimal = Field(Decimal("0"), ge=0, description="复诊金额")
    status: int = Field(1, ge=0, le=1, description="状态: 0禁用 1启用")


class ConsultationFeeTemplateCreate(ConsultationFeeTemplateBase):
    pass


class ConsultationFeeTemplateUpdate(BaseModel):
    fee_type_id: Optional[str] = None
    initial_fee: Optional[Decimal] = Field(None, ge=0)
    follow_up_fee: Optional[Decimal] = Field(None, ge=0)
    status: Optional[int] = Field(None, ge=0, le=1)


class ConsultationFeeTemplateResponse(ConsultationFeeTemplateBase):
    id: str
    fee_type_name: Optional[str] = None
    fee_type_code: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ConsultationFeeTemplateWithType(BaseModel):
    """带诊费类型信息的模板响应"""
    id: Optional[str] = None
    fee_type_id: str
    fee_type_name: str
    fee_type_code: Optional[str] = None
    initial_fee: Decimal = Decimal("0")
    follow_up_fee: Decimal = Decimal("0")
    status: int = 1


# ========== 医生诊费配置 Schema ==========

class DoctorConsultationFeeBase(BaseModel):
    doctor_id: str = Field(..., description="医生ID")
    store_id: str = Field(..., description="门店ID")
    department_id: str = Field(..., description="科室ID")
    fee_type_id: str = Field(..., description="诊费类型ID")
    initial_fee: Decimal = Field(Decimal("0"), ge=0, description="初诊金额")
    follow_up_fee: Decimal = Field(Decimal("0"), ge=0, description="复诊金额")
    status: int = Field(1, ge=0, le=1, description="状态: 0禁用 1启用")


class DoctorConsultationFeeCreate(DoctorConsultationFeeBase):
    pass


class DoctorConsultationFeeUpdate(BaseModel):
    initial_fee: Optional[Decimal] = Field(None, ge=0)
    follow_up_fee: Optional[Decimal] = Field(None, ge=0)
    status: Optional[int] = Field(None, ge=0, le=1)


class DoctorConsultationFeeResponse(DoctorConsultationFeeBase):
    id: str
    store_name: Optional[str] = None
    department_name: Optional[str] = None
    fee_type_name: Optional[str] = None
    fee_type_code: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class DoctorConsultationFeeItem(BaseModel):
    """单个诊费类型的金额配置"""
    fee_type_id: str
    fee_type_name: Optional[str] = None
    fee_type_code: Optional[str] = None
    initial_fee: Decimal = Decimal("0")
    follow_up_fee: Decimal = Decimal("0")


class DoctorConsultationFeeBatchCreate(BaseModel):
    """批量创建/更新医生诊费配置"""
    doctor_id: str = Field(..., description="医生ID")
    store_id: str = Field(..., description="门店ID")
    department_id: str = Field(..., description="科室ID")
    fees: List[DoctorConsultationFeeItem] = Field(..., description="诊费配置列表")


class DoctorConsultationFeeQuery(BaseModel):
    """查询医生诊费配置的参数"""
    doctor_id: str
    store_id: Optional[str] = None
    department_id: Optional[str] = None


class DoctorFeeSettingResponse(BaseModel):
    """医生诊费设置响应（包含是否使用模板）"""
    doctor_id: str
    doctor_name: str
    use_fee_template: int
    fees: List[DoctorConsultationFeeResponse] = []


class DoctorFeeSettingUpdate(BaseModel):
    """更新医生诊费设置"""
    use_fee_template: int = Field(..., ge=0, le=1, description="是否使用诊费模板 0否 1是")


class StoreDepartmentFeeGroup(BaseModel):
    """门店-科室下的诊费配置分组"""
    store_id: str
    store_name: str
    department_id: str
    department_name: str
    fees: List[DoctorConsultationFeeItem] = []
