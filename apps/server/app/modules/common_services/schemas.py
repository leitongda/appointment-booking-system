"""常见服务模块 DTOs"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field


def to_camel(string: str) -> str:
    """将 snake_case 转换为 camelCase"""
    components = string.split('_')
    return components[0] + ''.join(x.title() for x in components[1:])


# ========== 常见服务 ==========

class CommonServiceResponse(BaseModel):
    """常见服务响应"""
    id: str
    name: str
    code: str
    icon: Optional[str] = None
    variant: Optional[str] = None
    link_type: int = 1
    link_url: Optional[str] = None
    department_id: Optional[str] = None
    department_name: Optional[str] = None
    description: Optional[str] = None
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
    items: List[CommonServiceResponse]


# ========== 健康提醒 ==========

class HealthReminderResponse(BaseModel):
    """健康提醒响应"""
    id: str
    reminder_type: str
    name: str
    title: Optional[str] = None
    content: Optional[str] = None
    tips: Optional[List[str]] = None
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
    next_check_date: Optional[str] = None
    last_check_date: Optional[str] = None
    check_type: Optional[str] = None
    tips: Optional[List[str]] = None
    reminder_content: Optional[str] = None
