"""低代码页面 Pydantic schemas。"""

from datetime import datetime
from typing import Any, Optional

from pydantic import Field, field_validator

from app.schemas.base import BaseSchema

_MAX_SCHEMA_DEPTH = 10

_VALID_HTTP_METHODS = frozenset({"GET", "POST", "PUT", "DELETE"})


def _validate_data_sources(data_sources: Any, path: str) -> None:
    """校验 dataSources 数组结构。"""
    if not isinstance(data_sources, list):
        raise ValueError(f"{path} 必须是数组")
    for i, ds in enumerate(data_sources):
        prefix = f"{path}[{i}]"
        if not isinstance(ds, dict):
            raise ValueError(f"{prefix} 必须是一个对象")
        for key in ("id", "url", "method"):
            if key not in ds:
                raise ValueError(f"{prefix} 缺少 {key} 字段")
        if not isinstance(ds["id"], str):
            raise ValueError(f"{prefix}.id 必须是字符串")
        if not isinstance(ds["url"], str):
            raise ValueError(f"{prefix}.url 必须是字符串")
        if ds["method"] not in _VALID_HTTP_METHODS:
            raise ValueError(
                f"{prefix}.method 必须是以下之一: {', '.join(sorted(_VALID_HTTP_METHODS))}"
            )


def _validate_state(state: Any, path: str) -> None:
    """校验 state 对象结构。"""
    if not isinstance(state, dict):
        raise ValueError(f"{path} 必须是一个对象")
    for key, val in state.items():
        prefix = f"{path}.{key}"
        if not isinstance(val, dict):
            raise ValueError(f"{prefix} 必须是一个对象")
        if "type" not in val:
            raise ValueError(f"{prefix} 缺少 type 字段")
        if "defaultValue" not in val:
            raise ValueError(f"{prefix} 缺少 defaultValue 字段")


def _validate_data_binding(data_binding: Any, path: str) -> None:
    """校验 dataBinding 中的绑定表达式均为字符串。"""
    if not isinstance(data_binding, dict):
        raise ValueError(f"{path} 必须是一个对象")
    for key, val in data_binding.items():
        if not isinstance(val, str):
            raise ValueError(f"{path}.{key} 绑定表达式必须是字符串")


def _validate_events(events: Any, path: str) -> None:
    """校验 events 数组结构。"""
    if not isinstance(events, list):
        raise ValueError(f"{path} 必须是数组")
    for i, evt in enumerate(events):
        prefix = f"{path}[{i}]"
        if not isinstance(evt, dict):
            raise ValueError(f"{prefix} 必须是一个对象")
        if "event" not in evt:
            raise ValueError(f"{prefix} 缺少 event 字段")
        if not isinstance(evt["event"], str):
            raise ValueError(f"{prefix}.event 必须是字符串")
        if "actions" not in evt:
            raise ValueError(f"{prefix} 缺少 actions 字段")
        if not isinstance(evt["actions"], list):
            raise ValueError(f"{prefix}.actions 必须是数组")


def _validate_loop(loop: Any, path: str) -> None:
    """校验 loop 配置结构。"""
    if not isinstance(loop, dict):
        raise ValueError(f"{path} 必须是一个对象")
    if "dataSource" not in loop:
        raise ValueError(f"{path} 缺少 dataSource 字段")
    if not isinstance(loop["dataSource"], str):
        raise ValueError(f"{path}.dataSource 必须是字符串")


def _validate_data_binding_fields(schema: dict[str, Any]) -> None:
    """校验 schema_data 中的数据绑定相关字段。"""
    if "dataSources" in schema:
        _validate_data_sources(schema["dataSources"], "schema_data.dataSources")
    if "state" in schema:
        _validate_state(schema["state"], "schema_data.state")
    if "dataBinding" in schema:
        _validate_data_binding(schema["dataBinding"], "schema_data.dataBinding")
    if "events" in schema:
        _validate_events(schema["events"], "schema_data.events")
    if "loop" in schema:
        _validate_loop(schema["loop"], "schema_data.loop")


