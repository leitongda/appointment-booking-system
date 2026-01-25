"""
班次类型管理 API

提供班次类型的 CRUD 接口
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict

from app.db.session import get_db
from app.api.deps import get_current_user, get_current_admin, get_current_super_admin
from app.services.shift_type_service import ShiftTypeService
from app.schemas.rule_set import PageResult
from app.core.config import settings


def to_camel(string: str) -> str:
    """将 snake_case 转换为 camelCase"""
    components = string.split('_')
    return components[0] + ''.join(x.title() for x in components[1:])


# ==================== Schema ====================

class ShiftTypeCreate(BaseModel):
    """创建班次类型"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    code: str = Field(..., max_length=50, description="类型代码")
    name: str = Field(..., max_length=100, description="类型名称")
    description: Optional[str] = Field(None, description="描述")
    enabled: bool = True


class ShiftTypeUpdate(BaseModel):
    """更新班次类型"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    enabled: Optional[bool] = None


class ShiftTypeResponse(BaseModel):
    """班次类型响应"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
        by_alias=True
    )

    id: str
    code: str
    name: str
    description: Optional[str] = None
    enabled: bool


router = APIRouter()


@router.get("", response_model=PageResult[ShiftTypeResponse])
async def get_shift_types(
    enabled: Optional[bool] = Query(None, description="是否启用"),
    keyword: Optional[str] = Query(None, description="搜索关键词"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=settings.MAX_PAGE_SIZE, description="每页数量"),
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin)
):
    """获取班次类型列表"""
    service = ShiftTypeService(db)
    shift_types, total = await service.get_list(
        enabled=enabled,
        keyword=keyword,
        page=page,
        page_size=page_size
    )
    return PageResult(data=shift_types, total=total)


@router.get("/all", response_model=list[ShiftTypeResponse])
async def get_all_shift_types(
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin)
):
    """获取所有启用的班次类型（用于下拉选择）"""
    service = ShiftTypeService(db)
    shift_types = await service.get_all_enabled()
    return shift_types


@router.get("/{shift_type_id}", response_model=ShiftTypeResponse)
async def get_shift_type(
    shift_type_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin)
):
    """获取班次类型详情"""
    service = ShiftTypeService(db)
    shift_type = await service.get_by_id(shift_type_id)
    if not shift_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="班次类型不存在"
        )
    return shift_type


@router.post("", response_model=ShiftTypeResponse, status_code=status.HTTP_201_CREATED)
async def create_shift_type(
    data: ShiftTypeCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_super_admin)
):
    """创建班次类型（仅超级管理员）"""
    service = ShiftTypeService(db)
    try:
        shift_type = await service.create(
            code=data.code,
            name=data.name,
            description=data.description,
            enabled=data.enabled,
            operator_id=current_user["id"]
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    return shift_type


@router.put("/{shift_type_id}", response_model=ShiftTypeResponse)
async def update_shift_type(
    shift_type_id: str,
    data: ShiftTypeUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_super_admin)
):
    """更新班次类型（仅超级管理员）"""
    service = ShiftTypeService(db)
    shift_type = await service.update(
        shift_type_id=shift_type_id,
        name=data.name,
        description=data.description,
        enabled=data.enabled,
        operator_id=current_user["id"]
    )
    if not shift_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="班次类型不存在"
        )
    return shift_type


@router.delete("/{shift_type_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_shift_type(
    shift_type_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_super_admin)
):
    """删除班次类型（仅超级管理员）"""
    service = ShiftTypeService(db)
    success = await service.delete(shift_type_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="班次类型不存在"
        )
    return None
