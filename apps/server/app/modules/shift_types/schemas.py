from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


def to_camel(string: str) -> str:
    components = string.split("_")
    return components[0] + "".join(x.title() for x in components[1:])


class ShiftTypeCreate(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    code: str = Field(..., max_length=50, description="类型代码")
    name: str = Field(..., max_length=100, description="类型名称")
    description: Optional[str] = Field(None, description="描述")
    enabled: bool = True


class ShiftTypeUpdate(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    enabled: Optional[bool] = None


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
    description: Optional[str] = None
    enabled: bool
