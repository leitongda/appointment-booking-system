from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload
from typing import Optional, List
from datetime import datetime, date, time, timedelta
import uuid

from app.models.appointment import Appointment
from app.models.schedule import Schedule
from app.models.user import Patient
from app.models.doctor import Doctor
from app.models.rule_set import AppointmentCheckin
from app.schemas.appointment import AppointmentCreate, AppointmentStatistics
from app.utils.audit import set_create_audit, set_update_audit
from app.services.settings_service import SettingsService
from app.services.rule_engine_service import RuleEngineService

# 预约状态 - 与前端共享常量保持一致
APPOINTMENT_STATUS = {
    'PENDING': 0,      # 待支付
    'CONFIRMED': 1,    # 已预约
    'SIGNED': 2,       # 已签到
    'WAITING': 3,      # 候诊中
    'SEEING': 4,       # 就诊中
    'COMPLETED': 5,    # 已完成
    'CANCELLED': 6,    # 已取消
    'EXPIRED': 7,      # 已过期
    'CLOSED': 8        # 已关闭
}

class AppointmentService:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_by_id(self, appointment_id: str) -> Optional[Appointment]:
        result = await self.db.execute(
            select(Appointment)
            .options(selectinload(Appointment.schedule))
            .where(Appointment.id == appointment_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_appointment_no(self, appointment_no: str) -> Optional[Appointment]:
        """按预约号获取预约"""
        result = await self.db.execute(
            select(Appointment)
            .options(selectinload(Appointment.schedule))
            .where(Appointment.appointment_no == appointment_no)
        )
        return result.scalar_one_or_none()
    
    async def get_list(
        self,
        user_id: Optional[str] = None,
        doctor_id: Optional[str] = None,
        patient_id: Optional[str] = None,
        store_id: Optional[str] = None,
        status: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        keyword: Optional[str] = None,
        department_id: Optional[str] = None,
        created_start: Optional[datetime] = None,
        created_end: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 10
    ) -> tuple[List[Appointment], int]:
        """获取预约列表
        
        Args:
            keyword: 关键字搜索（预约编号/患者姓名/手机号）
            department_id: 科室ID（通过科室名称匹配）
            created_start: 创建时间开始
            created_end: 创建时间结束
        """
        query = select(Appointment).options(selectinload(Appointment.schedule))
        count_query = select(func.count(Appointment.id))
        
        # 标记是否已经 join 了 Schedule 表
        schedule_joined = False
        
        if user_id:
            query = query.where(Appointment.user_id == user_id)
            count_query = count_query.where(Appointment.user_id == user_id)
        if doctor_id:
            query = query.where(Appointment.doctor_id == doctor_id)
            count_query = count_query.where(Appointment.doctor_id == doctor_id)
        if patient_id:
            query = query.where(Appointment.patient_id == patient_id)
            count_query = count_query.where(Appointment.patient_id == patient_id)
        if store_id:
            # 通过关联的 Schedule 表的 store_id 进行过滤
            if not schedule_joined:
                query = query.join(Schedule)
                count_query = count_query.join(Schedule)
                schedule_joined = True
            query = query.where(Schedule.store_id == store_id)
            count_query = count_query.where(Schedule.store_id == store_id)
        if status is not None:
            query = query.where(Appointment.status == status)
            count_query = count_query.where(Appointment.status == status)
        
        # 关键字搜索（预约编号/患者姓名/手机号）
        if keyword:
            keyword_filter = or_(
                Appointment.appointment_no.ilike(f'%{keyword}%'),
                Appointment.patient_name.ilike(f'%{keyword}%'),
                Appointment.patient_phone.ilike(f'%{keyword}%')
            )
            query = query.where(keyword_filter)
            count_query = count_query.where(keyword_filter)
        
        # 科室过滤（通过科室名称匹配，因为 Appointment 只有 department_name 快照）
        if department_id:
            # 需要查询科室名称，然后用名称匹配
            from app.models.department import Department
            dept_result = await self.db.execute(
                select(Department.name).where(Department.id == department_id)
            )
            dept_name = dept_result.scalar_one_or_none()
            if dept_name:
                query = query.where(Appointment.department_name == dept_name)
                count_query = count_query.where(Appointment.department_name == dept_name)
        
        # 预约日期范围过滤（通过 Schedule.schedule_date）
        if start_date or end_date:
            if not schedule_joined:
                query = query.join(Schedule)
                count_query = count_query.join(Schedule)
                schedule_joined = True
            if start_date:
                query = query.where(Schedule.schedule_date >= start_date)
                count_query = count_query.where(Schedule.schedule_date >= start_date)
            if end_date:
                query = query.where(Schedule.schedule_date <= end_date)
                count_query = count_query.where(Schedule.schedule_date <= end_date)
        
        # 创建时间范围过滤
        if created_start:
            query = query.where(Appointment.created_at >= created_start)
            count_query = count_query.where(Appointment.created_at >= created_start)
        if created_end:
            query = query.where(Appointment.created_at <= created_end)
            count_query = count_query.where(Appointment.created_at <= created_end)
        
        query = query.order_by(Appointment.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        
        result = await self.db.execute(query)
        count_result = await self.db.execute(count_query)
        
        return list(result.scalars().all()), count_result.scalar() or 0
    
    async def get_today_by_doctor(self, doctor_id: str) -> List[Appointment]:
        """获取医生今日预约"""
        today = date.today()
        
        result = await self.db.execute(
            select(Appointment)
            .join(Schedule)
            .where(
                and_(
                    Appointment.doctor_id == doctor_id,
                    Schedule.schedule_date == today,
                    # 已预约、已签到、候诊中、就诊中
                    Appointment.status.in_([
                        APPOINTMENT_STATUS['CONFIRMED'],
                        APPOINTMENT_STATUS['SIGNED'],
                        APPOINTMENT_STATUS['WAITING'],
                        APPOINTMENT_STATUS['SEEING']
                    ])
                )
            )
            .order_by(Appointment.queue_number)
        )
        return list(result.scalars().all())
    
    async def get_statistics(self, doctor_id: Optional[str] = None, start_date: Optional[date] = None, end_date: Optional[date] = None) -> AppointmentStatistics:
        """获取预约统计"""
        base_query = select(Appointment.status, func.count(Appointment.id))
        
        if doctor_id:
            base_query = base_query.where(Appointment.doctor_id == doctor_id)
        
        base_query = base_query.group_by(Appointment.status)
        
        result = await self.db.execute(base_query)
        status_counts = dict(result.all())
        
        return AppointmentStatistics(
            total=sum(status_counts.values()),
            pending=status_counts.get(1, 0),
            signed_in=status_counts.get(2, 0),
            in_progress=status_counts.get(3, 0),
            completed=status_counts.get(5, 0),
            cancelled=status_counts.get(6, 0),
            no_show=status_counts.get(7, 0)
        )
    
    async def create(self, user_id: str, data: AppointmentCreate, operator_id: Optional[str] = None) -> Appointment:
        # 获取排班信息（包含医生和科室信息，用于快照）
        schedule_result = await self.db.execute(
            select(Schedule)
            .options(selectinload(Schedule.doctor).selectinload(Doctor.department))
            .where(Schedule.id == data.schedule_id)
        )
        schedule = schedule_result.scalar_one_or_none()

        if not schedule:
            raise ValueError("排班不存在")
        if schedule.status != 1:
            raise ValueError("该排班已停诊")
        if schedule.booked_slots >= schedule.total_slots:
            raise ValueError("号源已满")

        # 获取门店配置
        settings_service = SettingsService(self.db)
        store_id = schedule.store_id

        # 规则引擎集成 - 检查预约时间窗
        rule_engine = RuleEngineService(self.db)
        book_result = await rule_engine.check_action_window(schedule, 'BOOK')

        # 如果规则引擎返回不允许且失败策略是 REJECT，则拒绝预约
        if not book_result['allowed'] and book_result['fail_policy'] == 'REJECT':
            raise ValueError(book_result['message'])

        # 获取签到和取消时间窗信息（用于快照）
        checkin_result = await rule_engine.check_action_window(schedule, 'CHECKIN')
        cancel_result = await rule_engine.check_action_window(schedule, 'CANCEL')

        # 获取规则组ID和预约策略
        rule_set = None
        booking_policy = None
        capacity_policy = None

        if schedule.shift_type_id:
            rule_set = await rule_engine.get_applicable_rule_set(schedule.shift_type_id)
            if rule_set:
                booking_policy = await rule_engine.get_booking_policy(schedule.shift_type_id)
                capacity_policy = await rule_engine.get_capacity_policy(schedule.shift_type_id)

        # ========== 规则引擎验证（优先使用规则组配置） ==========

        # 验证1：预约策略 - 检查预约冲突
        if booking_policy:
            conflict_result = await rule_engine.check_booking_conflicts(
                db=self.db,
                shift_id=data.schedule_id,
                user_id=user_id,
                policy=booking_policy,
                booking_time=datetime.now()
            )
            if not conflict_result['allowed']:
                raise ValueError(conflict_result['reason'])

        # 验证2：容量策略 - 检查容量限制
        if capacity_policy:
            capacity_result = await rule_engine.check_capacity_limits(
                db=self.db,
                shift_id=data.schedule_id,
                user_id=user_id,
                policy=capacity_policy
            )
            if not capacity_result['allowed']:
                # 如果候补位置存在，可以提示用户候补（未来功能）
                raise ValueError(capacity_result['reason'])

        # ========== 兼容旧配置：没有规则组时使用门店配置 ==========

        # 验证3：预约日期范围（仅当没有规则组时使用）
        if not rule_set:
            advance_days = await settings_service.get_value('booking', 'advance_days', 10, store_id=store_id)
            max_date = date.today() + timedelta(days=advance_days)
            if schedule.schedule_date > max_date:
                raise ValueError(f"预约日期不能超过{advance_days}天")

            # 验证4：同用户同门店单日预约次数限制（仅当没有规则组时使用）
            per_day_limit = await settings_service.get_value('booking', 'per_day_limit', 3, store_id=store_id)
            today_count = await self._count_user_store_daily_appointments(
                user_id, store_id, schedule.schedule_date
            )
            if today_count >= per_day_limit:
                raise ValueError(f"当日预约已达上限（最多{per_day_limit}次）")

        # 验证就诊人
        patient_result = await self.db.execute(
            select(Patient).where(Patient.id == data.patient_id, Patient.user_id == user_id)
        )
        patient = patient_result.scalar_one_or_none()
        if not patient:
            raise ValueError("就诊人不存在")
        
        # 检查是否重复预约
        existing = await self.db.execute(
            select(Appointment).where(
                and_(
                    Appointment.patient_id == data.patient_id,
                    Appointment.schedule_id == data.schedule_id,
                    # 已预约、已签到、候诊中
                    Appointment.status.in_([
                        APPOINTMENT_STATUS['CONFIRMED'],
                        APPOINTMENT_STATUS['SIGNED'],
                        APPOINTMENT_STATUS['WAITING']
                    ])
                )
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError("该就诊人已预约此时段")
        
        # 生成预约号
        appointment_no = f"YY{datetime.now().strftime('%Y%m%d%H%M%S')}{str(uuid.uuid4())[:4].upper()}"
        
        # 获取队列号
        queue_result = await self.db.execute(
            select(func.max(Appointment.queue_number)).where(Appointment.schedule_id == data.schedule_id)
        )
        max_queue = queue_result.scalar() or 0
        queue_number = max_queue + 1
        
        # 创建预约（包含快照信息）
        doctor = schedule.doctor
        appointment = Appointment(
            id=str(uuid.uuid4()),
            appointment_no=appointment_no,
            user_id=user_id,
            patient_id=data.patient_id,
            doctor_id=schedule.doctor_id,
            schedule_id=data.schedule_id,
            queue_number=queue_number,
            status=APPOINTMENT_STATUS['CONFIRMED'],
            symptom_description=data.symptom_description,
            # 就诊人快照信息
            patient_name=patient.name,
            patient_phone=patient.phone,
            # 医生快照信息
            doctor_name=doctor.name if doctor else None,
            doctor_title=doctor.title if doctor else None,
            department_name=doctor.department.name if doctor and doctor.department else None,
            # 规则快照信息
            rule_set_id=rule_set.id if rule_set else None,
            book_open_at=book_result['open_at'],
            book_close_at=book_result['close_at'],
            checkin_open_at=checkin_result['open_at'],
            checkin_close_at=checkin_result['close_at'],
            cancel_open_at=cancel_result['open_at'],
            cancel_close_at=cancel_result['close_at'],
            checkin_count=0,
        )
        # 设置创建人（如果是用户自己创建，使用 user_id；如果是管理员创建，使用 operator_id）
        set_create_audit(appointment, operator_id or user_id)
        self.db.add(appointment)
        
        # 更新排班已预约数
        schedule.booked_slots += 1
        
        await self.db.commit()
        await self.db.refresh(appointment)
        
        # 设置 schedule 关联，以便 API 层可以访问排班信息
        appointment.schedule = schedule
        
        return appointment
    
    async def cancel(self, appointment_id: str, user_id: str, reason: Optional[str] = None, is_admin: bool = False, operator_id: Optional[str] = None) -> Optional[Appointment]:
        """取消预约"""
        appointment = await self.get_by_id(appointment_id)
        if not appointment:
            return None

        # 非管理员只能取消自己的预约
        if not is_admin and appointment.user_id != user_id:
            return None

        # 只有已预约或已签到状态可以取消
        if appointment.status not in [APPOINTMENT_STATUS['CONFIRMED'], APPOINTMENT_STATUS['SIGNED']]:
            raise ValueError("当前状态不可取消")

        # 非管理员需要检查取消时间限制
        if not is_admin:
            now = datetime.now()

            # 优先使用规则快照中的取消时间窗
            if appointment.cancel_open_at and appointment.cancel_close_at:
                if now < appointment.cancel_open_at:
                    raise ValueError("未到取消时间窗口")
                if now > appointment.cancel_close_at:
                    raise ValueError("已过取消时间窗口，无法取消预约")
            else:
                # 兼容旧数据：使用门店配置
                settings_service = SettingsService(self.db)
                cancel_hours = await settings_service.get_value('booking', 'cancel_hours', 2)

                schedule = appointment.schedule
                if schedule and cancel_hours > 0:
                    # 计算就诊时间
                    if schedule.start_time:
                        visit_time = schedule.start_time
                    else:
                        time_slot_start_map = {
                            'AM': time(8, 0),
                            'PM': time(14, 0),
                            'morning': time(8, 0),
                            'afternoon': time(14, 0),
                            'evening': time(18, 0),
                            'NIGHT': time(18, 0),
                        }
                        visit_time = time_slot_start_map.get(schedule.time_slot, time(8, 0))

                    visit_datetime = datetime.combine(schedule.schedule_date, visit_time)
                    cancel_deadline = visit_datetime - timedelta(hours=cancel_hours)

                    if now > cancel_deadline:
                        raise ValueError(f"就诊前{cancel_hours}小时内不可取消预约")
        
        appointment.status = APPOINTMENT_STATUS['CANCELLED']
        appointment.cancel_time = datetime.now()
        appointment.cancel_reason = reason
        set_update_audit(appointment, operator_id or user_id)

        # 恢复号源
        schedule = appointment.schedule
        if schedule:
            schedule.booked_slots = max(0, schedule.booked_slots - 1)

        await self.db.commit()

        # 候补队列自动递补
        if schedule:
            try:
                from app.services.waitlist_service import WaitlistService
                waitlist_service = WaitlistService(self.db)
                await waitlist_service.auto_promote(
                    schedule_id=appointment.schedule_id,
                    reason='APPOINTMENT_CANCELLED'
                )
            except Exception as e:
                # 候补递补失败不影响取消操作
                print(f'候补自动递补失败: {e}')

        await self.db.refresh(appointment)
        return appointment
    
    async def sign_in(
        self,
        appointment_id: str,
        checkin_method: str = 'MANUAL',
        device_info: Optional[str] = None,
        location_info: Optional[str] = None,
        operator_id: Optional[str] = None,
        operator_type: Optional[str] = None
    ) -> Optional[Appointment]:
        """签到（带审计日志）

        Args:
            appointment_id: 预约ID
            checkin_method: 签到方式 (QR_CODE/MANUAL/PHONE)
            device_info: 设备信息（用户代理等）
            location_info: 位置信息（IP地址等）
            operator_id: 操作人ID
            operator_type: 操作人类型 (USER/ADMIN/DOCTOR)
        """
        appointment = await self.get_by_id(appointment_id)
        if not appointment:
            # 记录失败日志：预约不存在
            await self._create_checkin_log(
                appointment_id=None,
                checkin_method=checkin_method,
                device_info=device_info,
                location_info=location_info,
                operator_id=operator_id,
                operator_type=operator_type,
                status='FAILED',
                fail_reason='预约不存在'
            )
            return None

        try:
            # 验证预约状态
            if appointment.status != APPOINTMENT_STATUS['CONFIRMED']:
                raise ValueError("当前状态不可签到")

            now = datetime.now()

            # 优先使用规则快照中的签到时间窗
            if appointment.checkin_open_at and appointment.checkin_close_at:
                if now < appointment.checkin_open_at:
                    minutes_until = int((appointment.checkin_open_at - now).total_seconds() / 60)
                    raise ValueError(f"未到签到时间，请等待{minutes_until}分钟后再试")
                if now > appointment.checkin_close_at:
                    raise ValueError("已过签到时间，无法签到")
            else:
                # 兼容旧数据：使用门店配置
                stmt = select(Schedule).where(Schedule.id == appointment.schedule_id)
                result = await self.db.execute(stmt)
                schedule = result.scalar_one_or_none()

                if schedule:
                    settings_service = SettingsService(self.db)
                    settings = await settings_service.get_booking_settings(store_id=schedule.store_id)

                    sign_in_advance_minutes = settings.get('signInAdvanceMinutes', 30)
                    sign_in_late_minutes = settings.get('signInLateMinutes', 30)

                    if schedule.start_time:
                        visit_time = schedule.start_time
                    else:
                        time_slot_start_map = {
                            'AM': time(8, 0),
                            'PM': time(14, 0),
                            'morning': time(8, 0),
                            'afternoon': time(14, 0),
                            'evening': time(18, 0),
                            'NIGHT': time(18, 0),
                        }
                        visit_time = time_slot_start_map.get(schedule.time_slot, time(8, 0))

                    visit_datetime = datetime.combine(schedule.schedule_date, visit_time)
                    sign_in_start = visit_datetime - timedelta(minutes=sign_in_advance_minutes)
                    sign_in_end = visit_datetime + timedelta(minutes=sign_in_late_minutes)

                    if now < sign_in_start:
                        minutes_until = int((sign_in_start - now).total_seconds() / 60)
                        raise ValueError(f"未到签到时间，请等待{minutes_until}分钟后再试")

                    if now > sign_in_end:
                        raise ValueError("已过签到时间，无法签到")

            # 检查签到策略：签到次数限制
            if appointment.rule_set_id:
                rule_engine = RuleEngineService(self.db)
                checkin_policy = await rule_engine.get_checkin_policy_by_rule_set_id(appointment.rule_set_id)
                if checkin_policy and checkin_policy.max_times:
                    current_count = appointment.checkin_count or 0
                    if current_count >= checkin_policy.max_times:
                        raise ValueError(f"已达到最大签到次数限制（{checkin_policy.max_times}次）")

                # 计算宽限期
                if checkin_policy:
                    grace_result = rule_engine.calculate_checkin_grace_period(
                        appointment=appointment,
                        policy=checkin_policy,
                        current_time=now
                    )

                    # 虽然超过宽限期，但只要在签到窗口内仍可签到
                    # 宽限期影响签到状态标记（准时/迟到）
                    if grace_result['is_late']:
                        # 可以签到，但标记为迟到
                        pass  # 未来可以添加迟到标记字段

            # 更新预约状态
            appointment.status = APPOINTMENT_STATUS['SIGNED']
            appointment.sign_in_time = now
            # 更新签到次数
            appointment.checkin_count = (appointment.checkin_count or 0) + 1

            # 记录成功审计日志
            await self._create_checkin_log(
                appointment_id=appointment.id,
                checkin_method=checkin_method,
                device_info=device_info,
                location_info=location_info,
                operator_id=operator_id,
                operator_type=operator_type,
                status='SUCCESS',
                fail_reason=None
            )

            await self.db.commit()
            await self.db.refresh(appointment)
            return appointment

        except Exception as e:
            # 记录失败审计日志
            await self._create_checkin_log(
                appointment_id=appointment.id if appointment else None,
                checkin_method=checkin_method,
                device_info=device_info,
                location_info=location_info,
                operator_id=operator_id,
                operator_type=operator_type,
                status='FAILED',
                fail_reason=str(e)
            )
            raise

    async def _create_checkin_log(
        self,
        appointment_id: Optional[str],
        checkin_method: str,
        device_info: Optional[str],
        location_info: Optional[str],
        operator_id: Optional[str],
        operator_type: Optional[str],
        status: str,
        fail_reason: Optional[str]
    ):
        """创建签到审计日志

        Args:
            appointment_id: 预约ID（失败时可能为None）
            checkin_method: 签到方式
            device_info: 设备信息
            location_info: 位置信息
            operator_id: 操作人ID
            operator_type: 操作人类型
            status: 状态 (SUCCESS/FAILED)
            fail_reason: 失败原因
        """
        checkin_log = AppointmentCheckin(
            appointment_id=appointment_id,
            checkin_method=checkin_method,
            device_info=device_info,
            location_info=location_info,
            operator_id=operator_id,
            operator_type=operator_type,
            status=status,
            fail_reason=fail_reason
        )
        self.db.add(checkin_log)
        await self.db.flush()  # 立即写入，但不提交事务

    async def cancel_sign_in(self, appointment_id: str) -> Optional[Appointment]:
        """取消签到（将状态从已签到恢复为已预约）
        
        仅超级管理员可调用
        """
        appointment = await self.get_by_id(appointment_id)
        if not appointment:
            return None
        
        if appointment.status != APPOINTMENT_STATUS['SIGNED']:
            raise ValueError("只有已签到状态的预约才能取消签到")
        
        appointment.status = APPOINTMENT_STATUS['CONFIRMED']
        appointment.sign_in_time = None
        
        await self.db.commit()
        await self.db.refresh(appointment)
        return appointment
    
    async def call_patient(self, appointment_id: str) -> Optional[Appointment]:
        """叫号"""
        appointment = await self.get_by_id(appointment_id)
        if not appointment:
            return None
        
        if appointment.status != APPOINTMENT_STATUS['SIGNED']:
            raise ValueError("患者未签到")
        
        appointment.status = APPOINTMENT_STATUS['SEEING']
        appointment.call_time = datetime.now()
        
        await self.db.commit()
        await self.db.refresh(appointment)
        return appointment
    
    async def complete(self, appointment_id: str) -> Optional[Appointment]:
        """完成就诊"""
        appointment = await self.get_by_id(appointment_id)
        if not appointment:
            return None
        
        appointment.status = APPOINTMENT_STATUS['COMPLETED']
        appointment.complete_time = datetime.now()
        
        await self.db.commit()
        await self.db.refresh(appointment)
        return appointment

    async def pass_number(self, appointment_id: str) -> Optional[Appointment]:
        """过号（患者未到，跳过）"""
        appointment = await self.get_by_id(appointment_id)
        if not appointment:
            return None
        
        if appointment.status not in [APPOINTMENT_STATUS['SIGNED'], APPOINTMENT_STATUS['SEEING']]:
            raise ValueError("当前状态不可过号")
        
        appointment.status = APPOINTMENT_STATUS['EXPIRED']  # 使用 EXPIRED 表示已过号
        
        await self.db.commit()
        await self.db.refresh(appointment)
        return appointment

    async def recall(self, appointment_id: str) -> Optional[Appointment]:
        """重新叫号（过号后再次呼叫）"""
        appointment = await self.get_by_id(appointment_id)
        if not appointment:
            return None
        
        if appointment.status != APPOINTMENT_STATUS['EXPIRED']:
            raise ValueError("只有过号状态可以重新叫号")
        
        appointment.status = APPOINTMENT_STATUS['SEEING']
        appointment.call_time = datetime.now()
        
        await self.db.commit()
        await self.db.refresh(appointment)
        return appointment

    async def mark_no_show(self, appointment_id: str) -> Optional[Appointment]:
        """标记爽约"""
        appointment = await self.get_by_id(appointment_id)
        if not appointment:
            return None
        
        if appointment.status not in [APPOINTMENT_STATUS['CONFIRMED'], APPOINTMENT_STATUS['EXPIRED']]:
            raise ValueError("当前状态不可标记爽约")
        
        appointment.status = APPOINTMENT_STATUS['CLOSED']  # 使用 CLOSED 表示已爽约
        
        await self.db.commit()
        await self.db.refresh(appointment)
        return appointment

    async def get_queue_info(self, doctor_id: str) -> dict:
        """获取医生当前叫号信息"""
        today = date.today()
        
        # 当前就诊中的患者
        in_progress_result = await self.db.execute(
            select(Appointment)
            .join(Schedule)
            .options(selectinload(Appointment.patient))
            .where(
                and_(
                    Appointment.doctor_id == doctor_id,
                    Schedule.schedule_date == today,
                    Appointment.status == APPOINTMENT_STATUS['SEEING']
                )
            )
        )
        current = in_progress_result.scalar_one_or_none()
        
        # 候诊队列（已签到）
        waiting_result = await self.db.execute(
            select(Appointment)
            .join(Schedule)
            .options(selectinload(Appointment.patient))
            .where(
                and_(
                    Appointment.doctor_id == doctor_id,
                    Schedule.schedule_date == today,
                    Appointment.status == APPOINTMENT_STATUS['SIGNED']
                )
            )
            .order_by(Appointment.sign_in_time)
        )
        waiting_list = list(waiting_result.scalars().all())
        
        # 过号队列
        passed_result = await self.db.execute(
            select(Appointment)
            .join(Schedule)
            .options(selectinload(Appointment.patient))
            .where(
                and_(
                    Appointment.doctor_id == doctor_id,
                    Schedule.schedule_date == today,
                    Appointment.status == APPOINTMENT_STATUS['EXPIRED']
                )
            )
            .order_by(Appointment.queue_number)
        )
        passed_list = list(passed_result.scalars().all())
        
        return {
            'current': {
                'id': current.id,
                'queueNumber': current.queue_number,
                'patientName': current.patient.name if current and current.patient else None,
                'callTime': current.call_time.isoformat() if current and current.call_time else None,
            } if current else None,
            'waitingCount': len(waiting_list),
            'waitingList': [
                {
                    'id': a.id,
                    'queueNumber': a.queue_number,
                    'patientName': a.patient.name if a.patient else None,
                    'signInTime': a.sign_in_time.isoformat() if a.sign_in_time else None,
                }
                for a in waiting_list[:10]
            ],
            'passedCount': len(passed_list),
            'passedList': [
                {
                    'id': a.id,
                    'queueNumber': a.queue_number,
                    'patientName': a.patient.name if a.patient else None,
                }
                for a in passed_list
            ],
        }

    async def get_today_pending_by_user_and_store(
        self, 
        user_id: str, 
        store_id: str
    ) -> List[Appointment]:
        """获取用户在指定门店的今日待签到预约
        
        用于患者扫码签到时选择要签到的预约
        """
        from app.models.doctor import Doctor
        
        today = date.today()
        
        result = await self.db.execute(
            select(Appointment)
            .join(Schedule)
            .options(
                selectinload(Appointment.schedule),
                selectinload(Appointment.patient),
                selectinload(Appointment.doctor).selectinload(Doctor.department)
            )
            .where(
                and_(
                    Appointment.user_id == user_id,
                    Schedule.store_id == store_id,
                    Schedule.schedule_date == today,
                    Appointment.status == APPOINTMENT_STATUS['CONFIRMED']
                )
            )
            .order_by(Schedule.time_slot)
        )
        
        return list(result.scalars().all())

    async def get_checkin_queue(
        self,
        store_id: Optional[str] = None,
        doctor_id: Optional[str] = None,
        target_date: Optional[date] = None
    ) -> List[Appointment]:
        """获取签到队列
        
        返回指定日期的已签到及后续状态的预约，按签到时间排序
        用于管理后台和医生端查看叫号队列
        """
        from app.models.doctor import Doctor
        
        if not target_date:
            target_date = date.today()
        
        query = (
            select(Appointment)
            .join(Schedule)
            .options(
                selectinload(Appointment.schedule),
                selectinload(Appointment.patient),
                selectinload(Appointment.doctor).selectinload(Doctor.department)
            )
            .where(
                and_(
                    Schedule.schedule_date == target_date,
                    # 已签到、候诊中、就诊中、已完成
                    Appointment.status.in_([
                        APPOINTMENT_STATUS['SIGNED'],
                        APPOINTMENT_STATUS['WAITING'],
                        APPOINTMENT_STATUS['SEEING'],
                        APPOINTMENT_STATUS['COMPLETED']
                    ])
                )
            )
        )
        
        if store_id:
            query = query.where(Schedule.store_id == store_id)
        
        if doctor_id:
            query = query.where(Appointment.doctor_id == doctor_id)
        
        # 按签到时间排序
        query = query.order_by(Appointment.sign_in_time)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def check_duplicate_same_day(
        self, 
        user_id: str, 
        patient_id: str, 
        schedule_date: date, 
        time_slot: str
    ) -> List[Appointment]:
        """检查同一天同一时段是否有重复预约
        
        Args:
            user_id: 用户ID
            patient_id: 就诊人ID
            schedule_date: 预约日期
            time_slot: 时段 (AM=上午, PM=下午)
            
        Returns:
            该时段已有的预约列表（有效状态：已预约/已签到/候诊中）
        """
        result = await self.db.execute(
            select(Appointment)
            .join(Schedule)
            .options(selectinload(Appointment.schedule))
            .where(
                and_(
                    Appointment.patient_id == patient_id,
                    Schedule.schedule_date == schedule_date,
                    Schedule.time_slot == time_slot,
                    Appointment.status.in_([
                        APPOINTMENT_STATUS['CONFIRMED'],
                        APPOINTMENT_STATUS['SIGNED'],
                        APPOINTMENT_STATUS['WAITING']
                    ])
                )
            )
        )
        return list(result.scalars().all())

    async def _count_user_store_daily_appointments(
        self,
        user_id: str,
        store_id: Optional[str],
        schedule_date: date
    ) -> int:
        """统计用户在指定门店指定日期的有效预约数
        
        Args:
            user_id: 用户ID
            store_id: 门店ID
            schedule_date: 预约日期
            
        Returns:
            有效预约数量（已预约/已签到/候诊中/就诊中）
        """
        query = (
            select(func.count(Appointment.id))
            .join(Schedule)
            .where(
                and_(
                    Appointment.user_id == user_id,
                    Schedule.schedule_date == schedule_date,
                    Appointment.status.in_([
                        APPOINTMENT_STATUS['CONFIRMED'],
                        APPOINTMENT_STATUS['SIGNED'],
                        APPOINTMENT_STATUS['WAITING'],
                        APPOINTMENT_STATUS['SEEING']
                    ])
                )
            )
        )
        
        # 如果指定了门店，则增加门店过滤条件
        if store_id:
            query = query.where(Schedule.store_id == store_id)
        
        result = await self.db.execute(query)
        return result.scalar() or 0