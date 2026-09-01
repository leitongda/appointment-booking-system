from app.schemas.base import BaseRequestSchema, BaseSchema

"""字典管理 Schema 定义"""
from datetime import datetime
from typing import Any

from pydantic import Field

# ==================== 字典类型 ====================

class DictTypeCreate(BaseRequestSchema):
    code: str = Field(..., max_length=50, description="字典类型编码")
    name: str = Field(..., max_length=100, description="字典类型名称")
    description: str | None = Field(None, description="描述")

class DictTypeUpdate(BaseRequestSchema):
    name: str | None = Field(None, max_length=100)
    description: str | None = None
    status: int | None = None

class DictTypeResponse(BaseSchema):
    id: str
    code: str
    name: str
    description: str | None = None
    status: int
    created_at: datetime | None = None
    updated_at: datetime | None = None

# ==================== 字典项 ====================

class DictItemCreate(BaseRequestSchema):
    label: str = Field(..., max_length=200, description="显示标签")
    value: str = Field(..., max_length=100, description="字典值")
    sort_order: int = Field(0, description="排序")
    extra: Any | None = Field(None, description="扩展数据")

class DictItemUpdate(BaseRequestSchema):
    label: str | None = Field(None, max_length=200)
    value: str | None = Field(None, max_length=100)
    sort_order: int | None = None
    status: int | None = None
    extra: Any | None = None

class DictItemResponse(BaseSchema):
    id: str
    dict_type_id: str
    label: str
    value: str
    sort_order: int
    status: int
    extra: Any | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

class SortItem(BaseRequestSchema):
    id: str = Field(..., description="字典项ID")
    sort_order: int = Field(..., description="排序值")

class SortRequest(BaseRequestSchema):
    items: list[SortItem] = Field(..., description="排序列表")

# ==================== 公开查询 ====================

class DictOptionItem(BaseSchema):
    """公开查询返回的字典项（不含内部字段）"""
    label: str
    value: str
    extra: Any | None = None

class DictOptionsResponse(BaseRequestSchema):
    """单个字典类型的选项列表"""
    code: str
    items: list[DictOptionItem] = Field(default_factory=list)

class BatchDictOptionsResponse(BaseRequestSchema):
    """批量字典选项查询结果"""
    dicts: list[DictOptionsResponse] = Field(default_factory=list)
