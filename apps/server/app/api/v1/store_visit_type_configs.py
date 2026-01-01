from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.api.deps import get_current_admin, get_store_filter, check_store_access
from app.schemas.store_visit_type_config import (
    StoreVisitTypeConfigCreate,
    StoreVisitTypeConfigUpdate,
    StoreVisitTypeConfigResponse
)
from app.schemas.response import ResponseModel
from app.services.visit_type_service import VisitTypeService

router = APIRouter()


def config_to_response(config) -> StoreVisitTypeConfigResponse:
    """将配置模型转换为响应对象"""
    return StoreVisitTypeConfigResponse(
        id=config.id,
        store_id=config.store_id,
        store_name=config.store.name if config.store else None,
        time_limit=config.time_limit,
        time_unit=config.time_unit,
        scope=config.scope,
        status=config.status,
        created_at=config.created_at,
        updated_at=config.updated_at
    )


@router.get("/store/{store_id}", response_model=ResponseModel)
async def get_store_visit_type_config(
    store_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    """获取门店复诊规则配置"""
    # 检查门店访问权限
    if not check_store_access(current_admin, store_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="您无权访问此门店配置")
    
    service = VisitTypeService(db)
    config = await service.get_by_store_id(store_id)
    
    if config:
        return ResponseModel(data=config_to_response(config))
    
    # 返回默认配置
    return ResponseModel(data={
        "storeId": store_id,
        "timeLimit": 30,
        "timeUnit": "days",
        "scope": "same_doctor",
        "status": 1
    })


@router.put("/store/{store_id}", response_model=ResponseModel)
async def update_store_visit_type_config(
    store_id: str,
    data: StoreVisitTypeConfigUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    """更新门店复诊规则配置（不存在则创建）"""
    # 检查门店访问权限
    if not check_store_access(current_admin, store_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="您无权修改此门店配置")
    
    service = VisitTypeService(db)
    config = await service.create_or_update(store_id, data, current_admin.id)
    
    return ResponseModel(data=config_to_response(config), message="配置更新成功")


@router.delete("/store/{store_id}", response_model=ResponseModel)
async def delete_store_visit_type_config(
    store_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    """删除门店复诊规则配置（恢复默认）"""
    # 检查门店访问权限
    if not check_store_access(current_admin, store_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="您无权删除此门店配置")
    
    service = VisitTypeService(db)
    config = await service.get_by_store_id(store_id)
    
    if config:
        await service.delete(config.id)
    
    return ResponseModel(message="配置已恢复默认")

