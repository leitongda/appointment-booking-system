"""Policy lookup helpers for the rule engine."""


from sqlalchemy import select

from app.models.rule_set import RuleBookingPolicy, RuleCapacityPolicy, RuleCheckinPolicy
from app.modules.rule_engine.monitoring import monitor_performance


class RuleEnginePolicyMixin:
    @monitor_performance("get_booking_policy")
    async def get_booking_policy(self, shift_type_id: str) -> RuleBookingPolicy | None:
        rule_set = await self.get_applicable_rule_set(shift_type_id)
        if not rule_set:
            return None

        result = await self.db.execute(
            select(RuleBookingPolicy).where(RuleBookingPolicy.rule_set_id == rule_set.id)
        )
        return result.scalar_one_or_none()

    @monitor_performance("get_checkin_policy")
    async def get_checkin_policy(self, shift_type_id: str) -> RuleCheckinPolicy | None:
        rule_set = await self.get_applicable_rule_set(shift_type_id)
        if not rule_set:
            return None

        result = await self.db.execute(
            select(RuleCheckinPolicy).where(RuleCheckinPolicy.rule_set_id == rule_set.id)
        )
        return result.scalar_one_or_none()

    async def get_checkin_policy_by_rule_set_id(
        self, rule_set_id: str
    ) -> RuleCheckinPolicy | None:
        result = await self.db.execute(
            select(RuleCheckinPolicy).where(RuleCheckinPolicy.rule_set_id == rule_set_id)
        )
        return result.scalar_one_or_none()

    @monitor_performance("get_capacity_policy")
    async def get_capacity_policy(self, shift_type_id: str) -> RuleCapacityPolicy | None:
        rule_set = await self.get_applicable_rule_set(shift_type_id)
        if not rule_set:
            return None

        result = await self.db.execute(
            select(RuleCapacityPolicy).where(RuleCapacityPolicy.rule_set_id == rule_set.id)
        )
        return result.scalar_one_or_none()
