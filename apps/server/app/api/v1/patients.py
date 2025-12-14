"""患者管理 API（管理后台）"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.db.session import get_db
from app.api.deps import get_current_admin
from app.services.patient_service import PatientManageService
from app.services.point_service import PointService
from app.schemas.response import PageResponse
from app.schemas.user import PatientUpdate
from app.schemas.point_log import PointAdjustData

router = APIRouter()


@router.get("")
async def get_patients(
    keyword: Optional[str] = None,
    is_blacklist: Optional[bool] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin),
):
    """获取患者列表"""
    service = PatientManageService(db)
    items, total = await service.get_list(
        keyword=keyword,
        is_blacklist=is_blacklist,
        page=page,
        page_size=page_size,
    )
    return PageResponse(data=items, total=total, page=page, page_size=page_size)


@router.get("/blacklist")
async def get_blacklist(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin),
):
    """获取黑名单列表"""
    service = PatientManageService(db)
    items, total = await service.get_blacklist(page=page, page_size=page_size)
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="患者不存在")
    
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="患者不存在")
    
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="患者不存在")
    
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="患者不存在")
    
    return {"message": "已移出黑名单"}
