"""操作指引 - Pydantic Schemas"""
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import Field

from app.schemas.base import BaseSchema


# ==================== 通用 ====================


class LocaleMap(BaseSchema):
    """多语言文本"""
    zh: str = Field("", description="中文")
    en: str = Field("", description="英文")


class TourStep(BaseSchema):
    """单个指引步骤"""
    target: str = Field(..., description="CSS 选择器，定位高亮元素")
    placement: str = Field("bottom", description="气泡位置: top/bottom/left/right")
    route: str = Field(..., description="步骤所在路由，如 /dashboard")
    title: Dict[str, str] = Field(..., description="多语言标题 {zh, en}")
    description: Dict[str, str] = Field(default_factory=dict, description="多语言描述 {zh, en}")
    highlight_padding: int = Field(4, alias="highlightPadding", description="高亮区域边距")


# ==================== 用户端 ====================


class GuideTourItem(BaseSchema):
    """用户端：返回的指引摘要"""
    id: str
    code: str
    title: Dict[str, str]
    description: Optional[Dict[str, str]] = None
    steps: List[TourStep]
    current_step: int = Field(0, alias="currentStep")
    progress_status: int = Field(0, alias="progressStatus", description="0=进行中, 1=已完成, 2=跳过")


class ProgressUpdate(BaseSchema):
    """用户端：更新进度请求"""
    current_step: Optional[int] = Field(None, alias="currentStep")
    status: Optional[int] = None


# ==================== 管理端 ====================


class GuideTourCreate(BaseSchema):
    """管理端：创建指引"""
    code: str = Field(..., min_length=1, max_length=100)
    title: Dict[str, str]
    description: Optional[Dict[str, str]] = None
    steps: List[TourStep] = Field(default_factory=list)
    sort_order: int = Field(0, alias="sortOrder")
    tenant_id: Optional[str] = Field(None, alias="tenantId")


class GuideTourUpdate(BaseSchema):
    """管理端：更新指引"""
    code: Optional[str] = Field(None, min_length=1, max_length=100)
    title: Optional[Dict[str, str]] = None
    description: Optional[Dict[str, str]] = None
    steps: Optional[List[TourStep]] = None
    sort_order: Optional[int] = Field(None, alias="sortOrder")
    tenant_id: Optional[str] = Field(None, alias="tenantId")


class GuideTourResponse(BaseSchema):
    """管理端：指引详情响应"""
    id: str
    code: str
    title: Dict[str, str]
    description: Optional[Dict[str, str]] = None
    steps: List[TourStep]
    status: int
    sort_order: int = Field(alias="sortOrder")
    tenant_id: Optional[str] = Field(None, alias="tenantId")
    created_at: Optional[datetime] = Field(None, alias="createdAt")
    updated_at: Optional[datetime] = Field(None, alias="updatedAt")


class GuideTourListResponse(BaseSchema):
    """管理端：指引列表项"""
    id: str
    code: str
    title: Dict[str, str]
    status: int
    sort_order: int = Field(alias="sortOrder")
    step_count: int = Field(0, alias="stepCount")
    created_at: Optional[datetime] = Field(None, alias="createdAt")


class StatusUpdate(BaseSchema):
    """管理端：更新发布状态"""
    status: int = Field(..., description="0=下线, 1=发布")
