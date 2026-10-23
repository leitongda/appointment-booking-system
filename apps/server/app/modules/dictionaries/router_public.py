"""字典公开查询 API（三端共用）

R1-15：公开端同样必须识别租户，避免跨租户读取他租户私有字典。
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_tenant
from app.db.session import get_db
from app.modules.dictionaries.schemas import (
    BatchDictOptionsResponse,
    DictOptionItem,
    DictOptionsResponse,
)
from app.modules.dictionaries.service import DictService

router = APIRouter()


async def _require_public_tenant(
    tenant: dict | None = Depends(get_current_tenant),
) -> dict:
    """R1-15：公开端必须识别租户，缺失时 400。

    说明：D4 对公开读接口给出的备选口径是「空集 + 告警」，但 B8 验收门明确要求
    `/dict-options/{code}` 无租户头返回 400，此处按更具体的验收门执行。
    """
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="缺少租户上下文，请通过 X-Tenant-ID 或 X-Tenant-Code 指定租户",
        )
    return tenant


@router.get(
    "/{type_code}",
    response_model=DictOptionsResponse,
    summary="按类型编码获取字典选项",
)
async def get_dict_options(
    type_code: str,
    db: AsyncSession = Depends(get_db),
    tenant: dict = Depends(_require_public_tenant),
):
    """按类型编码获取已启用的字典项（三端共用，必须先识别租户）"""
    service = DictService(db)
    items = await service.get_items_by_type_code(
        type_code, enabled_only=True, tenant_id=tenant["id"]
    )
    return DictOptionsResponse(
        code=type_code,
        items=[DictOptionItem.model_validate(item) for item in items],
    )


@router.get(
    "",
    response_model=BatchDictOptionsResponse,
    summary="批量获取字典选项",
)
async def batch_get_dict_options(
    codes: str = Query(..., description="字典类型编码，逗号分隔"),
    db: AsyncSession = Depends(get_db),
    tenant: dict = Depends(_require_public_tenant),
):
    """批量获取多个字典类型的选项（三端共用，必须先识别租户）"""
    service = DictService(db)
    code_list = [c.strip() for c in codes.split(",") if c.strip()]

    results = []
    for code in code_list:
        items = await service.get_items_by_type_code(
            code, enabled_only=True, tenant_id=tenant["id"]
        )
        results.append(
            DictOptionsResponse(
                code=code,
                items=[DictOptionItem.model_validate(item) for item in items],
            )
        )

    return BatchDictOptionsResponse(dicts=results)
