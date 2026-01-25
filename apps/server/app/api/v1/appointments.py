from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from datetime import date, datetime, time, timedelta
from fastapi.security.utils import get_authorization_scheme_param
import pytz

from app.db.session import get_db
from app.api.deps import get_current_user, get_current_user_or_admin, get_store_filter, get_current_super_admin
from app.schemas.appointment import AppointmentCreate, AppointmentResponse, AppointmentCancelRequest, AppointmentStatistics
from app.schemas.response import PageResponse
from app.services.appointment_service import AppointmentService
from app.services.settings_service import SettingsService
from app.services.rule_engine_service import RuleEngineService
from app.core.config import settings

router = APIRouter()

@router.get("", response_model=PageResponse[AppointmentResponse])
async def get_appointments(
    status: Optional[int] = None,
    patient_id: Optional[str] = None,
    store_id: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    keyword: Optional[str] = None,
    doctor_id: Optional[str] = None,
    department_id: Optional[str] = None,
    created_start: Optional[datetime] = None,
    created_end: Optional[datetime] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=settings.MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user_or_admin)
):
    """获取预约列表
    
    Args:
        keyword: 关键字搜索（预约编号/患者姓名/手机号）
        doctor_id: 医生ID
        department_id: 科室ID
        created_start: 创建时间开始
        created_end: 创建时间结束
    """
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
        keyword=keyword,
        doctor_id=doctor_id,
        department_id=department_id,
        created_start=created_start,
        created_end=created_end,
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
            patient_name=a.patient_name,
            patient_phone=a.patient_phone,
            doctor_id=a.doctor_id,
            doctor_name=a.doctor_name,
            doctor_title=a.doctor_title,
            department_name=a.department_name,
            schedule_id=a.schedule_id,
            schedule_date=a.schedule.schedule_date if a.schedule else None,
            time_slot=a.schedule.time_slot if a.schedule else None,
            start_time=a.schedule.start_time if a.schedule else None,
            end_time=a.schedule.end_time if a.schedule else None,
            queue_number=a.queue_number,
            status=a.status,
            sign_in_time=a.sign_in_time,
            call_time=a.call_time,
            complete_time=a.complete_time,
            cancel_time=a.cancel_time,
            cancel_reason=a.cancel_reason,
            symptom_description=a.symptom_description,
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
    """获取用户在指定门店的今日待签到预约（增强版：包含详细时间窗信息）

    用于患者扫码签到时选择要签到的预约
    """
    service = AppointmentService(db)
    rule_engine = RuleEngineService(db)
    appointments = await service.get_today_pending_by_user_and_store(
        user_id=current_user["id"],
        store_id=store_id
    )

    now = datetime.now(pytz.UTC)
    result = []

    for a in appointments:
        signInStatus = 'available'
        signInMessage = ''
        checkin_open_at = None
        checkin_close_at = None
        minutes_until_open = None
        minutes_until_close = None

        if a.schedule:
            # 使用规则引擎检查签到时间窗
            try:
                window_check = await rule_engine.check_action_window(a.schedule, 'CHECKIN', now)

                checkin_open_at = window_check.get('open_at')
                checkin_close_at = window_check.get('close_at')

                if not window_check.get('allowed'):
                    if now < window_check.get('open_at', now):
                        signInStatus = 'early'
                        if checkin_open_at:
                            minutes_until_open = int((checkin_open_at - now).total_seconds() / 60)
                            signInMessage = f'未到签到时间，还需等待{minutes_until_open}分钟'
                        else:
                            signInMessage = '未到签到时间'
                    else:
                        signInStatus = 'late'
                        signInMessage = '已过签到时间'
                else:
                    signInStatus = 'available'
                    if checkin_close_at:
                        minutes_until_close = int((checkin_close_at - now).total_seconds() / 60)
                        signInMessage = f'可以签到（余{minutes_until_close}分钟）'
                    else:
                        signInMessage = '可以签到'
            except Exception:
                # 规则引擎检查失败，降级使用门店配置
                settings_service = SettingsService(db)
                settings = await settings_service.get_booking_settings(store_id=store_id)
                sign_in_advance_minutes = settings.get('signInAdvanceMinutes', 30)
                sign_in_late_minutes = settings.get('signInLateMinutes', 30)

                # 计算班次开始时间
                if a.schedule.start_time:
                    visit_time = a.schedule.start_time
                else:
                    time_slot_start_map = {
                        'AM': time(8, 0),
                        'PM': time(14, 0),
                        'morning': time(8, 0),
                        'afternoon': time(14, 0),
                        'evening': time(18, 0),
                        'NIGHT': time(18, 0),
                    }
                    visit_time = time_slot_start_map.get(a.schedule.time_slot, time(8, 0))

                visit_datetime = datetime.combine(a.schedule.schedule_date, visit_time)

                # 计算允许签到的时间窗口
                sign_in_start = visit_datetime - timedelta(minutes=sign_in_advance_minutes)
                sign_in_end = visit_datetime + timedelta(minutes=sign_in_late_minutes)

                if now < sign_in_start:
                    signInStatus = 'early'
                    minutes_until_open = int((sign_in_start - now).total_seconds() / 60)
                    signInMessage = f'未到签到时间，请等待{minutes_until_open}分钟'
                    checkin_open_at = sign_in_start
                    checkin_close_at = sign_in_end
                elif now > sign_in_end:
                    signInStatus = 'late'
                    signInMessage = '已过签到时间'
                    checkin_open_at = sign_in_start
                    checkin_close_at = sign_in_end
                else:
                    signInStatus = 'available'
                    minutes_until_close = int((sign_in_end - now).total_seconds() / 60)
                    signInMessage = f'可以签到（余{minutes_until_close}分钟）'
                    checkin_open_at = sign_in_start
                    checkin_close_at = sign_in_end

        result.append({
            "id": a.id,
            "appointmentNo": a.appointment_no,
            "patientName": a.patient_name,
            "doctorName": a.doctor_name,
            "departmentName": a.department_name,
            "scheduleDate": a.schedule.schedule_date.isoformat() if a.schedule else None,
            "timeSlot": a.schedule.time_slot if a.schedule else None,
            "startTime": a.schedule.start_time.isoformat() if a.schedule and a.schedule.start_time else None,
            "endTime": a.schedule.end_time.isoformat() if a.schedule and a.schedule.end_time else None,
            "status": a.status,
            "signInStatus": signInStatus,
            "signInMessage": signInMessage,
            "checkinOpenAt": checkin_open_at.isoformat() if checkin_open_at else None,
            "checkinCloseAt": checkin_close_at.isoformat() if checkin_close_at else None,
            "minutesUntilOpen": minutes_until_open,
            "minutesUntilClose": minutes_until_close,
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
            "patientName": a.patient_name,
            "doctorId": a.doctor_id,
            "doctorName": a.doctor_name,
            "departmentName": a.department_name,
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

@router.get("/check-duplicate")
async def check_duplicate_appointment(
    schedule_id: str = Query(..., description="排班ID"),
    patient_id: str = Query(..., description="就诊人ID"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """检查同一天同一时段是否有重复预约
    
    返回该时段已有的预约列表，用于前端提醒用户
    """
    from app.models.schedule import Schedule
    
    service = AppointmentService(db)
    
    # 先获取排班信息以获取日期和时段
    schedule_result = await db.execute(
        select(Schedule).where(Schedule.id == schedule_id)
    )
    schedule = schedule_result.scalar_one_or_none()
    
    if not schedule:
        return {"hasDuplicate": False, "appointments": []}
    
    # 检查重复预约
    duplicates = await service.check_duplicate_same_day(
        user_id=current_user["id"],
        patient_id=patient_id,
        schedule_date=schedule.schedule_date,
        time_slot=schedule.time_slot
    )
    
    result = []
    for a in duplicates:
        result.append({
            "id": a.id,
            "appointmentNo": a.appointment_no,
            "doctorName": a.doctor_name,
            "departmentName": a.department_name,
            "scheduleDate": a.schedule.schedule_date.isoformat() if a.schedule else None,
            "timeSlot": a.schedule.time_slot if a.schedule else None,
            "status": a.status,
        })
    
    return {
        "hasDuplicate": len(result) > 0,
        "appointments": result
    }

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
        patient_name=appointment.patient_name,
        patient_phone=appointment.patient_phone,
        doctor_id=appointment.doctor_id,
        doctor_name=appointment.doctor_name,
        doctor_title=appointment.doctor_title,
        department_name=appointment.department_name,
        schedule_id=appointment.schedule_id,
        schedule_date=appointment.schedule.schedule_date if appointment.schedule else None,
        time_slot=appointment.schedule.time_slot if appointment.schedule else None,
        start_time=appointment.schedule.start_time if appointment.schedule else None,
        end_time=appointment.schedule.end_time if appointment.schedule else None,
        queue_number=appointment.queue_number,
        status=appointment.status,
        sign_in_time=appointment.sign_in_time,
        call_time=appointment.call_time,
        complete_time=appointment.complete_time,
        cancel_time=appointment.cancel_time,
        cancel_reason=appointment.cancel_reason,
        symptom_description=appointment.symptom_description,
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
        patient_name=appointment.patient_name,
        patient_phone=appointment.patient_phone,
        doctor_id=appointment.doctor_id,
        doctor_name=appointment.doctor_name,
        doctor_title=appointment.doctor_title,
        department_name=appointment.department_name,
        schedule_id=appointment.schedule_id,
        schedule_date=appointment.schedule.schedule_date if appointment.schedule else None,
        time_slot=appointment.schedule.time_slot if appointment.schedule else None,
        start_time=appointment.schedule.start_time if appointment.schedule else None,
        end_time=appointment.schedule.end_time if appointment.schedule else None,
        queue_number=appointment.queue_number,
        status=appointment.status,
        sign_in_time=appointment.sign_in_time,
        call_time=appointment.call_time,
        complete_time=appointment.complete_time,
        cancel_time=appointment.cancel_time,
        cancel_reason=appointment.cancel_reason,
        symptom_description=appointment.symptom_description,
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
        patient_name=appointment.patient_name,
        patient_phone=appointment.patient_phone,
        doctor_id=appointment.doctor_id,
        doctor_name=appointment.doctor_name,
        doctor_title=appointment.doctor_title,
        department_name=appointment.department_name,
        schedule_id=appointment.schedule_id,
        schedule_date=appointment.schedule.schedule_date if appointment.schedule else None,
        time_slot=appointment.schedule.time_slot if appointment.schedule else None,
        start_time=appointment.schedule.start_time if appointment.schedule else None,
        end_time=appointment.schedule.end_time if appointment.schedule else None,
        queue_number=appointment.queue_number,
        status=appointment.status,
        sign_in_time=appointment.sign_in_time,
        symptom_description=appointment.symptom_description,
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
async def sign_in_appointment(
    appointment_id: str,
    checkin_method: Optional[str] = Body(None, embed=True),
    device_info: Optional[str] = Body(None, embed=True),
    location_info: Optional[str] = Body(None, embed=True),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user_or_admin)
):
    """签到"""
    service = AppointmentService(db)

    # 提取设备信息（从请求头）
    if not device_info:
        # 可以从请求头获取用户代理等信息
        device_info = current_user.get("user_agent")

    try:
        appointment = await service.sign_in(
            appointment_id=appointment_id,
            checkin_method=checkin_method or 'MANUAL',
            device_info=device_info,
            location_info=location_info,
            operator_id=current_user.get("id"),
            operator_type='ADMIN' if current_user.get("is_admin") else 'USER'
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    if not appointment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="预约不存在，请检查后重试")

    return {"message": "签到成功", "queue_number": appointment.queue_number}


@router.put("/{appointment_id}/cancel-sign-in")
async def cancel_sign_in_appointment(
    appointment_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_super_admin)
):
    """取消签到（仅超级管理员）
    
    将状态从"已签到"恢复为"已预约"
    """
    service = AppointmentService(db)
    
    try:
        appointment = await service.cancel_sign_in(appointment_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    
    if not appointment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="预约不存在，请检查后重试")
    
    return {"message": "取消签到成功"}


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
