"""
规则组管理服务

负责规则组的 CRUD 操作
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from sqlalchemy.orm import selectinload
from typing import Optional, List, Tuple
import uuid

from app.models.rule_set import (
    RuleSet, RuleSetShiftType, RuleWindow, RuleBookingPolicy,
    RuleCheckinPolicy, RuleCapacityPolicy, ShiftType
)
from app.schemas.rule_set import (
    RuleSetCreate, RuleSetUpdate, RuleSetDetailResponse,
    RuleWindowCreate, RuleWindowUpdate, RuleBookingPolicyCreate,
    RuleCheckinPolicyCreate, RuleCapacityPolicyCreate
)
from app.utils.audit import set_create_audit, set_update_audit


class RuleSetService:
    """规则组服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_list(
        self,
        enabled: Optional[bool] = None,
        shift_type_id: Optional[str] = None,
        page: int = 1,
        page_size: int = 10
    ) -> Tuple[List[RuleSetDetailResponse], int]:
        """获取规则组列表

        Args:
            enabled: 是否启用
            shift_type_id: 班次类型ID
            page: 页码
            page_size: 每页数量

        Returns:
            (规则组列表, 总数)
        """
        # 构建查询条件
        conditions = []

        if enabled is not None:
            conditions.append(RuleSet.enabled == enabled)

        if shift_type_id:
            conditions.append(ShiftType.id == shift_type_id)

        # 查询总数
        count_query = select(func.count(RuleSet.id))
        if conditions:
            count_query = count_query.where(and_(*conditions))
        if shift_type_id:
            count_query = count_query.join(RuleSet.shift_types)

        count_result = await self.db.execute(count_query)
        total = count_result.scalar_one() or 0

        # 查询数据
        query = select(RuleSet).options(selectinload(RuleSet.shift_types))
        if conditions:
            query = query.where(and_(*conditions))
        if shift_type_id:
            query = query.join(RuleSet.shift_types)

        query = query.order_by(RuleSet.priority.asc(), RuleSet.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await self.db.execute(query)
        rule_sets = result.scalars().all()

        # 转换为响应模型
        responses = []
        for rs in rule_sets:
            responses.append(await self._to_detail_response(rs))

        return responses, total

    async def get_by_id(self, rule_set_id: str) -> Optional[RuleSetDetailResponse]:
        """获取规则组详情

        Args:
            rule_set_id: 规则组ID

        Returns:
            规则组详情
        """
        result = await self.db.execute(
            select(RuleSet)
            .options(
                selectinload(RuleSet.shift_types),
                selectinload(RuleSet.windows),
                selectinload(RuleSet.booking_policy),
                selectinload(RuleSet.checkin_policy),
                selectinload(RuleSet.capacity_policy)
            )
            .where(RuleSet.id == rule_set_id)
        )
        rule_set = result.scalar_one_or_none()

        if not rule_set:
            return None

        return await self._to_detail_response(rule_set)

    async def create(
        self,
        data: RuleSetCreate,
        operator_id: Optional[str] = None
    ) -> RuleSetDetailResponse:
        """创建规则组

        Args:
            data: 创建数据
            operator_id: 操作人ID

        Returns:
            创建的规则组
        """
        # 创建规则组
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
            description=data.description
        )

        set_create_audit(rule_set, operator_id)

        self.db.add(rule_set)
        await self.db.flush()

        # 关联班次类型
        for shift_type_id in data.shift_type_ids:
            rs_st = RuleSetShiftType(
                rule_set_id=rule_set.id,
                shift_type_id=shift_type_id
            )
            self.db.add(rs_st)

        # 创建时间窗
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
                    description=window_data.description
                )
                set_create_audit(window, operator_id)
                self.db.add(window)

        # 创建预约策略
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
                conflict_same_type_same_day=data.booking_policy.conflict_same_type_same_day
            )
            set_create_audit(booking_policy, operator_id)
            self.db.add(booking_policy)

        # 创建签到策略
        if data.checkin_policy:
            checkin_policy = RuleCheckinPolicy(
                rule_set_id=rule_set.id,
                require_booking=data.checkin_policy.require_booking,
                allow_onsite_booking=data.checkin_policy.allow_onsite_booking,
                max_times=data.checkin_policy.max_times,
                audit_log=data.checkin_policy.audit_log,
                grace_period_sec=data.checkin_policy.grace_period_sec,
                after_grace_status=data.checkin_policy.after_grace_status,
                no_checkin_after_close=data.checkin_policy.no_checkin_after_close
            )
            set_create_audit(checkin_policy, operator_id)
            self.db.add(checkin_policy)

        # 创建容量策略
        if data.capacity_policy:
            capacity_policy = RuleCapacityPolicy(
                rule_set_id=rule_set.id,
                total_capacity=data.capacity_policy.total_capacity,
                per_user_capacity=data.capacity_policy.per_user_capacity,
                waitlist_enabled=data.capacity_policy.waitlist_enabled,
                waitlist_max_size=data.capacity_policy.waitlist_max_size,
                waitlist_promote_policy=data.capacity_policy.waitlist_promote_policy,
                overbooking_enabled=data.capacity_policy.overbooking_enabled,
                overbooking_max=data.capacity_policy.overbooking_max
            )
            set_create_audit(capacity_policy, operator_id)
            self.db.add(capacity_policy)

        await self.db.commit()

        # 重新加载并返回
        return await self.get_by_id(rule_set.id)

    async def update(
        self,
        rule_set_id: str,
        data: RuleSetUpdate,
        operator_id: Optional[str] = None
    ) -> Optional[RuleSetDetailResponse]:
        """更新规则组

        Args:
            rule_set_id: 规则组ID
            data: 更新数据
            operator_id: 操作人ID

        Returns:
            更新后的规则组
        """
        result = await self.db.execute(
            select(RuleSet).where(RuleSet.id == rule_set_id)
        )
        rule_set = result.scalar_one_or_none()

        if not rule_set:
            return None

        # 更新基础字段
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

        # 更新班次类型关联
        if data.shift_type_ids is not None:
            # 删除旧关联
            await self.db.execute(
                select(RuleSetShiftType).where(RuleSetShiftType.rule_set_id == rule_set_id)
            )
            old_relations = await self.db.execute(
                select(RuleSetShiftType).where(RuleSetShiftType.rule_set_id == rule_set_id)
            )
            for old_rel in old_relations.scalars().all():
                await self.db.delete(old_rel)

            # 添加新关联
            for shift_type_id in data.shift_type_ids:
                rs_st = RuleSetShiftType(
                    rule_set_id=rule_set.id,
                    shift_type_id=shift_type_id
                )
                self.db.add(rs_st)

        await self.db.commit()

        # 重新加载并返回
        return await self.get_by_id(rule_set_id)

    async def delete(self, rule_set_id: str) -> bool:
        """删除规则组

        Args:
            rule_set_id: 规则组ID

        Returns:
            是否删除成功
        """
        result = await self.db.execute(
            select(RuleSet).where(RuleSet.id == rule_set_id)
        )
        rule_set = result.scalar_one_or_none()

        if not rule_set:
            return False

        await self.db.delete(rule_set)
        await self.db.commit()

        return True

    async def enable(self, rule_set_id: str, operator_id: Optional[str] = None) -> bool:
        """启用规则组

        Args:
            rule_set_id: 规则组ID
            operator_id: 操作人ID

        Returns:
            是否成功
        """
        result = await self.db.execute(
            select(RuleSet).where(RuleSet.id == rule_set_id)
        )
        rule_set = result.scalar_one_or_none()

        if not rule_set:
            return False

        rule_set.enabled = True
        set_update_audit(rule_set, operator_id)

        await self.db.commit()
        return True

    async def disable(self, rule_set_id: str, operator_id: Optional[str] = None) -> bool:
        """禁用规则组

        Args:
            rule_set_id: 规则组ID
            operator_id: 操作人ID

        Returns:
            是否成功
        """
        result = await self.db.execute(
            select(RuleSet).where(RuleSet.id == rule_set_id)
        )
        rule_set = result.scalar_one_or_none()

        if not rule_set:
            return False

        rule_set.enabled = False
        set_update_audit(rule_set, operator_id)

        await self.db.commit()
        return True

    async def _to_detail_response(self, rule_set: RuleSet) -> RuleSetDetailResponse:
        """转换为详情响应

        Args:
            rule_set: 规则组实体

        Returns:
            详情响应
        """
        # 加载关联数据
        await self.db.refresh(rule_set, ["shift_types", "windows", "booking_policy", "checkin_policy", "capacity_policy"])

        # 转换为字典
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

        # 转换班次类型
        shift_types = []
        if rule_set.shift_types:
            for st in rule_set.shift_types:
                shift_types.append({
                    "id": st.id,
                    "code": st.code,
                    "name": st.name,
                    "description": st.description,
                    "enabled": st.enabled,
                    "created_at": st.created_at,
                    "updated_at": st.updated_at,
                })
        data["shift_types"] = shift_types

        return RuleSetDetailResponse(**data)

    # ==================== RuleWindow 方法 ====================

    async def get_window_by_id(self, window_id: str) -> Optional[RuleWindow]:
        """获取时间窗详情

        Args:
            window_id: 时间窗ID

        Returns:
            时间窗
        """
        result = await self.db.execute(
            select(RuleWindow).where(RuleWindow.id == window_id)
        )
        return result.scalar_one_or_none()

    async def create_window(
        self,
        rule_set_id: str,
        data: RuleWindowCreate,
        operator_id: Optional[str] = None
    ) -> Optional[RuleWindow]:
        """创建时间窗

        Args:
            rule_set_id: 规则组ID
            data: 创建数据
            operator_id: 操作人ID

        Returns:
            创建的时间窗
        """
        # 检查规则组是否存在
        result = await self.db.execute(
            select(RuleSet).where(RuleSet.id == rule_set_id)
        )
        if not result.scalar_one_or_none():
            return None

        import uuid
        window = RuleWindow(
            id=str(uuid.uuid4()),
            rule_set_id=rule_set_id,
            action=data.action,
            reference_point=data.reference_point,
            open_offset_sec=data.open_offset_sec,
            close_offset_sec=data.close_offset_sec,
            open_inclusive=data.open_inclusive,
            close_inclusive=data.close_inclusive,
            fail_policy=data.fail_policy,
            fail_tag=data.fail_tag,
            enabled=data.enabled,
            description=data.description
        )
        set_create_audit(window, operator_id)
        self.db.add(window)
        await self.db.commit()
        await self.db.refresh(window)
        return window

    async def update_window(
        self,
        window_id: str,
        data: 'RuleWindowUpdate',
        operator_id: Optional[str] = None
    ) -> Optional[RuleWindow]:
        """更新时间窗

        Args:
            window_id: 时间窗ID
            data: 更新数据
            operator_id: 操作人ID

        Returns:
            更新后的时间窗
        """
        window = await self.get_window_by_id(window_id)
        if not window:
            return None

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

        await self.db.commit()
        await self.db.refresh(window)
        return window

    async def delete_window(self, window_id: str) -> bool:
        """删除时间窗

        Args:
            window_id: 时间窗ID

        Returns:
            是否删除成功
        """
        window = await self.get_window_by_id(window_id)
        if not window:
            return False

        await self.db.delete(window)
        await self.db.commit()
        return True

    # ==================== 策略更新方法 ====================

    async def update_booking_policy(
        self,
        rule_set_id: str,
        data: RuleBookingPolicyCreate,
        operator_id: Optional[str] = None
    ) -> Optional[RuleBookingPolicy]:
        """更新预约策略

        Args:
            rule_set_id: 规则组ID
            data: 策略数据
            operator_id: 操作人ID

        Returns:
            更新后的策略
        """
        # 查找现有策略
        result = await self.db.execute(
            select(RuleBookingPolicy).where(RuleBookingPolicy.rule_set_id == rule_set_id)
        )
        policy = result.scalar_one_or_none()

        if policy:
            # 更新
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
            # 创建
            policy = RuleBookingPolicy(
                rule_set_id=rule_set_id,
                require_auth=data.require_auth,
                require_patient_profile_complete=data.require_patient_profile_complete,
                per_user_per_shift=data.per_user_per_shift,
                per_user_per_day=data.per_user_per_day,
                per_user_per_week=data.per_user_per_week,
                conflict_same_shift=data.conflict_same_shift,
                conflict_overlap_time=data.conflict_overlap_time,
                conflict_same_type_same_day=data.conflict_same_type_same_day
            )
            set_create_audit(policy, operator_id)
            self.db.add(policy)

        await self.db.commit()
        await self.db.refresh(policy)
        return policy

    async def update_checkin_policy(
        self,
        rule_set_id: str,
        data: RuleCheckinPolicyCreate,
        operator_id: Optional[str] = None
    ) -> Optional[RuleCheckinPolicy]:
        """更新签到策略

        Args:
            rule_set_id: 规则组ID
            data: 策略数据
            operator_id: 操作人ID

        Returns:
            更新后的策略
        """
        # 查找现有策略
        result = await self.db.execute(
            select(RuleCheckinPolicy).where(RuleCheckinPolicy.rule_set_id == rule_set_id)
        )
        policy = result.scalar_one_or_none()

        if policy:
            # 更新
            policy.require_booking = data.require_booking
            policy.allow_onsite_booking = data.allow_onsite_booking
            policy.max_times = data.max_times
            policy.audit_log = data.audit_log
            policy.grace_period_sec = data.grace_period_sec
            policy.after_grace_status = data.after_grace_status
            policy.no_checkin_after_close = data.no_checkin_after_close
            set_update_audit(policy, operator_id)
        else:
            # 创建
            policy = RuleCheckinPolicy(
                rule_set_id=rule_set_id,
                require_booking=data.require_booking,
                allow_onsite_booking=data.allow_onsite_booking,
                max_times=data.max_times,
                audit_log=data.audit_log,
                grace_period_sec=data.grace_period_sec,
                after_grace_status=data.after_grace_status,
                no_checkin_after_close=data.no_checkin_after_close
            )
            set_create_audit(policy, operator_id)
            self.db.add(policy)

        await self.db.commit()
        await self.db.refresh(policy)
        return policy

    async def update_capacity_policy(
        self,
        rule_set_id: str,
        data: RuleCapacityPolicyCreate,
        operator_id: Optional[str] = None
    ) -> Optional[RuleCapacityPolicy]:
        """更新容量策略

        Args:
            rule_set_id: 规则组ID
            data: 策略数据
            operator_id: 操作人ID

        Returns:
            更新后的策略
        """
        # 查找现有策略
        result = await self.db.execute(
            select(RuleCapacityPolicy).where(RuleCapacityPolicy.rule_set_id == rule_set_id)
        )
        policy = result.scalar_one_or_none()

        if policy:
            # 更新
            policy.total_capacity = data.total_capacity
            policy.per_user_capacity = data.per_user_capacity
            policy.waitlist_enabled = data.waitlist_enabled
            policy.waitlist_max_size = data.waitlist_max_size
            policy.waitlist_promote_policy = data.waitlist_promote_policy
            policy.overbooking_enabled = data.overbooking_enabled
            policy.overbooking_max = data.overbooking_max
            set_update_audit(policy, operator_id)
        else:
            # 创建
            policy = RuleCapacityPolicy(
                rule_set_id=rule_set_id,
                total_capacity=data.total_capacity,
                per_user_capacity=data.per_user_capacity,
                waitlist_enabled=data.waitlist_enabled,
                waitlist_max_size=data.waitlist_max_size,
                waitlist_promote_policy=data.waitlist_promote_policy,
                overbooking_enabled=data.overbooking_enabled,
                overbooking_max=data.overbooking_max
            )
            set_create_audit(policy, operator_id)
            self.db.add(policy)

        await self.db.commit()
        await self.db.refresh(policy)
        return policy