def _get_schema_depth(node: dict[str, Any], current: int = 0) -> int:
    """递归计算 schema 节点树的最大深度。"""
    if not isinstance(node, dict):
        return current
    children = node.get("children")
    if not isinstance(children, list) or not children:
        return current
    child_depths = [
        _get_schema_depth(child, current + 1)
        for child in children
        if isinstance(child, dict)
    ]
    return max(child_depths) if child_depths else current


def _validate_component_node(node: Any, path: str = "root") -> None:
    """递归校验每个组件节点的结构。"""
    if not isinstance(node, dict):
        raise ValueError(f"{path} 必须是一个对象")

    if "componentName" not in node:
        raise ValueError(f"{path} 缺少 componentName 字段")
    if not isinstance(node["componentName"], str):
        raise ValueError(f"{path}.componentName 必须是字符串")

    if "props" not in node:
        raise ValueError(f"{path} 缺少 props 字段")
    if not isinstance(node["props"], dict):
        raise ValueError(f"{path}.props 必须是一个对象")

    children = node.get("children")
    if children is not None and not isinstance(children, list):
        raise ValueError(f"{path}.children 必须是数组")

    if isinstance(children, list):
        for i, child in enumerate(children):
            _validate_component_node(child, f"{path}.children[{i}]")


class LowCodePageBase(BaseSchema):
    """低代码页面基础 schema。"""

    name: str = Field(..., min_length=1, max_length=100, description="页面名称")
    slug: str = Field(..., min_length=1, max_length=100, description="页面标识")
    description: Optional[str] = Field(None, max_length=500, description="页面描述")
    schema_data: dict[str, Any] = Field(default_factory=dict, description="页面Schema JSON")
    thumbnail_url: Optional[str] = Field(None, description="缩略图URL")
    miniapp_instance_id: Optional[str] = Field(None, description="关联小程序实例ID")

    @field_validator("schema_data")
    @classmethod
    def validate_schema_data(cls, v: dict[str, Any]) -> dict[str, Any]:
        if not v:
            return v
        depth = _get_schema_depth(v)
        if depth >= _MAX_SCHEMA_DEPTH:
            raise ValueError(
                f"schema_data 嵌套深度不能超过 {_MAX_SCHEMA_DEPTH} 层，当前深度: {depth}"
            )
        _validate_component_node(v)
        _validate_data_binding_fields(v)
        return v


class LowCodePageCreate(LowCodePageBase):
    """创建低代码页面请求。"""
    pass


class LowCodePageUpdate(BaseSchema):
    """更新低代码页面请求。"""

    name: Optional[str] = Field(None, min_length=1, max_length=100, description="页面名称")
    slug: Optional[str] = Field(None, min_length=1, max_length=100, description="页面标识")
    description: Optional[str] = Field(None, max_length=500, description="页面描述")
    schema_data: Optional[dict[str, Any]] = Field(None, description="页面Schema JSON")
    status: Optional[int] = Field(None, ge=0, le=2, description="状态: 0草稿 1已发布 2已归档")
    thumbnail_url: Optional[str] = Field(None, description="缩略图URL")
    miniapp_instance_id: Optional[str] = Field(None, description="关联小程序实例ID")

    @field_validator("schema_data")
    @classmethod
    def validate_schema_data(cls, v: Optional[dict[str, Any]]) -> Optional[dict[str, Any]]:
        if not v:
            return v
        depth = _get_schema_depth(v)
        if depth >= _MAX_SCHEMA_DEPTH:
            raise ValueError(
                f"schema_data 嵌套深度不能超过 {_MAX_SCHEMA_DEPTH} 层，当前深度: {depth}"
            )
        _validate_component_node(v)
        _validate_data_binding_fields(v)
        return v


class LowCodePageResponse(LowCodePageBase):
    """低代码页面响应。"""

    id: str = Field(..., description="页面ID")
    tenant_id: str = Field(..., description="租户ID")
    status: int = Field(0, description="状态: 0草稿 1已发布 2已归档")
    created_at: Optional[datetime] = Field(None, description="创建时间")
    updated_at: Optional[datetime] = Field(None, description="更新时间")
