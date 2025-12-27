"""患者管理 API（管理后台）"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.db.session import get_db
from app.api.deps import get_current_admin, get_store_filter
from app.services.patient_service import PatientManageService
from app.services.point_service import PointService
from app.schemas.response import PageResponse
from app.schemas.user import PatientUpdate, PatientCreateByAdmin, FamilyMemberCreate
from app.schemas.point_log import PointAdjustData

router = APIRouter()


@router.post("")
async def create_patient(
    data: PatientCreateByAdmin,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin),
):
    """创建患者（管理员手动添加）"""
    # 获取当前管理员的门店ID（非超管创建时自动关联门店）
    store_id = None
    if not current_admin.get("is_super_admin"):
        store_id = current_admin.get("current_store_id") or current_admin.get("store_id")
    
    service = PatientManageService(db)
    try:
        result = await service.create_patient(data, store_id=store_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("")
async def get_patients(
    keyword: Optional[str] = None,
    is_blacklist: Optional[bool] = None,
    store_id: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin),
):
    """获取患者列表"""
    # 门店过滤
    store_filter = get_store_filter(current_admin)
    if store_filter:
        store_id = store_filter
    
    service = PatientManageService(db)
    items, total = await service.get_list(
        keyword=keyword,
        is_blacklist=is_blacklist,
        store_id=store_id,
        page=page,
        page_size=page_size,
    )
    return PageResponse(data=items, total=total, page=page, page_size=page_size)


@router.get("/blacklist")
async def get_blacklist(
    store_id: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin),
):
    """获取黑名单列表"""
    # 门店过滤
    store_filter = get_store_filter(current_admin)
    if store_filter:
        store_id = store_filter
    
    service = PatientManageService(db)
    items, total = await service.get_blacklist(store_id=store_id, page=page, page_size=page_size)
    return PageResponse(data=items, total=total, page=page, page_size=page_size)


@router.get("/{patient_id}")
async def get_patient_detail(
    patient_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin),
):
    """获取患者详情"""
    service = PatientManageService(db)
    detail = await service.get_detail(patient_id)
    
    if not detail:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="患者不存在，请检查后重试")
    
    return detail


@router.put("/{patient_id}")
async def update_patient(
    patient_id: str,
    data: PatientUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin),
):
    """更新患者信息"""
    service = PatientManageService(db)
    result = await service.update_patient(patient_id, data)
    
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="患者不存在，请检查后重试")
    
    return result


@router.get("/{patient_id}/appointments")
async def get_patient_appointments(
    patient_id: str,
    doctor_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    status: Optional[int] = None,
    is_admin_booked: Optional[bool] = None,
    is_follow_up: Optional[bool] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin),
):
    """获取患者预约记录"""
    service = PatientManageService(db)
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


@router.get("/{patient_id}/consumption-records")
async def get_consumption_records(
    patient_id: str,
    item_name: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin),
):
    """获取患者消费/项目记录"""
    service = PatientManageService(db)
    items, total = await service.get_consumption_records(
        patient_id=patient_id,
        item_name=item_name,
        page=page,
        page_size=page_size,
    )
    return PageResponse(data=items, total=total, page=page, page_size=page_size)


@router.get("/{patient_id}/points")
async def get_point_logs(
    patient_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin),
):
    """获取积分流水"""
    service = PointService(db)
    items, total, current_points = await service.get_point_logs(
        patient_id=patient_id,
        page=page,
        page_size=page_size,
    )
    return {
        "data": items,
        "total": total,
        "page": page,
        "pageSize": page_size,
        "currentPoints": current_points,
    }


@router.post("/{patient_id}/points")
async def adjust_points(
    patient_id: str,
    data: PointAdjustData,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin),
):
    """调整积分（手动增减）"""
    service = PointService(db)
    result = await service.adjust_points(
        patient_id=patient_id,
        amount=data.amount,
        remark=data.remark,
        operator_id=current_admin.id,
        log_type=4,  # 手动调整
    )
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="积分调整失败，请检查患者是否存在或积分余额是否充足"
        )
    
    return result


@router.get("/{patient_id}/points/summary")
async def get_point_summary(
    patient_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin),
):
    """获取积分汇总"""
    service = PointService(db)
    summary = await service.get_point_summary(patient_id)
    return summary


@router.put("/{patient_id}/blacklist")
async def add_to_blacklist(
    patient_id: str,
    reason: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin),
):
    """加入黑名单"""
    service = PatientManageService(db)
    success = await service.add_to_blacklist(patient_id, reason)
    
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="患者不存在，请检查后重试")
    
    return {"message": "已加入黑名单"}


@router.delete("/{patient_id}/blacklist")
async def remove_from_blacklist(
    patient_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin),
):
    """移出黑名单"""
    service = PatientManageService(db)
    success = await service.remove_from_blacklist(patient_id)
    
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="患者不存在，请检查后重试")
    
    return {"message": "已移出黑名单"}


# ========== 家庭成员（亲友）管理 ==========
@router.post("/{patient_id}/family-members")
async def add_family_member(
    patient_id: str,
    data: FamilyMemberCreate,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin),
):
    """为患者添加家庭成员（亲友）"""
    service = PatientManageService(db)
    try:
        result = await service.add_family_member(patient_id, data)
        if not result:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="患者不存在，请检查后重试")
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.put("/{patient_id}/family-members/{member_id}")
async def update_family_member(
    patient_id: str,
    member_id: str,
    data: PatientUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin),
):
    """编辑家庭成员信息"""
    service = PatientManageService(db)
    result = await service.update_family_member(patient_id, member_id, data)
    
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="家庭成员不存在，请检查后重试")
    
    return result


@router.delete("/{patient_id}/family-members/{member_id}")
async def delete_family_member(
    patient_id: str,
    member_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin),
):
    """删除家庭成员"""
    service = PatientManageService(db)
    try:
        success = await service.delete_family_member(patient_id, member_id)
        
        if not success:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="家庭成员不存在或无法删除，请检查后重试")
        
        return {"message": "删除成功"}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
