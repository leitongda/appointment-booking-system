"""
规则引擎核心服务

负责规则匹配和时间窗校验逻辑
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from typing import Optional, Dict, Any
from datetime import datetime, time, date, timedelta
import pytz

from app.models.rule_set import RuleSet, RuleWindow, RuleBookingPolicy, RuleCheckinPolicy, RuleCapacityPolicy, ShiftType
from app.models.schedule import Schedule
from app.models.appointment import Appointment
from app.models.waitlist import WaitlistEntry


class RuleEngineService:
    """规则引擎服务 - 核心业务逻辑"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_applicable_rule_set(self, shift_type_id: str) -> Optional[RuleSet]:
        """获取适用的规则组

        根据班次类型查找适用的规则组，按优先级排序，取第一个启用的

        Args:
            shift_type_id: 班次类型ID

        Returns:
            RuleSet or None
        """
        result = await self.db.execute(
            select(RuleSet)
            .join(RuleSet.shift_types)
            .where(
                and_(
                    RuleSet.enabled == True,
                    ShiftType.id == shift_type_id,
                    ShiftType.enabled == True
                )
            )
            .order_by(RuleSet.priority.asc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def check_action_window(
        self,
        schedule: Schedule,
        action: str,
        current_time: Optional[datetime] = None,
        booking_created_at: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """检查动作是否在时间窗口内

        支持多时间窗组合校验（AND 逻辑）：
        - 如果同一动作配置了多个时间窗，所有时间窗都必须满足才允许操作
        - 返回的开放时间是所有时间窗中最晚的开放时间
        - 返回的截止时间是所有时间窗中最早的截止时间

        Args:
            schedule: 排班对象
            action: 动作类型 (BOOK/CHECKIN/CANCEL)
            current_time: 当前时间，默认使用服务端时间
            booking_created_at: 预约创建时间（用于 BOOKING_CREATED_AT 参考点）

        Returns:
            {
                "allowed": bool,  # 是否允许
                "open_at": datetime,  # 开放时间（多个窗口取最晚）
                "close_at": datetime,  # 截止时间（多个窗口取最早）
                "current_time": datetime,  # 当前时间
                "fail_policy": str,  # 失败策略（第一个不满足的窗口）
                "fail_tag": str,  # 失败标签
                "message": str,  # 提示信息
            }
        """
        if not current_time:
            current_time = datetime.now(pytz.UTC)

        # 获取班次类型
        shift_type_id = schedule.shift_type_id
        if not shift_type_id:
            # 如果没有班次类型，返回默认规则（允许操作）
            return self._get_default_window_result(schedule, action, current_time)

        # 获取适用的规则组
        rule_set = await self.get_applicable_rule_set(shift_type_id)
        if not rule_set:
            return self._get_default_window_result(schedule, action, current_time)

        # 获取对应动作的所有启用时间窗
        result = await self.db.execute(
            select(RuleWindow).where(
                and_(
                    RuleWindow.rule_set_id == rule_set.id,
                    RuleWindow.action == action,
                    RuleWindow.enabled == True
                )
            )
        )
        windows = result.scalars().all()

        if not windows:
            return self._get_default_window_result(schedule, action, current_time)

        # 多时间窗组合校验（AND 逻辑）
        combined_open_at = None  # 最晚的开放时间
        combined_close_at = None  # 最早的截止时间
        all_allowed = True
        first_failed_window = None

        for window in windows:
            # 计算参考时间
            reference_time = self._get_reference_time(
                schedule, 
                window.reference_point,
                booking_created_at=booking_created_at
            )

            # 计算开放和截止时间
            # 处理 None 值：如果偏移量为 None，则不限制该边界
            if window.open_offset_sec is not None:
                window_open_at = reference_time + timedelta(seconds=window.open_offset_sec)
            else:
                # 无开放偏移表示从很早就开放
                window_open_at = current_time - timedelta(days=365)

            if window.close_offset_sec is not None:
                window_close_at = reference_time + timedelta(seconds=window.close_offset_sec)
            else:
                # 无截止偏移表示永不截止
                window_close_at = current_time + timedelta(days=365)

            # 获取边界包含设置
            open_inclusive = window.open_inclusive if window.open_inclusive is not None else rule_set.default_open_inclusive
            close_inclusive = window.close_inclusive if window.close_inclusive is not None else rule_set.default_close_inclusive

            # 判断是否在窗口内
            window_allowed = self._is_in_window(current_time, window_open_at, window_close_at, open_inclusive, close_inclusive)

            # 记录第一个不满足的窗口
            if not window_allowed and first_failed_window is None:
                first_failed_window = {
                    'window': window,
                    'open_at': window_open_at,
                    'close_at': window_close_at
                }
                all_allowed = False

            # 组合时间窗：开放时间取最晚，截止时间取最早
            if combined_open_at is None or window_open_at > combined_open_at:
                combined_open_at = window_open_at
            if combined_close_at is None or window_close_at < combined_close_at:
                combined_close_at = window_close_at

        # 如果有不满足的窗口，使用第一个不满足的窗口信息
        if first_failed_window:
            window = first_failed_window['window']
            return {
                "allowed": False,
                "open_at": combined_open_at,
                "close_at": combined_close_at,
                "current_time": current_time,
                "fail_policy": window.fail_policy,
                "fail_tag": window.fail_tag,
                "message": self._generate_window_message(
                    False,
                    first_failed_window['open_at'],
                    first_failed_window['close_at'],
                    action,
                    window.fail_policy
                )
            }

        # 所有窗口都满足
        return {
            "allowed": True,
            "open_at": combined_open_at,
            "close_at": combined_close_at,
            "current_time": current_time,
            "fail_policy": "ALLOW",
            "fail_tag": None,
            "message": "操作允许"
        }

    def _get_reference_time(
        self, 
        schedule: Schedule, 
        reference_point: str,
        booking_created_at: Optional[datetime] = None
    ) -> datetime:
        """获取参考时间

        Args:
            schedule: 排班对象
            reference_point: 参考点类型
            booking_created_at: 预约创建时间（用于 BOOKING_CREATED_AT 参考点）

        Returns:
            参考时间（带时区）
        """
        # 优先使用 start_at/end_at（带时区的绝对时间）
        if reference_point == 'SHIFT_START':
            if schedule.start_at:
                return schedule.start_at
            # 如果没有 start_at，使用 schedule_date + start_time，添加 UTC 时区
            if schedule.start_time:
                return pytz.UTC.localize(datetime.combine(schedule.schedule_date, schedule.start_time))
        elif reference_point == 'SHIFT_END':
            if schedule.end_at:
                return schedule.end_at
            # 添加 UTC 时区
            if schedule.end_time:
                return pytz.UTC.localize(datetime.combine(schedule.schedule_date, schedule.end_time))
        elif reference_point == 'BOOKING_CREATED_AT':
            # 优先使用调用方提供的预约创建时间
            if booking_created_at:
                if booking_created_at.tzinfo is None:
                    return pytz.UTC.localize(booking_created_at)
                return booking_created_at
            # 默认使用当前时间
            return datetime.now(pytz.UTC)

        # 默认返回班次开始时间
        if schedule.start_at:
            return schedule.start_at
        if schedule.start_time:
            return pytz.UTC.localize(datetime.combine(schedule.schedule_date, schedule.start_time))

        return datetime.now(pytz.UTC)

    def _is_in_window(
        self,
        current_time: datetime,
        open_at: datetime,
        close_at: datetime,
        open_inclusive: bool,
        close_inclusive: bool
    ) -> bool:
        """判断时间是否在窗口内

        Args:
            current_time: 当前时间
            open_at: 开放时间
            close_at: 截止时间
            open_inclusive: 是否包含开放边界
            close_inclusive: 是否包含截止边界

        Returns:
            是否在窗口内
        """
        # 比较开放边界
        if open_inclusive:
            if current_time < open_at:
                return False
        else:
            if current_time <= open_at:
                return False

        # 比较截止边界
        if close_inclusive:
            if current_time > close_at:
                return False
        else:
            if current_time >= close_at:
                return False

        return True

    def _generate_window_message(
        self,
        allowed: bool,
        open_at: datetime,
        close_at: datetime,
        action: str,
        fail_policy: str
    ) -> str:
        """生成窗口提示信息

        Args:
            allowed: 是否允许
            open_at: 开放时间
            close_at: 截止时间
            action: 动作类型
            fail_policy: 失败策略

        Returns:
            提示信息
        """
        if allowed:
            return "操作允许"

        action_names = {
            'BOOK': '预约',
            'CHECKIN': '签到',
            'CANCEL': '取消',
            'HOLD_RELEASE': '释放'
        }

        action_name = action_names.get(action, action)

        # 判断是未开放还是已截止
        current_time = datetime.now(pytz.UTC)

        # 确保 open_at 和 close_at 是带时区的
        if open_at.tzinfo is None:
            open_at = open_at.replace(tzinfo=pytz.UTC)
        if close_at.tzinfo is None:
            close_at = close_at.replace(tzinfo=pytz.UTC)
        if current_time.tzinfo is None:
            current_time = current_time.replace(tzinfo=pytz.UTC)

        if current_time < open_at:
            return f"{action_name}未开放，开放时间：{open_at.strftime('%Y-%m-%d %H:%M')}"
        elif current_time > close_at:
            return f"{action_name}已截止，截止时间：{close_at.strftime('%Y-%m-%d %H:%M')}"
        else:
            return f"{action_name}操作不允许"

    def _get_default_window_result(
        self,
        schedule: Schedule,
        action: str,
        current_time: datetime
    ) -> Dict[str, Any]:
        """获取默认窗口结果（当没有配置规则时）

        Args:
            schedule: 排班对象
            action: 动作类型
            current_time: 当前时间

        Returns:
            默认窗口结果
        """
        # 使用现有 system_settings 的配置或宽松的默认值
        return {
            "allowed": True,
            "open_at": current_time,
            "close_at": current_time + timedelta(days=365),
            "current_time": current_time,
            "fail_policy": "ALLOW",
            "fail_tag": None,
            "message": "使用默认配置"
        }

    async def get_booking_policy(self, shift_type_id: str) -> Optional[RuleBookingPolicy]:
        """获取预约策略

        Args:
            shift_type_id: 班次类型ID

        Returns:
            RuleBookingPolicy or None
        """
        rule_set = await self.get_applicable_rule_set(shift_type_id)
        if not rule_set:
            return None

        # 获取预约策略
        result = await self.db.execute(
            select(RuleBookingPolicy).where(RuleBookingPolicy.rule_set_id == rule_set.id)
        )
        return result.scalar_one_or_none()

    async def get_checkin_policy(self, shift_type_id: str) -> Optional[RuleCheckinPolicy]:
        """获取签到策略

        Args:
            shift_type_id: 班次类型ID

        Returns:
            RuleCheckinPolicy or None
        """
        rule_set = await self.get_applicable_rule_set(shift_type_id)
        if not rule_set:
            return None

        # 获取签到策略
        result = await self.db.execute(
            select(RuleCheckinPolicy).where(RuleCheckinPolicy.rule_set_id == rule_set.id)
        )
        return result.scalar_one_or_none()

    async def get_checkin_policy_by_rule_set_id(self, rule_set_id: str) -> Optional[RuleCheckinPolicy]:
        """根据规则组ID获取签到策略

        Args:
            rule_set_id: 规则组ID

        Returns:
            RuleCheckinPolicy or None
        """
        result = await self.db.execute(
            select(RuleCheckinPolicy).where(RuleCheckinPolicy.rule_set_id == rule_set_id)
        )
        return result.scalar_one_or_none()

    async def get_capacity_policy(self, shift_type_id: str) -> Optional[RuleCapacityPolicy]:
        """获取容量策略

        Args:
            shift_type_id: 班次类型ID

        Returns:
            RuleCapacityPolicy or None
        """
        rule_set = await self.get_applicable_rule_set(shift_type_id)
        if not rule_set:
            return None

        # 获取容量策略
        result = await self.db.execute(
            select(RuleCapacityPolicy).where(RuleCapacityPolicy.rule_set_id == rule_set.id)
        )
        return result.scalar_one_or_none()

    async def check_booking_conflicts(
        self,
        db: AsyncSession,
        shift_id: str,
        user_id: str,
        policy: RuleBookingPolicy,
        booking_time: datetime,
        schedule: Optional[Schedule] = None,
    ) -> Dict[str, Any]:
        """检查预约冲突

        验证规则：
        1. 每班次限约数 (per_user_per_shift)
        2. 每日限约数 (per_user_per_day)
        3. 每周限约数 (per_user_per_week)
        4. 同班次冲突策略 (conflict_same_shift)
        5. 时间重叠策略 (conflict_overlap_time)
        6. 同类型同日策略 (conflict_same_type_same_day)

        Args:
            db: 数据库会话
            shift_id: 班次ID
            user_id: 用户ID
            policy: 预约策略对象
            booking_time: 预约时间
            schedule: 排班对象（用于日期、时间、类型检查）

        Returns:
            {
                'allowed': bool,  # 是否允许
                'reason': str | None,  # 不允许的原因
                'conflict_with': dict | None  # 冲突的预约信息
            }
        """
        # 1. 检查每班次限约数
        if policy.per_user_per_shift and policy.per_user_per_shift > 0:
            existing_count = await db.execute(
                select(func.count(Appointment.id))
                .where(
                    and_(
                        Appointment.schedule_id == shift_id,
                        Appointment.user_id == user_id,
                        Appointment.status.in_([1, 2])  # 1=已预约, 2=已签到
                    )
                )
            )
            count = existing_count.scalar() or 0
            if count >= policy.per_user_per_shift:
                return {
                    'allowed': False,
                    'reason': f'每班次最多可预约{policy.per_user_per_shift}次，您已预约{count}次',
                    'conflict_with': None
                }

        # 2. 检查同班次冲突策略
        if policy.conflict_same_shift == 'REJECT':
            existing = await db.execute(
                select(Appointment).where(
                    and_(
                        Appointment.schedule_id == shift_id,
                        Appointment.user_id == user_id,
                        Appointment.status.in_([1, 2])  # 1=已预约, 2=已签到
                    )
                ).limit(1)
            )
            if existing.scalar_one_or_none():
                return {
                    'allowed': False,
                    'reason': '您已预约该班次，请勿重复预约',
                    'conflict_with': None
                }

        # 以下检查需要 schedule 信息
        if schedule:
            schedule_date = schedule.schedule_date

            # 3. 检查每日限约数 (per_user_per_day)
            if policy.per_user_per_day and policy.per_user_per_day > 0:
                day_count_result = await db.execute(
                    select(func.count(Appointment.id))
                    .join(Schedule, Appointment.schedule_id == Schedule.id)
                    .where(
                        and_(
                            Appointment.user_id == user_id,
                            Appointment.status.in_([1, 2])  # 1=已预约, 2=已签到,
                            Schedule.schedule_date == schedule_date
                        )
                    )
                )
                day_count = day_count_result.scalar() or 0
                if day_count >= policy.per_user_per_day:
                    return {
                        'allowed': False,
                        'reason': f'您今日已预约{day_count}次，每日最多可预约{policy.per_user_per_day}次',
                        'conflict_with': None
                    }

            # 4. 检查每周限约数 (per_user_per_week)
            if policy.per_user_per_week and policy.per_user_per_week > 0:
                # 计算本周的开始和结束日期（周一到周日）
                week_start = schedule_date - timedelta(days=schedule_date.weekday())
                week_end = week_start + timedelta(days=6)

                week_count_result = await db.execute(
                    select(func.count(Appointment.id))
                    .join(Schedule, Appointment.schedule_id == Schedule.id)
                    .where(
                        and_(
                            Appointment.user_id == user_id,
                            Appointment.status.in_([1, 2])  # 1=已预约, 2=已签到,
                            Schedule.schedule_date >= week_start,
                            Schedule.schedule_date <= week_end
                        )
                    )
                )
                week_count = week_count_result.scalar() or 0
                if week_count >= policy.per_user_per_week:
                    return {
                        'allowed': False,
                        'reason': f'您本周已预约{week_count}次，每周最多可预约{policy.per_user_per_week}次',
                        'conflict_with': None
                    }

            # 5. 检查时间重叠策略 (conflict_overlap_time)
            if policy.conflict_overlap_time == 'REJECT' and schedule.start_time and schedule.end_time:
                # 查找同一日期、时间有重叠的预约
                overlap_result = await db.execute(
                    select(Appointment, Schedule)
                    .join(Schedule, Appointment.schedule_id == Schedule.id)
                    .where(
                        and_(
                            Appointment.user_id == user_id,
                            Appointment.status.in_([1, 2])  # 1=已预约, 2=已签到,
                            Schedule.schedule_date == schedule_date,
                            Schedule.id != shift_id,  # 排除当前班次
                            # 时间重叠判断：A.start < B.end AND A.end > B.start
                            Schedule.start_time < schedule.end_time,
                            Schedule.end_time > schedule.start_time
                        )
                    )
                    .limit(1)
                )
                overlap_row = overlap_result.first()
                if overlap_row:
                    conflict_appointment, conflict_schedule = overlap_row
                    return {
                        'allowed': False,
                        'reason': f'您在该时间段已有其他预约（{conflict_schedule.start_time.strftime("%H:%M")}-{conflict_schedule.end_time.strftime("%H:%M")}），时间冲突',
                        'conflict_with': {
                            'appointment_id': conflict_appointment.id,
                            'schedule_id': conflict_schedule.id,
                            'start_time': str(conflict_schedule.start_time),
                            'end_time': str(conflict_schedule.end_time)
                        }
                    }

            # 6. 检查同类型同日策略 (conflict_same_type_same_day)
            if policy.conflict_same_type_same_day == 'REJECT' and schedule.appointment_type:
                same_type_result = await db.execute(
                    select(Appointment, Schedule)
                    .join(Schedule, Appointment.schedule_id == Schedule.id)
                    .where(
                        and_(
                            Appointment.user_id == user_id,
                            Appointment.status.in_([1, 2])  # 1=已预约, 2=已签到,
                            Schedule.schedule_date == schedule_date,
                            Schedule.appointment_type == schedule.appointment_type,
                            Schedule.id != shift_id  # 排除当前班次
                        )
                    )
                    .limit(1)
                )
                same_type_row = same_type_result.first()
                if same_type_row:
                    conflict_appointment, conflict_schedule = same_type_row
                    appointment_type_names = {
                        'normal': '普通门诊',
                        'expert': '专家门诊',
                        'urgent': '急诊',
                        'medical_insurance': '医保门诊',
                        'self_pay': '自费门诊'
                    }
                    type_name = appointment_type_names.get(schedule.appointment_type, schedule.appointment_type)
                    return {
                        'allowed': False,
                        'reason': f'您今日已预约{type_name}，同类型预约每日限一次',
                        'conflict_with': {
                            'appointment_id': conflict_appointment.id,
                            'schedule_id': conflict_schedule.id,
                            'appointment_type': conflict_schedule.appointment_type
                        }
                    }

        return {
            'allowed': True,
            'reason': None,
            'conflict_with': None
        }

    async def check_capacity_limits(
        self,
        db: AsyncSession,
        shift_id: str,
        user_id: str,
        policy: RuleCapacityPolicy,
    ) -> Dict[str, Any]:
        """检查容量限制

        验证规则：
        1. 总容量限制 (total_capacity)
        2. 每用户容量限制 (per_user_capacity)
        3. 候补队列检查 (waitlist_enabled)
        4. 超额预订检查 (overbooking_enabled)

        Args:
            db: 数据库会话
            shift_id: 班次ID
            user_id: 用户ID
            policy: 容量策略对象

        Returns:
            {
                'allowed': bool,  # 是否允许
                'reason': str | None,  # 不允许的原因
                'waitlist_position': int | None,  # 候补位置
                'is_overbooking': bool  # 是否为超额预订
            }
        """
        # 1. 检查总容量限制
        if policy.total_capacity:
            total_count = await db.execute(
                select(func.count(Appointment.id))
                .where(
                    and_(
                        Appointment.schedule_id == shift_id,
                        Appointment.status.in_([1, 2])  # 1=已预约, 2=已签到
                    )
                )
            )
            count = total_count.scalar() or 0

            # 如果启用超额预订，检查是否超过超额限制
            if policy.overbooking_enabled and count >= policy.total_capacity + policy.overbooking_max:
                return {
                    'allowed': False,
                    'reason': f'该班次已约满（总容量{policy.total_capacity}，超额{policy.overbooking_max}）',
                    'waitlist_position': None,
                    'is_overbooking': False
                }
            elif not policy.overbooking_enabled and count >= policy.total_capacity:
                # 检查是否启用候补
                if policy.waitlist_enabled:
                    # TODO: 计算候补位置
                    waitlist_pos = await self._calculate_waitlist_position(db, shift_id, user_id)
                    return {
                        'allowed': False,
                        'reason': f'该班次已约满（总容量{policy.total_capacity}），您的候补位置：第{waitlist_pos}位',
                        'waitlist_position': waitlist_pos,
                        'is_overbooking': False
                    }
                else:
                    return {
                        'allowed': False,
                        'reason': f'该班次已约满（总容量{policy.total_capacity}）',
                        'waitlist_position': None,
                        'is_overbooking': False
                    }

        # 2. 检查每用户容量限制
        if policy.per_user_capacity:
            user_count = await db.execute(
                select(func.count(Appointment.id))
                .where(
                    and_(
                        Appointment.schedule_id == shift_id,
                        Appointment.user_id == user_id,
                        Appointment.status.in_([1, 2])  # 1=已预约, 2=已签到
                    )
                )
            )
            count = user_count.scalar() or 0
            if count >= policy.per_user_capacity:
                return {
                    'allowed': False,
                    'reason': f'您已达到该班次的预约上限（{policy.per_user_capacity}次）',
                    'waitlist_position': None,
                    'is_overbooking': False
                }

        return {
            'allowed': True,
            'reason': None,
            'waitlist_position': None,
            'is_overbooking': False
        }

    def calculate_checkin_grace_period(
        self,
        appointment: Appointment,
        policy: RuleCheckinPolicy,
        current_time: datetime,
    ) -> Dict[str, Any]:
        """计算签到宽限期

        规则说明：
        - 宽限期内的签到不标记为迟到
        - 超过宽限期但仍在签到窗口内，标记为迟到但允许签到
        - 超过签到窗口，根据 no_checkin_after_close 处理

        Args:
            appointment: 预约对象
            policy: 签到策略对象
            current_time: 当前时间

        Returns:
            {
                'in_grace_period': bool,  # 是否在宽限期内
                'is_late': bool,  # 是否迟到
                'can_checkin': bool,  # 是否可以签到
                'suggested_status': str | None  # ON_TIME, LATE, 或其他状态
            }
        """
        # 获取签到窗口的截止时间
        checkin_close_at = appointment.checkin_close_at
        if not checkin_close_at:
            return {
                'in_grace_period': True,
                'is_late': False,
                'can_checkin': True,
                'suggested_status': 'ON_TIME'
            }

        # 确保时间带时区
        if checkin_close_at.tzinfo is None:
            checkin_close_at = checkin_close_at.replace(tzinfo=pytz.UTC)
        if current_time.tzinfo is None:
            current_time = current_time.replace(tzinfo=pytz.UTC)

        # 计算宽限期截止时间（签到窗口截止时间 + 宽限期秒数）
        grace_period_end = checkin_close_at + timedelta(seconds=policy.grace_period_sec)

        # 判断是否在宽限期内
        in_grace_period = current_time <= grace_period_end

        # 判断是否迟到（在签到窗口截止时间之后）
        is_late = current_time > checkin_close_at

        # 判断是否可以签到（宽限期后仍可签到，只是标记为迟到）
        # 实际的签到窗口检查在调用方完成
        can_checkin = True  # 假设已在时间窗口内，这里只判断宽限期

        # 确定建议的状态
        if not in_grace_period and is_late:
            suggested_status = policy.after_grace_status or 'LATE'
        else:
            suggested_status = 'ON_TIME'

        return {
            'in_grace_period': in_grace_period,
            'is_late': is_late,
            'can_checkin': can_checkin,
            'suggested_status': suggested_status
        }

    async def _calculate_waitlist_position(
        self,
        db: AsyncSession,
        shift_id: str,
        user_id: str
    ) -> int:
        """计算用户在候补队列中的位置

        Args:
            db: 数据库会话
            shift_id: 班次ID
            user_id: 用户ID

        Returns:
            候补位置（从1开始），如果不在队列中返回 -1
        """
        from sqlalchemy import select, and_

        result = await db.execute(
            select(WaitlistEntry.position).where(
                and_(
                    WaitlistEntry.schedule_id == shift_id,
                    WaitlistEntry.user_id == user_id,
                    WaitlistEntry.status == 'WAITING'
                )
            )
        )
        position = result.scalar_one_or_none()
        return position if position is not None else -1
