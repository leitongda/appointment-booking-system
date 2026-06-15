from app.schemas.response import to_camel

"""用户收藏 Schema"""
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class UserFavoriteCreate(BaseModel):
    """创建收藏请求"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )
    
    target_type: str = Field(..., pattern="^(doctor|department)$", description="收藏类型: doctor/department")
    target_id: str = Field(..., description="收藏目标ID")

class UserFavoriteResponse(BaseModel):
    """收藏响应"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
        by_alias=True,
    )
    
    id: str
    user_id: str
    target_type: str
    target_id: str
    created_at: datetime | None = None

class UserFavoriteWithTarget(BaseModel):
    """收藏响应（包含目标详情）"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        by_alias=True,
    )
    
    id: str
    user_id: str
    target_type: str
    target_id: str
    created_at: datetime | None = None
    # 目标详情（医生或科室信息）
    target: Any | None = None

class FavoriteCheckRequest(BaseModel):
    """检查收藏状态请求"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )
    
    target_type: str = Field(..., pattern="^(doctor|department)$")
    target_id: str

class FavoriteCheckResponse(BaseModel):
    """检查收藏状态响应"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        by_alias=True,
    )
    
    is_favorited: bool
    favorite_id: str | None = None

