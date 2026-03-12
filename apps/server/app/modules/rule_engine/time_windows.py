"""Time-window evaluation logic for the rule engine."""

from datetime import date, datetime, time, timedelta
from typing import Any, Dict, Optional

import pytz
from sqlalchemy import and_, select

from app.models.rule_set import RuleSet, RuleWindow, ShiftType
from app.models.schedule import Schedule
from app.modules.rule_engine.monitoring import monitor_performance


class RuleEngineTimeWindowMixin:
    @monitor_performance("get_applicable_rule_set")
    async def get_applicable_rule_set(self, shift_type_id: str) -> Optional[RuleSet]:
        result = await self.db.execute(
            select(RuleSet)
            .join(RuleSet.shift_types)
            .where(
                and_(
                    RuleSet.enabled == True,
                    ShiftType.id == shift_type_id,
                    ShiftType.enabled == True,
                )
            )
            .order_by(RuleSet.priority.asc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    @monitor_performance("check_action_window")
    async def check_action_window(
        self,
        schedule: Schedule,
        action: str,
        current_time: Optional[datetime] = None,
        booking_created_at: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        schedule_tz = pytz.timezone(getattr(schedule, "timezone", None) or "Asia/Shanghai")

        if not current_time:
            current_time = datetime.now(schedule_tz)
        elif current_time.tzinfo is None:
            current_time = schedule_tz.localize(current_time)

        shift_type_id = schedule.shift_type_id
        if not shift_type_id:
            return self._get_default_window_result(schedule, action, current_time)

        rule_set = await self.get_applicable_rule_set(shift_type_id)
        if not rule_set:
            return self._get_default_window_result(schedule, action, current_time)

        result = await self.db.execute(
            select(RuleWindow).where(
                and_(
                    RuleWindow.rule_set_id == rule_set.id,
                    RuleWindow.action == action,
                    RuleWindow.enabled == True,
                )
            )
        )
        windows = result.scalars().all()

        if not windows:
            return self._get_default_window_result(schedule, action, current_time)

        combined_open_at = None
        combined_close_at = None
        first_failed_window = None

        for window in windows:
            reference_time = self._get_reference_time(
                schedule,
                window.reference_point,
                booking_created_at=booking_created_at,
            )

            if window.open_offset_sec is not None:
                window_open_at = reference_time + timedelta(seconds=window.open_offset_sec)
            else:
                window_open_at = current_time - timedelta(days=365)

            if window.close_offset_sec is not None:
                window_close_at = reference_time + timedelta(seconds=window.close_offset_sec)
            else:
                window_close_at = current_time + timedelta(days=365)

            open_inclusive = (
                window.open_inclusive
                if window.open_inclusive is not None
                else rule_set.default_open_inclusive
            )
            close_inclusive = (
                window.close_inclusive
                if window.close_inclusive is not None
                else rule_set.default_close_inclusive
            )

            window_allowed = self._is_in_window(
                current_time, window_open_at, window_close_at, open_inclusive, close_inclusive
            )

            if not window_allowed and first_failed_window is None:
                first_failed_window = {
                    "window": window,
                    "open_at": window_open_at,
                    "close_at": window_close_at,
                }

            if combined_open_at is None or window_open_at > combined_open_at:
                combined_open_at = window_open_at
            if combined_close_at is None or window_close_at < combined_close_at:
                combined_close_at = window_close_at

        if first_failed_window:
            window = first_failed_window["window"]
            return {
                "allowed": False,
                "open_at": combined_open_at,
                "close_at": combined_close_at,
                "current_time": current_time,
                "fail_policy": window.fail_policy,
                "fail_tag": window.fail_tag,
                "message": self._generate_window_message(
                    False,
                    first_failed_window["open_at"],
                    first_failed_window["close_at"],
                    action,
                    window.fail_policy,
                ),
            }

        return {
            "allowed": True,
            "open_at": combined_open_at,
            "close_at": combined_close_at,
            "current_time": current_time,
            "fail_policy": "ALLOW",
            "fail_tag": None,
            "message": "操作允许",
        }

    def _get_reference_time(
        self,
        schedule: Schedule,
        reference_point: str,
        booking_created_at: Optional[datetime] = None,
    ) -> datetime:
        schedule_tz = pytz.timezone(getattr(schedule, "timezone", None) or "Asia/Shanghai")

        def localize_local_time(local_dt: datetime) -> datetime:
            if local_dt.tzinfo is None:
                return schedule_tz.localize(local_dt)
            return local_dt

        if reference_point == "SHIFT_START":
            if schedule.start_at:
                return schedule.start_at
            if schedule.start_time:
                return localize_local_time(datetime.combine(schedule.schedule_date, schedule.start_time))
        elif reference_point == "SHIFT_END":
            if schedule.end_at:
                return schedule.end_at
            if schedule.end_time:
                return localize_local_time(datetime.combine(schedule.schedule_date, schedule.end_time))
        elif reference_point == "BOOKING_CREATED_AT":
            if booking_created_at:
                if booking_created_at.tzinfo is None:
                    return schedule_tz.localize(booking_created_at)
                return booking_created_at
            return datetime.now(schedule_tz)

        if schedule.start_at:
            return schedule.start_at
        if schedule.start_time:
            return localize_local_time(datetime.combine(schedule.schedule_date, schedule.start_time))
        return datetime.now(schedule_tz)

    def _is_in_window(
        self,
        current_time: datetime,
        open_at: datetime,
        close_at: datetime,
        open_inclusive: bool,
        close_inclusive: bool,
    ) -> bool:
        if open_inclusive:
            if current_time < open_at:
                return False
        else:
            if current_time <= open_at:
                return False

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
        fail_policy: str,
    ) -> str:
        if allowed:
            return "操作允许"

        action_names = {
            "BOOK": "预约",
            "CHECKIN": "签到",
            "CANCEL": "取消",
            "HOLD_RELEASE": "释放",
        }
        action_name = action_names.get(action, action)
        local_tz = pytz.timezone("Asia/Shanghai")
        current_time = datetime.now(local_tz)

        if open_at.tzinfo is None:
            open_at = local_tz.localize(open_at)
        if close_at.tzinfo is None:
            close_at = local_tz.localize(close_at)
        if current_time.tzinfo is None:
            current_time = local_tz.localize(current_time)

        if current_time < open_at:
            return f"{action_name}未开放，开放时间：{open_at.strftime('%Y-%m-%d %H:%M')}"
        if current_time > close_at:
            return f"{action_name}已截止，截止时间：{close_at.strftime('%Y-%m-%d %H:%M')}"
        return f"{action_name}操作不允许"

    def _get_default_window_result(
        self,
        schedule: Schedule,
        action: str,
        current_time: datetime,
    ) -> Dict[str, Any]:
        return {
            "allowed": True,
            "open_at": current_time,
            "close_at": current_time + timedelta(days=365),
            "current_time": current_time,
            "fail_policy": "ALLOW",
            "fail_tag": None,
            "message": "使用默认配置",
        }
