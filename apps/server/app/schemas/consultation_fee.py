from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.base import BaseRequestSchema, BaseSchema
from app.schemas.response import to_camel

# ========== 诊费类型 Schema ==========

class ConsultationFeeTypeBase(BaseRequestSchema):

    store_id: str | None = Field(None, description="门店ID，NULL表示全局类型")
    name: str = Field(..., max_length=50, description="诊费类型名称")
    code: str | None = Field(None, max_length=50, description="类型编码")
    description: str | None = Field(None, max_length=255, description="描述")
    sort_order: int = Field(0, ge=0, description="排序")
    status: int = Field(1, ge=0, le=1, description="状态: 0禁用 1启用")

class ConsultationFeeTypeCreate(ConsultationFeeTypeBase):
    pass

class ConsultationFeeTypeUpdate(BaseRequestSchema):

    store_id: str | None = None
    name: str | None = Field(None, max_length=50)
    code: str | None = Field(None, max_length=50)
    description: str | None = Field(None, max_length=255)
    sort_order: int | None = Field(None, ge=0)
    status: int | None = Field(None, ge=0, le=1)

class ConsultationFeeTypeResponse(BaseSchema):

    id: str
    store_id: str | None = None
    store_name: str | None = None
    name: str | None = None
    code: str | None = None
    description: str | None = None
    sort_order: int | None = 0
    status: int | None = 1
    is_global: bool | None = None  # 是否为全局类型
    created_at: datetime | None = None
    updated_at: datetime | None = None

# ========== 诊费模板 Schema ==========

class ConsultationFeeTemplateBase(BaseRequestSchema):

    fee_type_id: str = Field(..., description="诊费类型ID")
    initial_fee: Decimal = Field(Decimal("0"), ge=0, description="初诊金额")
    follow_up_fee: Decimal = Field(Decimal("0"), ge=0, description="复诊金额")
    status: int = Field(1, ge=0, le=1, description="状态: 0禁用 1启用")

class ConsultationFeeTemplateCreate(ConsultationFeeTemplateBase):
    pass

class ConsultationFeeTemplateUpdate(BaseRequestSchema):

    fee_type_id: str | None = None
    initial_fee: Decimal | None = Field(None, ge=0)
    follow_up_fee: Decimal | None = Field(None, ge=0)
    status: int | None = Field(None, ge=0, le=1)

class ConsultationFeeTemplateResponse(BaseSchema):

    id: str
    fee_type_id: str | None = None
    fee_type_name: str | None = None
    fee_type_code: str | None = None
    initial_fee: Decimal | None = Decimal("0")
    follow_up_fee: Decimal | None = Decimal("0")
    status: int | None = 1
    created_at: datetime | None = None
    updated_at: datetime | None = None

class ConsultationFeeTemplateWithType(BaseModel):
    """带诊费类型信息的模板响应"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        by_alias=True,
    )
    
    id: str | None = None
    fee_type_id: str | None = None
    fee_type_name: str | None = None
    fee_type_code: str | None = None
    initial_fee: Decimal = Decimal("0")
    follow_up_fee: Decimal = Decimal("0")
    status: int = 1

# ========== 门店诊费模板 Schema ==========

class StoreFeeTemplateBase(BaseRequestSchema):
    """门店诊费模板基础"""

    store_id: str = Field(..., description="门店ID")
    fee_type_id: str = Field(..., description="诊费类型ID")
    initial_fee: Decimal = Field(Decimal("0"), ge=0, description="初诊金额")
    follow_up_fee: Decimal = Field(Decimal("0"), ge=0, description="复诊金额")
    status: int = Field(1, ge=0, le=1, description="状态: 0禁用 1启用")

class StoreFeeTemplateCreate(StoreFeeTemplateBase):
    pass

class StoreFeeTemplateUpdate(BaseRequestSchema):

    initial_fee: Decimal | None = Field(None, ge=0)
    follow_up_fee: Decimal | None = Field(None, ge=0)
    status: int | None = Field(None, ge=0, le=1)

class StoreFeeTemplateResponse(BaseSchema):
    """门店诊费模板响应"""

    id: str
    store_id: str | None = None
    store_name: str | None = None
    fee_type_id: str | None = None
    fee_type_name: str | None = None
    fee_type_code: str | None = None
    initial_fee: Decimal | None = Decimal("0")
    follow_up_fee: Decimal | None = Decimal("0")
    status: int | None = 1
    created_at: datetime | None = None
    updated_at: datetime | None = None

class StoreFeeTemplateItem(BaseModel):
    """门店诊费模板项（用于批量保存）"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        by_alias=True,
    )
    
    fee_type_id: str
    fee_type_name: str | None = None
    fee_type_code: str | None = None
    initial_fee: Decimal = Decimal("0")
    follow_up_fee: Decimal = Decimal("0")

