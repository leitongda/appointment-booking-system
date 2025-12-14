"""黑名单 Schema"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class BlacklistCreate(BaseModel):
    """创建黑名单"""
    user_id: Optional[str] = Field(None, description="用户ID，可选")
    store_id: Optional[str] = Field(None, description="门店ID，可选，不选则针对所有门店")
    keyword: Optional[str] = Field(None, max_length=50, description="手机号或身份证关键词")
    reason: Optional[str] = Field(None, max_length=500, description="黑名单原因/备注")
    expire_at: Optional[datetime] = Field(None, description="解禁时间")


class BlacklistResponse(BaseModel):
    """黑名单响应"""
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
    created_at: datetime
    
    class Config:
        from_attributes = True


class BlacklistListParams(BaseModel):
    """黑名单列表查询参数"""
    keyword: Optional[str] = Field(None, description="搜索关键词（用户昵称/电话/身份证）")
    store_id: Optional[str] = Field(None, description="门店ID")
    status: Optional[int] = Field(None, description="状态: 1生效 0已解禁")
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)


class BlacklistCheckResult(BaseModel):
    """黑名单检查结果"""
    is_blacklisted: bool = False
    reason: Optional[str] = None
    expire_at: Optional[datetime] = None
