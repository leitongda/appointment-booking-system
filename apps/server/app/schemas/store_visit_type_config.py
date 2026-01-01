from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from datetime import datetime
from enum import Enum


def to_camel(string: str) -> str:
    """将 snake_case 转换为 camelCase"""
    components = string.split('_')
    return components[0] + ''.join(x.title() for x in components[1:])


class TimeUnit(str, Enum):
    HOURS = "hours"
    DAYS = "days"


class VisitScope(str, Enum):
    SAME_DOCTOR = "same_doctor"
    SAME_DEPARTMENT = "same_department"
    SAME_STORE = "same_store"


class StoreVisitTypeConfigBase(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )
    
    time_limit: int = Field(30, ge=1, description="复诊时间限制值")
    time_unit: TimeUnit = Field(TimeUnit.DAYS, description="时间单位：hours/days")
    scope: VisitScope = Field(VisitScope.SAME_DOCTOR, description="复诊范围")
    status: int = Field(1, ge=0, le=1, description="状态: 0禁用 1启用")


class StoreVisitTypeConfigCreate(StoreVisitTypeConfigBase):
    store_id: str = Field(..., description="门店ID")


class StoreVisitTypeConfigUpdate(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )
    
    time_limit: Optional[int] = Field(None, ge=1)
    time_unit: Optional[TimeUnit] = None
    scope: Optional[VisitScope] = None
    status: Optional[int] = Field(None, ge=0, le=1)


class StoreVisitTypeConfigResponse(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
        by_alias=True,
    )
    
    id: str
    store_id: str
    store_name: Optional[str] = None
    time_limit: int
    time_unit: str
    scope: str
    status: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

