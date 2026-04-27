"""Rule-set CRUD and enable/disable operations."""

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import and_, delete, func, select

from app.core.redis import RedisCache
from app.middleware.tenant_context import get_current_tenant_id
from app.models.rule_set import (
    RuleBookingPolicy,
    RuleCapacityPolicy,
    RuleCheckinPolicy,
    RuleSet,
    RuleSetPreset,
    RuleSetShiftType,
    RuleWindow,
)
from app.modules.rule_engine.cache import RuleCache
import json

from app.modules.rule_sets.audit_helpers import (
    compute_rule_set_diff,
    make_rule_set_audit,
    snapshot_rule_set,
)
from app.schemas.rule_set import (
    RuleBookingPolicyCreate,
    RuleCapacityPolicyCreate,
    RuleCheckinPolicyCreate,
    RuleSetCreate,
    RuleSetUpdate,
    RuleWindowCreate,
)
from app.utils.audit import set_create_audit, set_update_audit


class RuleSetMutationMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._rule_cache: Optional[RuleCache] = None

    @property
    def rule_cache(self) -> RuleCache:
        """Lazy init of rule cache."""
        if self._rule_cache is None:
            self._rule_cache = RuleCache(RedisCache())
        return self._rule_cache

    async def _invalidate_rule_set_cache(self, rule_set_id: str) -> None:
        """使规则组的缓存失效（包括门店/科室级缓存）。"""
        try:
            # 查询规则组本身，获取 store_id 和 department_id
            rule_set_result = await self.db.execute(
                select(RuleSet.store_id, RuleSet.department_id).where(
                    RuleSet.id == rule_set_id
                )
            )
            rule_set_info = rule_set_result.first()
            if not rule_set_info:
                return

            store_id, department_id = rule_set_info

            # 查询规则组关联的 shift_type_ids
            result = await self.db.execute(
                select(RuleSetShiftType.shift_type_id).where(
                    RuleSetShiftType.rule_set_id == rule_set_id
                )
            )
            shift_type_ids = [row[0] for row in result.all()]
            tenant_id = get_current_tenant_id()

            # 使用 v2 方法失效所有相关缓存
            await self.rule_cache.invalidate_v2(
                tenant_id,
                shift_type_ids,
                store_ids=[store_id] if store_id else None,
                department_ids=[department_id] if department_id else None,
            )
        except Exception:
            # 缓存失效失败不应阻塞主流程
            pass
    async def _get_rule_set_with_tenant(self, rule_set_id: str):
        """根据 ID 查询规则组，同时过滤租户和软删除（与 service_query.get_by_id 保持一致）。"""
        conditions = [RuleSet.id == rule_set_id, RuleSet.deleted_at.is_(None)]
        tenant_id = get_current_tenant_id()
        if tenant_id is not None:
            conditions.append(RuleSet.tenant_id == tenant_id)

        result = await self.db.execute(
            select(RuleSet).where(and_(*conditions))
        )
        return result.scalar_one_or_none()

    async def create(
        self, data: RuleSetCreate, operator_id: Optional[str] = None
    ):
        rule_set = RuleSet(
            id=str(uuid.uuid4()),
            name=data.name,
            enabled=data.enabled,
            priority=data.priority,
            time_source=data.time_source,
            timezone_source=data.timezone_source,
            compare_precision=data.compare_precision,
            default_open_inclusive=data.default_open_inclusive,
            default_close_inclusive=data.default_close_inclusive,
            rounding_mode=data.rounding_mode,
            clock_skew_tolerance_sec=data.clock_skew_tolerance_sec,
            description=data.description,
            tenant_id=get_current_tenant_id(),
            store_id=data.store_id,
            department_id=data.department_id,
        )
        set_create_audit(rule_set, operator_id)
        self.db.add(rule_set)
        await self.db.flush()

        for shift_type_id in data.shift_type_ids:
            self.db.add(RuleSetShiftType(rule_set_id=rule_set.id, shift_type_id=shift_type_id))

        if data.windows:
            for window_data in data.windows:
                window = RuleWindow(
                    id=str(uuid.uuid4()),
                    rule_set_id=rule_set.id,
                    name=window_data.name,
                    action=window_data.action,
                    reference_point=window_data.reference_point,
                    open_offset_sec=window_data.open_offset_sec,
                    close_offset_sec=window_data.close_offset_sec,
                    open_inclusive=window_data.open_inclusive,
                    close_inclusive=window_data.close_inclusive,
                    fail_policy=window_data.fail_policy,
                    fail_tag=window_data.fail_tag,
                    enabled=window_data.enabled,
                    description=window_data.description,
                )
                set_create_audit(window, operator_id)
                self.db.add(window)

        if data.booking_policy:
            booking_policy = RuleBookingPolicy(
                rule_set_id=rule_set.id,
                require_auth=data.booking_policy.require_auth,
                require_patient_profile_complete=data.booking_policy.require_patient_profile_complete,
                per_user_per_shift=data.booking_policy.per_user_per_shift,
                per_user_per_day=data.booking_policy.per_user_per_day,
                per_user_per_week=data.booking_policy.per_user_per_week,
                conflict_same_shift=data.booking_policy.conflict_same_shift,
                conflict_overlap_time=data.booking_policy.conflict_overlap_time,
                conflict_same_type_same_day=data.booking_policy.conflict_same_type_same_day,
            )
            set_create_audit(booking_policy, operator_id)
            self.db.add(booking_policy)

        if data.checkin_policy:
            checkin_policy = RuleCheckinPolicy(
                rule_set_id=rule_set.id,
                require_booking=data.checkin_policy.require_booking,
                allow_onsite_booking=data.checkin_policy.allow_onsite_booking,
                max_times=data.checkin_policy.max_times,
                audit_log=data.checkin_policy.audit_log,
                grace_period_sec=data.checkin_policy.grace_period_sec,
                after_grace_status=data.checkin_policy.after_grace_status,
                no_checkin_after_close=data.checkin_policy.no_checkin_after_close,
            )
            set_create_audit(checkin_policy, operator_id)
            self.db.add(checkin_policy)

        if data.capacity_policy:
            capacity_policy = RuleCapacityPolicy(
                rule_set_id=rule_set.id,
                total_capacity=data.capacity_policy.total_capacity,
                per_user_capacity=data.capacity_policy.per_user_capacity,
                waitlist_enabled=data.capacity_policy.waitlist_enabled,
                waitlist_max_size=data.capacity_policy.waitlist_max_size,
                waitlist_promote_policy=data.capacity_policy.waitlist_promote_policy,
                overbooking_enabled=data.capacity_policy.overbooking_enabled,
                overbooking_max=data.capacity_policy.overbooking_max,
            )
            set_create_audit(capacity_policy, operator_id)
            self.db.add(capacity_policy)

        await self.db.flush()
        snapshot_after = await snapshot_rule_set(self.db, rule_set.id)
        self.db.add(
            make_rule_set_audit(
                rule_set_id=rule_set.id,
                action="CREATE",
                resource_type="rule_set",
                resource_id=rule_set.id,
                operator_id=operator_id,
                snapshot_after=snapshot_after,
                changes=json.dumps({"created": True}, ensure_ascii=False),
            )
        )

        await self.db.commit()

        # 缓存失效
        await self._invalidate_rule_set_cache(rule_set.id)

        return await self.get_by_id(rule_set.id)

    async def update(
        self, rule_set_id: str, data: RuleSetUpdate, operator_id: Optional[str] = None
    ):
        rule_set = await self._get_rule_set_with_tenant(rule_set_id)
        if not rule_set:
            return None

        snapshot_before = await snapshot_rule_set(self.db, rule_set.id)

        # 乐观锁检查
        if data.expected_updated_at is not None:
            if rule_set.updated_at and rule_set.updated_at != data.expected_updated_at:
                raise ValueError("规则组已被其他操作修改，请刷新后重试")

        if data.name is not None:
            rule_set.name = data.name
        if data.enabled is not None:
            rule_set.enabled = data.enabled
        if data.priority is not None:
            rule_set.priority = data.priority
        if data.description is not None:
            rule_set.description = data.description
        if data.time_source is not None:
            rule_set.time_source = data.time_source
        if data.timezone_source is not None:
            rule_set.timezone_source = data.timezone_source
        if data.compare_precision is not None:
            rule_set.compare_precision = data.compare_precision
        if data.default_open_inclusive is not None:
            rule_set.default_open_inclusive = data.default_open_inclusive
        if data.default_close_inclusive is not None:
            rule_set.default_close_inclusive = data.default_close_inclusive
        if data.rounding_mode is not None:
            rule_set.rounding_mode = data.rounding_mode
        if data.clock_skew_tolerance_sec is not None:
            rule_set.clock_skew_tolerance_sec = data.clock_skew_tolerance_sec
        if data.store_id is not None:
            rule_set.store_id = data.store_id
        if data.department_id is not None:
            rule_set.department_id = data.department_id

        set_update_audit(rule_set, operator_id)

        if data.shift_type_ids is not None:
            await self.db.execute(
                delete(RuleSetShiftType).where(RuleSetShiftType.rule_set_id == rule_set_id)
            )

            for shift_type_id in data.shift_type_ids:
                self.db.add(RuleSetShiftType(rule_set_id=rule_set.id, shift_type_id=shift_type_id))

        # 处理时间窗更新
        if data.windows is not None:
            await self.db.execute(
                delete(RuleWindow).where(RuleWindow.rule_set_id == rule_set_id)
            )

            # 创建新时间窗
            for window_data in data.windows:
                window = RuleWindow(
                    id=str(uuid.uuid4()),
                    rule_set_id=rule_set.id,
                    name=window_data.name,
                    action=window_data.action,
                    reference_point=window_data.reference_point,
                    open_offset_sec=window_data.open_offset_sec,
                    close_offset_sec=window_data.close_offset_sec,
                    open_inclusive=window_data.open_inclusive,
                    close_inclusive=window_data.close_inclusive,
                    fail_policy=window_data.fail_policy,
                    fail_tag=window_data.fail_tag,
                    enabled=window_data.enabled,
                    description=window_data.description,
                )
                set_create_audit(window, operator_id)
                self.db.add(window)

        # 处理策略更新
        if data.booking_policy is not None:
            await self._upsert_booking_policy(rule_set.id, data.booking_policy, operator_id)

        if data.checkin_policy is not None:
            await self._upsert_checkin_policy(rule_set.id, data.checkin_policy, operator_id)

        if data.capacity_policy is not None:
            await self._upsert_capacity_policy(rule_set.id, data.capacity_policy, operator_id)

        await self.db.flush()
        snapshot_after = await snapshot_rule_set(self.db, rule_set.id)
        diff = compute_rule_set_diff(snapshot_before, snapshot_after)
        changes_json = json.dumps(diff, ensure_ascii=False) if diff else None
        self.db.add(
            make_rule_set_audit(
                rule_set_id=rule_set.id,
                action="UPDATE",
                resource_type="rule_set",
                resource_id=rule_set.id,
                operator_id=operator_id,
                snapshot_before=snapshot_before,
                snapshot_after=snapshot_after,
                changes=changes_json,
            )
        )

        await self.db.commit()

        # 缓存失效（包括 shift_type_ids 变更的情况）
        await self._invalidate_rule_set_cache(rule_set_id)

        return await self.get_by_id(rule_set_id)

    async def _upsert_booking_policy(
        self, rule_set_id: str, data: RuleBookingPolicyCreate, operator_id: Optional[str] = None
    ):
        """Upsert 预约策略"""
        result = await self.db.execute(
            select(RuleBookingPolicy).where(RuleBookingPolicy.rule_set_id == rule_set_id)
        )
        policy = result.scalar_one_or_none()

        if policy:
            policy.require_auth = data.require_auth
            policy.require_patient_profile_complete = data.require_patient_profile_complete
            policy.per_user_per_shift = data.per_user_per_shift
            policy.per_user_per_day = data.per_user_per_day
            policy.per_user_per_week = data.per_user_per_week
            policy.conflict_same_shift = data.conflict_same_shift
            policy.conflict_overlap_time = data.conflict_overlap_time
            policy.conflict_same_type_same_day = data.conflict_same_type_same_day
            set_update_audit(policy, operator_id)
        else:
            policy = RuleBookingPolicy(
                rule_set_id=rule_set_id,
                require_auth=data.require_auth,
                require_patient_profile_complete=data.require_patient_profile_complete,
                per_user_per_shift=data.per_user_per_shift,
                per_user_per_day=data.per_user_per_day,
                per_user_per_week=data.per_user_per_week,
                conflict_same_shift=data.conflict_same_shift,
                conflict_overlap_time=data.conflict_overlap_time,
                conflict_same_type_same_day=data.conflict_same_type_same_day,
            )
            set_create_audit(policy, operator_id)
            self.db.add(policy)

    async def _upsert_checkin_policy(
        self, rule_set_id: str, data: RuleCheckinPolicyCreate, operator_id: Optional[str] = None
    ):
        """Upsert 签到策略"""
        result = await self.db.execute(
            select(RuleCheckinPolicy).where(RuleCheckinPolicy.rule_set_id == rule_set_id)
        )
        policy = result.scalar_one_or_none()

        if policy:
            policy.require_booking = data.require_booking
            policy.allow_onsite_booking = data.allow_onsite_booking
            policy.max_times = data.max_times
            policy.audit_log = data.audit_log
            policy.grace_period_sec = data.grace_period_sec
            policy.after_grace_status = data.after_grace_status
            policy.no_checkin_after_close = data.no_checkin_after_close
            set_update_audit(policy, operator_id)
        else:
            policy = RuleCheckinPolicy(
                rule_set_id=rule_set_id,
                require_booking=data.require_booking,
                allow_onsite_booking=data.allow_onsite_booking,
                max_times=data.max_times,
                audit_log=data.audit_log,
                grace_period_sec=data.grace_period_sec,
                after_grace_status=data.after_grace_status,
                no_checkin_after_close=data.no_checkin_after_close,
            )
            set_create_audit(policy, operator_id)
            self.db.add(policy)

    async def _upsert_capacity_policy(
        self, rule_set_id: str, data: RuleCapacityPolicyCreate, operator_id: Optional[str] = None
    ):
        """Upsert 容量策略"""
        result = await self.db.execute(
            select(RuleCapacityPolicy).where(RuleCapacityPolicy.rule_set_id == rule_set_id)
        )
        policy = result.scalar_one_or_none()

        if policy:
            policy.total_capacity = data.total_capacity
            policy.per_user_capacity = data.per_user_capacity
            policy.waitlist_enabled = data.waitlist_enabled
            policy.waitlist_max_size = data.waitlist_max_size
            policy.waitlist_promote_policy = data.waitlist_promote_policy
            policy.overbooking_enabled = data.overbooking_enabled
            policy.overbooking_max = data.overbooking_max
            set_update_audit(policy, operator_id)
        else:
            policy = RuleCapacityPolicy(
                rule_set_id=rule_set_id,
                total_capacity=data.total_capacity,
                per_user_capacity=data.per_user_capacity,
                waitlist_enabled=data.waitlist_enabled,
                waitlist_max_size=data.waitlist_max_size,
                waitlist_promote_policy=data.waitlist_promote_policy,
                overbooking_enabled=data.overbooking_enabled,
                overbooking_max=data.overbooking_max,
            )
            set_create_audit(policy, operator_id)
            self.db.add(policy)

    async def delete(self, rule_set_id: str, operator_id: Optional[str] = None) -> bool:
        rule_set = await self._get_rule_set_with_tenant(rule_set_id)
        if not rule_set:
            return False

        # 引用检查：排班表是否有记录关联此规则组
        from app.models.schedule import Schedule

        schedule_count_result = await self.db.execute(
            select(func.count(Schedule.id)).where(Schedule.shift_type_id.in_(
                select(RuleSetShiftType.shift_type_id).where(
                    RuleSetShiftType.rule_set_id == rule_set_id
                )
            ))
        )
        schedule_count = schedule_count_result.scalar() or 0

        # 检查预约表是否有记录关联此规则组
        from app.models.appointment import Appointment

        appointment_count_result = await self.db.execute(
            select(func.count(Appointment.id)).where(Appointment.rule_set_id == rule_set_id)
        )
        appointment_count = appointment_count_result.scalar() or 0

        if schedule_count > 0 or appointment_count > 0:
            parts = []
            if schedule_count > 0:
                parts.append(f"{schedule_count} 个排班")
            if appointment_count > 0:
                parts.append(f"{appointment_count} 个预约")
            raise ValueError(f"该规则组已被{'、'.join(parts)}引用，无法删除。请先禁用规则组。")

        snapshot_before = await snapshot_rule_set(self.db, rule_set.id)
        self.db.add(
            make_rule_set_audit(
                rule_set_id=rule_set.id,
                action="DELETE",
                resource_type="rule_set",
                resource_id=rule_set.id,
                operator_id=operator_id,
                snapshot_before=snapshot_before,
                changes=json.dumps({"deleted": True}, ensure_ascii=False),
            )
        )

        # 软删除
        rule_set.deleted_at = datetime.now(timezone.utc)
        rule_set.enabled = False
        await self.db.commit()
        await self._invalidate_rule_set_cache(rule_set_id)
        return True

    async def enable(self, rule_set_id: str, operator_id: Optional[str] = None) -> bool:
        rule_set = await self._get_rule_set_with_tenant(rule_set_id)
        if not rule_set:
            return False

        snapshot_before = await snapshot_rule_set(self.db, rule_set.id)
        rule_set.enabled = True
        set_update_audit(rule_set, operator_id)

        await self.db.flush()
        snapshot_after = await snapshot_rule_set(self.db, rule_set.id)
        diff = compute_rule_set_diff(snapshot_before, snapshot_after)
        changes_json = json.dumps(diff, ensure_ascii=False) if diff else None
        self.db.add(
            make_rule_set_audit(
                rule_set_id=rule_set.id,
                action="ENABLE",
                resource_type="rule_set",
                resource_id=rule_set.id,
                operator_id=operator_id,
                snapshot_before=snapshot_before,
                snapshot_after=snapshot_after,
                changes=changes_json,
            )
        )

        await self.db.commit()
        await self._invalidate_rule_set_cache(rule_set_id)
        return True

    async def disable(self, rule_set_id: str, operator_id: Optional[str] = None) -> bool:
        rule_set = await self._get_rule_set_with_tenant(rule_set_id)
        if not rule_set:
            return False

        snapshot_before = await snapshot_rule_set(self.db, rule_set.id)
        rule_set.enabled = False
        set_update_audit(rule_set, operator_id)

        await self.db.flush()
        snapshot_after = await snapshot_rule_set(self.db, rule_set.id)
        diff = compute_rule_set_diff(snapshot_before, snapshot_after)
        changes_json = json.dumps(diff, ensure_ascii=False) if diff else None
        self.db.add(
            make_rule_set_audit(
                rule_set_id=rule_set.id,
                action="DISABLE",
                resource_type="rule_set",
                resource_id=rule_set.id,
                operator_id=operator_id,
                snapshot_before=snapshot_before,
                snapshot_after=snapshot_after,
                changes=changes_json,
            )
        )

        await self.db.commit()
        await self._invalidate_rule_set_cache(rule_set_id)
        return True

    # ==================== 预设模板 ====================

    async def create_preset(
        self, name: str, description: Optional[str], config: dict,
        sort_order: int = 0, operator_id: Optional[str] = None,
    ) -> RuleSetPreset:
        """创建自定义预设模板。"""
        tenant_id = get_current_tenant_id()
        preset = RuleSetPreset(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            name=name,
            description=description,
            config=config,
            is_system=False,
            sort_order=sort_order,
        )
        set_create_audit(preset, operator_id)
        self.db.add(preset)
        await self.db.commit()
        return preset

    async def update_preset(
        self, preset_id: str, operator_id: Optional[str] = None, **kwargs,
    ) -> Optional[RuleSetPreset]:
        """更新自定义预设模板（系统预设不可修改）。"""
        result = await self.db.execute(
            select(RuleSetPreset).where(RuleSetPreset.id == preset_id)
        )
        preset = result.scalar_one_or_none()
        if not preset or preset.is_system:
            return None

        for key, value in kwargs.items():
            if value is not None and hasattr(preset, key):
                setattr(preset, key, value)
        set_update_audit(preset, operator_id)
        await self.db.commit()
        return preset

    async def delete_preset(self, preset_id: str) -> bool:
        """删除自定义预设模板（系统预设不可删除）。"""
        result = await self.db.execute(
            select(RuleSetPreset).where(RuleSetPreset.id == preset_id)
        )
        preset = result.scalar_one_or_none()
        if not preset or preset.is_system:
            return False

        await self.db.delete(preset)
        await self.db.commit()
        return True
