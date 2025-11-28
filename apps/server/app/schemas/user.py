from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

# ========== 用户相关 ==========
class UserBase(BaseModel):
    phone: str = Field(..., min_length=11, max_length=11, description="手机号")
    nickname: Optional[str] = Field(None, max_length=50)
    avatar: Optional[str] = None
    gender: Optional[int] = Field(0, ge=0, le=2, description="性别: 0未知 1男 2女")

class UserCreate(BaseModel):
    phone: str = Field(..., min_length=11, max_length=11)
    password: str = Field("", max_length=20, description="密码，微信用户可为空")
    openid: Optional[str] = Field(None, max_length=100, description="微信 openid")

class UserUpdate(BaseModel):
    nickname: Optional[str] = Field(None, max_length=50)
    avatar: Optional[str] = None
    gender: Optional[int] = Field(None, ge=0, le=2)

class UserInDB(UserBase):
    id: str
    status: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class UserResponse(UserBase):
    id: str
    status: int

# ========== 就诊人相关 ==========
class PatientBase(BaseModel):
    name: str = Field(..., max_length=50, description="姓名")
    phone: str = Field(..., min_length=11, max_length=11)
    id_card: Optional[str] = Field(None, max_length=18, description="身份证号")
    gender: Optional[int] = Field(None, ge=0, le=2)
    relationship: Optional[str] = Field(None, max_length=20, description="与账号用户关系")
    is_default: bool = False

class PatientCreate(PatientBase):
    pass

class PatientUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=50)
    phone: Optional[str] = Field(None, min_length=11, max_length=11)
    id_card: Optional[str] = Field(None, max_length=18)
    gender: Optional[int] = Field(None, ge=0, le=2)
    relationship: Optional[str] = Field(None, max_length=20)
    is_default: Optional[bool] = None

class PatientResponse(PatientBase):
    id: str
    user_id: str
    
    class Config:
        from_attributes = True

