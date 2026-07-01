from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.response import to_camel

# 与前端 @hospital/shared PATIENT_RELATIONSHIP 保持一致
RELATIONSHIP_TYPE = Literal["本人", "父母", "子女", "配偶", "其他"]

# ========== 用户相关 ==========
class UserBase(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )
    
    phone: str = Field(..., min_length=11, max_length=11, description="手机号")
    nickname: str | None = Field(None, max_length=50)
    avatar: str | None = None
    gender: int | None = Field(0, ge=0, le=2, description="性别: 0未知 1男 2女")

class UserCreate(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )
    
    phone: str = Field("", max_length=11, description="手机号，微信用户可为空")
    email: str | None = Field(None, max_length=100, description="邮箱")
    password: str = Field("", max_length=20, description="密码，微信用户可为空")
    openid: str | None = Field(None, max_length=100, description="微信 openid")
    unionid: str | None = Field(None, max_length=100, description="微信开放平台统一ID")
    nickname: str | None = Field(None, max_length=50, description="昵称")
    avatar: str | None = Field(None, description="头像URL")

class UserUpdate(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    nickname: str | None = Field(None, max_length=50)
    avatar: str | None = None
    gender: int | None = Field(None, ge=0, le=2)

class AdminUserUpdate(BaseModel):
    """管理员更新用户信息"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    nickname: str | None = Field(None, max_length=50, description="昵称")
    phone: str | None = Field(None, min_length=11, max_length=11, description="手机号")
    avatar: str | None = Field(None, description="头像URL")
    gender: int | None = Field(None, ge=0, le=2, description="性别: 0未知 1男 2女")

# NOTE: ChangePasswordRequest 已收敛到 app.schemas.common（统一密码策略 6-20 位）。
# 原 old/new min_length=6, max_length=20 与统一版完全等价，无行为变化。
# 请改为: from app.schemas.common import ChangePasswordRequest

class BindPhoneRequest(BaseModel):
    """绑定手机号请求"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )
    
    phone: str = Field(..., min_length=11, max_length=11, description="新手机号")
    code: str | None = Field(None, max_length=6, description="验证码（可选）")

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
    phone: str | None = Field(None, description="手机号")
    email: str | None = Field(None, description="邮箱")
    nickname: str | None = Field(None, description="昵称")
    avatar: str | None = Field(None, description="头像URL")
    gender: int | None = Field(0, description="性别: 0未知 1男 2女")
    status: int | None = Field(1, description="状态: 0禁用 1正常")
    points: int = Field(0, description="积分")
    has_password: bool = Field(False, description="是否已设置密码")

# ========== 就诊人相关 ==========
class PatientBase(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )
    
    name: str = Field(..., max_length=50, description="姓名")
    phone: str = Field(..., min_length=11, max_length=11)
    id_card: str | None = Field(None, max_length=18, description="身份证号")
    gender: int | None = Field(None, ge=0, le=2)
    age: int | None = Field(None, ge=0, le=150, description="年龄")
    relationship: RELATIONSHIP_TYPE | None = Field(None, description="与账号用户关系")
    is_default: bool = False
    # 新增字段
    card_no: str | None = Field(None, max_length=50, description="就诊卡编号")
    province: str | None = Field(None, max_length=50, description="省")
    city: str | None = Field(None, max_length=50, description="市")
    district: str | None = Field(None, max_length=50, description="区")
    street: str | None = Field(None, max_length=100, description="街道/社区")
    id_card_type: int = Field(1, ge=1, le=3, description="证件类型: 1身份证 2户口簿 3护照")
    ethnicity: str = Field("汉族", max_length=20, description="民族")
    address: str | None = Field(None, max_length=255, description="详细地址")
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
    id_card: str | None = Field(None, max_length=18, description="身份证号")
    gender: int | None = Field(None, ge=0, le=2)
    age: int | None = Field(None, ge=0, le=150, description="年龄")
    birthday: str | None = Field(None, description="出生日期 YYYY-MM-DD")
    relationship: RELATIONSHIP_TYPE | None = Field(None, description="与账号用户关系")
    is_default: bool = True
    province: str | None = Field(None, max_length=50, description="省")
    city: str | None = Field(None, max_length=50, description="市")
    district: str | None = Field(None, max_length=50, description="区")
    street: str | None = Field(None, max_length=100, description="街道/社区")
    id_card_type: int = Field(1, ge=1, le=3, description="证件类型: 1身份证 2户口簿 3护照")
    ethnicity: str = Field("汉族", max_length=20, description="民族")
    address: str | None = Field(None, max_length=255, description="详细地址")

class FamilyMemberCreate(BaseModel):
    """添加家庭成员（亲友）"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )
    
    name: str = Field(..., max_length=50, description="姓名")
    phone: str = Field(..., min_length=11, max_length=11, description="手机号")
    id_card: str | None = Field(None, max_length=18, description="身份证号")
    gender: int | None = Field(None, ge=0, le=2)
    age: int | None = Field(None, ge=0, le=150, description="年龄")
    birthday: str | None = Field(None, description="出生日期 YYYY-MM-DD")
    relationship: RELATIONSHIP_TYPE | None = Field(None, description="与账号用户关系")
    is_default: bool = False
    province: str | None = Field(None, max_length=50, description="省")
    city: str | None = Field(None, max_length=50, description="市")
    district: str | None = Field(None, max_length=50, description="区")
    street: str | None = Field(None, max_length=100, description="街道/社区")
    id_card_type: int = Field(1, ge=1, le=3, description="证件类型: 1身份证 2户口簿 3护照")
    ethnicity: str = Field("汉族", max_length=20, description="民族")
    address: str | None = Field(None, max_length=255, description="详细地址")

class PatientUpdate(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )
    
    name: str | None = Field(None, max_length=50)
    phone: str | None = Field(None, min_length=11, max_length=11)
    id_card: str | None = Field(None, max_length=18)
    gender: int | None = Field(None, ge=0, le=2)
    age: int | None = Field(None, ge=0, le=150, description="年龄")
    relationship: RELATIONSHIP_TYPE | None = None
    is_default: bool | None = None
    # 新增可更新字段
    province: str | None = Field(None, max_length=50)
    city: str | None = Field(None, max_length=50)
    district: str | None = Field(None, max_length=50)
    street: str | None = Field(None, max_length=100)
    id_card_type: int | None = Field(None, ge=1, le=3)
    ethnicity: str | None = Field(None, max_length=20)
    address: str | None = Field(None, max_length=255)

class PatientResponse(BaseModel):
    """就诊人信息响应"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
        by_alias=True,
    )
    
    id: str = Field(..., description="就诊人ID")
    user_id: str | None = Field(None, description="所属用户ID")
    name: str | None = Field(None, description="姓名")
    phone: str | None = Field(None, description="手机号")
    id_card: str | None = Field(None, description="证件号码")
    gender: int | None = Field(None, description="性别: 0未知 1男 2女")
    age: int | None = Field(None, description="年龄")
    relationship: str | None = Field(None, description="与账号用户关系")
    is_default: bool = Field(False, description="是否默认就诊人")
    card_no: str | None = Field(None, description="就诊卡编号")
    province: str | None = Field(None, description="省")
    city: str | None = Field(None, description="市")
    district: str | None = Field(None, description="区")
    street: str | None = Field(None, description="街道/社区")
    id_card_type: int = Field(1, description="证件类型: 1身份证 2户口簿 3护照")
    ethnicity: str = Field("汉族", description="民族")
    address: str | None = Field(None, description="详细地址")
    source: int = Field(1, description="来源: 1用户添加 2管理员添加")
    birthday: datetime | None = Field(None, description="出生日期")
    total_consumption: Decimal = Field(Decimal("0"), description="总消费金额")
    created_at: datetime | None = Field(None, description="创建时间")

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
    user_id: str | None = None
    card_no: str | None = None
    name: str | None = None
    phone: str | None = None
    id_card: str | None = None
    gender: int | None = None
    age: int | None = None
    birthday: str | None = None
    relationship: str | None = None
    is_default: bool = False
    source: int = 1
    appointment_count: int = 0
    no_show_count: int = 0
    is_blacklist: bool = False
    created_at: str | None = None
    # 所属患者信息（用于就诊卡列表显示）
    user_phone: str | None = None
    user_nickname: str | None = None

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
    user_id: str | None = None
    card_no: str | None = None
    name: str | None = None
    phone: str | None = None
    gender: int | None = None
    province: str | None = None
    city: str | None = None
    district: str | None = None
    street: str | None = None
    id_card_type: int = 1
    id_card: str | None = None
    ethnicity: str = "汉族"
    birthday: str | None = None
    age: int | None = None
    relationship: str | None = None
    address: str | None = None
    source: int = 1
    total_consumption: float = 0
    last_visit_date: str | None = None
    is_blacklist: bool = False
    created_at: str | None = None
    
    # 用户信息
    nickname: str | None = None
    points: int = 0
    
    # 统计信息
    statistics: PatientStatistics
    
    # 家庭成员
    family_members: list[PatientListItemResponse] = []
