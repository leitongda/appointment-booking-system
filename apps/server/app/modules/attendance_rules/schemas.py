"""考勤规则管理 Schema 定义"""

from datetime import datetime

from pydantic import Field

from app.schemas.base import BaseSchema


class AttendanceRuleCreate(BaseSchema):
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = None
    late_policy: str = "flexible"  # flexible/strict/ignore
    early_policy: str = "flexible"
    absent_policy: str = "strict"
    overtime_enabled: bool = False
    overtime_min_minutes: int = 30
    enabled: bool = True


class AttendanceRuleUpdate(BaseSchema):
    name: str | None = None
    description: str | None = None
    late_policy: str | None = None
    early_policy: str | None = None
    absent_policy: str | None = None
    overtime_enabled: bool | None = None
    overtime_min_minutes: int | None = None
    enabled: bool | None = None


class AttendanceRuleResponse(BaseSchema):
    id: str
    name: str
    description: str | None = None
    late_policy: str
    early_policy: str
    absent_policy: str
    overtime_enabled: bool
    overtime_min_minutes: int
    enabled: bool
    created_at: datetime | None = None
