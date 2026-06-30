from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.response import to_camel


# ========== 管理员列表响应 ==========

class AdminListResponse(BaseModel):
    """管理员列表响应（用于门店用户列表等场景）"""
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        alias_generator=to_camel,
    )
    
    id: str = Field(..., description="管理员ID")
    username: str = Field(..., description="用户名")
    name: str | None = Field(None, description="姓名")
    phone: str | None = Field(None, description="手机号")
    email: str | None = Field(None, description="邮箱")
    avatar: str | None = Field(None, description="头像URL")
    role_id: str | None = Field(None, description="角色ID")
    status: int = Field(1, description="状态: 0禁用 1正常")
    created_at: datetime | None = Field(None, description="创建时间")
