from app.schemas.base import BaseSchema

"""常见服务模块 DTOs"""
from pydantic import BaseModel

# ========== 常见服务 ==========

class CommonServiceResponse(BaseSchema):
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

class CommonServiceListResponse(BaseModel):
    """常见服务列表响应"""
    items: list[CommonServiceResponse]

# ========== 健康提醒 ==========

class HealthReminderResponse(BaseSchema):
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

class UserHealthReminderResponse(BaseModel):
    """用户健康提醒响应（包含用户的检查历史）"""
    next_check_date: str | None = None
    last_check_date: str | None = None
    check_type: str | None = None
    tips: list[str] | None = None
    reminder_content: str | None = None
