"""Query helpers for rule-set management."""

import uuid
from typing import List, Optional, Tuple

from sqlalchemy import and_, func, select
from sqlalchemy.orm import selectinload

from app.middleware.tenant_context import get_current_tenant_id
from app.models.rule_set import (
    RuleBookingPolicy,
    RuleCapacityPolicy,
    RuleCheckinPolicy,
    RuleSet,
    RuleSetPreset,
    RuleSetShiftType,
    RuleWindow,
    ShiftType,
    get_system_presets,
)
from app.models.rule_set_audit import RuleSetAuditLog
from app.schemas.rule_set import RuleSetDetailResponse


async def _get_active_rule_set_ids(db, shift_type_ids: List[str]) -> set:
    """
    获取每个班次类型下优先级最高的启用规则组 ID。

    对于每个班次类型，查询所有启用的规则组，按 priority 升序排序，
    取第一个（优先级最高）的规则组 ID。
    """
    if not shift_type_ids:
        return set()

    active_ids = set()
    for shift_type_id in shift_type_ids:
        # 查询该班次类型下所有启用的规则组，按 priority 升序
        query = (
            select(RuleSet.id)
            .join(RuleSetShiftType, RuleSet.id == RuleSetShiftType.rule_set_id)
            .where(
                and_(
                    RuleSetShiftType.shift_type_id == shift_type_id,
                    RuleSet.enabled == True,
                    RuleSet.deleted_at.is_(None),
                )
            )
            .order_by(RuleSet.priority.asc())
            .limit(1)
        )
        result = await db.execute(query)
        rule_set_id = result.scalar_one_or_none()
        if rule_set_id:
            active_ids.add(rule_set_id)

    return active_ids


