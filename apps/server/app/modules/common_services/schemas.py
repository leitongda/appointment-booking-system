from app.schemas.response import to_camel

"""常见服务模块 DTOs"""
from pydantic import BaseModel, ConfigDict

# ========== 常见服务 ==========

class CommonServiceResponse(BaseModel):
    """常见服务响应"""
    id: str
    name: str
    code: str
    icon: str | None = None
    variant: str | None = None
    link_type: int = 1
    link_url: str | None = None
    department_id: str | None = None
    department_name: str | None = None
    description: str | None = None
    sort_order: int = 0
    status: int = 1

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        alias_generator=to_camel,
        by_alias=True,
    )

class CommonServiceListResponse(BaseModel):
    """常见服务列表响应"""
    items: list[CommonServiceResponse]

# ========== 健康提醒 ==========

class HealthReminderResponse(BaseModel):
    """健康提醒响应"""
    id: str
    reminder_type: str
    name: str
    title: str | None = None
    content: str | None = None
    tips: list[str] | None = None
    recommended_interval: int = 365
    sort_order: int = 0
    status: int = 1

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        alias_generator=to_camel,
        by_alias=True,
    )

class UserHealthReminderResponse(BaseModel):
    """用户健康提醒响应（包含用户的检查历史）"""
    next_check_date: str | None = None
    last_check_date: str | None = None
    check_type: str | None = None
    tips: list[str] | None = None
    reminder_content: str | None = None
