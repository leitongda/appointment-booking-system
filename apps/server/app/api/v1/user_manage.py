"""用户（患者）管理 API（管理后台）"""
from fastapi import APIRouter, Depends, HTTPException, status as http_status, Query, Body
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.db.session import get_db
from app.api.deps import get_current_admin, get_store_filter, require_permission
from app.services.patient_service import UserManageService
from app.schemas.response import PageResponse
from app.schemas.user import PatientUpdate, FamilyMemberCreate
from app.core.config import settings

router = APIRouter()


@router.get("", summary="获取患者列表")
async def get_users(
    keyword: Optional[str] = None,
    status: Optional[int] = None,
    store_id: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=settings.MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin),
):
    """获取患者（用户）列表"""
    # 门店过滤
    store_filter = get_store_filter(current_admin)
    if store_filter:
        store_id = store_filter
    
    service = UserManageService(db)
    items, total = await service.get_list(
        keyword=keyword,
        status=status,
        store_id=store_id,
        page=page,
        page_size=page_size,
    )
    return PageResponse(data=items, total=total, page=page, page_size=page_size)


@router.get("/{user_id}", summary="获取患者详情")
async def get_user_detail(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin),
):
    """获取患者（用户）详情"""
    service = UserManageService(db)
    detail = await service.get_detail(user_id)
    
    if not detail:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="用户不存在，请检查后重试")
    
    return detail


@router.put("/{user_id}/status", summary="更新用户状态")
async def update_user_status(
    user_id: str,
    user_status: int = Query(..., ge=0, le=1, description="状态: 0禁用 1正常", alias="status"),
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("patient:update")),
):
    """更新用户状态（禁用/启用）"""
    service = UserManageService(db)
    success = await service.update_status(
        user_id=user_id,
        status=user_status,
        operator_id=current_admin.get("id"),
    )
    
    if not success:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="用户不存在，请检查后重试")
    
    return {"message": "状态更新成功"}


@router.post("/{user_id}/points", summary="调整用户积分")
async def adjust_user_points(
    user_id: str,
    amount: int = Query(..., description="调整积分数量（正数增加，负数减少）"),
    remark: str = Query(..., min_length=1, max_length=200, description="调整原因"),
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("patient:update")),
):
    """调整用户积分"""
    service = UserManageService(db)
    try:
        success = await service.adjust_points(
            user_id=user_id,
            amount=amount,
            remark=remark,
            operator_id=current_admin.get("id"),
        )
        
        if not success:
            raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="用户不存在，请检查后重试")
        
        return {"message": "积分调整成功"}
    except ValueError as e:
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/{user_id}", summary="删除用户")
async def delete_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("patient:delete")),
):
    """删除用户（患者）"""
    service = UserManageService(db)
    try:
        success = await service.delete_user(
            user_id=user_id,
            operator_id=current_admin.get("id"),
        )
        
        if not success:
            raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="用户不存在，请检查后重试")
        
        return {"message": "删除成功"}
    except ValueError as e:
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.put("/{user_id}", summary="更新用户信息")
async def update_user(
    user_id: str,
    data: dict = Body(...),
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("patient:update")),
):
    """更新用户基本信息"""
    service = UserManageService(db)
    result = await service.update_user(
        user_id=user_id,
        data=data,
        operator_id=current_admin.get("id"),
    )
    
    if not result:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="用户不存在，请检查后重试")
    
    return result


# ========== 就诊卡管理 ==========
@router.post("/{user_id}/cards", summary="添加就诊卡")
async def create_card(
    user_id: str,
    data: FamilyMemberCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("patient:update")),
):
    """为用户添加就诊卡"""
    service = UserManageService(db)
    try:
        result = await service.create_card(
            user_id=user_id,
            data=data,
            operator_id=current_admin.get("id"),
        )
        if not result:
            raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="用户不存在，请检查后重试")
        return result
    except ValueError as e:
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.put("/{user_id}/cards/{card_id}", summary="更新就诊卡信息")
async def update_card(
    user_id: str,
    card_id: str,
    data: PatientUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("patient:update")),
):
    """更新就诊卡信息"""
    service = UserManageService(db)
    result = await service.update_card(
        user_id=user_id,
        card_id=card_id,
        data=data,
        operator_id=current_admin.get("id"),
    )
    
    if not result:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="就诊卡不存在，请检查后重试")
    
    return result


@router.delete("/{user_id}/cards/{card_id}", summary="删除就诊卡")
async def delete_card(
    user_id: str,
    card_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("patient:delete")),
):
    """删除就诊卡"""
    service = UserManageService(db)
    try:
        success = await service.delete_card(
            user_id=user_id,
            card_id=card_id,
        )
        
        if not success:
            raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="就诊卡不存在，请检查后重试")
        
        return {"message": "删除成功"}
    except ValueError as e:
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail=str(e))

