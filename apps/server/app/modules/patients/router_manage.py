"""Admin patient-card management router."""


from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi import status as http_status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    check_store_access,
    get_current_admin,
    get_store_filter,
    require_permission,
    resolve_admin_tenant_anchor,
)
from app.core.config import settings
from app.db.session import get_db
from app.modules.patients.service_manage import PatientManageService
from app.modules.points.service import PointService
from app.schemas.point_log import PointAdjustData
from app.schemas.response import PageResponse
from app.schemas.user import FamilyMemberCreate, PatientCreateByAdmin, PatientUpdate

router = APIRouter()


async def _ensure_patient_store_access(
    service: PatientManageService,
    current_admin: dict,
    patient_id: str,
    detail_message: str = "您无权查看此患者信息",
) -> None:
    patient_store_id = await service.get_patient_store_id(patient_id)
    if patient_store_id and not check_store_access(current_admin, patient_store_id):
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail=detail_message)


@router.post("", summary="创建患者")
async def create_patient(
    data: PatientCreateByAdmin,
    db: AsyncSession = Depends(get_db),
    current_admin=Depends(get_current_admin),
    _: None = Depends(require_permission("patient:create")),
):
    store_id = None
    if not current_admin.get("is_super_admin"):
        store_id = current_admin.get("current_store_id") or current_admin.get("store_id")

    service = PatientManageService(db, resolve_admin_tenant_anchor(current_admin))
    try:
        return await service.create_patient(data, store_id=store_id)
    except ValueError as exc:
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("", summary="获取患者列表")
async def get_patients(
    keyword: str | None = None,
    is_blacklist: bool | None = None,
    store_id: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=settings.MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
    current_admin=Depends(get_current_admin),
    _: None = Depends(require_permission("patient:list")),
):
    store_filter = get_store_filter(current_admin)
    if store_filter:
        store_id = store_filter

    service = PatientManageService(db, resolve_admin_tenant_anchor(current_admin))
    items, total = await service.get_list(
        keyword=keyword,
        is_blacklist=is_blacklist,
        store_id=store_id,
        page=page,
        page_size=page_size,
    )
    return PageResponse(data=items, total=total, page=page, page_size=page_size)


@router.get("/blacklist", summary="获取黑名单列表")
async def get_blacklist(
    store_id: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=settings.MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
    current_admin=Depends(get_current_admin),
    _: None = Depends(require_permission("patient:list")),
):
    store_filter = get_store_filter(current_admin)
    if store_filter:
        store_id = store_filter

    service = PatientManageService(db, resolve_admin_tenant_anchor(current_admin))
    items, total = await service.get_blacklist(store_id=store_id, page=page, page_size=page_size)
    return PageResponse(data=items, total=total, page=page, page_size=page_size)


@router.get("/{patient_id}", summary="获取患者详情")
async def get_patient_detail(
    patient_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin=Depends(get_current_admin),
    _: None = Depends(require_permission("patient:detail")),
):
    service = PatientManageService(db, resolve_admin_tenant_anchor(current_admin))
    await _ensure_patient_store_access(service, current_admin, patient_id)

    detail = await service.get_detail(patient_id)
    if not detail:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="患者不存在，请检查后重试")
    return detail


@router.put("/{patient_id}", summary="更新患者信息")
async def update_patient(
    patient_id: str,
    data: PatientUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("patient:update")),
):
    service = PatientManageService(db, resolve_admin_tenant_anchor(current_admin))
    await _ensure_patient_store_access(service, current_admin, patient_id, "您无权修改此患者信息")

    result = await service.update_patient(patient_id, data)
    if not result:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="患者不存在，请检查后重试")
    return result


@router.delete("/{patient_id}", summary="删除患者")
async def delete_patient(
    patient_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("patient:delete")),
):
    service = PatientManageService(db, resolve_admin_tenant_anchor(current_admin))
    await _ensure_patient_store_access(service, current_admin, patient_id, "您无权删除此患者")

    try:
        success = await service.delete_patient(patient_id)
        if not success:
            raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="患者不存在，请检查后重试")
        return {"message": "删除成功"}
    except ValueError as exc:
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/{patient_id}/appointments", summary="获取患者预约记录")
async def get_patient_appointments(
    patient_id: str,
    doctor_id: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    status: int | None = None,
    is_admin_booked: bool | None = None,
    is_follow_up: bool | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=settings.MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
    current_admin=Depends(get_current_admin),
    _: None = Depends(require_permission("patient:detail")),
):
    service = PatientManageService(db, resolve_admin_tenant_anchor(current_admin))
    await _ensure_patient_store_access(service, current_admin, patient_id)
    items, total = await service.get_appointments(
        patient_id=patient_id,
        doctor_id=doctor_id,
        start_date=start_date,
        end_date=end_date,
        status=status,
        is_admin_booked=is_admin_booked,
        is_follow_up=is_follow_up,
        page=page,
        page_size=page_size,
    )
    return PageResponse(data=items, total=total, page=page, page_size=page_size)


