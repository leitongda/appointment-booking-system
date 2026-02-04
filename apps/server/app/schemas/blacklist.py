"""黑名单 Schema"""
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List
from datetime import datetime
from app.core.config import settings


def to_camel(string: str) -> str:
    """将 snake_case 转换为 camelCase"""
    components = string.split('_')
    return components[0] + ''.join(x.title() for x in components[1:])


class BlacklistCreate(BaseModel):
    """创建黑名单"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )
    
    user_id: Optional[str] = Field(None, description="用户ID，可选")
    store_id: Optional[str] = Field(None, description="门店ID，可选，不选则针对所有门店")
    keyword: Optional[str] = Field(None, max_length=50, description="手机号或身份证关键词")
    reason: Optional[str] = Field(None, max_length=500, description="黑名单原因/备注")
    expire_at: Optional[datetime] = Field(None, description="解禁时间")


class BlacklistResponse(BaseModel):
    """黑名单响应"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
        by_alias=True,
    )
    
    id: str = Field(..., description="黑名单ID")
    user_id: Optional[str] = Field(None, description="用户ID")
    user_name: Optional[str] = Field(None, description="用户名称")
    user_phone: Optional[str] = Field(None, description="用户手机号")
    store_id: Optional[str] = Field(None, description="门店ID")
    store_name: Optional[str] = Field(None, description="门店名称")
    keyword: Optional[str] = Field(None, description="手机号或身份证关键词")
    reason: Optional[str] = Field(None, description="黑名单原因")
    no_show_count: int = Field(0, description="爽约次数")
    source: int = Field(1, description="来源: 1手动添加 2自动添加")
    expire_at: Optional[datetime] = Field(None, description="解禁时间")
    released_at: Optional[datetime] = Field(None, description="实际解禁时间")
    status: int = Field(1, description="状态: 0已解禁 1生效中")
    created_at: Optional[datetime] = Field(None, description="创建时间")


class BlacklistListParams(BaseModel):
    """黑名单列表查询参数"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )
    
    keyword: Optional[str] = Field(None, description="搜索关键词（用户昵称/电话/身份证）")
    store_id: Optional[str] = Field(None, description="门店ID")
    status: Optional[int] = Field(None, description="状态: 1生效 0已解禁")
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
    reason: Optional[str] = Field(None, description="黑名单原因")
    expire_at: Optional[datetime] = Field(None, description="解禁时间")