class StoreFeeTemplateBatchCreate(BaseRequestSchema):
    """批量创建/更新门店诊费模板"""

    store_id: str = Field(..., description="门店ID")
    templates: list[StoreFeeTemplateItem] = Field(..., description="诊费模板列表")

class StoreFeeTemplateWithType(BaseModel):
    """带诊费类型信息的门店模板响应（用于列表展示）"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        by_alias=True,
    )
    
    id: str | None = None
    store_id: str | None = None
    fee_type_id: str
    fee_type_name: str
    fee_type_code: str | None = None
    initial_fee: Decimal = Decimal("0")
    follow_up_fee: Decimal = Decimal("0")
    global_initial_fee: Decimal | None = Decimal("0")  # 全局模板的初诊金额（用于参考）
    global_follow_up_fee: Decimal | None = Decimal("0")  # 全局模板的复诊金额（用于参考）
    status: int = 1
    is_global_type: bool = True  # 是否为全局类型

class ApplyTemplateRequest(BaseRequestSchema):
    """一键带入模板请求"""

    store_id: str = Field(..., description="门店ID")
    department_id: str = Field(..., description="科室ID")

# ========== 医生诊费配置 Schema ==========

class DoctorConsultationFeeBase(BaseRequestSchema):

    doctor_id: str = Field(..., description="医生ID")
    store_id: str = Field(..., description="门店ID")
    department_id: str = Field(..., description="科室ID")
    fee_type_id: str = Field(..., description="诊费类型ID")
    initial_fee: Decimal = Field(Decimal("0"), ge=0, description="初诊金额")
    follow_up_fee: Decimal = Field(Decimal("0"), ge=0, description="复诊金额")
    status: int = Field(1, ge=0, le=1, description="状态: 0禁用 1启用")

class DoctorConsultationFeeCreate(DoctorConsultationFeeBase):
    pass

class DoctorConsultationFeeUpdate(BaseRequestSchema):

    initial_fee: Decimal | None = Field(None, ge=0)
    follow_up_fee: Decimal | None = Field(None, ge=0)
    status: int | None = Field(None, ge=0, le=1)

class DoctorConsultationFeeResponse(BaseSchema):

    id: str
    doctor_id: str | None = None
    store_id: str | None = None
    department_id: str | None = None
    fee_type_id: str | None = None
    initial_fee: Decimal | None = Decimal("0")
    follow_up_fee: Decimal | None = Decimal("0")
    status: int | None = 1
    store_name: str | None = None
    department_name: str | None = None
    fee_type_name: str | None = None
    fee_type_code: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

class DoctorConsultationFeeItem(BaseModel):
    """单个诊费类型的金额配置"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        by_alias=True,
    )
    
    fee_type_id: str | None = None
    fee_type_name: str | None = None
    fee_type_code: str | None = None
    initial_fee: Decimal = Decimal("0")
    follow_up_fee: Decimal = Decimal("0")

class DoctorConsultationFeeBatchCreate(BaseRequestSchema):
    """批量创建/更新医生诊费配置"""

    doctor_id: str = Field(..., description="医生ID")
    store_id: str = Field(..., description="门店ID")
    department_id: str = Field(..., description="科室ID")
    fees: list[DoctorConsultationFeeItem] = Field(..., description="诊费配置列表")

class DoctorConsultationFeeQuery(BaseRequestSchema):
    """查询医生诊费配置的参数"""

    doctor_id: str
    store_id: str | None = None
    department_id: str | None = None

class DoctorFeeSettingResponse(BaseModel):
    """医生诊费设置响应（包含是否使用模板）"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        by_alias=True,
    )
    
    doctor_id: str | None = None
    doctor_name: str | None = None
    use_fee_template: int | None = 0
    fees: list[DoctorConsultationFeeResponse] = []

class DoctorFeeSettingUpdate(BaseRequestSchema):
    """更新医生诊费设置"""

    use_fee_template: int = Field(..., ge=0, le=1, description="是否使用诊费模板 0否 1是")

class StoreDepartmentFeeGroup(BaseModel):
    """门店-科室下的诊费配置分组"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        by_alias=True,
    )
    
    store_id: str | None = None
    store_name: str | None = None
    department_id: str | None = None
    department_name: str | None = None
    fees: list[DoctorConsultationFeeItem] = []
