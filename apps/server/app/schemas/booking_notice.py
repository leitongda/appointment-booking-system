"""预约须知 Schema"""
from datetime import datetime

from pydantic import Field

from app.core.config import settings
from app.schemas.base import BaseRequestSchema, BaseSchema


class BookingNoticeCreate(BaseRequestSchema):
    """创建预约须知请求"""

    type: str = Field(..., max_length=50, description="类型: BOOKING/VISIT/REFUND")
    title: str | None = Field(None, max_length=100, description="标题")
    content: str | None = Field(None, description="内容")
    sort_order: int = Field(0, ge=0, description="排序")
    status: int = Field(1, ge=0, le=1, description="状态: 0禁用 1启用")

class BookingNoticeUpdate(BaseRequestSchema):
    """更新预约须知请求"""

    type: str | None = Field(None, max_length=50)
    title: str | None = Field(None, max_length=100)
    content: str | None = None
    sort_order: int | None = Field(None, ge=0)
    status: int | None = Field(None, ge=0, le=1)

class BookingNoticeResponse(BaseSchema):
    """预约须知响应"""

    id: str
    type: str
    title: str | None = None
    content: str | None = None
    sort_order: int = 0
    status: int = 1
    created_at: datetime | None = None
    updated_at: datetime | None = None

class BookingNoticeListQuery(BaseRequestSchema):
    """预约须知列表查询"""

    type: str | None = None
    status: int | None = None
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=settings.MAX_PAGE_SIZE)

