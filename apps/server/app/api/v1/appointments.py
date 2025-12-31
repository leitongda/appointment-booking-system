from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from datetime import date

from app.db.session import get_db
from app.api.deps import get_current_user, get_current_user_or_admin, get_store_filter
from app.schemas.appointment import AppointmentCreate, AppointmentResponse, AppointmentCancelRequest, AppointmentStatistics
from app.schemas.response import PageResponse
from app.services.appointment_service import AppointmentService

router = APIRouter()

@router.get("", response_model=PageResponse[AppointmentResponse])
async def get_appointments(
    status: Optional[int] = None,
    patient_id: Optional[str] = None,
    store_id: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user_or_admin)
):
    """获取预约列表"""
    service = AppointmentService(db)
    # 管理员可以查看所有预约，普通用户只能查看自己的
    user_id = None if current_user.get("is_admin") else current_user["id"]
    
    # 门店过滤（只对管理员生效）
    if current_user.get("is_admin"):
        store_filter = get_store_filter(current_user)
        if store_filter:
            store_id = store_filter
    
    appointments, total = await service.get_list(
        user_id=user_id,
        store_id=store_id,
        status=status,
        patient_id=patient_id,
        start_date=start_date,
        end_date=end_date,
        page=page,
        page_size=page_size
    )
    
    result = []
    for a in appointments:
        result.append(AppointmentResponse(
            id=a.id,
            appointment_no=a.appointment_no,
            user_id=a.user_id,
            patient_id=a.patient_id,
            doctor_id=a.doctor_id,
            schedule_id=a.schedule_id,
            schedule_date=a.schedule.schedule_date if a.schedule else None,
            time_slot=a.schedule.time_slot if a.schedule else None,
            queue_number=a.queue_number,
            status=a.status,
            sign_in_time=a.sign_in_time,
            call_time=a.call_time,
            complete_time=a.complete_time,
            cancel_time=a.cancel_time,
            cancel_reason=a.cancel_reason,
            created_at=a.created_at
        ))
    
    return PageResponse(data=result, total=total, page=page, page_size=page_size)

@router.get("/today")
async def get_today_appointments(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user_or_admin)
):
    """获取今日预约（医生端）"""
    service = AppointmentService(db)
    # 假设 current_user 包含 doctor_id
    doctor_id = current_user.get("doctor_id")
    if not doctor_id:
        return []
    
    appointments = await service.get_today_by_doctor(doctor_id)
    return appointments


@router.get("/today-pending")
async def get_today_pending_appointments(
    store_id: str = Query(..., description="门店ID"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """获取用户在指定门店的今日待签到预约
    
    用于患者扫码签到时选择要签到的预约
    """
    service = AppointmentService(db)
    appointments = await service.get_today_pending_by_user_and_store(
        user_id=current_user["id"],
        store_id=store_id
    )
    
    result = []
    for a in appointments:
        result.append({
            "id": a.id,
            "appointmentNo": a.appointment_no,
            "patientName": a.patient.name if a.patient else None,
            "doctorName": a.doctor.name if a.doctor else None,
            "departmentName": a.doctor.department.name if a.doctor and a.doctor.department else None,
            "scheduleDate": a.schedule.schedule_date.isoformat() if a.schedule else None,
            "timeSlot": a.schedule.time_slot if a.schedule else None,
            "status": a.status,
        })
    
    return result


@router.get("/queue")
async def get_checkin_queue(
    store_id: Optional[str] = None,
    doctor_id: Optional[str] = None,
    target_date: Optional[date] = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user_or_admin)
):
    """获取签到队列
    
    用于管理后台和医生端查看当日已签到的患者队列
    按签到时间排序
    """
    service = AppointmentService(db)
    
    # 如果是医生端，只能查看自己的队列
    if not current_user.get("is_admin"):
        doctor_id = current_user.get("doctor_id")
        if not doctor_id:
            return []
    
    # 默认查询今日
    if not target_date:
        target_date = date.today()
    
    appointments = await service.get_checkin_queue(
        store_id=store_id,
        doctor_id=doctor_id,
        target_date=target_date
    )
    
    result = []
    for a in appointments:
        result.append({
            "id": a.id,
            "appointmentNo": a.appointment_no,
            "queueNumber": a.queue_number,
            "patientId": a.patient_id,
            "patientName": a.patient.name if a.patient else None,
            "doctorId": a.doctor_id,
            "doctorName": a.doctor.name if a.doctor else None,
            "departmentName": a.doctor.department.name if a.doctor and a.doctor.department else None,
            "scheduleDate": a.schedule.schedule_date.isoformat() if a.schedule else None,
            "timeSlot": a.schedule.time_slot if a.schedule else None,
            "status": a.status,
            "signInTime": a.sign_in_time.isoformat() if a.sign_in_time else None,
            "callTime": a.call_time.isoformat() if a.call_time else None,
        })
    
    return result

@router.get("/statistics", response_model=AppointmentStatistics)
async def get_appointment_statistics(
    doctor_id: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: AsyncSession = Depends(get_db)
):
    """获取预约统计"""
    service = AppointmentService(db)
    return await service.get_statistics(doctor_id=doctor_id, start_date=start_date, end_date=end_date)

@router.get("/by-no/{appointment_no}", response_model=AppointmentResponse)
async def get_appointment_by_no(
    appointment_no: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user_or_admin)
):
    """按预约号获取预约详情"""
    service = AppointmentService(db)
    appointment = await service.get_by_appointment_no(appointment_no)
    
    if not appointment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="预约不存在，请检查后重试")
    
    # 验证权限：普通用户只能查看自己的预约
    if not current_user.get("is_admin") and appointment.user_id != current_user["id"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权查看此预约")
    
    return AppointmentResponse(
        id=appointment.id,
        appointment_no=appointment.appointment_no,
        user_id=appointment.user_id,
        patient_id=appointment.patient_id,
        doctor_id=appointment.doctor_id,
        schedule_id=appointment.schedule_id,
        schedule_date=appointment.schedule.schedule_date if appointment.schedule else None,
        time_slot=appointment.schedule.time_slot if appointment.schedule else None,
        queue_number=appointment.queue_number,
        status=appointment.status,
        sign_in_time=appointment.sign_in_time,
        call_time=appointment.call_time,
        complete_time=appointment.complete_time,
        cancel_time=appointment.cancel_time,
        cancel_reason=appointment.cancel_reason,
        created_at=appointment.created_at
    )

@router.get("/{appointment_id}", response_model=AppointmentResponse)
async def get_appointment(
    appointment_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user_or_admin)
):
    """获取预约详情"""
    service = AppointmentService(db)
    appointment = await service.get_by_id(appointment_id)
    
    if not appointment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="预约不存在，请检查后重试")
    
    return AppointmentResponse(
        id=appointment.id,
        appointment_no=appointment.appointment_no,
        user_id=appointment.user_id,
        patient_id=appointment.patient_id,
        doctor_id=appointment.doctor_id,
        schedule_id=appointment.schedule_id,
        schedule_date=appointment.schedule.schedule_date if appointment.schedule else None,
        time_slot=appointment.schedule.time_slot if appointment.schedule else None,
        queue_number=appointment.queue_number,
        status=appointment.status,
        sign_in_time=appointment.sign_in_time,
        call_time=appointment.call_time,
        complete_time=appointment.complete_time,
        cancel_time=appointment.cancel_time,
        cancel_reason=appointment.cancel_reason,
        created_at=appointment.created_at
    )

