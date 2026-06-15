from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.enums.general import TimeUnit, VisitScope  # noqa: F401 — re-export
from app.schemas.response import to_camel


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
    
    time_limit: int | None = Field(None, ge=1)
    time_unit: TimeUnit | None = None
    scope: VisitScope | None = None
    status: int | None = Field(None, ge=0, le=1)

class StoreVisitTypeConfigResponse(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
        by_alias=True,
    )
    
    id: str
    store_id: str
    store_name: str | None = None
    time_limit: int
    time_unit: str
    scope: str
    status: int
    created_at: datetime | None = None
    updated_at: datetime | None = None

