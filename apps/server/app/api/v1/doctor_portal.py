"""医生端专属 API

此模块提供医生端专属的 API 接口，使用医生 token 进行认证。
所有接口都会自动限制为医生所属门店的数据。
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import Optional, List
from datetime import date, datetime
from pydantic import BaseModel
import json

from app.db.session import get_db
from app.api.deps import get_current_doctor_by_token
from app.models.doctor import Doctor
from app.models.appointment import Appointment
from app.models.rest_day import RestDay
from app.services.appointment_service import AppointmentService
from app.services.schedule_service import ScheduleService
from app.services.visit_type_service import VisitTypeService
from app.core.websocket import (
    notify_doctor,
    WSMessageType,
)

router = APIRouter()


# ========== 响应模型 ==========

class DoctorScheduleResponse(BaseModel):
    """医生排班响应"""
    id: str
    schedule_date: date
    time_slot: str
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    total_slots: int
    booked_slots: int
    status: int
    is_rest_day: Optional[bool] = False  # 是否在休息日（后端计算）
    
    class Config:
        from_attributes = True


class DoctorAppointmentResponse(BaseModel):
    """医生端预约响应"""
    id: str
    appointment_no: str
    patient_id: Optional[str] = None
    patient_name: str
    patient_phone: Optional[str] = None
    schedule_date: Optional[date] = None
    time_slot: Optional[str] = None
    queue_number: Optional[int] = None
    status: int
    sign_in_time: Optional[datetime] = None
    call_time: Optional[datetime] = None
    complete_time: Optional[datetime] = None
    symptom_description: Optional[str] = None
    is_follow_up: bool = False  # 是否为复诊
    
    class Config:
        from_attributes = True


class QueuePatientResponse(BaseModel):
    """叫号队列患者响应"""
    id: str
    appointment_no: str
    queue_number: Optional[int] = None
    patient_name: str
    status: int
    sign_in_time: Optional[datetime] = None
    call_time: Optional[datetime] = None


# ========== 医生信息 ==========

@router.get("/me", summary="获取我的信息")
async def get_my_info(
    doctor: Doctor = Depends(get_current_doctor_by_token),
):
    """获取当前医生信息"""
    return {
        "id": doctor.id,
        "name": doctor.name,
        "phone": doctor.phone,
        "title": doctor.title,
        "avatar": doctor.avatar,
        "store_id": doctor.store_id,
        "store_name": doctor.store.name if doctor.store else None,
        "department_id": doctor.department_id,
        "department_name": doctor.department.name if doctor.department else None,
        "specialty": doctor.specialty,
        "introduction": doctor.introduction,
    }


# ========== 排班管理 ==========

def _check_rest_day_for_schedule(
    schedule_date: date,
    store_id: Optional[str],
    doctor_id: str,
    rest_days: list
) -> bool:
    """检查指定排班是否在休息日"""
    for rd in rest_days:
        # 检查日期是否在休息日范围内
        if not (rd.start_date <= schedule_date <= rd.end_date):
            continue
        # 检查门店是否匹配
        if store_id and rd.store_id != store_id:
            continue
        # 如果 doctor_ids 为空，表示门店所有医生休息
        if rd.doctor_ids is None:
            return True
        # 检查医生是否在休息日列表中
        try:
            doctor_ids_list = json.loads(rd.doctor_ids)
            if doctor_id in doctor_ids_list:
                return True
        except:
            pass
    return False


@router.get("/schedules", response_model=List[DoctorScheduleResponse], summary="获取排班列表")
async def get_my_schedules(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    status: Optional[int] = None,
    doctor: Doctor = Depends(get_current_doctor_by_token),
    db: AsyncSession = Depends(get_db)
):
    """获取当前医生的排班列表
    
    自动限制为当前医生的排班，门店隔离通过 doctor.store_id 实现
    """
    service = ScheduleService(db)
    
    # 默认查询未来7天的排班
    if not start_date:
        start_date = date.today()
    if not end_date:
        from datetime import timedelta
        end_date = start_date + timedelta(days=7)
    
    schedules, _ = await service.get_list(
        doctor_id=doctor.id,
        store_id=doctor.store_id,  # 门店隔离
        start_date=start_date,
        end_date=end_date,
        status=status,
        page=1,
        page_size=100  # 医生端一般不需要分页
    )
    
    # 查询日期范围内的所有有效休息日
    rest_days = []
    if schedules:
        rest_day_result = await db.execute(
            select(RestDay).where(
                and_(
                    RestDay.status == 1,
                    RestDay.start_date <= end_date,
                    RestDay.end_date >= start_date,
                    RestDay.store_id == doctor.store_id
                )
            )
        )
        rest_days = rest_day_result.scalars().all()
    
    return [
        DoctorScheduleResponse(
            id=s.id,
            schedule_date=s.schedule_date,
            time_slot=s.time_slot,
            start_time=s.start_time,
            end_time=s.end_time,
            total_slots=s.total_slots,
            booked_slots=s.booked_slots,
            status=s.status,
            is_rest_day=_check_rest_day_for_schedule(
                s.schedule_date, s.store_id, doctor.id, rest_days
            ),
        )
        for s in schedules
    ]


@router.get("/schedules/today", response_model=List[DoctorScheduleResponse], summary="获取今日排班")
async def get_my_today_schedules(
    doctor: Doctor = Depends(get_current_doctor_by_token),
    db: AsyncSession = Depends(get_db)
):
    """获取当前医生今日排班"""
    today = date.today()
    service = ScheduleService(db)
    
    schedules, _ = await service.get_list(
        doctor_id=doctor.id,
        store_id=doctor.store_id,
        start_date=today,
        end_date=today,
        page=1,
        page_size=10
    )
    
    # 查询今日的休息日
    rest_days = []
    if schedules:
        rest_day_result = await db.execute(
            select(RestDay).where(
                and_(
                    RestDay.status == 1,
                    RestDay.start_date <= today,
                    RestDay.end_date >= today,
                    RestDay.store_id == doctor.store_id
                )
            )
        )
        rest_days = rest_day_result.scalars().all()
    
    return [
        DoctorScheduleResponse(
            id=s.id,
            schedule_date=s.schedule_date,
            time_slot=s.time_slot,
            start_time=s.start_time,
            end_time=s.end_time,
            total_slots=s.total_slots,
            booked_slots=s.booked_slots,
            status=s.status,
            is_rest_day=_check_rest_day_for_schedule(
                s.schedule_date, s.store_id, doctor.id, rest_days
            ),
        )
        for s in schedules
    ]


# ========== 预约管理 ==========

@router.get("/appointments", response_model=List[DoctorAppointmentResponse], summary="获取预约列表")
async def get_my_appointments(
    status: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    doctor: Doctor = Depends(get_current_doctor_by_token),
    db: AsyncSession = Depends(get_db)
):
    """获取当前医生的预约列表
    
    自动限制为当前医生的预约
    """
    service = AppointmentService(db)
    visit_type_service = VisitTypeService(db)
    
    appointments, total = await service.get_list(
        doctor_id=doctor.id,
        status=status,
        start_date=start_date,
        end_date=end_date,
        page=page,
        page_size=page_size
    )
    
    result = []
    for a in appointments:
        # 判断是否为复诊
        is_follow_up = False
        if a.patient_id and doctor.department_id:
            try:
                is_follow_up = await visit_type_service.is_follow_up_visit(
                    patient_id=a.patient_id,
                    store_id=doctor.store_id,
                    doctor_id=doctor.id,
                    department_id=doctor.department_id,
                )
            except Exception:
                pass
        
        result.append(DoctorAppointmentResponse(
            id=a.id,
            appointment_no=a.appointment_no,
            patient_id=a.patient_id,
            patient_name=a.patient_name,
            patient_phone=a.patient_phone,
            schedule_date=a.schedule.schedule_date if a.schedule else None,
            time_slot=a.schedule.time_slot if a.schedule else None,
            queue_number=a.queue_number,
            status=a.status,
            sign_in_time=a.sign_in_time,
            call_time=a.call_time,
            complete_time=a.complete_time,
            symptom_description=a.symptom_description,
            is_follow_up=is_follow_up,
        ))
    
    return result


@router.get("/appointments/today", response_model=List[DoctorAppointmentResponse], summary="获取今日预约")
async def get_my_today_appointments(
    doctor: Doctor = Depends(get_current_doctor_by_token),
    db: AsyncSession = Depends(get_db)
):
    """获取当前医生今日预约"""
    service = AppointmentService(db)
    visit_type_service = VisitTypeService(db)
    appointments = await service.get_today_by_doctor(doctor.id)
    
    result = []
    for a in appointments:
        # 判断是否为复诊
        is_follow_up = False
        if a.patient_id and doctor.department_id:
            try:
                is_follow_up = await visit_type_service.is_follow_up_visit(
                    patient_id=a.patient_id,
                    store_id=doctor.store_id,
                    doctor_id=doctor.id,
                    department_id=doctor.department_id,
                )
            except Exception:
                pass  # 复诊判断失败不影响正常显示
        
        result.append(DoctorAppointmentResponse(
            id=a.id,
            appointment_no=a.appointment_no,
            patient_id=a.patient_id,
            patient_name=a.patient_name,
            patient_phone=a.patient_phone,
            schedule_date=a.schedule.schedule_date if a.schedule else None,
            time_slot=a.schedule.time_slot if a.schedule else None,
            queue_number=a.queue_number,
            status=a.status,
            sign_in_time=a.sign_in_time,
            call_time=a.call_time,
            complete_time=a.complete_time,
            symptom_description=a.symptom_description,
            is_follow_up=is_follow_up,
        ))
    
    return result


# ========== 叫号管理 ==========

@router.get("/queue", response_model=List[QueuePatientResponse], summary="获取叫号队列")
async def get_my_queue(
    target_date: Optional[date] = None,
    doctor: Doctor = Depends(get_current_doctor_by_token),
    db: AsyncSession = Depends(get_db)
):
    """获取当前医生的签到队列
    
    返回已签到等待叫号的患者列表
    """
    service = AppointmentService(db)
    
    if not target_date:
        target_date = date.today()
    
    appointments = await service.get_checkin_queue(
        store_id=doctor.store_id,  # 门店隔离
        doctor_id=doctor.id,       # 只看自己的队列
        target_date=target_date
    )
    
    return [
        QueuePatientResponse(
            id=a.id,
            appointment_no=a.appointment_no,
            queue_number=a.queue_number,
            patient_name=a.patient_name,
            status=a.status,
            sign_in_time=a.sign_in_time,
            call_time=a.call_time,
        )
        for a in appointments
    ]


@router.get("/queue/info", summary="获取队列信息")
async def get_my_queue_info(
    doctor: Doctor = Depends(get_current_doctor_by_token),
    db: AsyncSession = Depends(get_db)
):
    """获取当前医生的叫号队列统计信息"""
    service = AppointmentService(db)
    return await service.get_queue_info(doctor.id)


async def _verify_appointment_ownership(
    appointment_id: str,
    doctor: Doctor,
    db: AsyncSession
) -> Appointment:
    """验证预约是否属于当前医生
    
    Args:
        appointment_id: 预约ID
        doctor: 当前医生
        db: 数据库会话
    
    Returns:
        预约对象
    
    Raises:
        HTTPException: 如果预约不存在或不属于当前医生
    """
    service = AppointmentService(db)
    appointment = await service.get_by_id(appointment_id)
    
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="预约不存在"
        )
    
    # 验证预约属于当前医生
    if appointment.doctor_id != doctor.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="您无权操作此预约"
        )
    
    return appointment


@router.put("/appointments/{appointment_id}/call", summary="叫号")
async def call_patient(
    appointment_id: str,
    doctor: Doctor = Depends(get_current_doctor_by_token),
    db: AsyncSession = Depends(get_db)
):
    """叫号 - 只能叫自己的患者"""
    # 验证预约属于当前医生
    await _verify_appointment_ownership(appointment_id, doctor, db)
    
    service = AppointmentService(db)
    
    try:
        appointment = await service.call_patient(appointment_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    
    # 发送 WebSocket 通知
    try:
        await notify_doctor(
            doctor_id=doctor.id,
            message_type=WSMessageType.PATIENT_CALLED,
            data={
                "appointment_id": appointment.id,
                "patient_name": appointment.patient_name,
                "queue_number": appointment.queue_number,
            }
        )
    except Exception:
        pass  # WebSocket 通知失败不影响业务
    
    return {"message": "已呼叫", "queue_number": appointment.queue_number}


@router.put("/appointments/{appointment_id}/complete", summary="完成就诊")
async def complete_consultation(
    appointment_id: str,
    doctor: Doctor = Depends(get_current_doctor_by_token),
    db: AsyncSession = Depends(get_db)
):
    """完成就诊 - 只能操作自己的患者"""
    # 验证预约属于当前医生
    await _verify_appointment_ownership(appointment_id, doctor, db)
    
    service = AppointmentService(db)
    appointment = await service.complete(appointment_id)
    
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="预约不存在"
        )
    
    # 发送 WebSocket 通知
    try:
        await notify_doctor(
            doctor_id=doctor.id,
            message_type=WSMessageType.PATIENT_COMPLETED,
            data={
                "appointment_id": appointment.id,
                "patient_name": appointment.patient_name,
                "queue_number": appointment.queue_number,
            }
        )
    except Exception:
        pass
    
    return {"message": "就诊完成"}


@router.put("/appointments/{appointment_id}/pass", summary="过号")
async def pass_patient(
    appointment_id: str,
    doctor: Doctor = Depends(get_current_doctor_by_token),
    db: AsyncSession = Depends(get_db)
):
    """过号 - 只能操作自己的患者"""
    # 验证预约属于当前医生
    await _verify_appointment_ownership(appointment_id, doctor, db)
    
    service = AppointmentService(db)
    
    try:
        appointment = await service.pass_number(appointment_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    
    # 发送 WebSocket 通知
    try:
        await notify_doctor(
            doctor_id=doctor.id,
            message_type=WSMessageType.PATIENT_PASSED,
            data={
                "appointment_id": appointment.id,
                "patient_name": appointment.patient_name,
                "queue_number": appointment.queue_number,
            }
        )
    except Exception:
        pass
    
    return {"message": "已过号"}


@router.put("/appointments/{appointment_id}/recall", summary="重新叫号")
async def recall_patient(
    appointment_id: str,
    doctor: Doctor = Depends(get_current_doctor_by_token),
    db: AsyncSession = Depends(get_db)
):
    """重新叫号 - 只能操作自己的患者"""
    # 验证预约属于当前医生
    await _verify_appointment_ownership(appointment_id, doctor, db)
    
    service = AppointmentService(db)
    
    try:
        appointment = await service.recall(appointment_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    
    # 发送 WebSocket 通知
    try:
        await notify_doctor(
            doctor_id=doctor.id,
            message_type=WSMessageType.PATIENT_RECALLED,
            data={
                "appointment_id": appointment.id,
                "patient_name": appointment.patient_name,
                "queue_number": appointment.queue_number,
            }
        )
    except Exception:
        pass
    
    return {"message": "已重新呼叫"}


@router.put("/appointments/{appointment_id}/no-show", summary="标记爽约")
async def mark_patient_no_show(
    appointment_id: str,
    doctor: Doctor = Depends(get_current_doctor_by_token),
    db: AsyncSession = Depends(get_db)
):
    """标记爽约 - 只能操作自己的患者"""
    # 验证预约属于当前医生
    await _verify_appointment_ownership(appointment_id, doctor, db)
    
    service = AppointmentService(db)
    
    try:
        appointment = await service.mark_no_show(appointment_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    
    # 发送 WebSocket 通知
    try:
        await notify_doctor(
            doctor_id=doctor.id,
            message_type=WSMessageType.PATIENT_NO_SHOW,
            data={
                "appointment_id": appointment.id,
                "patient_name": appointment.patient_name,
                "queue_number": appointment.queue_number,
            }
        )
    except Exception:
        pass
    
    return {"message": "已标记爽约"}


# ========== 统计信息 ==========

@router.get("/statistics/today", summary="获取今日统计")
async def get_my_today_statistics(
    doctor: Doctor = Depends(get_current_doctor_by_token),
    db: AsyncSession = Depends(get_db)
):
    """获取当前医生今日统计数据"""
    service = AppointmentService(db)
    today = date.today()
    
    stats = await service.get_statistics(
        doctor_id=doctor.id,
        start_date=today,
        end_date=today
    )
    
    return {
        "total": stats.total,
        "pending": stats.pending,
        "signed_in": stats.signed_in,
        "in_progress": stats.in_progress,
        "completed": stats.completed,
        "cancelled": stats.cancelled,
        "no_show": stats.no_show,
    }


# ========== 患者历史记录 ==========

class PatientHistoryResponse(BaseModel):
    """患者历史就诊记录响应"""
    id: str
    appointment_no: str
    schedule_date: Optional[date] = None
    time_slot: Optional[str] = None
    status: int
    complete_time: Optional[datetime] = None
    symptom_description: Optional[str] = None
    has_medical_record: bool = False  # 是否有病历
    
    class Config:
        from_attributes = True


@router.get("/patients/{patient_id}/appointments", summary="获取患者历史")
async def get_patient_history(
    patient_id: str,
    status: Optional[int] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    doctor: Doctor = Depends(get_current_doctor_by_token),
    db: AsyncSession = Depends(get_db)
):
    """获取患者在当前医生处的历史就诊记录
    
    只返回该患者在当前医生处的历史预约，用于医生查看患者就诊历史。
    """
    service = AppointmentService(db)
    
    # 只查询该患者在当前医生处的预约
    appointments, total = await service.get_list(
        patient_id=patient_id,
        doctor_id=doctor.id,
        status=status,
        page=page,
        page_size=page_size
    )
    
    # 查询病历记录（判断是否有病历）
    from app.models.medical_record import MedicalRecord
    appointment_ids = [a.id for a in appointments]
    medical_records = {}
    if appointment_ids:
        result = await db.execute(
            select(MedicalRecord.appointment_id).where(
                MedicalRecord.appointment_id.in_(appointment_ids)
            )
        )
        medical_records = {row[0]: True for row in result.fetchall()}
    
    return {
        "items": [
            PatientHistoryResponse(
                id=a.id,
                appointment_no=a.appointment_no,
                schedule_date=a.schedule.schedule_date if a.schedule else None,
                time_slot=a.schedule.time_slot if a.schedule else None,
                status=a.status,
                complete_time=a.complete_time,
                symptom_description=a.symptom_description,
                has_medical_record=medical_records.get(a.id, False),
            )
            for a in appointments
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


# ========== 快速复诊预约 ==========

class FollowUpBookingRequest(BaseModel):
    """快速复诊预约请求"""
    schedule_id: str


@router.post("/appointments/{appointment_id}/follow-up", summary="创建复诊预约")
async def create_follow_up_booking(
    appointment_id: str,
    request: FollowUpBookingRequest,
    doctor: Doctor = Depends(get_current_doctor_by_token),
    db: AsyncSession = Depends(get_db)
):
    """为患者创建复诊预约
    
    基于原预约的患者信息，在指定排班下创建新的预约。
    原预约必须属于当前医生且已完成。
    """
    # 验证原预约属于当前医生
    original = await _verify_appointment_ownership(appointment_id, doctor, db)
    
    # 验证原预约已完成
    if original.status != 5:  # COMPLETED
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="只能为已完成的预约创建复诊"
        )
    
    service = AppointmentService(db)
    
    try:
        # 创建新预约
        new_appointment = await service.create(
            user_id=original.user_id,
            patient_id=original.patient_id,
            schedule_id=request.schedule_id,
            symptom_description=f"复诊（原预约号：{original.appointment_no}）",
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    
    return {
        "message": "复诊预约创建成功",
        "appointment_id": new_appointment.id,
        "appointment_no": new_appointment.appointment_no,
    }
