from app.schemas.response import to_camel
"""字典管理 Schema 定义"""
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List, Any
from datetime import datetime

# ==================== 字典类型 ====================

class DictTypeCreate(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    code: str = Field(..., max_length=50, description="字典类型编码")
    name: str = Field(..., max_length=100, description="字典类型名称")
    description: Optional[str] = Field(None, description="描述")

class DictTypeUpdate(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    status: Optional[int] = None

class DictTypeResponse(BaseModel):
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
    status: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

# ==================== 字典项 ====================

class DictItemCreate(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    label: str = Field(..., max_length=200, description="显示标签")
    value: str = Field(..., max_length=100, description="字典值")
    sort_order: int = Field(0, description="排序")
    extra: Optional[Any] = Field(None, description="扩展数据")

class DictItemUpdate(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    label: Optional[str] = Field(None, max_length=200)
    value: Optional[str] = Field(None, max_length=100)
    sort_order: Optional[int] = None
    status: Optional[int] = None
    extra: Optional[Any] = None

class DictItemResponse(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
        by_alias=True,
    )

    id: str
    dict_type_id: str
    label: str
    value: str
    sort_order: int
    status: int
    extra: Optional[Any] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class SortItem(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    id: str = Field(..., description="字典项ID")
    sort_order: int = Field(..., description="排序值")

class SortRequest(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    items: List[SortItem] = Field(..., description="排序列表")

# ==================== 公开查询 ====================

class DictOptionItem(BaseModel):
    """公开查询返回的字典项（不含内部字段）"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
        by_alias=True,
    )

    label: str
    value: str
    extra: Optional[Any] = None

class DictOptionsResponse(BaseModel):
    """单个字典类型的选项列表"""
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    code: str
    items: List[DictOptionItem] = Field(default_factory=list)

class BatchDictOptionsResponse(BaseModel):
    """批量字典选项查询结果"""
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    dicts: List[DictOptionsResponse] = Field(default_factory=list)
