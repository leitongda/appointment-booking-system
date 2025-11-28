from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List

from app.db.session import get_db
from app.schemas.store import (
    StoreCreate, StoreUpdate, StoreResponse, StoreListResponse, StoreQuery,
    StoreDepartmentCreate, StoreDepartmentUpdate, StoreDepartmentResponse
)
from app.schemas.response import PageResponse
from app.services.store_service import StoreService

router = APIRouter()


@router.get("", response_model=PageResponse[StoreListResponse])
async def get_stores(
    keyword: Optional[str] = None,
    status: Optional[int] = None,
    city: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """获取门店列表"""
    service = StoreService(db)
    query = StoreQuery(
        keyword=keyword,
        status=status,
        city=city,
        page=page,
        page_size=page_size
    )
    stores, total = await service.get_list(query)
    
    # 获取每个门店的科室数量
    result = []
    for store in stores:
        dept_count = await service.get_department_count(store.id)
        result.append(StoreListResponse(
            id=store.id,
            name=store.name,
            code=store.code,
            address=store.address,
            phone=store.phone,
            status=store.status,
            department_count=dept_count,
            created_at=store.created_at
        ))
    
    return PageResponse(
        data=result,
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/all", response_model=List[StoreResponse])
async def get_all_stores(db: AsyncSession = Depends(get_db)):
    """获取所有营业中的门店（下拉选择用）"""
    service = StoreService(db)
    stores = await service.get_all_active()
    return [StoreResponse.model_validate(s) for s in stores]


@router.get("/{store_id}", response_model=StoreResponse)
async def get_store(store_id: str, db: AsyncSession = Depends(get_db)):
    """获取门店详情"""
    service = StoreService(db)
    store = await service.get_by_id(store_id)
    
    if not store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="门店不存在"
        )
    
    return StoreResponse.model_validate(store)


@router.post("", response_model=StoreResponse)
async def create_store(
    data: StoreCreate,
    db: AsyncSession = Depends(get_db)
):
    """创建门店"""
    service = StoreService(db)
    
    try:
        store = await service.create(data)
        return StoreResponse.model_validate(store)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=str(e)
        )


@router.put("/{store_id}", response_model=StoreResponse)
async def update_store(
    store_id: str,
    data: StoreUpdate,
    db: AsyncSession = Depends(get_db)
):
    """更新门店"""
    service = StoreService(db)
    
    try:
        store = await service.update(store_id, data)
        if not store:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="门店不存在"
            )
        return StoreResponse.model_validate(store)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=str(e)
        )


@router.delete("/{store_id}")
async def delete_store(store_id: str, db: AsyncSession = Depends(get_db)):
    """删除门店"""
    service = StoreService(db)
    
    try:
        success = await service.delete(store_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="门店不存在"
            )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=str(e)
        )
    
    return {"message": "删除成功"}


@router.patch("/{store_id}/status")
async def update_store_status(
    store_id: str,
    status: int = Query(..., ge=0, le=1, description="状态: 0-停业 1-营业"),
    db: AsyncSession = Depends(get_db)
):
    """更新门店状态"""
    service = StoreService(db)
    store = await service.update_status(store_id, status)
    
    if not store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="门店不存在"
        )
    
    return {"message": "状态更新成功"}


# ========== 门店科室关联 ==========

@router.get("/{store_id}/departments", response_model=List[StoreDepartmentResponse])
async def get_store_departments(
    store_id: str,
    db: AsyncSession = Depends(get_db)
):
    """获取门店的科室列表"""
    service = StoreService(db)
    
    # 检查门店是否存在
    store = await service.get_by_id(store_id)
    if not store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="门店不存在"
        )
    
    departments = await service.get_store_departments(store_id)
    return [StoreDepartmentResponse(**d) for d in departments]


@router.post("/{store_id}/departments", response_model=StoreDepartmentResponse)
async def add_store_department(
    store_id: str,
    department_id: str,
    floor: Optional[str] = None,
    room: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """添加门店科室关联"""
    service = StoreService(db)
    
    # 检查门店是否存在
    store = await service.get_by_id(store_id)
    if not store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="门店不存在"
        )
    
    try:
        data = StoreDepartmentCreate(
            store_id=store_id,
            department_id=department_id,
            floor=floor,
            room=room
        )
        store_dept = await service.add_department(data)
        return StoreDepartmentResponse(
            id=store_dept.id,
            store_id=store_dept.store_id,
            department_id=store_dept.department_id,
            floor=store_dept.floor,
            room=store_dept.room,
            status=store_dept.status,
            created_at=store_dept.created_at
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=str(e)
        )


@router.put("/departments/{relation_id}", response_model=StoreDepartmentResponse)
async def update_store_department(
    relation_id: str,
    data: StoreDepartmentUpdate,
    db: AsyncSession = Depends(get_db)
):
    """更新门店科室关联"""
    service = StoreService(db)
    store_dept = await service.update_department(relation_id, data)
    
    if not store_dept:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="关联记录不存在"
        )
    
    return StoreDepartmentResponse(
        id=store_dept.id,
        store_id=store_dept.store_id,
        department_id=store_dept.department_id,
        floor=store_dept.floor,
        room=store_dept.room,
        status=store_dept.status,
        created_at=store_dept.created_at
    )


@router.delete("/departments/{relation_id}")
async def remove_store_department(
    relation_id: str,
    db: AsyncSession = Depends(get_db)
):
    """移除门店科室关联"""
    service = StoreService(db)
    success = await service.remove_department(relation_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="关联记录不存在"
        )
    
    return {"message": "移除成功"}
