"""跨模块复用的通用请求 Schema。

本文件集中定义在多个业务模块中**语义完全等价**的请求体模型，
消除复制粘贴式的内联定义。每个被收敛到这里来的 schema 都经过逐处
字段/校验比对，确保与各原始定义**行为等价**（字段、类型、校验规则、
错误信息不变）。

注意：
    - 基类统一使用 ``BaseSchema``（继承自 BaseModel，含 ``alias_generator=to_camel``
      + ``populate_by_name=True``）。这样既接受 snake_case 也接受 camelCase
      输入，兼容前端 camelCase 契约（如 ChangePasswordRequest 的
      oldPassword/newPassword）与既有 snake_case 调用方。符合 CLAUDE.md
      的 Schema 基类规则。
    - 出现字段集或校验规则存在实质差异的同名 schema 时，不要强行合并，
      保留各自定义并在本文件 docstring 中记录差异原因。
"""

from pydantic import Field

from app.schemas.base import BaseSchema


class BatchDeleteRequest(BaseSchema):
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


class SortOrderItem(BaseSchema):
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


class SortOrderRequest(BaseSchema):
    """通用批量排序请求体（容器）。

    收敛自 ``app/modules/cms/schemas.py`` —— ``SortOrderRequest``。

    注意：``app/modules/content/schemas.py`` 中同名语义的容器命名为
    ``BannerSortRequest``（字段与校验完全一致），保留其原名称不变，
    仅复用统一的 ``SortOrderItem``。
    """

    items: list[SortOrderItem] = Field(..., min_length=1, description="排序项列表")


class ChangePasswordRequest(BaseSchema):
    """通用修改密码请求体。

    统一收敛四处历史定义，字段集完全一致（``old_password`` /
    ``new_password``，无 confirm/captcha/token 等附加字段），校验取**最严格**
    版本：两字段均 ``min_length=6, max_length=20``。

    原始各处校验强度（合并前）：
        - ``app/schemas/user.py``: old/new 均 ``min_length=6, max_length=20``
          （已是目标强度，本次直接采用）。
        - ``app/schemas/auth.py``: old 仅 ``min_length=6``（无 max），
          new ``min_length=6, max_length=20`` —— 本次为 old 补齐 ``max_length=20``。
        - ``app/modules/admin/schemas.py``: 同 auth.py（old 无 max）—— 补齐。
        - ``app/modules/doctors/schemas.py``: old/new 均为裸 ``str``（无 schema
          校验），长度靠 ``doctors/router.py`` 手动 ``HTTPException(400,
          '密码长度必须为6-20位')``。本次迁移到 Pydantic schema 层，由
          ``min_length/max_length`` 在 422 拦截（见行为变更说明）。

    **行为变更**：
        - doctors 改密端点（``POST /doctors/change-password``）长度校验从
          service 层 ``HTTPException(400, '密码长度必须为6-20位')`` 迁移到
          Pydantic schema 层 422（Pydantic 默认英文消息）。前端若依赖
          HTTP 400 状态码或该中文消息需适配。
        - auth/admin 改密端点：old_password 超长（>20）原本 200 通过（无
          max 校验）现在会被 422 拦截——属于收紧，符合"只紧不松"红线。
    """

    old_password: str = Field(..., min_length=6, max_length=20, description="旧密码")
    new_password: str = Field(..., min_length=6, max_length=20, description="新密码")
