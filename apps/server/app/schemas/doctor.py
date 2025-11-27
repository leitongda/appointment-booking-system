from pydantic import BaseModel, Field
from typing import Optional
from decimal import Decimal
from datetime import datetime

class DoctorBase(BaseModel):
    department_id: str = Field(..., description="科室ID")
    name: str = Field(..., max_length=50, description="医生姓名")
    phone: Optional[str] = Field(None, max_length=20)
    avatar: Optional[str] = None
    title: Optional[str] = Field(None, max_length=50, description="职称")
    specialty: Optional[str] = Field(None, description="擅长")
    introduction: Optional[str] = Field(None, description="简介")
    registration_fee: Decimal = Field(Decimal("0"), ge=0, description="挂号费")
    is_recommended: int = Field(0, ge=0, le=1, description="是否推荐")
    sort_order: int = Field(0, ge=0)
    status: int = Field(1, ge=0, le=1)

class DoctorCreate(DoctorBase):
    password: Optional[str] = Field(None, min_length=6, description="医生账号密码")

class DoctorUpdate(BaseModel):
    department_id: Optional[str] = None
    name: Optional[str] = Field(None, max_length=50)
    phone: Optional[str] = Field(None, max_length=20)
    avatar: Optional[str] = None
    title: Optional[str] = Field(None, max_length=50)
    specialty: Optional[str] = None
    introduction: Optional[str] = None
    registration_fee: Optional[Decimal] = Field(None, ge=0)
    is_recommended: Optional[int] = Field(None, ge=0, le=1)
    sort_order: Optional[int] = Field(None, ge=0)
    status: Optional[int] = Field(None, ge=0, le=1)

class DoctorResponse(DoctorBase):
    id: str
    user_id: Optional[str]
    department_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class DoctorListResponse(BaseModel):
    id: str
    name: str
    avatar: Optional[str]
    title: Optional[str]
    department_id: str
    department_name: Optional[str]
    specialty: Optional[str]
    registration_fee: Decimal
    is_recommended: int
    
    class Config:
        from_attributes = True

