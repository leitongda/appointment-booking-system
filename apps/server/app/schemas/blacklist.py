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
    
    id: str
    user_id: Optional[str] = None
    user_name: Optional[str] = None
    user_phone: Optional[str] = None
    store_id: Optional[str] = None
    store_name: Optional[str] = None
    keyword: Optional[str] = None
    reason: Optional[str] = None
    no_show_count: int = 0
    source: int = 1  # 1手动 2自动
    expire_at: Optional[datetime] = None
    released_at: Optional[datetime] = None
    status: int = 1
    created_at: Optional[datetime] = None


class BlacklistListParams(BaseModel):
    """黑名单列表查询参数"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )
    
    keyword: Optional[str] = Field(None, description="搜索关键词（用户昵称/电话/身份证）")
    store_id: Optional[str] = Field(None, description="门店ID")
    status: Optional[int] = Field(None, description="状态: 1生效 0已解禁")
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=settings.MAX_PAGE_SIZE)


class BlacklistCheckResult(BaseModel):
    """黑名单检查结果"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        by_alias=True,
    )
    
    is_blacklisted: bool = False
    reason: Optional[str] = None
    expire_at: Optional[datetime] = None
