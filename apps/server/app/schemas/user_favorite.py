"""用户收藏 Schema"""
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.base import BaseRequestSchema, BaseSchema
from app.schemas.response import to_camel


class UserFavoriteCreate(BaseRequestSchema):
    """创建收藏请求"""

    target_type: str = Field(..., pattern="^(doctor|department)$", description="收藏类型: doctor/department")
    target_id: str = Field(..., description="收藏目标ID")

class UserFavoriteResponse(BaseSchema):
    """收藏响应"""

    id: str
    user_id: str
    target_type: str
    target_id: str
    created_at: datetime | None = None

class UserFavoriteWithTarget(BaseModel):
    """收藏响应（包含目标详情）
    NOTE: 原 ConfigDict 为 {alias_generator, populate_by_name, by_alias=True}（3 字段，无 from_attributes），
    与 BaseSchema（4 字段）不一致，保留手写配置避免行为变化。
    """
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

class FavoriteCheckRequest(BaseRequestSchema):
    """检查收藏状态请求"""

    target_type: str = Field(..., pattern="^(doctor|department)$")
    target_id: str

class FavoriteCheckResponse(BaseModel):
    """检查收藏状态响应
    NOTE: 原 ConfigDict 为 {alias_generator, populate_by_name, by_alias=True}（3 字段，无 from_attributes），
    与 BaseSchema（4 字段）不一致，保留手写配置避免行为变化。
    """
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        by_alias=True,
    )

    is_favorited: bool
    favorite_id: str | None = None
