"""预约查询相关端点"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from datetime import date, datetime
import pytz

from app.db.session import get_db
from app.api.deps import get_current_user, get_current_user_or_admin, get_store_filter, get_current_admin
from app.schemas.appointment import AppointmentResponse, AppointmentStatistics
from app.schemas.response import PageResponse, ErrorResponse
from app.modules.appointments.service import AppointmentService
from app.modules.rule_engine import RuleEngineService
from app.core.config import settings


# 常规分页上限（超过此值需要管理员权限+日期范围）
PAGE_SIZE_STANDARD_LIMIT = 100

router = APIRouter()


@router.get(
    "",
    response_model=PageResponse[AppointmentResponse],
    summary="获取预约列表",
    description="""
    获取当前租户下的预约列表，支持分页和多条件筛选。

    **支持筛选条件**：
    - status: 按状态筛选（1=已预约 2=已签到 3=叫号中 4=就诊中 5=已完成 6=已取消 7=已过期 8=已爽约 9=过号）
    - doctor_id: 按医生筛选
    - department_id: 按科室筛选
    - patient_id: 按患者筛选
    - store_id: 按门店筛选
    - start_date / end_date: 按排班日期范围筛选
    - created_start / created_end: 按创建时间范围筛选
    - keyword: 关键字搜索（预约编号/患者姓名/手机号）

    **分页规则**：
    - 默认 page_size=10，常规上限 100
    - page_size > 100 时需要管理员权限，且必须提供 start_date 和 end_date

    **数据隔离**：
    - 管理员可查看所有预约（门店管理员仅查看本门店）
    - 普通用户只能查看自己的预约
    """,
)
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
    page_size: int = Query(10, ge=1, le=settings.APPOINTMENTS_MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user_or_admin)
):
    """获取预约列表

    分页规则：
    - 默认 page_size=10
    - 常规上限为 100
    - 当 page_size > 100 时，需要管理员权限且必须提供 start_date 和 end_date

    Args:
        keyword: 关键字搜索（预约编号/患者姓名/手机号）
        doctor_id: 医生ID
        department_id: 科室ID
        created_start: 创建时间开始
        created_end: 创建时间结束
    """
    # 分页参数校验：超过100需要管理员权限+日期范围
    if page_size > PAGE_SIZE_STANDARD_LIMIT:
        is_admin = current_user.get("is_admin", False)
        if not is_admin:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "code": "PAGE_SIZE_REQUIRES_ADMIN",
                    "message": f"page_size > {PAGE_SIZE_STANDARD_LIMIT} 需要管理员权限",
                    "hint": f"当前 page_size={page_size}，普通用户上限为 {PAGE_SIZE_STANDARD_LIMIT}"
                }
            )
        if not start_date or not end_date:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "code": "PAGE_SIZE_REQUIRES_DATE_RANGE",
                    "message": f"page_size > {PAGE_SIZE_STANDARD_LIMIT} 必须提供 start_date 和 end_date",
                    "hint": "请提供日期范围以限制查询数据量"
                }
            )

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
        result.append(AppointmentResponse.from_appointment(a))

    return PageResponse(data=result, total=total, page=page, page_size=page_size)


@router.get(
    "/today",
    summary="获取今日预约",
    description="""
    获取当前医生今日的所有预约列表（医生端专用）。

    **业务规则**：
    - 仅返回当前登录医生今日的预约
    - 需要通过 Token 识别医生身份（doctor_id）
    - 每条预约包含 isFollowUp 字段，标记是否为复诊患者

    **返回数据**：
    - 包含患者基本信息、预约编号、排班时间、状态流转时间等
    - 复诊判断基于患者在该医生/科室的历史就诊记录
    """,
)
async def get_today_appointments(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user_or_admin)
):
    """获取今日预约（医生端）

    返回当前医生今日的所有预约，包含复诊判断标记。
    """
    from app.models.doctor import Doctor
    from app.modules.visit_types.service import VisitTypeService

    service = AppointmentService(db)
    # 假设 current_user 包含 doctor_id
    doctor_id = current_user.get("doctor_id")
    if not doctor_id:
        return []

    appointments = await service.get_today_by_doctor(doctor_id)

    # 获取医生信息（用于复诊判断）
    doctor_result = await db.execute(select(Doctor).where(Doctor.id == doctor_id, Doctor.deleted_at.is_(None)))
    doctor = doctor_result.scalar_one_or_none()

    if not doctor:
        return appointments

    # 为每个预约判断是否为复诊
    visit_type_service = VisitTypeService(db)
    result = []
    for a in appointments:
        is_follow_up = False
        if a.patient_id and doctor.store_id and doctor.department_id:
            try:
                is_follow_up = await visit_type_service.is_follow_up_visit(
                    patient_id=a.patient_id,
                    store_id=doctor.store_id,
                    doctor_id=doctor.id,
                    department_id=doctor.department_id,
                )
            except Exception:
                pass

        # 将 ORM 对象转换为字典并添加 isFollowUp 字段
        appointment_dict = {
            "id": a.id,
            "appointmentNo": a.appointment_no,
            "userId": a.user_id,
            "patientId": a.patient_id,
            "patientName": a.patient_name,
            "patientPhone": a.patient_phone,
            "doctorId": a.doctor_id,
            "doctorName": a.doctor_name,
            "doctorTitle": a.doctor_title,
            "departmentName": a.department_name,
            "scheduleId": a.schedule_id,
            "scheduleDate": a.schedule.schedule_date.isoformat() if a.schedule and a.schedule.schedule_date else None,
            "timeSlot": a.schedule.time_slot if a.schedule else None,
            "queueNumber": a.queue_number,
            "status": a.status,
            "signInTime": a.sign_in_time.isoformat() if a.sign_in_time else None,
            "callTime": a.call_time.isoformat() if a.call_time else None,
            "completeTime": a.complete_time.isoformat() if a.complete_time else None,
            "cancelTime": a.cancel_time.isoformat() if a.cancel_time else None,
            "cancelReason": a.cancel_reason,
            "createdAt": a.created_at.isoformat() if a.created_at else None,
            "isFollowUp": is_follow_up,
        }
        result.append(appointment_dict)

    return result


@router.get(
    "/today-pending",
    summary="获取今日待签到预约",
    description="""
    获取当前用户在指定门店的今日待签到预约（患者端专用）。

    **适用场景**：患者扫码签到时选择要签到的预约。

    **参数说明**：
    - store_id: 门店ID（必填），用于筛选该门店下的待签到预约

    **返回数据**：
    - 包含签到状态判断（signInStatus）：available（可签到）/ early（未到时间）/ late（已过时间）/ error（异常）
    - signInMessage: 签到状态对应的提示信息
    - 通过规则引擎计算签到时间窗（checkinOpenAt / checkinCloseAt）
    - minutesUntilOpen / minutesUntilClose: 距离签到开放/截止的剩余分钟数
    """,
)
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

    # 使用本地时区（中国标准时间）
    local_tz = pytz.timezone('Asia/Shanghai')
    now = datetime.now(local_tz)
    result = []

    for a in appointments:
        signInStatus = 'error'  # 默认为错误状态，只有明确允许时才改为可用
        signInMessage = '签到状态异常，请联系工作人员'
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
            except Exception as e:
                # 规则引擎检查失败，记录日志
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f'规则引擎检查签到时间窗失败: {e}')
        else:
            # 没有排班信息，无法判断签到时间窗
            signInStatus = 'error'
            signInMessage = '预约信息不完整，请联系工作人员'

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


@router.get(
    "/queue",
    summary="获取签到队列",
    description="""
    获取当日已签到的患者队列，按签到时间排序。

    **适用场景**：管理后台和医生端查看当日叫号/就诊队列。

    **参数说明**：
    - store_id: 按门店筛选（可选）
    - doctor_id: 按医生筛选（可选，医生端自动取当前医生）
    - target_date: 指定日期（可选，默认今日）

    **业务规则**：
    - 医生端只能查看自己的队列（通过 Token 识别医生身份）
    - 管理员可查看任意医生/门店的队列
    - 返回数据包含签到方式（checkinMethod），如手动签到、扫码签到等
    """,
)
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
    from app.models.rule_set import AppointmentCheckin

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

    # 批量获取签到方式（从签到日志中获取最近一条成功记录）
    appointment_ids = [a.id for a in appointments]
    checkin_methods = {}
    if appointment_ids:
        checkin_result = await db.execute(
            select(AppointmentCheckin.appointment_id, AppointmentCheckin.checkin_method)
            .where(
                AppointmentCheckin.appointment_id.in_(appointment_ids),
                AppointmentCheckin.status == 'SUCCESS'
            )
            .order_by(AppointmentCheckin.checkin_time.desc())
        )
        for row in checkin_result:
            # 只保留最近一条记录
            if row.appointment_id not in checkin_methods:
                checkin_methods[row.appointment_id] = row.checkin_method

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
            "checkinMethod": checkin_methods.get(a.id),
        })

    return result


@router.get(
    "/statistics",
    response_model=AppointmentStatistics,
    summary="获取预约统计",
    description="""
    获取预约统计数据，支持按医生和日期范围筛选。

    **权限要求**：管理员权限。

    **参数说明**：
    - doctor_id: 按医生筛选（可选）
    - start_date / end_date: 日期范围（可选）

    **返回数据**：
    - 各状态的预约数量统计（已预约、已签到、已完成、已取消、已爽约等）
    - 用于管理后台的数据看板
    """,
)
async def get_appointment_statistics(
    doctor_id: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin)
):
    """获取预约统计（需要管理员权限）

    TODO: 添加门店过滤支持
    """
    service = AppointmentService(db)
    return await service.get_statistics(doctor_id=doctor_id, start_date=start_date, end_date=end_date)


@router.get(
    "/check-duplicate",
    summary="检查重复预约",
    description="""
    检查同一患者在同一天同一时段是否已有预约。

    **适用场景**：患者端提交预约前的重复校验，用于前端提醒。

    **参数说明**：
    - schedule_id: 排班ID（必填），用于获取日期和时段信息
    - patient_id: 就诊人ID（必填）

    **返回数据**：
    - hasDuplicate: 是否存在重复预约
    - appointments: 已有预约列表（包含医生、科室、状态等信息）
    """,
)
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


@router.get(
    "/by-no/{appointment_no}",
    response_model=AppointmentResponse,
    summary="按预约号获取详情",
    description="""
    通过预约编号查询预约详情。

    **参数说明**：
    - appointment_no: 预约编号（路径参数，如 AP20240101001）

    **权限规则**：
    - 管理员可查看任意预约
    - 普通用户只能查看自己的预约（通过 user_id 校验）
    """,
)
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

    return AppointmentResponse.from_appointment(appointment)


@router.get(
    "/{appointment_id}",
    response_model=AppointmentResponse,
    summary="获取预约详情",
    description="""
    通过预约ID获取预约详情。

    **参数说明**：
    - appointment_id: 预约记录ID（路径参数）

    **返回数据**：
    - 包含患者、医生、门店、排班等关联信息
    - 包含状态流转时间（签到时间、叫号时间、完成时间、取消时间等）
    """,
    responses={
        404: {"model": ErrorResponse, "description": "预约不存在"},
    }
)
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

    return AppointmentResponse.from_appointment(appointment)


@router.get(
    "/queue/info",
    summary="获取叫号队列信息",
    description="""
    获取当前医生的叫号队列信息（医生端专用）。

    **权限要求**：需要医生身份（Token 中包含 doctor_id）。

    **返回数据**：
    - 当前叫号患者信息
    - 等候队列列表
    - 已完成/已过号数量统计
    """,
)
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
