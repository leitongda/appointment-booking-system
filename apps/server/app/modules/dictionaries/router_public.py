"""字典公开查询 API（三端共用）"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.modules.dictionaries.schemas import (
    BatchDictOptionsResponse,
    DictOptionItem,
    DictOptionsResponse,
)
from app.modules.dictionaries.service import DictService

router = APIRouter()


@router.get(
    "/{type_code}",
    response_model=DictOptionsResponse,
    summary="按类型编码获取字典选项",
)
async def get_dict_options(
    type_code: str,
    db: AsyncSession = Depends(get_db),
):
    """按类型编码获取已启用的字典项（三端共用）"""
    service = DictService(db)
    items = await service.get_items_by_type_code(type_code, enabled_only=True)
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
):
    """批量获取多个字典类型的选项（三端共用）"""
    service = DictService(db)
    code_list = [c.strip() for c in codes.split(",") if c.strip()]

    results = []
    for code in code_list:
        items = await service.get_items_by_type_code(code, enabled_only=True)
        results.append(
            DictOptionsResponse(
                code=code,
                items=[DictOptionItem.model_validate(item) for item in items],
            )
        )

    return BatchDictOptionsResponse(dicts=results)
