from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List
from datetime import datetime
from decimal import Decimal


def to_camel(string: str) -> str:
    """将 snake_case 转换为 camelCase"""
    components = string.split('_')
    return components[0] + ''.join(x.title() for x in components[1:])


# ========== 用户相关 ==========
class UserBase(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )
    
    phone: str = Field(..., min_length=11, max_length=11, description="手机号")
    nickname: Optional[str] = Field(None, max_length=50)
    avatar: Optional[str] = None
    gender: Optional[int] = Field(0, ge=0, le=2, description="性别: 0未知 1男 2女")


class UserCreate(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )
    
    phone: str = Field(..., min_length=11, max_length=11)
    password: str = Field("", max_length=20, description="密码，微信用户可为空")
    openid: Optional[str] = Field(None, max_length=100, description="微信 openid")


class UserUpdate(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )
    
    nickname: Optional[str] = Field(None, max_length=50)
    avatar: Optional[str] = None
    gender: Optional[int] = Field(None, ge=0, le=2)


class ChangePasswordRequest(BaseModel):
    """修改密码请求"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )
    
    old_password: str = Field(..., min_length=6, max_length=20, description="旧密码")
    new_password: str = Field(..., min_length=6, max_length=20, description="新密码")


class BindPhoneRequest(BaseModel):
    """绑定手机号请求"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )
    
    phone: str = Field(..., min_length=11, max_length=11, description="新手机号")
    code: Optional[str] = Field(None, max_length=6, description="验证码（可选）")

class UserInDB(UserBase):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
        by_alias=True,
    )
    
    id: str
    status: int
    points: int = 0
    created_at: datetime
    updated_at: datetime


class UserResponse(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
        by_alias=True,
    )
    
    id: str
    phone: Optional[str] = None
    nickname: Optional[str] = None
    avatar: Optional[str] = None
    gender: Optional[int] = 0
    status: Optional[int] = 1
    points: int = 0

# ========== 就诊人相关 ==========
class PatientBase(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )
    
    name: str = Field(..., max_length=50, description="姓名")
    phone: str = Field(..., min_length=11, max_length=11)
    id_card: Optional[str] = Field(None, max_length=18, description="身份证号")
    gender: Optional[int] = Field(None, ge=0, le=2)
    relationship: Optional[str] = Field(None, max_length=20, description="与账号用户关系")
    is_default: bool = False
    # 新增字段
    card_no: Optional[str] = Field(None, max_length=50, description="就诊卡编号")
    province: Optional[str] = Field(None, max_length=50, description="省")
    city: Optional[str] = Field(None, max_length=50, description="市")
    district: Optional[str] = Field(None, max_length=50, description="区")
    street: Optional[str] = Field(None, max_length=100, description="街道/社区")
    id_card_type: int = Field(1, ge=1, le=3, description="证件类型: 1身份证 2户口簿 3护照")
    ethnicity: str = Field("汉族", max_length=20, description="民族")
    address: Optional[str] = Field(None, max_length=255, description="详细地址")
    source: int = Field(1, ge=1, le=2, description="来源: 1用户添加 2管理员添加")


class PatientCreate(PatientBase):
    pass


class PatientCreateByAdmin(BaseModel):
    """管理员创建患者（会同时创建用户）"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )
    
    name: str = Field(..., max_length=50, description="姓名")
    phone: str = Field(..., min_length=11, max_length=11, description="手机号")
    id_card: Optional[str] = Field(None, max_length=18, description="身份证号")
    gender: Optional[int] = Field(None, ge=0, le=2)
    birthday: Optional[str] = Field(None, description="出生日期 YYYY-MM-DD")
    relationship: Optional[str] = Field(None, max_length=20, description="与账号用户关系")
    is_default: bool = True
    province: Optional[str] = Field(None, max_length=50, description="省")
    city: Optional[str] = Field(None, max_length=50, description="市")
    district: Optional[str] = Field(None, max_length=50, description="区")
    street: Optional[str] = Field(None, max_length=100, description="街道/社区")
    id_card_type: int = Field(1, ge=1, le=3, description="证件类型: 1身份证 2户口簿 3护照")
    ethnicity: str = Field("汉族", max_length=20, description="民族")
    address: Optional[str] = Field(None, max_length=255, description="详细地址")


class FamilyMemberCreate(BaseModel):
    """添加家庭成员（亲友）"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )
    
    name: str = Field(..., max_length=50, description="姓名")
    phone: str = Field(..., min_length=11, max_length=11, description="手机号")
    id_card: Optional[str] = Field(None, max_length=18, description="身份证号")
    gender: Optional[int] = Field(None, ge=0, le=2)
    birthday: Optional[str] = Field(None, description="出生日期 YYYY-MM-DD")
    relationship: Optional[str] = Field(None, max_length=20, description="与账号用户关系")
    is_default: bool = False
    province: Optional[str] = Field(None, max_length=50, description="省")
    city: Optional[str] = Field(None, max_length=50, description="市")
    district: Optional[str] = Field(None, max_length=50, description="区")
    street: Optional[str] = Field(None, max_length=100, description="街道/社区")
    id_card_type: int = Field(1, ge=1, le=3, description="证件类型: 1身份证 2户口簿 3护照")
    ethnicity: str = Field("汉族", max_length=20, description="民族")
    address: Optional[str] = Field(None, max_length=255, description="详细地址")


