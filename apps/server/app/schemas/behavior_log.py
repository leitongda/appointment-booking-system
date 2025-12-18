"""用户行为日志 Schema"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


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
    events: List[TrackEventRequest] = Field(..., min_length=1, max_length=100, description="事件列表")


class UserBehaviorLogResponse(BaseModel):
    """用户行为日志响应"""
    id: str
    platform: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    event_type: str
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
    created_at: datetime

    class Config:
        from_attributes = True


# ========== 统计相关 Schema ==========

class PageViewStats(BaseModel):
    """页面访问统计"""
    page_path: str
    page_title: Optional[str] = None
    view_count: int
    unique_users: int


class ClickStats(BaseModel):
    """点击统计"""
    element_id: Optional[str] = None
    element_text: Optional[str] = None
    page_path: Optional[str] = None
    click_count: int


class SearchKeywordStats(BaseModel):
    """搜索关键词统计"""
    keyword: str
    search_count: int


class DailyStats(BaseModel):
    """每日统计"""
    date: str
    page_views: int
    unique_users: int
    clicks: int
    searches: int


class BehaviorOverview(BaseModel):
    """行为概览"""
    total_page_views: int
    total_unique_users: int
    total_clicks: int
    total_searches: int
    avg_duration: Optional[float] = None
    top_pages: List[PageViewStats]
    top_clicks: List[ClickStats]
    top_keywords: List[SearchKeywordStats]
    daily_stats: List[DailyStats]

