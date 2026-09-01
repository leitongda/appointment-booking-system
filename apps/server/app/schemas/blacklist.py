"""黑名单 Schema"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.config import settings
from app.schemas.base import BaseRequestSchema, BaseSchema
from app.schemas.response import to_camel


class BlacklistCreate(BaseRequestSchema):
    """创建黑名单"""

    user_id: str | None = Field(None, description="用户ID，可选")
    store_id: str | None = Field(None, description="门店ID，可选，不选则针对所有门店")
    keyword: str | None = Field(None, max_length=50, description="手机号或身份证关键词")
    reason: str | None = Field(None, max_length=500, description="黑名单原因/备注")
    expire_at: datetime | None = Field(None, description="解禁时间")

class BlacklistResponse(BaseSchema):
    """黑名单响应"""

    id: str = Field(..., description="黑名单ID")
    user_id: str | None = Field(None, description="用户ID")
    user_name: str | None = Field(None, description="用户名称")
    user_phone: str | None = Field(None, description="用户手机号")
    store_id: str | None = Field(None, description="门店ID")
    store_name: str | None = Field(None, description="门店名称")
    keyword: str | None = Field(None, description="手机号或身份证关键词")
    reason: str | None = Field(None, description="黑名单原因")
    no_show_count: int = Field(0, description="爽约次数")
    source: int = Field(1, description="来源: 1手动添加 2自动添加")
    expire_at: datetime | None = Field(None, description="解禁时间")
    released_at: datetime | None = Field(None, description="实际解禁时间")
    status: int = Field(1, description="状态: 0已解禁 1生效中")
    created_at: datetime | None = Field(None, description="创建时间")

class BlacklistListParams(BaseRequestSchema):
    """黑名单列表查询参数"""

    keyword: str | None = Field(None, description="搜索关键词（用户昵称/电话/身份证）")
    store_id: str | None = Field(None, description="门店ID")
    status: int | None = Field(None, description="状态: 1生效 0已解禁")
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(20, ge=1, le=settings.MAX_PAGE_SIZE, description="每页数量")

class BlacklistCheckResult(BaseModel):
    """黑名单检查结果"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        by_alias=True,
    )
    
    is_blacklisted: bool = Field(False, description="是否在黑名单中")
    reason: str | None = Field(None, description="黑名单原因")
    expire_at: datetime | None = Field(None, description="解禁时间")