class PatientUpdate(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )
    
    name: Optional[str] = Field(None, max_length=50)
    phone: Optional[str] = Field(None, min_length=11, max_length=11)
    id_card: Optional[str] = Field(None, max_length=18)
    gender: Optional[int] = Field(None, ge=0, le=2)
    relationship: Optional[str] = Field(None, max_length=20)
    is_default: Optional[bool] = None
    # 新增可更新字段
    province: Optional[str] = Field(None, max_length=50)
    city: Optional[str] = Field(None, max_length=50)
    district: Optional[str] = Field(None, max_length=50)
    street: Optional[str] = Field(None, max_length=100)
    id_card_type: Optional[int] = Field(None, ge=1, le=3)
    ethnicity: Optional[str] = Field(None, max_length=20)
    address: Optional[str] = Field(None, max_length=255)


class PatientResponse(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
        by_alias=True,
    )
    
    id: str
    user_id: Optional[str] = None
    name: Optional[str] = None
    phone: Optional[str] = None
    id_card: Optional[str] = None
    gender: Optional[int] = None
    relationship: Optional[str] = None
    is_default: bool = False
    card_no: Optional[str] = None
    province: Optional[str] = None
    city: Optional[str] = None
    district: Optional[str] = None
    street: Optional[str] = None
    id_card_type: int = 1
    ethnicity: str = "汉族"
    address: Optional[str] = None
    source: int = 1
    birthday: Optional[datetime] = None
    total_consumption: Decimal = Decimal("0")
    created_at: Optional[datetime] = None


# ========== 患者详情响应（管理后台） ==========
class PatientListItemResponse(BaseModel):
    """患者列表项"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
        by_alias=True,
    )
    
    id: str
    user_id: Optional[str] = None
    card_no: Optional[str] = None
    name: Optional[str] = None
    phone: Optional[str] = None
    id_card: Optional[str] = None
    gender: Optional[int] = None
    birthday: Optional[str] = None
    relationship: Optional[str] = None
    is_default: bool = False
    appointment_count: int = 0
    no_show_count: int = 0
    is_blacklist: bool = False
    created_at: Optional[str] = None


class PatientStatistics(BaseModel):
    """患者统计信息"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        by_alias=True,
    )
    
    appointment_count: int = 0
    completed_count: int = 0
    no_show_count: int = 0


class PatientDetailResponse(BaseModel):
    """患者详情响应"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
        by_alias=True,
    )
    
    # 基本信息
    id: str
    user_id: Optional[str] = None
    card_no: Optional[str] = None
    name: Optional[str] = None
    phone: Optional[str] = None
    gender: Optional[int] = None
    province: Optional[str] = None
    city: Optional[str] = None
    district: Optional[str] = None
    street: Optional[str] = None
    id_card_type: int = 1
    id_card: Optional[str] = None
    ethnicity: str = "汉族"
    birthday: Optional[str] = None
    age: Optional[int] = None
    relationship: Optional[str] = None
    address: Optional[str] = None
    source: int = 1
    total_consumption: float = 0
    last_visit_date: Optional[str] = None
    is_blacklist: bool = False
    created_at: Optional[str] = None
    
    # 用户信息
    nickname: Optional[str] = None
    points: int = 0
    
    # 统计信息
    statistics: PatientStatistics
    
    # 家庭成员
    family_members: List[PatientListItemResponse] = []

