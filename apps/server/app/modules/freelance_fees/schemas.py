"""兼职费用模块 Schema"""
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.base import BaseSchema

# ========== 兼职人员 ==========

class FreelancerBase(BaseSchema):
    name: str = Field(..., max_length=50, description="姓名")
    phone: str | None = Field(None, max_length=20, description="手机号")
    store_id: str | None = Field(None, description="绑定门店ID")
    account_name: str | None = Field(None, max_length=100, description="社交媒体账号名")
    account_platform: str = Field("xiaohongshu", description="平台: xiaohongshu/douyin/weibo/wechat/other")
    account_type: str = Field("old", description="账号类型: old/new")
    status: int = Field(1, description="状态: 0禁用 1正常")
    remark: str | None = Field(None, description="备注")


class FreelancerCreate(FreelancerBase):
    pass


class FreelancerUpdate(BaseModel):
    model_config = ConfigDict(
        alias_generator=lambda f: f,
        populate_by_name=True,
        from_attributes=True,
        by_alias=True,
    )
    name: str | None = Field(None, max_length=50)
    phone: str | None = Field(None, max_length=20)
    store_id: str | None = None
    account_name: str | None = Field(None, max_length=100)
    account_platform: str | None = None
    account_type: str | None = None
    status: int | None = None
    remark: str | None = None


class FreelancerResponse(BaseSchema):
    id: str
    tenant_id: str | None = None
    store_id: str | None = None
    name: str
    phone: str | None = None
    account_name: str | None = None
    account_platform: str = "xiaohongshu"
    account_type: str = "old"
    status: int = 1
    access_token: str | None = None
    remark: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


# ========== 发布任务 ==========

class FreelanceTaskBase(BaseSchema):
    freelancer_id: str = Field(..., description="兼职人员ID")
    store_id: str | None = Field(None, description="门店ID")
    title: str = Field(..., max_length=200, description="笔记标题")
    content_url: str | None = Field(None, max_length=500, description="笔记链接")
    published_at: datetime | None = Field(None, description="发布时间")
    remark: str | None = Field(None, description="备注")


class FreelanceTaskCreate(FreelanceTaskBase):
    pass


class FreelanceTaskUpdate(BaseModel):
    model_config = ConfigDict(
        alias_generator=lambda f: f,
        populate_by_name=True,
        from_attributes=True,
        by_alias=True,
    )
    title: str | None = Field(None, max_length=200)
    content_url: str | None = Field(None, max_length=500)
    published_at: datetime | None = None
    status: str | None = None
    is_indexed: bool | None = None
    likes_count: int | None = None
    comments_count: int | None = None
    bonus_amount: Decimal | None = Field(None, ge=0, le=30)
    remark: str | None = None


class FreelanceTaskResponse(BaseSchema):
    id: str
    tenant_id: str | None = None
    store_id: str | None = None
    freelancer_id: str
    title: str
    content_url: str | None = None
    published_at: datetime | None = None
    status: str = "pending"
    is_indexed: bool = False
    likes_count: int = 0
    comments_count: int = 0
    base_amount: Decimal = Decimal("5")
    bonus_amount: Decimal = Decimal("0")
    likes_bonus_amount: Decimal = Decimal("0")
    planned_base_settle_at: datetime | None = None
    planned_bonus_settle_at: datetime | None = None
    planned_likes_settle_at: datetime | None = None
    remark: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    # 关联字段
    freelancer_name: str | None = None


# ========== 互动记录 ==========

class FreelanceInteractionCreate(BaseSchema):
    task_id: str = Field(..., description="关联任务ID")
    interaction_type: str = Field(..., comment="类型: comment/dm")
    content: str | None = Field(None, description="互动内容")
    interacted_at: datetime | None = Field(None, description="互动时间")


class FreelanceInteractionResponse(BaseSchema):
    id: str
    task_id: str
    interaction_type: str
    content: str | None = None
    amount: Decimal = Decimal("0.5")
    interacted_at: datetime | None = None
    created_at: datetime | None = None


# ========== 结算单 ==========

class FreelanceSettlementResponse(BaseSchema):
    id: str
    tenant_id: str | None = None
    store_id: str | None = None
    freelancer_id: str
    settlement_no: str
    period_start: datetime | None = None
    period_end: datetime | None = None
    base_total: Decimal = Decimal("0")
    bonus_total: Decimal = Decimal("0")
    likes_bonus_total: Decimal = Decimal("0")
    interaction_total: Decimal = Decimal("0")
    total_amount: Decimal = Decimal("0")
    tax_amount: Decimal = Decimal("0")
    actual_amount: Decimal = Decimal("0")
    status: str = "pending"
    confirmed_at: datetime | None = None
    confirmed_by: str | None = None
    paid_at: datetime | None = None
    reject_reason: str | None = None
    remark: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    # 关联字段
    freelancer_name: str | None = None
    items: list["FreelanceSettlementItemResponse"] | None = None


class FreelanceSettlementItemResponse(BaseSchema):
    id: str
    settlement_id: str
    item_type: str
    task_id: str | None = None
    interaction_id: str | None = None
    description: str | None = None
    amount: Decimal = Decimal("0")
    created_at: datetime | None = None


class SettlementConfirmRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    remark: str | None = Field(None, description="备注")


class SettlementRejectRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    reject_reason: str = Field(..., max_length=500, description="驳回原因")


class EngagementDataUpdate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    task_id: str = Field(..., description="任务ID")
    likes_count: int | None = Field(None, ge=0, description="点赞数")
    comments_count: int | None = Field(None, ge=0, description="评论数")
    is_indexed: bool | None = Field(None, description="是否收录")
    screenshot_url: str | None = Field(None, max_length=500, description="截图URL")
    remark: str | None = Field(None, description="备注")


class EngagementBatchUpdate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    updates: list[EngagementDataUpdate] = Field(..., description="批量更新数据")


# ========== 查询参数 ==========

class FreelancerQuery(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    name: str | None = None
    store_id: str | None = None
    status: int | None = None
    page: int = Field(1, ge=1)
    page_size: int = Field(10, ge=1, le=100)


class FreelanceTaskQuery(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    freelancer_id: str | None = None
    store_id: str | None = None
    status: str | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    page: int = Field(1, ge=1)
    page_size: int = Field(10, ge=1, le=100)


class FreelanceSettlementQuery(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    freelancer_id: str | None = None
    store_id: str | None = None
    status: str | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    page: int = Field(1, ge=1)
    page_size: int = Field(10, ge=1, le=100)
