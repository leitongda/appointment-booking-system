from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import date, datetime
from app.core.config import settings


def to_camel(string: str) -> str:
    """将 snake_case 转换为 camelCase"""
    components = string.split('_')
    return components[0] + ''.join(x.title() for x in components[1:])


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
    
    id: str
    store_id: str
    store_name: Optional[str] = None
    doctor_ids: Optional[List[str]] = None
    doctor_names: Optional[List[str]] = None
    reason: Optional[str] = None
    start_date: date
    end_date: date
    status: int
    created_at: datetime


class RestDayListParams(BaseModel):
    """查询休息日列表参数"""
    store_id: Optional[str] = None
    doctor_id: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    status: Optional[int] = Field(None, ge=0, le=1)
    page: int = Field(1, ge=1)
    page_size: int = Field(10, ge=1, le=settings.MAX_PAGE_SIZE)
