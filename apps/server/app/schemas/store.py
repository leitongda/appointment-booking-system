from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, time


class StoreBase(BaseModel):
    """门店基础模型"""
    name: str = Field(..., max_length=100, description="门店名称")
    code: Optional[str] = Field(None, max_length=50, description="门店编码")
    address: Optional[str] = Field(None, max_length=255, description="详细地址")
    province: Optional[str] = Field(None, max_length=50, description="省份")
    city: Optional[str] = Field(None, max_length=50, description="城市")
    district: Optional[str] = Field(None, max_length=50, description="区县")
    latitude: Optional[str] = Field(None, max_length=20, description="纬度")
    longitude: Optional[str] = Field(None, max_length=20, description="经度")
    phone: Optional[str] = Field(None, max_length=50, description="联系电话")
    contact_person: Optional[str] = Field(None, max_length=50, description="联系人")
    description: Optional[str] = Field(None, description="门店简介")
    opening_time: Optional[time] = Field(None, description="营业开始时间")
    closing_time: Optional[time] = Field(None, description="营业结束时间")
    working_days: Optional[str] = Field("1,2,3,4,5,6,7", description="工作日")
    image: Optional[str] = Field(None, max_length=255, description="门店图片")
    sort_order: int = Field(0, ge=0, description="排序")
    status: int = Field(1, ge=0, le=1, description="状态: 0-停业 1-营业")


class StoreCreate(StoreBase):
    """创建门店"""
    pass


class StoreUpdate(BaseModel):
    """更新门店"""
    name: Optional[str] = Field(None, max_length=100)
    code: Optional[str] = Field(None, max_length=50)
    address: Optional[str] = Field(None, max_length=255)
    province: Optional[str] = Field(None, max_length=50)
    city: Optional[str] = Field(None, max_length=50)
    district: Optional[str] = Field(None, max_length=50)
    latitude: Optional[str] = Field(None, max_length=20)
    longitude: Optional[str] = Field(None, max_length=20)
    phone: Optional[str] = Field(None, max_length=50)
    contact_person: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = None
    opening_time: Optional[time] = None
    closing_time: Optional[time] = None
    working_days: Optional[str] = None
    image: Optional[str] = Field(None, max_length=255)
    sort_order: Optional[int] = Field(None, ge=0)
    status: Optional[int] = Field(None, ge=0, le=1)


class StoreResponse(StoreBase):
    """门店响应"""
    id: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class StoreListResponse(BaseModel):
    """门店列表响应"""
    id: str
    name: str
    code: Optional[str]
    address: Optional[str]
    phone: Optional[str]
    status: int
    department_count: int = 0
    created_at: datetime
    
    class Config:
        from_attributes = True


class StoreDepartmentBase(BaseModel):
    """门店科室关联基础模型"""
    store_id: str = Field(..., description="门店ID")
    department_id: str = Field(..., description="科室ID")
    floor: Optional[str] = Field(None, max_length=20, description="楼层")
    room: Optional[str] = Field(None, max_length=50, description="诊室")
    status: int = Field(1, ge=0, le=1, description="状态")


class StoreDepartmentCreate(StoreDepartmentBase):
    """创建门店科室关联"""
    pass


class StoreDepartmentUpdate(BaseModel):
    """更新门店科室关联"""
    floor: Optional[str] = Field(None, max_length=20)
    room: Optional[str] = Field(None, max_length=50)
    status: Optional[int] = Field(None, ge=0, le=1)


class StoreDepartmentResponse(StoreDepartmentBase):
    """门店科室关联响应"""
    id: str
    department_name: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class StoreQuery(BaseModel):
    """门店查询参数"""
    keyword: Optional[str] = Field(None, description="搜索关键词")
    status: Optional[int] = Field(None, description="状态筛选")
    city: Optional[str] = Field(None, description="城市筛选")
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(10, ge=1, le=100, description="每页数量")
