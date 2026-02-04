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
    
    phone: str = Field("", max_length=11, description="手机号，微信用户可为空")
    password: str = Field("", max_length=20, description="密码，微信用户可为空")
    openid: Optional[str] = Field(None, max_length=100, description="微信 openid")
    unionid: Optional[str] = Field(None, max_length=100, description="微信开放平台统一ID")
    nickname: Optional[str] = Field(None, max_length=50, description="昵称")
    avatar: Optional[str] = Field(None, description="头像URL")


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
    """用户信息响应"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
        by_alias=True,
    )
    
    id: str = Field(..., description="用户ID")
    phone: Optional[str] = Field(None, description="手机号")
    nickname: Optional[str] = Field(None, description="昵称")
    avatar: Optional[str] = Field(None, description="头像URL")
    gender: Optional[int] = Field(0, description="性别: 0未知 1男 2女")
    status: Optional[int] = Field(1, description="状态: 0禁用 1正常")
    points: int = Field(0, description="积分")

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
    age: Optional[int] = Field(None, ge=0, le=150, description="年龄")
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
    age: Optional[int] = Field(None, ge=0, le=150, description="年龄")
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
    age: Optional[int] = Field(None, ge=0, le=150, description="年龄")
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
    age: Optional[int] = Field(None, ge=0, le=150, description="年龄")
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
    """就诊人信息响应"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
        by_alias=True,
    )
    
    id: str = Field(..., description="就诊人ID")
    user_id: Optional[str] = Field(None, description="所属用户ID")
    name: Optional[str] = Field(None, description="姓名")
    phone: Optional[str] = Field(None, description="手机号")
    id_card: Optional[str] = Field(None, description="证件号码")
    gender: Optional[int] = Field(None, description="性别: 0未知 1男 2女")
    age: Optional[int] = Field(None, description="年龄")
    relationship: Optional[str] = Field(None, description="与账号用户关系")
    is_default: bool = Field(False, description="是否默认就诊人")
    card_no: Optional[str] = Field(None, description="就诊卡编号")
    province: Optional[str] = Field(None, description="省")
    city: Optional[str] = Field(None, description="市")
    district: Optional[str] = Field(None, description="区")
    street: Optional[str] = Field(None, description="街道/社区")
    id_card_type: int = Field(1, description="证件类型: 1身份证 2户口簿 3护照")
    ethnicity: str = Field("汉族", description="民族")
    address: Optional[str] = Field(None, description="详细地址")
    source: int = Field(1, description="来源: 1用户添加 2管理员添加")
    birthday: Optional[datetime] = Field(None, description="出生日期")
    total_consumption: Decimal = Field(Decimal("0"), description="总消费金额")
    created_at: Optional[datetime] = Field(None, description="创建时间")


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
    age: Optional[int] = None
    birthday: Optional[str] = None
    relationship: Optional[str] = None
    is_default: bool = False
    source: int = 1
    appointment_count: int = 0
    no_show_count: int = 0
    is_blacklist: bool = False
    created_at: Optional[str] = None
    # 所属患者信息（用于就诊卡列表显示）
    user_phone: Optional[str] = None
    user_nickname: Optional[str] = None


class PatientStatistics(BaseModel):
    """患者统计信息"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        by_alias=True,
    )
    
    appointment_count: int = Field(0, description="预约总数")
    completed_count: int = Field(0, description="已完成数")
    no_show_count: int = Field(0, description="爽约数")


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

