
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.response import to_camel


class ShiftTypeCreate(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    code: str = Field(..., max_length=50, description="类型代码")
    name: str = Field(..., max_length=100, description="类型名称")
    description: str | None = Field(None, description="描述")
    enabled: bool = True

class ShiftTypeUpdate(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    name: str | None = Field(None, max_length=100)
    description: str | None = None
    enabled: bool | None = None

class ShiftTypeResponse(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
        by_alias=True,
    )

    id: str
    code: str
    name: str
    description: str | None = None
    enabled: bool
