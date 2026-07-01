"""跨模块复用的通用请求 Schema。

本文件集中定义在多个业务模块中**语义完全等价**的请求体模型，
消除复制粘贴式的内联定义。每个被收敛到这里来的 schema 都经过逐处
字段/校验比对，确保与各原始定义**行为等价**（字段、类型、校验规则、
错误信息不变）。

注意：
    - 基类一律使用 ``BaseModel``（而非 ``BaseSchema``），以保持与原始
      定义一致的请求解析语义（不额外引入 camelCase 别名）。某些原始
      定义（如 contacts 模块）使用 ``BaseSchema``，因其序列化语义不同，
      未纳入本文件，保留原处。
    - 出现字段集或校验规则存在实质差异的同名 schema 时，不要强行合并，
      保留各自定义并在本文件 docstring 中记录差异原因。
"""

from pydantic import BaseModel, Field


class BatchDeleteRequest(BaseModel):
    """通用批量删除请求体。

    收敛自 ``app/modules/content/schemas.py`` 与 ``app/modules/cms/schemas.py``
    —— 两处定义完全一致（``ids: list[str]``，``min_length=1``）。

    未纳入的相似定义（保留原处，存在行为差异）：
        - ``app/modules/contacts/schemas.py``: 基于 ``BaseSchema``，字段
          description 不同（"联系人ID列表"），切换基类会改变请求解析。
        - ``app/modules/approval_flows/router.py``: 使用自定义
          ``field_validator`` 校验非空，错误信息为 "ids 不能为空"，
          与 Pydantic ``min_length=1`` 的默认信息不同。
    """

    ids: list[str] = Field(..., min_length=1, description="要删除的ID列表")


class SortOrderItem(BaseModel):
    """通用排序项。

    收敛自 ``app/modules/content/schemas.py`` 与 ``app/modules/cms/schemas.py``
    —— 两处定义完全一致（``id: str``，``sort_order: int`` 带 ``ge=0``）。

    未纳入的相似定义（保留原处，存在校验差异）：
        - ``app/modules/departments/router.py`` / ``app/modules/doctors/schemas.py``:
          ``sort_order`` **不带** ``ge=0`` 校验，且容器无 ``min_length=1``，
          合并将收紧校验、改变行为。
    """

    id: str
    sort_order: int = Field(..., ge=0)


class SortOrderRequest(BaseModel):
    """通用批量排序请求体（容器）。

    收敛自 ``app/modules/cms/schemas.py`` —— ``SortOrderRequest``。

    注意：``app/modules/content/schemas.py`` 中同名语义的容器命名为
    ``BannerSortRequest``（字段与校验完全一致），保留其原名称不变，
    仅复用统一的 ``SortOrderItem``。
    """

    items: list[SortOrderItem] = Field(..., min_length=1, description="排序项列表")
