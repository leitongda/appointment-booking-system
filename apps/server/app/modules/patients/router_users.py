"""Admin patient-user management router."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status as http_status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin, get_store_filter, require_permission
from app.core.config import settings
from app.db.session import get_db
from app.modules.patients.service_users import UserManageService
from app.modules.points.service import PointService
from app.schemas.response import PageResponse
from app.schemas.user import FamilyMemberCreate, PatientUpdate, AdminUserUpdate

router = APIRouter()


@router.get("", summary="获取患者列表")
async def get_users(
    keyword: Optional[str] = None,
    status: Optional[int] = None,
    store_id: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=settings.MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
    current_admin=Depends(get_current_admin),
):
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
    current_admin=Depends(get_current_admin),
):
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
    service = UserManageService(db)
    success = await service.update_status(user_id=user_id, status=user_status, operator_id=current_admin.get("id"))
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
    from sqlalchemy import select
    from app.models.user import Patient

    # 查找用户的默认就诊卡
    result = await db.execute(
        select(Patient.id)
        .where(Patient.user_id == user_id)
        .order_by(Patient.is_default.desc(), Patient.created_at.asc())
        .limit(1)
    )
    patient_id = result.scalar_one_or_none()
    if not patient_id:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="该用户没有就诊卡，无法调整积分")

    point_service = PointService(db)
    try:
        result_data = await point_service.adjust_points(
            patient_id=patient_id,
            amount=amount,
            remark=remark,
            operator_id=current_admin.get("id"),
            log_type=4,
        )
        if not result_data:
            raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail="积分调整失败，请检查积分余额是否充足")
        return {"message": "积分调整成功"}
    except ValueError as exc:
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.delete("/{user_id}", summary="删除用户")
async def delete_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("patient:delete")),
):
    service = UserManageService(db)
    try:
        success = await service.delete_user(user_id=user_id, operator_id=current_admin.get("id"))
        if not success:
            raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="用户不存在，请检查后重试")
        return {"message": "删除成功"}
    except ValueError as exc:
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.put("/{user_id}", summary="更新用户信息")
async def update_user(
    user_id: str,
    data: AdminUserUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("patient:update")),
):
    service = UserManageService(db)
    result = await service.update_user(user_id=user_id, data=data, operator_id=current_admin.get("id"))
    if not result:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="用户不存在，请检查后重试")
    return result


@router.post("/{user_id}/cards", summary="添加就诊卡")
async def create_card(
    user_id: str,
    data: FamilyMemberCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("patient:update")),
):
    service = UserManageService(db)
    try:
        result = await service.create_card(user_id=user_id, data=data, operator_id=current_admin.get("id"))
        if not result:
            raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="用户不存在，请检查后重试")
        return result
    except ValueError as exc:
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.put("/{user_id}/cards/{card_id}", summary="更新就诊卡信息")
async def update_card(
    user_id: str,
    card_id: str,
    data: PatientUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("patient:update")),
):
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
    service = UserManageService(db)
    try:
        success = await service.delete_card(user_id=user_id, card_id=card_id)
        if not success:
            raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="就诊卡不存在，请检查后重试")
        return {"message": "删除成功"}
    except ValueError as exc:
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
