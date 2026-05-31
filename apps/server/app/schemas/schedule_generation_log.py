from app.schemas.response import to_camel
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List
from datetime import date, datetime

from app.enums.schedule import ActionType  # noqa: F401 — re-export

class ScheduleGenerationLogResponse(BaseModel):
    """排班生成日志响应"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
        by_alias=True,
    )
    
    id: str
    template_id: str
    operator_id: Optional[str] = None
    operator_name: Optional[str] = None
    action_type: str
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    affected_count: int = 0
    remark: Optional[str] = None
    created_at: datetime

class CheckGeneratedResponse(BaseModel):
    """检查是否已生成排班响应"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        by_alias=True,
    )
    
    has_generated: bool = Field(description="是否已生成过排班")
    schedule_count: int = Field(default=0, description="已生成的排班数量")
    date_range_count: int = Field(default=0, description="日期范围内的排班数量")
    earliest_date: Optional[date] = Field(None, description="最早的排班日期")
    latest_date: Optional[date] = Field(None, description="最晚的排班日期")

class BatchOperateRequest(BaseModel):
    """批量操作请求"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )
    
    start_date: Optional[date] = Field(None, description="开始日期（可选，不传则操作所有）")
    end_date: Optional[date] = Field(None, description="结束日期（可选，不传则操作所有）")
    future_only: bool = Field(True, description="是否只操作未来的排班")

class BatchOperateResponse(BaseModel):
    """批量操作响应"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        by_alias=True,
    )
    
    success: bool = True
    affected_count: int = 0
    message: str = ""

