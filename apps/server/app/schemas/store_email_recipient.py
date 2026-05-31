"""门店邮件接收人 Schema"""
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List
from datetime import datetime
from app.core.config import settings
from app.schemas.response import to_camel

class StoreEmailRecipientCreate(BaseModel):
    """创建门店邮件接收人"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    store_id: str = Field(..., description="门店ID")
    name: str = Field(..., max_length=50, description="接收人姓名")
    email: str = Field(..., max_length=100, description="邮箱地址")
    event_types: List[str] = Field(default_factory=list, description="订阅事件类型列表")
    status: int = Field(1, ge=0, le=1, description="状态: 0-禁用 1-启用")

class StoreEmailRecipientUpdate(BaseModel):
    """更新门店邮件接收人"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    name: Optional[str] = Field(None, max_length=50, description="接收人姓名")
    email: Optional[str] = Field(None, max_length=100, description="邮箱地址")
    event_types: Optional[List[str]] = Field(None, description="订阅事件类型列表")
    status: Optional[int] = Field(None, ge=0, le=1, description="状态: 0-禁用 1-启用")

class StoreEmailRecipientResponse(BaseModel):
    """门店邮件接收人响应"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
        by_alias=True,
    )

    id: str
    store_id: str = Field(..., description="门店ID")
    store_name: Optional[str] = Field(None, description="门店名称")
    name: str = Field(..., description="接收人姓名")
    email: str = Field(..., description="邮箱地址")
    event_types: Optional[List[str]] = Field(None, description="订阅事件类型列表")
    status: int = Field(1, description="状态: 0-禁用 1-启用")
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class StoreEmailRecipientQuery(BaseModel):
    """门店邮件接收人查询参数"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    store_id: Optional[str] = Field(None, description="门店ID")
    keyword: Optional[str] = Field(None, description="关键词搜索（姓名/邮箱）")
    status: Optional[int] = Field(None, description="状态筛选")
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(10, ge=1, le=settings.MAX_PAGE_SIZE, description="每页数量")