class RuleSetQueryMixin:
    async def get_list(
        self,
        enabled: Optional[bool] = None,
        shift_type_id: Optional[str] = None,
        page: int = 1,
        page_size: int = 10,
    ) -> Tuple[List[RuleSetDetailResponse], int]:
        conditions = [RuleSet.deleted_at.is_(None)]

        # 租户过滤：tenant_id 为 None 时（超级管理员等场景）不添加过滤条件
        tenant_id = get_current_tenant_id()
        if tenant_id is not None:
            conditions.append(RuleSet.tenant_id == tenant_id)

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

        query = select(RuleSet).options(
            selectinload(RuleSet.shift_types),
            selectinload(RuleSet.windows),
            selectinload(RuleSet.booking_policy),
            selectinload(RuleSet.checkin_policy),
            selectinload(RuleSet.capacity_policy),
        )
        if conditions:
            query = query.where(and_(*conditions))
        if shift_type_id:
            query = query.join(RuleSet.shift_types)

        query = query.order_by(RuleSet.priority.asc(), RuleSet.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(query)
        rule_sets = result.scalars().all()

        # 批量计算所有活跃规则组 ID（只查询启用状态，不使用筛选条件）
        # 这样可以正确显示被筛选掉的规则组的活跃状态
        active_conditions = [RuleSet.enabled == True]
        if tenant_id is not None:
            active_conditions.append(RuleSet.tenant_id == tenant_id)

        # 获取当前租户下所有启用的规则组关联的班次类型
        active_shift_types_query = (
            select(ShiftType.id)
            .join(RuleSetShiftType, ShiftType.id == RuleSetShiftType.shift_type_id)
            .join(RuleSet, RuleSetShiftType.rule_set_id == RuleSet.id)
            .where(and_(*active_conditions))
            .distinct()
        )
        active_shift_types_result = await self.db.execute(active_shift_types_query)
        active_shift_type_ids = [row[0] for row in active_shift_types_result.all()]

        # 计算活跃规则组 ID
        active_rule_set_ids = await _get_active_rule_set_ids(self.db, active_shift_type_ids)

        responses = []
        for rs in rule_sets:
            responses.append(await self._to_detail_response(rs, active_rule_set_ids))
        return responses, total

    async def get_by_id(self, rule_set_id: str) -> Optional[RuleSetDetailResponse]:
        conditions = [RuleSet.id == rule_set_id, RuleSet.deleted_at.is_(None)]

        # 租户过滤：tenant_id 为 None 时（超级管理员等场景）不添加过滤条件
        tenant_id = get_current_tenant_id()
        if tenant_id is not None:
            conditions.append(RuleSet.tenant_id == tenant_id)

        result = await self.db.execute(
            select(RuleSet)
            .options(
                selectinload(RuleSet.shift_types),
                selectinload(RuleSet.windows),
                selectinload(RuleSet.booking_policy),
                selectinload(RuleSet.checkin_policy),
                selectinload(RuleSet.capacity_policy),
            )
            .where(and_(*conditions))
        )
        rule_set = result.scalar_one_or_none()
        if not rule_set:
            return None
        return await self._to_detail_response(rule_set)

    async def _to_detail_response(
        self, rule_set: RuleSet, active_rule_set_ids: Optional[set] = None
    ) -> RuleSetDetailResponse:
        # 关联数据已通过 selectinload 预加载，无需 refresh

        # 获取规则组关联的班次类型 ID 列表
        shift_type_ids = []
        if rule_set.shift_types:
            for st in rule_set.shift_types:
                shift_type_ids.append(st.id)

        # 如果没有传入 active_rule_set_ids，则实时计算
        if active_rule_set_ids is None:
            active_rule_set_ids = await _get_active_rule_set_ids(self.db, shift_type_ids)

        # 判断当前规则组是否为实际生效的规则组
        is_active = rule_set.id in active_rule_set_ids if rule_set.enabled else False

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
            "is_active": is_active,
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

    # ==================== 预设模板 ====================

    async def ensure_system_presets(self) -> None:
        """Lazy seed: 确保系统预设模板已初始化。"""
        existing = await self.db.execute(
            select(RuleSetPreset).where(RuleSetPreset.is_system == True)
        )
        if existing.scalars().first():
            return

        for preset_data in get_system_presets():
            preset = RuleSetPreset(
                id=preset_data["id"],
                name=preset_data["name"],
                description=preset_data["description"],
                config=preset_data["config"],
                is_system=True,
                sort_order=preset_data["sort_order"],
            )
            self.db.add(preset)
        await self.db.flush()

    async def get_presets(self) -> List[RuleSetPreset]:
        """获取预设模板列表（系统预设 + 当前租户自定义预设）。"""
        await self.ensure_system_presets()

        tenant_id = get_current_tenant_id()
        conditions = [RuleSetPreset.is_system == True]
        if tenant_id is not None:
            # 系统预设 + 当前租户的自定义预设
            conditions_with_tenant = [
                (RuleSetPreset.is_system == True)
                | ((RuleSetPreset.tenant_id == tenant_id) & (RuleSetPreset.is_system == False))
            ]
            query = select(RuleSetPreset).where(*conditions_with_tenant)
        else:
            query = select(RuleSetPreset).where(*conditions)

        query = query.order_by(RuleSetPreset.sort_order.asc(), RuleSetPreset.created_at.asc())
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_preset_by_id(self, preset_id: str) -> Optional[RuleSetPreset]:
        """获取预设模板详情。"""
        result = await self.db.execute(
            select(RuleSetPreset).where(RuleSetPreset.id == preset_id)
        )
        return result.scalar_one_or_none()

    async def get_audit_logs(
        self, rule_set_id: str, page: int = 1, page_size: int = 20
    ) -> Tuple[List[RuleSetAuditLog], int]:
        conditions = [RuleSetAuditLog.rule_set_id == rule_set_id]

        tenant_id = get_current_tenant_id()
        if tenant_id is not None:
            conditions.append(RuleSetAuditLog.tenant_id == tenant_id)

        count_query = select(func.count(RuleSetAuditLog.id)).where(and_(*conditions))
        count_result = await self.db.execute(count_query)
        total = count_result.scalar_one() or 0

        query = (
            select(RuleSetAuditLog)
            .where(and_(*conditions))
            .order_by(RuleSetAuditLog.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.db.execute(query)
        logs = list(result.scalars().all())
        return logs, total
