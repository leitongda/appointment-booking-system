"""Query helpers for rule-set management."""

import uuid
from typing import List, Optional, Tuple

from sqlalchemy import and_, func, select
from sqlalchemy.orm import selectinload

from app.models.rule_set import (
    RuleBookingPolicy,
    RuleCapacityPolicy,
    RuleCheckinPolicy,
    RuleSet,
    RuleSetShiftType,
    RuleWindow,
    ShiftType,
)
from app.schemas.rule_set import RuleSetDetailResponse


class RuleSetQueryMixin:
    async def get_list(
        self,
        enabled: Optional[bool] = None,
        shift_type_id: Optional[str] = None,
        page: int = 1,
        page_size: int = 10,
    ) -> Tuple[List[RuleSetDetailResponse], int]:
        conditions = []
        if enabled is not None:
            conditions.append(RuleSet.enabled == enabled)
        if shift_type_id:
            conditions.append(ShiftType.id == shift_type_id)

        count_query = select(func.count(RuleSet.id))
        if conditions:
            count_query = count_query.where(and_(*conditions))
        if shift_type_id:
            count_query = count_query.join(RuleSet.shift_types)

        count_result = await self.db.execute(count_query)
        total = count_result.scalar_one() or 0

        query = select(RuleSet).options(selectinload(RuleSet.shift_types))
        if conditions:
            query = query.where(and_(*conditions))
        if shift_type_id:
            query = query.join(RuleSet.shift_types)

        query = query.order_by(RuleSet.priority.asc(), RuleSet.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(query)
        rule_sets = result.scalars().all()
        responses = []
        for rs in rule_sets:
            responses.append(await self._to_detail_response(rs))
        return responses, total

    async def get_by_id(self, rule_set_id: str) -> Optional[RuleSetDetailResponse]:
        result = await self.db.execute(
            select(RuleSet)
            .options(
                selectinload(RuleSet.shift_types),
                selectinload(RuleSet.windows),
                selectinload(RuleSet.booking_policy),
                selectinload(RuleSet.checkin_policy),
                selectinload(RuleSet.capacity_policy),
            )
            .where(RuleSet.id == rule_set_id)
        )
        rule_set = result.scalar_one_or_none()
        if not rule_set:
            return None
        return await self._to_detail_response(rule_set)

    async def _to_detail_response(self, rule_set: RuleSet) -> RuleSetDetailResponse:
        await self.db.refresh(
            rule_set, ["shift_types", "windows", "booking_policy", "checkin_policy", "capacity_policy"]
        )

        data = {
            "id": rule_set.id,
            "name": rule_set.name,
            "enabled": rule_set.enabled,
            "priority": rule_set.priority,
            "time_source": rule_set.time_source,
            "timezone_source": rule_set.timezone_source,
            "compare_precision": rule_set.compare_precision,
            "default_open_inclusive": rule_set.default_open_inclusive,
            "default_close_inclusive": rule_set.default_close_inclusive,
            "rounding_mode": rule_set.rounding_mode,
            "clock_skew_tolerance_sec": rule_set.clock_skew_tolerance_sec,
            "description": rule_set.description,
            "created_at": rule_set.created_at,
            "updated_at": rule_set.updated_at,
        }

        shift_types = []
        if rule_set.shift_types:
            for st in rule_set.shift_types:
                shift_types.append(
                    {
                        "id": st.id,
                        "code": st.code,
                        "name": st.name,
                        "description": st.description,
                        "enabled": st.enabled,
                        "created_at": st.created_at,
                        "updated_at": st.updated_at,
                    }
                )
        data["shift_types"] = shift_types
        return RuleSetDetailResponse(**data)

    async def get_window_by_id(self, window_id: str) -> Optional[RuleWindow]:
        result = await self.db.execute(select(RuleWindow).where(RuleWindow.id == window_id))
        return result.scalar_one_or_none()
