"""Rule-window and policy update helpers for rule sets."""

import uuid
from typing import Optional

from sqlalchemy import select

from app.modules.rule_sets.audit_helpers import make_rule_set_audit, snapshot_rule_set
from app.models.rule_set import (
    RuleBookingPolicy,
    RuleCapacityPolicy,
    RuleCheckinPolicy,
    RuleSet,
    RuleWindow,
)
from app.schemas.rule_set import (
    RuleBookingPolicyCreate,
    RuleCapacityPolicyCreate,
    RuleCheckinPolicyCreate,
    RuleWindowCreate,
    RuleWindowUpdate,
)
from app.utils.audit import set_create_audit, set_update_audit


class RuleSetPolicyMixin:
    async def create_window(
        self, rule_set_id: str, data: RuleWindowCreate, operator_id: Optional[str] = None
    ) -> Optional[RuleWindow]:
        result = await self.db.execute(select(RuleSet).where(RuleSet.id == rule_set_id))
        if not result.scalar_one_or_none():
            return None

        snapshot_before = await snapshot_rule_set(self.db, rule_set_id)

        window = RuleWindow(
            id=str(uuid.uuid4()),
            rule_set_id=rule_set_id,
            name=data.name,
            action=data.action,
            reference_point=data.reference_point,
            open_offset_sec=data.open_offset_sec,
            close_offset_sec=data.close_offset_sec,
            open_inclusive=data.open_inclusive,
            close_inclusive=data.close_inclusive,
            fail_policy=data.fail_policy,
            fail_tag=data.fail_tag,
            enabled=data.enabled,
            description=data.description,
        )
        set_create_audit(window, operator_id)
        self.db.add(window)
        await self.db.flush()
        self.db.add(
            make_rule_set_audit(
                rule_set_id=rule_set_id,
                action="CREATE",
                resource_type="window",
                resource_id=window.id,
                operator_id=operator_id,
                snapshot_before=snapshot_before,
                snapshot_after=await snapshot_rule_set(self.db, rule_set_id),
            )
        )
        await self.db.commit()
        await self.db.refresh(window)
        return window

    async def update_window(
        self, window_id: str, data: RuleWindowUpdate, operator_id: Optional[str] = None
    ) -> Optional[RuleWindow]:
        window = await self.get_window_by_id(window_id)
        if not window:
            return None

        snapshot_before = await snapshot_rule_set(self.db, window.rule_set_id)

        if data.open_offset_sec is not None:
            window.open_offset_sec = data.open_offset_sec
        if data.close_offset_sec is not None:
            window.close_offset_sec = data.close_offset_sec
        if data.open_inclusive is not None:
            window.open_inclusive = data.open_inclusive
        if data.close_inclusive is not None:
            window.close_inclusive = data.close_inclusive
        if data.fail_policy is not None:
            window.fail_policy = data.fail_policy
        if data.fail_tag is not None:
            window.fail_tag = data.fail_tag
        if data.enabled is not None:
            window.enabled = data.enabled
        if data.description is not None:
            window.description = data.description

        set_update_audit(window, operator_id)
        await self.db.flush()
        self.db.add(
            make_rule_set_audit(
                rule_set_id=window.rule_set_id,
                action="UPDATE",
                resource_type="window",
                resource_id=window.id,
                operator_id=operator_id,
                snapshot_before=snapshot_before,
                snapshot_after=await snapshot_rule_set(self.db, window.rule_set_id),
            )
        )
        await self.db.commit()
        await self.db.refresh(window)
        return window

    async def delete_window(self, window_id: str, operator_id: Optional[str] = None) -> bool:
        window = await self.get_window_by_id(window_id)
        if not window:
            return False

        rule_set_id = window.rule_set_id
        snapshot_before = await snapshot_rule_set(self.db, rule_set_id)
        await self.db.delete(window)
        await self.db.flush()
        self.db.add(
            make_rule_set_audit(
                rule_set_id=rule_set_id,
                action="DELETE",
                resource_type="window",
                resource_id=window.id,
                operator_id=operator_id,
                snapshot_before=snapshot_before,
                snapshot_after=await snapshot_rule_set(self.db, rule_set_id),
            )
        )
        await self.db.commit()
        return True

    async def update_booking_policy(
        self, rule_set_id: str, data: RuleBookingPolicyCreate, operator_id: Optional[str] = None
    ) -> Optional[RuleBookingPolicy]:
        snapshot_before = await snapshot_rule_set(self.db, rule_set_id)
        result = await self.db.execute(
            select(RuleBookingPolicy).where(RuleBookingPolicy.rule_set_id == rule_set_id)
        )
        policy = result.scalar_one_or_none()
        existed = policy is not None

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

        await self.db.flush()
        self.db.add(
            make_rule_set_audit(
                rule_set_id=rule_set_id,
                action="UPDATE" if existed else "CREATE",
                resource_type="booking_policy",
                resource_id=policy.rule_set_id,
                operator_id=operator_id,
                snapshot_before=snapshot_before,
                snapshot_after=await snapshot_rule_set(self.db, rule_set_id),
            )
        )
        await self.db.commit()
        await self.db.refresh(policy)
        return policy

    async def update_checkin_policy(
        self, rule_set_id: str, data: RuleCheckinPolicyCreate, operator_id: Optional[str] = None
    ) -> Optional[RuleCheckinPolicy]:
        snapshot_before = await snapshot_rule_set(self.db, rule_set_id)
        result = await self.db.execute(
            select(RuleCheckinPolicy).where(RuleCheckinPolicy.rule_set_id == rule_set_id)
        )
        policy = result.scalar_one_or_none()
        existed = policy is not None

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

        await self.db.flush()
        self.db.add(
            make_rule_set_audit(
                rule_set_id=rule_set_id,
                action="UPDATE" if existed else "CREATE",
                resource_type="checkin_policy",
                resource_id=policy.rule_set_id,
                operator_id=operator_id,
                snapshot_before=snapshot_before,
                snapshot_after=await snapshot_rule_set(self.db, rule_set_id),
            )
        )
        await self.db.commit()
        await self.db.refresh(policy)
        return policy

    async def update_capacity_policy(
        self, rule_set_id: str, data: RuleCapacityPolicyCreate, operator_id: Optional[str] = None
    ) -> Optional[RuleCapacityPolicy]:
        snapshot_before = await snapshot_rule_set(self.db, rule_set_id)
        result = await self.db.execute(
            select(RuleCapacityPolicy).where(RuleCapacityPolicy.rule_set_id == rule_set_id)
        )
        policy = result.scalar_one_or_none()
        existed = policy is not None

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

        await self.db.flush()
        self.db.add(
            make_rule_set_audit(
                rule_set_id=rule_set_id,
                action="UPDATE" if existed else "CREATE",
                resource_type="capacity_policy",
                resource_id=policy.rule_set_id,
                operator_id=operator_id,
                snapshot_before=snapshot_before,
                snapshot_after=await snapshot_rule_set(self.db, rule_set_id),
            )
        )
        await self.db.commit()
        await self.db.refresh(policy)
        return policy
