"""Schema 基类 — 统一 Pydantic 配置"""
from pydantic import BaseModel, ConfigDict, model_validator

from app.schemas.media import normalize_media
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


class BaseRequestSchema(BaseModel):
    """请求型 Schema 基类（仅 camelCase 别名 + populate_by_name）。

    与 ``BaseSchema`` 的差异：**不**含 ``from_attributes`` 与 ``by_alias``。
    用于纯入参 schema（请求体解析），刻意避免：
        - ``from_attributes=True``：请求体不应从 ORM 对象构造
        - ``by_alias=True``：请求解析阶段不需要默认按 alias 序列化

    等价于：
        class MyReq(BaseModel):
            model_config = ConfigDict(
                alias_generator=to_camel,
                populate_by_name=True,
            )

    选择基类的规则（迁移时逐类精确匹配其原 ConfigDict）：
        - 原 ConfigDict 恰为上述 2 字段 → ``BaseRequestSchema``
        - 原 ConfigDict 恰为 4 字段（含 from_attributes + by_alias）→ ``BaseSchema``
        - 原配置有任何额外字段或不同 alias_generator → 保持手写，不迁移
    """
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    @model_validator(mode="before")
    @classmethod
    def _normalize_media_paths(cls, data):
        """请求入口：客户端回写的「基址 + /uploads/」还原为相对路径（见 app/schemas/media.py）。

        保证对称性：响应出口会拼前缀，客户端原样回写时若不去前缀，库里的相对路径
        会被绝对 URL 覆盖。基址未配置时为 no-op，请求解析行为零变化。
        """
        return normalize_media(data)

