"""兼职费用模块 Schema"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime
from decimal import Decimal

from app.schemas.base import BaseSchema


# ========== 兼职人员 ==========

class FreelancerBase(BaseSchema):
    name: str = Field(..., max_length=50, description="姓名")
    phone: Optional[str] = Field(None, max_length=20, description="手机号")
    store_id: Optional[str] = Field(None, description="绑定门店ID")
    account_name: Optional[str] = Field(None, max_length=100, description="社交媒体账号名")
    account_platform: str = Field("xiaohongshu", description="平台: xiaohongshu/douyin/weibo/wechat/other")
    account_type: str = Field("old", description="账号类型: old/new")
    status: int = Field(1, description="状态: 0禁用 1正常")
    remark: Optional[str] = Field(None, description="备注")


class FreelancerCreate(FreelancerBase):
    pass


class FreelancerUpdate(BaseModel):
    model_config = ConfigDict(
        alias_generator=lambda f: f,
        populate_by_name=True,
        from_attributes=True,
        by_alias=True,
    )
    name: Optional[str] = Field(None, max_length=50)
    phone: Optional[str] = Field(None, max_length=20)
    store_id: Optional[str] = None
    account_name: Optional[str] = Field(None, max_length=100)
    account_platform: Optional[str] = None
    account_type: Optional[str] = None
    status: Optional[int] = None
    remark: Optional[str] = None


class FreelancerResponse(BaseSchema):
    id: str
    tenant_id: Optional[str] = None
    store_id: Optional[str] = None
    name: str
    phone: Optional[str] = None
    account_name: Optional[str] = None
    account_platform: str = "xiaohongshu"
    account_type: str = "old"
    status: int = 1
    access_token: Optional[str] = None
    remark: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# ========== 发布任务 ==========

class FreelanceTaskBase(BaseSchema):
    freelancer_id: str = Field(..., description="兼职人员ID")
    store_id: Optional[str] = Field(None, description="门店ID")
    title: str = Field(..., max_length=200, description="笔记标题")
    content_url: Optional[str] = Field(None, max_length=500, description="笔记链接")
    published_at: Optional[datetime] = Field(None, description="发布时间")
    remark: Optional[str] = Field(None, description="备注")


class FreelanceTaskCreate(FreelanceTaskBase):
    pass


class FreelanceTaskUpdate(BaseModel):
    model_config = ConfigDict(
        alias_generator=lambda f: f,
        populate_by_name=True,
        from_attributes=True,
        by_alias=True,
    )
    title: Optional[str] = Field(None, max_length=200)
    content_url: Optional[str] = Field(None, max_length=500)
    published_at: Optional[datetime] = None
    status: Optional[str] = None
    is_indexed: Optional[bool] = None
    likes_count: Optional[int] = None
    comments_count: Optional[int] = None
    bonus_amount: Optional[Decimal] = Field(None, ge=0, le=30)
    remark: Optional[str] = None


class FreelanceTaskResponse(BaseSchema):
    id: str
    tenant_id: Optional[str] = None
    store_id: Optional[str] = None
    freelancer_id: str
    title: str
    content_url: Optional[str] = None
    published_at: Optional[datetime] = None
    status: str = "pending"
    is_indexed: bool = False
    likes_count: int = 0
    comments_count: int = 0
    base_amount: Decimal = Decimal("5")
    bonus_amount: Decimal = Decimal("0")
    likes_bonus_amount: Decimal = Decimal("0")
    planned_base_settle_at: Optional[datetime] = None
    planned_bonus_settle_at: Optional[datetime] = None
    planned_likes_settle_at: Optional[datetime] = None
    remark: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    # 关联字段
    freelancer_name: Optional[str] = None


# ========== 互动记录 ==========

class FreelanceInteractionCreate(BaseSchema):
    task_id: str = Field(..., description="关联任务ID")
    interaction_type: str = Field(..., comment="类型: comment/dm")
    content: Optional[str] = Field(None, description="互动内容")
    interacted_at: Optional[datetime] = Field(None, description="互动时间")


class FreelanceInteractionResponse(BaseSchema):
    id: str
    task_id: str
    interaction_type: str
    content: Optional[str] = None
    amount: Decimal = Decimal("0.5")
    interacted_at: Optional[datetime] = None
    created_at: Optional[datetime] = None


# ========== 结算单 ==========

class FreelanceSettlementResponse(BaseSchema):
    id: str
    tenant_id: Optional[str] = None
    store_id: Optional[str] = None
    freelancer_id: str
    settlement_no: str
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    base_total: Decimal = Decimal("0")
    bonus_total: Decimal = Decimal("0")
    likes_bonus_total: Decimal = Decimal("0")
    interaction_total: Decimal = Decimal("0")
    total_amount: Decimal = Decimal("0")
    tax_amount: Decimal = Decimal("0")
    actual_amount: Decimal = Decimal("0")
    status: str = "pending"
    confirmed_at: Optional[datetime] = None
    confirmed_by: Optional[str] = None
    paid_at: Optional[datetime] = None
    reject_reason: Optional[str] = None
    remark: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    # 关联字段
    freelancer_name: Optional[str] = None
    items: Optional[List["FreelanceSettlementItemResponse"]] = None


class FreelanceSettlementItemResponse(BaseSchema):
    id: str
    settlement_id: str
    item_type: str
    task_id: Optional[str] = None
    interaction_id: Optional[str] = None
    description: Optional[str] = None
    amount: Decimal = Decimal("0")
    created_at: Optional[datetime] = None


class SettlementConfirmRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    remark: Optional[str] = Field(None, description="备注")


class SettlementRejectRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    reject_reason: str = Field(..., max_length=500, description="驳回原因")


class EngagementDataUpdate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    task_id: str = Field(..., description="任务ID")
    likes_count: Optional[int] = Field(None, ge=0, description="点赞数")
    comments_count: Optional[int] = Field(None, ge=0, description="评论数")
    is_indexed: Optional[bool] = Field(None, description="是否收录")
    screenshot_url: Optional[str] = Field(None, max_length=500, description="截图URL")
    remark: Optional[str] = Field(None, description="备注")


class EngagementBatchUpdate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    updates: list[EngagementDataUpdate] = Field(..., description="批量更新数据")


# ========== 查询参数 ==========

class FreelancerQuery(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    name: Optional[str] = None
    store_id: Optional[str] = None
    status: Optional[int] = None
    page: int = Field(1, ge=1)
    page_size: int = Field(10, ge=1, le=100)


class FreelanceTaskQuery(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    freelancer_id: Optional[str] = None
    store_id: Optional[str] = None
    status: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    page: int = Field(1, ge=1)
    page_size: int = Field(10, ge=1, le=100)


class FreelanceSettlementQuery(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    freelancer_id: Optional[str] = None
    store_id: Optional[str] = None
    status: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    page: int = Field(1, ge=1)
    page_size: int = Field(10, ge=1, le=100)
