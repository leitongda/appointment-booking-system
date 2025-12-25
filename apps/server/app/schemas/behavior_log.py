"""用户行为日志 Schema"""
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


def to_camel(string: str) -> str:
    """将 snake_case 转换为 camelCase"""
    components = string.split('_')
    return components[0] + ''.join(x.title() for x in components[1:])


class Platform(str, Enum):
    """平台枚举"""
    ADMIN = "admin"
    H5 = "h5"
    MINIAPP = "miniapp"


class EventType(str, Enum):
    """事件类型枚举"""
    PAGE_VIEW = "page_view"      # 页面访问
    PAGE_LEAVE = "page_leave"    # 页面离开
    CLICK = "click"              # 点击
    SEARCH = "search"            # 搜索
    CUSTOM = "custom"            # 自定义事件


class TrackEventRequest(BaseModel):
    """单条埋点上报请求"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )
    
    platform: Platform = Field(..., description="平台")
    session_id: Optional[str] = Field(None, max_length=64, description="会话ID")
    event_type: EventType = Field(..., description="事件类型")
    page_path: Optional[str] = Field(None, max_length=255, description="页面路径")
    page_title: Optional[str] = Field(None, max_length=100, description="页面标题")
    element_id: Optional[str] = Field(None, max_length=100, description="元素ID")
    element_text: Optional[str] = Field(None, max_length=200, description="元素文本")
    search_keyword: Optional[str] = Field(None, max_length=200, description="搜索关键词")
    event_name: Optional[str] = Field(None, max_length=100, description="自定义事件名称")
    duration: Optional[int] = Field(None, ge=0, description="停留时长(毫秒)")
    referrer: Optional[str] = Field(None, max_length=255, description="来源页面")
    extra_data: Optional[dict] = Field(None, description="额外数据")


class BatchTrackRequest(BaseModel):
    """批量埋点上报请求"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )
    
    events: List[TrackEventRequest] = Field(..., min_length=1, max_length=100, description="事件列表")


class UserBehaviorLogResponse(BaseModel):
    """用户行为日志响应"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
        by_alias=True,
    )
    
    id: str
    platform: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    event_type: Optional[str] = None
    page_path: Optional[str] = None
    page_title: Optional[str] = None
    element_id: Optional[str] = None
    element_text: Optional[str] = None
    search_keyword: Optional[str] = None
    event_name: Optional[str] = None
    duration: Optional[int] = None
    referrer: Optional[str] = None
    extra_data: Optional[str] = None
    ip: Optional[str] = None
    user_agent: Optional[str] = None
    device_type: Optional[str] = None
    browser: Optional[str] = None
    os: Optional[str] = None
    created_at: Optional[datetime] = None


# ========== 统计相关 Schema ==========

class PageViewStats(BaseModel):
    """页面访问统计"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        by_alias=True,
    )
    
    page_path: Optional[str] = None
    page_title: Optional[str] = None
    view_count: int = 0
    unique_users: int = 0


class ClickStats(BaseModel):
    """点击统计"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        by_alias=True,
    )
    
    element_id: Optional[str] = None
    element_text: Optional[str] = None
    page_path: Optional[str] = None
    click_count: int = 0


class SearchKeywordStats(BaseModel):
    """搜索关键词统计"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        by_alias=True,
    )
    
    keyword: Optional[str] = None
    search_count: int = 0


class DailyStats(BaseModel):
    """每日统计"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        by_alias=True,
    )
    
    date: Optional[str] = None
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
    avg_duration: Optional[float] = None
    top_pages: List[PageViewStats] = []
    top_clicks: List[ClickStats] = []
    top_keywords: List[SearchKeywordStats] = []
    daily_stats: List[DailyStats] = []
