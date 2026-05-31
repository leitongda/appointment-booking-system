"""预约须知 Schema"""
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List
from datetime import datetime
from app.core.config import settings
from app.schemas.response import to_camel

class BookingNoticeCreate(BaseModel):
    """创建预约须知请求"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )
    
    type: str = Field(..., max_length=50, description="类型: BOOKING/VISIT/REFUND")
    title: Optional[str] = Field(None, max_length=100, description="标题")
    content: Optional[str] = Field(None, description="内容")
    sort_order: int = Field(0, ge=0, description="排序")
    status: int = Field(1, ge=0, le=1, description="状态: 0禁用 1启用")

class BookingNoticeUpdate(BaseModel):
    """更新预约须知请求"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )
    
    type: Optional[str] = Field(None, max_length=50)
    title: Optional[str] = Field(None, max_length=100)
    content: Optional[str] = None
    sort_order: Optional[int] = Field(None, ge=0)
    status: Optional[int] = Field(None, ge=0, le=1)

class BookingNoticeResponse(BaseModel):
    """预约须知响应"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
        by_alias=True,
    )
    
    id: str
    type: str
    title: Optional[str] = None
    content: Optional[str] = None
    sort_order: int = 0
    status: int = 1
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class BookingNoticeListQuery(BaseModel):
    """预约须知列表查询"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )
    
    type: Optional[str] = None
    status: Optional[int] = None
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=settings.MAX_PAGE_SIZE)

