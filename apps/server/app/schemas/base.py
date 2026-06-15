"""Schema 基类 — 统一 Pydantic 配置"""
from pydantic import BaseModel, ConfigDict

from app.schemas.response import to_camel


class BaseSchema(BaseModel):
    """所有业务 Schema 的基类，统一 camelCase 序列化配置。

    使用方式：
        class MySchema(BaseSchema):
            my_field: str  # 自动转为 myField

    等价于：
        class MySchema(BaseModel):
            model_config = ConfigDict(
                alias_generator=to_camel,
                populate_by_name=True,
                from_attributes=True,
                by_alias=True,
            )
            my_field: str
    """
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
        by_alias=True,
    )
