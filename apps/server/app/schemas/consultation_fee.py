from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List
from decimal import Decimal
from datetime import datetime


def to_camel(string: str) -> str:
    """将 snake_case 转换为 camelCase"""
    components = string.split('_')
    return components[0] + ''.join(x.title() for x in components[1:])


# ========== 诊费类型 Schema ==========

class ConsultationFeeTypeBase(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )
    
    store_id: Optional[str] = Field(None, description="门店ID，NULL表示全局类型")
    name: str = Field(..., max_length=50, description="诊费类型名称")
    code: Optional[str] = Field(None, max_length=50, description="类型编码")
    description: Optional[str] = Field(None, max_length=255, description="描述")
    sort_order: int = Field(0, ge=0, description="排序")
    status: int = Field(1, ge=0, le=1, description="状态: 0禁用 1启用")


class ConsultationFeeTypeCreate(ConsultationFeeTypeBase):
    pass


class ConsultationFeeTypeUpdate(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )
    
    store_id: Optional[str] = None
    name: Optional[str] = Field(None, max_length=50)
    code: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = Field(None, max_length=255)
    sort_order: Optional[int] = Field(None, ge=0)
    status: Optional[int] = Field(None, ge=0, le=1)


class ConsultationFeeTypeResponse(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
        by_alias=True,
    )
    
    id: str
    store_id: Optional[str] = None
    store_name: Optional[str] = None
    name: Optional[str] = None
    code: Optional[str] = None
    description: Optional[str] = None
    sort_order: Optional[int] = 0
    status: Optional[int] = 1
    is_global: Optional[bool] = None  # 是否为全局类型
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# ========== 诊费模板 Schema ==========

class ConsultationFeeTemplateBase(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )
    
    fee_type_id: str = Field(..., description="诊费类型ID")
    initial_fee: Decimal = Field(Decimal("0"), ge=0, description="初诊金额")
    follow_up_fee: Decimal = Field(Decimal("0"), ge=0, description="复诊金额")
    status: int = Field(1, ge=0, le=1, description="状态: 0禁用 1启用")


class ConsultationFeeTemplateCreate(ConsultationFeeTemplateBase):
    pass


class ConsultationFeeTemplateUpdate(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )
    
    fee_type_id: Optional[str] = None
    initial_fee: Optional[Decimal] = Field(None, ge=0)
    follow_up_fee: Optional[Decimal] = Field(None, ge=0)
    status: Optional[int] = Field(None, ge=0, le=1)


class ConsultationFeeTemplateResponse(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
        by_alias=True,
    )
    
    id: str
    fee_type_id: Optional[str] = None
    fee_type_name: Optional[str] = None
    fee_type_code: Optional[str] = None
    initial_fee: Optional[Decimal] = Decimal("0")
    follow_up_fee: Optional[Decimal] = Decimal("0")
    status: Optional[int] = 1
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ConsultationFeeTemplateWithType(BaseModel):
    """带诊费类型信息的模板响应"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        by_alias=True,
    )
    
    id: Optional[str] = None
    fee_type_id: Optional[str] = None
    fee_type_name: Optional[str] = None
    fee_type_code: Optional[str] = None
    initial_fee: Decimal = Decimal("0")
    follow_up_fee: Decimal = Decimal("0")
    status: int = 1


# ========== 门店诊费模板 Schema ==========

class StoreFeeTemplateBase(BaseModel):
    """门店诊费模板基础"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )
    
    store_id: str = Field(..., description="门店ID")
    fee_type_id: str = Field(..., description="诊费类型ID")
    initial_fee: Decimal = Field(Decimal("0"), ge=0, description="初诊金额")
    follow_up_fee: Decimal = Field(Decimal("0"), ge=0, description="复诊金额")
    status: int = Field(1, ge=0, le=1, description="状态: 0禁用 1启用")


class StoreFeeTemplateCreate(StoreFeeTemplateBase):
    pass


class StoreFeeTemplateUpdate(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )
    
    initial_fee: Optional[Decimal] = Field(None, ge=0)
    follow_up_fee: Optional[Decimal] = Field(None, ge=0)
    status: Optional[int] = Field(None, ge=0, le=1)


