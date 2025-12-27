from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List

from app.db.session import get_db
from app.api.deps import get_current_admin
from app.schemas.store import (
    StoreCreate, StoreUpdate, StoreResponse, StoreListResponse, StoreQuery
)
from app.schemas.department import DepartmentResponse
from app.schemas.admin import AdminListResponse
from app.schemas.response import PageResponse
from app.services.store_service import StoreService

router = APIRouter()


# ==================== 公开接口（无需登录） ====================

@router.get("/by-code/{code}", response_model=StoreResponse)
async def get_store_by_code(
    code: str,
    db: AsyncSession = Depends(get_db)
):
    """通过编码获取门店（公开接口，无需登录）
    
    用于患者端H5/小程序初始化时验证门店
    """
    service = StoreService(db)
    store = await service.get_by_code(code)
    
    if not store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="门店不存在，请检查后重试"
        )
    
    if store.status != 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="门店已停业，暂不可用"
        )
    
    return StoreResponse.model_validate(store)


# ==================== 需要登录的接口 ====================

@router.get("", response_model=PageResponse[StoreListResponse])
async def get_stores(
    keyword: Optional[str] = None,
    status: Optional[int] = None,
    city: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin)
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
    
    # 门店管理员只能看到自己关联的门店（支持多门店）
    store_ids = current_admin.get("store_ids")
    if store_ids and not current_admin.get("is_super_admin"):
        # 如果是门店管理员，只返回关联的门店
        stores_result = []
        for store_id in store_ids:
            store = await service.get_by_id(store_id)
            if store:
                stores_result.append(StoreListResponse(
                    id=store.id,
                    name=store.name,
                    code=store.code,
                    address=store.address,
                    phone=store.phone,
                    logo=store.logo,
                    theme_style=store.theme_style,
                    status=store.status,
                    department_count=await service.get_department_count(store.id),
                    created_at=store.created_at
                ))
        return PageResponse(data=stores_result, total=len(stores_result), page=1, page_size=page_size)
    
    # 超级管理员可以看到所有门店
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
            logo=store.logo,
            theme_style=store.theme_style,
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
async def get_all_stores(
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    """获取所有营业中的门店（下拉选择用）"""
    service = StoreService(db)
    
    # 门店管理员只能看到自己的门店
    store_id = current_admin.get("store_id")
    if store_id:
        store = await service.get_by_id(store_id)
        if store and store.status == 1:
            return [StoreResponse.model_validate(store)]
        return []
    
    # 超级管理员可以看到所有门店
    stores = await service.get_all_active()
    return [StoreResponse.model_validate(s) for s in stores]


@router.get("/{store_id}", response_model=StoreResponse)
async def get_store(
    store_id: str, 
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    """获取门店详情"""
    # 门店管理员只能查看自己的门店
    admin_store_id = current_admin.get("store_id")
    if admin_store_id and admin_store_id != store_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="您无权访问此门店"
        )
    
    service = StoreService(db)
    store = await service.get_by_id(store_id)
    
    if not store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="门店不存在，请检查后重试"
        )
    
    return StoreResponse.model_validate(store)


@router.post("", response_model=StoreResponse)
async def create_store(
    data: StoreCreate,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    """创建门店（仅超级管理员）"""
    # 门店管理员不能创建门店
    if current_admin.get("store_id"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="门店管理员无权创建门店，请联系超级管理员"
        )
    
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
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    """更新门店"""
    # 门店管理员只能更新自己的门店
    admin_store_id = current_admin.get("store_id")
    if admin_store_id and admin_store_id != store_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="您无权修改此门店"
        )
    
    service = StoreService(db)
    
    try:
        store = await service.update(store_id, data)
        if not store:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="门店不存在，请检查后重试"
            )
        return StoreResponse.model_validate(store)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=str(e)
        )


@router.delete("/{store_id}")
async def delete_store(
    store_id: str, 
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    """删除门店（仅超级管理员）"""
    # 门店管理员不能删除门店
    if current_admin.get("store_id"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="门店管理员无权删除门店，请联系超级管理员"
        )
    
    service = StoreService(db)
    
    try:
        success = await service.delete(store_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="门店不存在，请检查后重试"
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
    new_status: int = Query(..., ge=0, le=1, alias="status", description="状态: 0-停业 1-营业"),
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    """更新门店状态"""
    # 门店管理员只能更新自己的门店状态
    admin_store_id = current_admin.get("store_id")
    if admin_store_id and admin_store_id != store_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="您无权修改此门店状态"
        )
    
    service = StoreService(db)
    store = await service.update_status(store_id, new_status)
    
    if not store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="门店不存在，请检查后重试"
        )
    
    return {"message": "状态更新成功"}


@router.get("/{store_id}/departments", response_model=List[DepartmentResponse])
async def get_store_departments(
    store_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    """获取门店已绑定的科室列表"""
    # 门店管理员只能查看自己的门店
    admin_store_id = current_admin.get("store_id")
    if admin_store_id and admin_store_id != store_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="您无权访问此门店"
        )
    
    service = StoreService(db)
    
    # 验证门店是否存在
    store = await service.get_by_id(store_id)
    if not store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="门店不存在，请检查后重试"
        )
    
    departments = await service.get_departments(store_id)
    return [DepartmentResponse.model_validate(d) for d in departments]


@router.put("/{store_id}/departments/batch")
async def batch_bind_departments(
    store_id: str,
    department_ids: List[str],
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    """批量绑定科室到门店"""
    # 门店管理员只能操作自己的门店
    admin_store_id = current_admin.get("store_id")
    if admin_store_id and admin_store_id != store_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="您无权操作此门店"
        )
    
    service = StoreService(db)
    
    try:
        count = await service.batch_bind_departments(store_id, department_ids)
        return {"message": "绑定成功", "count": count}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/{store_id}/admins", response_model=List[AdminListResponse])
async def get_store_admins(
    store_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    """获取门店已绑定的管理员列表"""
    # 仅超级管理员可操作
    if not current_admin.get("is_super_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="仅超级管理员可查看门店用户"
        )
    
    service = StoreService(db)
    
    # 验证门店是否存在
    store = await service.get_by_id(store_id)
    if not store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="门店不存在，请检查后重试"
        )
    
    admins = await service.get_admins(store_id)
    return [AdminListResponse.model_validate(a) for a in admins]


@router.put("/{store_id}/admins/batch")
async def batch_bind_admins(
    store_id: str,
    admin_ids: List[str],
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    """批量绑定管理员到门店"""
    # 仅超级管理员可操作
    if not current_admin.get("is_super_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="仅超级管理员可分配用户"
        )
    
    service = StoreService(db)
    
    try:
        count = await service.batch_bind_admins(store_id, admin_ids)
        return {"message": "分配成功", "count": count}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
