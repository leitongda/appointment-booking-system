"""Admin patient-user management router."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status as http_status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import check_store_access, get_current_admin, get_store_filter, require_permission
from app.core.config import settings
from app.db.session import get_db
from app.modules.patients.service_users import UserManageService
from app.modules.points.service import PointService
from app.schemas.response import PageResponse
from app.schemas.user import FamilyMemberCreate, PatientUpdate, AdminUserUpdate

router = APIRouter()


async def _ensure_user_store_access(
    service: UserManageService,
    current_admin: dict,
    user_id: str,
    detail_message: str = "您无权查看此用户信息",
) -> None:
    user_store_ids = await service.get_user_store_ids(user_id)
    if any(store_id and not check_store_access(current_admin, store_id) for store_id in user_store_ids):
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail=detail_message)


async def _ensure_card_store_access(
    service: UserManageService,
    current_admin: dict,
    user_id: str,
    card_id: str,
    detail_message: str = "您无权操作该就诊卡",
) -> None:
    card_store_id = await service.get_card_store_id(user_id, card_id)
    if card_store_id and not check_store_access(current_admin, card_store_id):
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail=detail_message)


@router.get("", summary="获取患者列表")
async def get_users(
    keyword: Optional[str] = None,
    status: Optional[int] = None,
    store_id: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=settings.MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
    current_admin=Depends(get_current_admin),
    _: None = Depends(require_permission("patient:list")),
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
    _: None = Depends(require_permission("patient:detail")),
):
    service = UserManageService(db)
    await _ensure_user_store_access(service, current_admin, user_id)
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
    await _ensure_user_store_access(service, current_admin, user_id, "您无权修改此用户状态")
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
    manage_service = UserManageService(db)
    await _ensure_user_store_access(manage_service, current_admin, user_id, "您无权调整此用户积分")
    patient_id = await manage_service.get_default_patient_id(user_id)
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
    await _ensure_user_store_access(service, current_admin, user_id, "您无权删除此用户")
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
    await _ensure_user_store_access(service, current_admin, user_id, "您无权修改此用户信息")
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
    await _ensure_user_store_access(service, current_admin, user_id, "您无权为此用户添加就诊卡")
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
    await _ensure_card_store_access(service, current_admin, user_id, card_id, "您无权修改该就诊卡")
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
    await _ensure_card_store_access(service, current_admin, user_id, card_id, "您无权删除该就诊卡")
    try:
        success = await service.delete_card(user_id=user_id, card_id=card_id)
        if not success:
            raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="就诊卡不存在，请检查后重试")
        return {"message": "删除成功"}
    except ValueError as exc:
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