class StoreFeeTemplateResponse(BaseModel):
    """门店诊费模板响应"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
        by_alias=True,
    )
    
    id: str
    store_id: Optional[str] = None
    store_name: Optional[str] = None
    fee_type_id: Optional[str] = None
    fee_type_name: Optional[str] = None
    fee_type_code: Optional[str] = None
    initial_fee: Optional[Decimal] = Decimal("0")
    follow_up_fee: Optional[Decimal] = Decimal("0")
    status: Optional[int] = 1
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class StoreFeeTemplateItem(BaseModel):
    """门店诊费模板项（用于批量保存）"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        by_alias=True,
    )
    
    fee_type_id: str
    fee_type_name: Optional[str] = None
    fee_type_code: Optional[str] = None
    initial_fee: Decimal = Decimal("0")
    follow_up_fee: Decimal = Decimal("0")


class StoreFeeTemplateBatchCreate(BaseModel):
    """批量创建/更新门店诊费模板"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )
    
    store_id: str = Field(..., description="门店ID")
    templates: List[StoreFeeTemplateItem] = Field(..., description="诊费模板列表")


class StoreFeeTemplateWithType(BaseModel):
    """带诊费类型信息的门店模板响应（用于列表展示）"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        by_alias=True,
    )
    
    id: Optional[str] = None
    store_id: Optional[str] = None
    fee_type_id: str
    fee_type_name: str
    fee_type_code: Optional[str] = None
    initial_fee: Decimal = Decimal("0")
    follow_up_fee: Decimal = Decimal("0")
    global_initial_fee: Optional[Decimal] = Decimal("0")  # 全局模板的初诊金额（用于参考）
    global_follow_up_fee: Optional[Decimal] = Decimal("0")  # 全局模板的复诊金额（用于参考）
    status: int = 1
    is_global_type: bool = True  # 是否为全局类型


class ApplyTemplateRequest(BaseModel):
    """一键带入模板请求"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )
    
    store_id: str = Field(..., description="门店ID")
    department_id: str = Field(..., description="科室ID")


# ========== 医生诊费配置 Schema ==========

class DoctorConsultationFeeBase(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )
    
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
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )
    
    initial_fee: Optional[Decimal] = Field(None, ge=0)
    follow_up_fee: Optional[Decimal] = Field(None, ge=0)
    status: Optional[int] = Field(None, ge=0, le=1)


class DoctorConsultationFeeResponse(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
        by_alias=True,
    )
    
    id: str
    doctor_id: Optional[str] = None
    store_id: Optional[str] = None
    department_id: Optional[str] = None
    fee_type_id: Optional[str] = None
    initial_fee: Optional[Decimal] = Decimal("0")
    follow_up_fee: Optional[Decimal] = Decimal("0")
    status: Optional[int] = 1
    store_name: Optional[str] = None
    department_name: Optional[str] = None
    fee_type_name: Optional[str] = None
    fee_type_code: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class DoctorConsultationFeeItem(BaseModel):
    """单个诊费类型的金额配置"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        by_alias=True,
    )
    
    fee_type_id: Optional[str] = None
    fee_type_name: Optional[str] = None
    fee_type_code: Optional[str] = None
    initial_fee: Decimal = Decimal("0")
    follow_up_fee: Decimal = Decimal("0")


class DoctorConsultationFeeBatchCreate(BaseModel):
    """批量创建/更新医生诊费配置"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )
    
    doctor_id: str = Field(..., description="医生ID")
    store_id: str = Field(..., description="门店ID")
    department_id: str = Field(..., description="科室ID")
    fees: List[DoctorConsultationFeeItem] = Field(..., description="诊费配置列表")


class DoctorConsultationFeeQuery(BaseModel):
    """查询医生诊费配置的参数"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )
    
    doctor_id: str
    store_id: Optional[str] = None
    department_id: Optional[str] = None


class DoctorFeeSettingResponse(BaseModel):
    """医生诊费设置响应（包含是否使用模板）"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        by_alias=True,
    )
    
    doctor_id: Optional[str] = None
    doctor_name: Optional[str] = None
    use_fee_template: Optional[int] = 0
    fees: List[DoctorConsultationFeeResponse] = []


class DoctorFeeSettingUpdate(BaseModel):
    """更新医生诊费设置"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )
    
    use_fee_template: int = Field(..., ge=0, le=1, description="是否使用诊费模板 0否 1是")


class StoreDepartmentFeeGroup(BaseModel):
    """门店-科室下的诊费配置分组"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        by_alias=True,
    )
    
    store_id: Optional[str] = None
    store_name: Optional[str] = None
    department_id: Optional[str] = None
    department_name: Optional[str] = None
    fees: List[DoctorConsultationFeeItem] = []
