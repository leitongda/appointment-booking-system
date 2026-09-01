"""门店邮件接收人 Schema"""
from datetime import datetime

from pydantic import Field

from app.core.config import settings
from app.schemas.base import BaseRequestSchema, BaseSchema


class StoreEmailRecipientCreate(BaseRequestSchema):
    """创建门店邮件接收人"""

    store_id: str = Field(..., description="门店ID")
    name: str = Field(..., max_length=50, description="接收人姓名")
    email: str = Field(..., max_length=100, description="邮箱地址")
    event_types: list[str] = Field(default_factory=list, description="订阅事件类型列表")
    status: int = Field(1, ge=0, le=1, description="状态: 0-禁用 1-启用")

class StoreEmailRecipientUpdate(BaseRequestSchema):
    """更新门店邮件接收人"""

    name: str | None = Field(None, max_length=50, description="接收人姓名")
    email: str | None = Field(None, max_length=100, description="邮箱地址")
    event_types: list[str] | None = Field(None, description="订阅事件类型列表")
    status: int | None = Field(None, ge=0, le=1, description="状态: 0-禁用 1-启用")

class StoreEmailRecipientResponse(BaseSchema):
    """门店邮件接收人响应"""

    id: str
    store_id: str = Field(..., description="门店ID")
    store_name: str | None = Field(None, description="门店名称")
    name: str = Field(..., description="接收人姓名")
    email: str = Field(..., description="邮箱地址")
    event_types: list[str] | None = Field(None, description="订阅事件类型列表")
    status: int = Field(1, description="状态: 0-禁用 1-启用")
    created_at: datetime | None = None
    updated_at: datetime | None = None

class StoreEmailRecipientQuery(BaseRequestSchema):
    """门店邮件接收人查询参数"""

    store_id: str | None = Field(None, description="门店ID")
    keyword: str | None = Field(None, description="关键词搜索（姓名/邮箱）")
    status: int | None = Field(None, description="状态筛选")
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(10, ge=1, le=settings.MAX_PAGE_SIZE, description="每页数量")
