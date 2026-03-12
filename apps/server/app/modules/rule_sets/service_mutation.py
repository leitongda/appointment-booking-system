"""Rule-set CRUD and enable/disable operations."""

import uuid
from typing import Optional

from sqlalchemy import select

from app.models.rule_set import (
    RuleBookingPolicy,
    RuleCapacityPolicy,
    RuleCheckinPolicy,
    RuleSet,
    RuleSetShiftType,
    RuleWindow,
)
from app.schemas.rule_set import RuleSetCreate, RuleSetUpdate
from app.utils.audit import set_create_audit, set_update_audit


class RuleSetMutationMixin:
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

        await self.db.commit()
        return await self.get_by_id(rule_set.id)

    async def update(
        self, rule_set_id: str, data: RuleSetUpdate, operator_id: Optional[str] = None
    ):
        result = await self.db.execute(select(RuleSet).where(RuleSet.id == rule_set_id))
        rule_set = result.scalar_one_or_none()
        if not rule_set:
            return None

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

        set_update_audit(rule_set, operator_id)

        if data.shift_type_ids is not None:
            old_relations = await self.db.execute(
                select(RuleSetShiftType).where(RuleSetShiftType.rule_set_id == rule_set_id)
            )
            for old_rel in old_relations.scalars().all():
                await self.db.delete(old_rel)

            for shift_type_id in data.shift_type_ids:
                self.db.add(RuleSetShiftType(rule_set_id=rule_set.id, shift_type_id=shift_type_id))

        await self.db.commit()
        return await self.get_by_id(rule_set_id)

    async def delete(self, rule_set_id: str) -> bool:
        result = await self.db.execute(select(RuleSet).where(RuleSet.id == rule_set_id))
        rule_set = result.scalar_one_or_none()
        if not rule_set:
            return False

        await self.db.delete(rule_set)
        await self.db.commit()
        return True

    async def enable(self, rule_set_id: str, operator_id: Optional[str] = None) -> bool:
        result = await self.db.execute(select(RuleSet).where(RuleSet.id == rule_set_id))
        rule_set = result.scalar_one_or_none()
        if not rule_set:
            return False

        rule_set.enabled = True
        set_update_audit(rule_set, operator_id)
        await self.db.commit()
        return True

    async def disable(self, rule_set_id: str, operator_id: Optional[str] = None) -> bool:
        result = await self.db.execute(select(RuleSet).where(RuleSet.id == rule_set_id))
        rule_set = result.scalar_one_or_none()
        if not rule_set:
            return False

        rule_set.enabled = False
        set_update_audit(rule_set, operator_id)
        await self.db.commit()
        return True