@router.post("", response_model=AppointmentResponse)
async def create_appointment(
    data: AppointmentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user_or_admin)
):
    """创建预约"""
    service = AppointmentService(db)
    
    try:
        appointment = await service.create(current_user["id"], data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    
    return AppointmentResponse(
        id=appointment.id,
        appointment_no=appointment.appointment_no,
        user_id=appointment.user_id,
        patient_id=appointment.patient_id,
        doctor_id=appointment.doctor_id,
        schedule_id=appointment.schedule_id,
        queue_number=appointment.queue_number,
        status=appointment.status,
        sign_in_time=appointment.sign_in_time,
        created_at=appointment.created_at
    )

@router.put("/{appointment_id}/cancel")
async def cancel_appointment(
    appointment_id: str,
    data: AppointmentCancelRequest = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user_or_admin)
):
    """取消预约"""
    service = AppointmentService(db)
    reason = data.reason if data else None
    is_admin = current_user.get("is_admin", False)
    
    try:
        appointment = await service.cancel(appointment_id, current_user["id"], reason, is_admin)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    
    if not appointment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="预约不存在，请检查后重试")
    
    return {"message": "取消成功"}

@router.put("/{appointment_id}/sign-in")
async def sign_in_appointment(appointment_id: str, db: AsyncSession = Depends(get_db)):
    """签到"""
    service = AppointmentService(db)
    
    try:
        appointment = await service.sign_in(appointment_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    
    if not appointment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="预约不存在，请检查后重试")
    
    return {"message": "签到成功", "queue_number": appointment.queue_number}

@router.put("/{appointment_id}/call")
async def call_appointment(appointment_id: str, db: AsyncSession = Depends(get_db)):
    """叫号"""
    service = AppointmentService(db)
    
    try:
        appointment = await service.call_patient(appointment_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    
    if not appointment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="预约不存在，请检查后重试")
    
    return {"message": "已呼叫"}

@router.put("/{appointment_id}/complete")
async def complete_appointment(appointment_id: str, db: AsyncSession = Depends(get_db)):
    """完成就诊"""
    service = AppointmentService(db)
    appointment = await service.complete(appointment_id)
    
    if not appointment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="预约不存在，请检查后重试")
    
    return {"message": "就诊完成"}


@router.put("/{appointment_id}/pass")
async def pass_appointment(appointment_id: str, db: AsyncSession = Depends(get_db)):
    """过号"""
    service = AppointmentService(db)
    
    try:
        appointment = await service.pass_number(appointment_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    
    if not appointment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="预约不存在，请检查后重试")
    
    return {"message": "已过号"}


@router.put("/{appointment_id}/recall")
async def recall_appointment(appointment_id: str, db: AsyncSession = Depends(get_db)):
    """重新叫号"""
    service = AppointmentService(db)
    
    try:
        appointment = await service.recall(appointment_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    
    if not appointment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="预约不存在，请检查后重试")
    
    return {"message": "已重新呼叫"}


@router.put("/{appointment_id}/no-show")
async def mark_no_show(appointment_id: str, db: AsyncSession = Depends(get_db)):
    """标记爽约"""
    service = AppointmentService(db)
    
    try:
        appointment = await service.mark_no_show(appointment_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    
    if not appointment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="预约不存在，请检查后重试")
    
    return {"message": "已标记爽约"}


@router.get("/queue/info")
async def get_queue_info(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user_or_admin)
):
    """获取当前叫号队列信息（医生端）"""
    doctor_id = current_user.get("doctor_id")
    if not doctor_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="需要医生权限，请联系管理员开通")
    
    service = AppointmentService(db)
    return await service.get_queue_info(doctor_id)
