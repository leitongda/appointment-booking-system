"""用户行为日志 Schema"""
import json
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.enums.general import BehaviorEventType as EventType  # noqa: F401 — re-export
from app.enums.general import Platform
from app.schemas.base import BaseRequestSchema, BaseSchema
from app.schemas.response import to_camel


class TrackEventRequest(BaseRequestSchema):
    """单条埋点上报请求"""

    platform: Platform = Field(..., description="平台")
    session_id: str | None = Field(None, max_length=64, description="会话ID")
    event_type: EventType = Field(..., description="事件类型")
    page_path: str | None = Field(None, max_length=255, description="页面路径")
    page_title: str | None = Field(None, max_length=100, description="页面标题")
    element_id: str | None = Field(None, max_length=100, description="元素ID")
    element_text: str | None = Field(None, max_length=200, description="元素文本")
    search_keyword: str | None = Field(None, max_length=200, description="搜索关键词")
    event_name: str | None = Field(None, max_length=100, description="自定义事件名称")
    duration: int | None = Field(None, ge=0, description="停留时长(毫秒)")
    referrer: str | None = Field(None, max_length=255, description="来源页面")
    extra_data: dict | None = Field(None, description="额外数据")

    @field_validator("extra_data")
    @classmethod
    def validate_extra_data_size(cls, v: dict | None) -> dict | None:
        if v is not None:
            serialized = json.dumps(v, ensure_ascii=False)
            if len(serialized) > 4096:
                raise ValueError("extra_data 序列化后不能超过 4096 字符")
        return v

class BatchTrackRequest(BaseRequestSchema):
    """批量埋点上报请求"""

    events: list[TrackEventRequest] = Field(..., min_length=1, max_length=100, description="事件列表")

class UserBehaviorLogResponse(BaseSchema):
    """用户行为日志响应"""

    id: str
    platform: str | None = None
    user_id: str | None = None
    session_id: str | None = None
    event_type: str | None = None
    page_path: str | None = None
    page_title: str | None = None
    element_id: str | None = None
    element_text: str | None = None
    search_keyword: str | None = None
    event_name: str | None = None
    duration: int | None = None
    referrer: str | None = None
    extra_data: str | None = None
    ip: str | None = None
    user_agent: str | None = None
    device_type: str | None = None
    browser: str | None = None
    os: str | None = None
    created_at: datetime | None = None

# ========== 统计相关 Schema ==========

class PageViewStats(BaseModel):
    """页面访问统计"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        by_alias=True,
    )
    
    page_path: str | None = None
    page_title: str | None = None
    view_count: int = 0
    unique_users: int = 0

class ClickStats(BaseModel):
    """点击统计"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        by_alias=True,
    )
    
    element_id: str | None = None
    element_text: str | None = None
    page_path: str | None = None
    click_count: int = 0

class SearchKeywordStats(BaseModel):
    """搜索关键词统计"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        by_alias=True,
    )
    
    keyword: str | None = None
    search_count: int = 0

class DailyStats(BaseModel):
    """每日统计"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        by_alias=True,
    )
    
    date: str | None = None
    page_views: int = 0
    unique_users: int = 0
    clicks: int = 0
    searches: int = 0

class BehaviorOverview(BaseModel):
    """行为概览"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        by_alias=True,
    )

    total_page_views: int = 0
    total_unique_users: int = 0
    total_clicks: int = 0
    total_searches: int = 0
    avg_duration: float | None = None
    top_pages: list[PageViewStats] = []
    top_clicks: list[ClickStats] = []
    top_keywords: list[SearchKeywordStats] = []
    daily_stats: list[DailyStats] = []

class TenantActivityDaily(BaseModel):
    """租户每日活跃度"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        by_alias=True,
    )

    date: str
    dau: int = 0
    new_users: int = 0
    total_sessions: int = 0

class TenantActivityStats(BaseModel):
    """租户活跃度统计响应"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        by_alias=True,
    )

    tenant_id: str | None = None
    start_date: str
    end_date: str
    current_dau: int = 0
    current_wau: int = 0
    current_mau: int = 0
    daily_stats: list[TenantActivityDaily] = []
