"""Time-window evaluation logic for the rule engine."""

from datetime import date, datetime, time, timedelta
from typing import Any, Dict, Optional, List, Union

import pytz
from sqlalchemy import and_, select

from app.core.redis import RedisCache
from app.middleware.tenant_context import get_current_tenant_id
from app.models.rule_set import RuleSet, RuleWindow, ShiftType
from app.models.schedule import Schedule
from app.modules.rule_engine.cache import CachedRuleSet, CachedRuleWindow, RuleCache
from app.modules.rule_engine.monitoring import monitor_performance


class RuleEngineTimeWindowMixin:
    """Mixin 提供时间窗评估逻辑。

    注意：此 mixin 的 __init__ 不调用 super().__init__，以避免 MRO 问题。
    使用此 mixin 的类应负责调用 RuleEngineTimeWindowMixin.__init__。
    """
    def __init__(self, *args, **kwargs):
        self._rule_cache: Optional[RuleCache] = None

    @property
    def rule_cache(self) -> RuleCache:
        """Lazy init of rule cache."""
        if self._rule_cache is None:
            self._rule_cache = RuleCache(RedisCache())
        return self._rule_cache
    @monitor_performance("get_applicable_rule_set")
    async def get_applicable_rule_set(
        self, shift_type_id: str, schedule: Optional[Schedule] = None
    ) -> Optional[RuleSet]:
        candidates = await self.get_candidate_rule_sets(shift_type_id, schedule)
        return candidates[0] if candidates else None

    async def get_candidate_rule_sets(
        self, shift_type_id: str, schedule: Optional[Schedule] = None
    ) -> list[RuleSet | CachedRuleSet]:
        """
        返回所有匹配班次类型的启用规则组，按优先级升序排列。

        支持门店/科室级匹配（多层级）：
        1. 如果排班有 department_id，优先匹配 department_id 相同的规则组
        2. 如果排班有 store_id，进一步匹配 store_id 相同的规则组（department_id 为空）
        3. 回退到租户级规则组（store_id 和 department_id 都为空）
        4. 最终按 priority 升序排序返回所有匹配的候选

        优先从缓存读取，缓存未命中则查询数据库并回填缓存。
        """
        tenant_id = get_current_tenant_id()

        # 获取排班的 store_id 和 department_id（安全处理）
        store_id = None
        department_id = None
        if schedule is not None:
            # 安全获取 store_id
            store_id = getattr(schedule, "store_id", None)
            if store_id is not None and not isinstance(store_id, str):
                store_id = None  # 非字符串值忽略（排除 Mock/MagicMock）

            # 安全获取 department_id
            # 注意：不访问 schedule.doctor 以避免触发 SQLAlchemy 延迟加载
            department_id = getattr(schedule, "department_id", None)
            if department_id is not None and not isinstance(department_id, str):
                department_id = None  # 非字符串值忽略

        # 尝试从缓存获取（使用扩展的缓存 key）
        cached_rule_sets = await self.rule_cache.get_rule_sets_v2(
            tenant_id, shift_type_id, store_id, department_id
        )
        if cached_rule_sets is not None:
            return cached_rule_sets

        # 缓存未命中，查询数据库
        base_conditions = and_(
            RuleSet.enabled == True,
            RuleSet.deleted_at.is_(None),
            ShiftType.id == shift_type_id,
            ShiftType.enabled == True,
        )

        candidates = []

        # 第一优先级：科室级匹配（department_id 相同）
        if department_id:
            result = await self.db.execute(
                select(RuleSet)
                .join(RuleSet.shift_types)
                .where(
                    and_(
                        base_conditions,
                        RuleSet.department_id == department_id,
                    )
                )
                .order_by(RuleSet.priority.asc())
            )
            candidates.extend(list(result.scalars().all()))

        # 第二优先级：门店级匹配（store_id 相同，但 department_id 为空）
        if store_id:
            result = await self.db.execute(
                select(RuleSet)
                .join(RuleSet.shift_types)
                .where(
                    and_(
                        base_conditions,
                        RuleSet.store_id == store_id,
                        RuleSet.department_id.is_(None),
                    )
                )
                .order_by(RuleSet.priority.asc())
            )
            candidates.extend(list(result.scalars().all()))

        # 第三优先级：租户级匹配（store_id 和 department_id 都为空）
        result = await self.db.execute(
            select(RuleSet)
            .join(RuleSet.shift_types)
            .where(
                and_(
                    base_conditions,
                    RuleSet.store_id.is_(None),
                    RuleSet.department_id.is_(None),
                )
            )
            .order_by(RuleSet.priority.asc())
        )
        candidates.extend(list(result.scalars().all()))

        # 去重并按优先级排序
        seen = set()
        unique_candidates = []
        for rs in candidates:
            if rs.id not in seen:
                seen.add(rs.id)
                unique_candidates.append(rs)

        rule_sets = sorted(unique_candidates, key=lambda x: x.priority)

        # 回填缓存
        if rule_sets:
            cached_sets = await self._build_cached_rule_sets(rule_sets)
            await self.rule_cache.set_rule_sets_v2(
                tenant_id, shift_type_id, store_id, department_id, cached_sets
            )

        return rule_sets

    async def _build_cached_rule_sets(self, rule_sets: List[RuleSet]) -> List[CachedRuleSet]:
        """从 ORM 对象构建可缓存的规则集列表。"""
        cached_sets = []
        for rs in rule_sets:
            # 查询该规则组的所有时间窗
            windows_result = await self.db.execute(
                select(RuleWindow).where(RuleWindow.rule_set_id == rs.id)
            )
            windows = windows_result.scalars().all()

            cached_set = CachedRuleSet(
                id=rs.id,
                name=rs.name,
                enabled=rs.enabled,
                priority=rs.priority,
                time_source=rs.time_source,
                timezone_source=rs.timezone_source,
                compare_precision=rs.compare_precision,
                default_open_inclusive=rs.default_open_inclusive,
                default_close_inclusive=rs.default_close_inclusive,
                rounding_mode=rs.rounding_mode,
                clock_skew_tolerance_sec=rs.clock_skew_tolerance_sec,
                tenant_id=rs.tenant_id,
                store_id=getattr(rs, "store_id", None),
                department_id=getattr(rs, "department_id", None),
                description=rs.description,
                windows=[
                    CachedRuleWindow(
                        id=w.id,
                        name=w.name,
                        action=w.action,
                        reference_point=w.reference_point,
                        open_offset_sec=w.open_offset_sec,
                        close_offset_sec=w.close_offset_sec,
                        open_inclusive=w.open_inclusive,
                        close_inclusive=w.close_inclusive,
                        fail_policy=w.fail_policy,
                        fail_tag=w.fail_tag,
                        enabled=w.enabled,
                    )
                    for w in windows
                ],
            )
            cached_sets.append(cached_set)
        return cached_sets

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

        rule_set = await self.get_applicable_rule_set(shift_type_id, schedule)
        if not rule_set:
            return self._get_default_window_result(schedule, action, current_time)

        # 获取时间窗：优先使用缓存的 windows，否则查询数据库
        if isinstance(rule_set, CachedRuleSet):
            windows = [w for w in rule_set.windows if w.action == action and w.enabled]
        else:
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
