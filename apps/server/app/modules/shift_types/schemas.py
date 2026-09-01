
from pydantic import Field

from app.schemas.base import BaseRequestSchema, BaseSchema


class ShiftTypeCreate(BaseRequestSchema):
    code: str = Field(..., max_length=50, description="类型代码")
    name: str = Field(..., max_length=100, description="类型名称")
    description: str | None = Field(None, description="描述")
    enabled: bool = True

class ShiftTypeUpdate(BaseRequestSchema):
    name: str | None = Field(None, max_length=100)
    description: str | None = None
    enabled: bool | None = None

class ShiftTypeResponse(BaseSchema):
    id: str
    code: str
    name: str
    description: str | None = None
    enabled: bool
