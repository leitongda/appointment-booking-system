from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import date, datetime
from app.core.config import settings
from app.schemas.response import to_camel

class RestDayCreate(BaseModel):
    """创建休息日"""
    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_camel,
    )
    
    store_id: str = Field(..., description="门店ID")
    doctor_ids: Optional[List[str]] = Field(None, description="医生ID列表,不填则门店所有医生休息")
    reason: Optional[str] = Field(None, max_length=255, description="休息原因")
    start_date: date = Field(..., description="开始日期")
    end_date: date = Field(..., description="结束日期")

class RestDayResponse(BaseModel):
    """休息日响应"""
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        alias_generator=to_camel,
        by_alias=True,
    )

    id: str = Field(..., description="休息日ID")
    store_id: str = Field(..., description="门店ID")
    store_name: Optional[str] = Field(None, description="门店名称")
    doctor_ids: Optional[List[str]] = Field(None, description="医生ID列表")
    doctor_names: Optional[List[str]] = Field(None, description="医生姓名列表")
    reason: Optional[str] = Field(None, description="休息原因")
    start_date: date = Field(..., description="开始日期")
    end_date: date = Field(..., description="结束日期")
    status: int = Field(..., description="状态")
    created_at: datetime = Field(..., description="创建时间")

class RestDayListParams(BaseModel):
    """查询休息日列表参数"""
    store_id: Optional[str] = Field(None, description="门店ID")
    doctor_id: Optional[str] = Field(None, description="医生ID")
    start_date: Optional[date] = Field(None, description="开始日期")
    end_date: Optional[date] = Field(None, description="结束日期")
    status: Optional[int] = Field(None, ge=0, le=1, description="状态")
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(10, ge=1, le=settings.MAX_PAGE_SIZE, description="每页数量")