@router.get("/{patient_id}/consumption-records", summary="获取消费记录")
async def get_consumption_records(
    patient_id: str,
    item_name: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=settings.MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
    current_admin=Depends(get_current_admin),
    _: None = Depends(require_permission("patient:detail")),
):
    service = PatientManageService(db, resolve_admin_tenant_anchor(current_admin))
    await _ensure_patient_store_access(service, current_admin, patient_id)
    items, total = await service.get_consumption_records(
        patient_id=patient_id,
        item_name=item_name,
        page=page,
        page_size=page_size,
    )
    return PageResponse(data=items, total=total, page=page, page_size=page_size)


@router.get("/{patient_id}/points", summary="获取积分流水")
async def get_point_logs(
    patient_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=settings.MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
    current_admin=Depends(get_current_admin),
    _: None = Depends(require_permission("patient:detail")),
):
    service = PointService(db)
    manage_service = PatientManageService(db, resolve_admin_tenant_anchor(current_admin))
    await _ensure_patient_store_access(manage_service, current_admin, patient_id)
    items, total, current_points = await service.get_point_logs(patient_id=patient_id, page=page, page_size=page_size)
    return {
        "data": items,
        "total": total,
        "page": page,
        "pageSize": page_size,
        "currentPoints": current_points,
    }


@router.post("/{patient_id}/points", summary="调整积分")
async def adjust_points(
    patient_id: str,
    data: PointAdjustData,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("patient:update")),
):
    service = PointService(db)
    manage_service = PatientManageService(db, resolve_admin_tenant_anchor(current_admin))
    await _ensure_patient_store_access(manage_service, current_admin, patient_id, "您无权调整此患者积分")
    result = await service.adjust_points(
        patient_id=patient_id,
        amount=data.amount,
        remark=data.remark,
        operator_id=current_admin.get("id"),
        log_type=4,
    )
    if not result:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="积分调整失败，请检查患者是否存在或积分余额是否充足",
        )
    return result


@router.get("/{patient_id}/points/summary", summary="获取积分汇总")
async def get_point_summary(
    patient_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin=Depends(get_current_admin),
    _: None = Depends(require_permission("patient:detail")),
):
    service = PointService(db)
    manage_service = PatientManageService(db, resolve_admin_tenant_anchor(current_admin))
    await _ensure_patient_store_access(manage_service, current_admin, patient_id)
    return await service.get_point_summary(patient_id)


@router.put("/{patient_id}/blacklist", summary="加入黑名单")
async def add_to_blacklist(
    patient_id: str,
    reason: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_admin=Depends(get_current_admin),
    _: None = Depends(require_permission("patient:update")),
):
    service = PatientManageService(db, resolve_admin_tenant_anchor(current_admin))
    await _ensure_patient_store_access(service, current_admin, patient_id, "您无权操作此患者黑名单状态")
    success = await service.add_to_blacklist(patient_id, reason)
    if not success:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="患者不存在，请检查后重试")
    return {"message": "已加入黑名单"}


@router.delete("/{patient_id}/blacklist", summary="移出黑名单")
async def remove_from_blacklist(
    patient_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin=Depends(get_current_admin),
    _: None = Depends(require_permission("patient:update")),
):
    service = PatientManageService(db, resolve_admin_tenant_anchor(current_admin))
    await _ensure_patient_store_access(service, current_admin, patient_id, "您无权操作此患者黑名单状态")
    success = await service.remove_from_blacklist(patient_id)
    if not success:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="患者不存在，请检查后重试")
    return {"message": "已移出黑名单"}


@router.post("/{patient_id}/family-members", summary="添加家庭成员")
async def add_family_member(
    patient_id: str,
    data: FamilyMemberCreate,
    db: AsyncSession = Depends(get_db),
    current_admin=Depends(get_current_admin),
    _: None = Depends(require_permission("patient:update")),
):
    service = PatientManageService(db, resolve_admin_tenant_anchor(current_admin))
    await _ensure_patient_store_access(service, current_admin, patient_id, "您无权修改此患者家庭成员")
    try:
        result = await service.add_family_member(patient_id, data)
        if not result:
            raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="患者不存在，请检查后重试")
        return result
    except ValueError as exc:
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.put("/{patient_id}/family-members/{member_id}", summary="更新家庭成员")
async def update_family_member(
    patient_id: str,
    member_id: str,
    data: PatientUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin=Depends(get_current_admin),
    _: None = Depends(require_permission("patient:update")),
):
    service = PatientManageService(db, resolve_admin_tenant_anchor(current_admin))
    await _ensure_patient_store_access(service, current_admin, patient_id, "您无权修改此患者家庭成员")
    result = await service.update_family_member(patient_id, member_id, data)
    if not result:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="家庭成员不存在，请检查后重试")
    return result


@router.delete("/{patient_id}/family-members/{member_id}", summary="删除家庭成员")
async def delete_family_member(
    patient_id: str,
    member_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin=Depends(get_current_admin),
    _: None = Depends(require_permission("patient:update")),
):
    service = PatientManageService(db, resolve_admin_tenant_anchor(current_admin))
    await _ensure_patient_store_access(service, current_admin, patient_id, "您无权修改此患者家庭成员")
    try:
        success = await service.delete_family_member(patient_id, member_id)
        if not success:
            raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="家庭成员不存在或无法删除，请检查后重试")
        return {"message": "删除成功"}
    except ValueError as exc:
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
