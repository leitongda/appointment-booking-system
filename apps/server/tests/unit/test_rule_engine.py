"""
规则引擎服务的单元测试

测试用例包括：
1. 规则匹配 (get_applicable_rule_set)
2. 时间窗校验 (check_action_window)
3. 冲突检查 (check_booking_conflicts)
4. 容量检查 (check_capacity_limits)
"""
import pytest
from datetime import datetime, date, time, timedelta
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock

from sqlalchemy import select

from app.modules.rule_engine import RuleEngineService
from app.models.rule_set import (
    RuleSet, RuleWindow, RuleBookingPolicy, RuleCheckinPolicy,
    RuleCapacityPolicy, ShiftType, RuleSetShiftType
)
from app.models.schedule import Schedule
from app.models.appointment import Appointment


# ==================== 测试辅助函数 ====================

def create_shift_type(code="OPD", name="门诊", enabled=True):
    """创建班次类型辅助函数"""
    return ShiftType(
        id=str(uuid4()),
        code=code,
        name=name,
        enabled=enabled,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )


def create_rule_set(
    name="测试规则组",
    enabled=True,
    priority=100,
    default_open_inclusive=True,
    default_close_inclusive=False
):
    """创建规则组辅助函数"""
    return RuleSet(
        id=str(uuid4()),
        name=name,
        enabled=enabled,
        priority=priority,
        default_open_inclusive=default_open_inclusive,
        default_close_inclusive=default_close_inclusive,
        time_source='SERVER',
        timezone_source='HOSPITAL',
        compare_precision='SECOND',
        rounding_mode='NONE',
        clock_skew_tolerance_sec=5,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )


def create_rule_window(
    rule_set_id,
    action="BOOK",
    reference_point="SHIFT_START",
    open_offset_sec=None,
    close_offset_sec=None,
    open_inclusive=None,
    close_inclusive=None,
    fail_policy="REJECT",
    enabled=True,
    fail_tag=None
):
    """创建时间窗辅助函数"""
    # 如果没有提供 fail_tag，根据 fail_policy 生成默认值
    if fail_tag is None:
        fail_tag = f"{action}_FAIL" if fail_policy == "REJECT" else None

    return RuleWindow(
        id=str(uuid4()),
        rule_set_id=rule_set_id,
        action=action,
        reference_point=reference_point,
        open_offset_sec=open_offset_sec,
        close_offset_sec=close_offset_sec,
        open_inclusive=open_inclusive,
        close_inclusive=close_inclusive,
        fail_policy=fail_policy,
        fail_tag=fail_tag,
        enabled=enabled,
        description=f"{action}时间窗",
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )


def create_booking_policy(
    rule_set_id,
    per_user_per_shift=1,
    per_user_per_day=None,
    per_user_per_week=None,
    conflict_same_shift="REJECT",
    conflict_overlap_time="REJECT",
    conflict_same_type_same_day="ALLOW"
):
    """创建预约策略辅助函数"""
    return RuleBookingPolicy(
        rule_set_id=rule_set_id,
        require_auth=True,
        require_patient_profile_complete=False,
        per_user_per_shift=per_user_per_shift,
        per_user_per_day=per_user_per_day,
        per_user_per_week=per_user_per_week,
        conflict_same_shift=conflict_same_shift,
        conflict_overlap_time=conflict_overlap_time,
        conflict_same_type_same_day=conflict_same_type_same_day,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )


def create_capacity_policy(
    rule_set_id,
    total_capacity=10,
    per_user_capacity=1,
    waitlist_enabled=False,
    waitlist_max_size=50,
    overbooking_enabled=False,
    overbooking_max=2
):
    """创建容量策略辅助函数"""
    return RuleCapacityPolicy(
        rule_set_id=rule_set_id,
        total_capacity=total_capacity,
        per_user_capacity=per_user_capacity,
        waitlist_enabled=waitlist_enabled,
        waitlist_max_size=waitlist_max_size,
        waitlist_promote_policy="MANUAL",
        overbooking_enabled=overbooking_enabled,
        overbooking_max=overbooking_max,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )


# ==================== 测试规则匹配 ====================

class TestGetApplicableRuleSet:
    """测试获取适用规则组"""

    @pytest.mark.asyncio
    async def test_get_applicable_rule_set_success(self, db_session):
        """测试成功获取适用规则组"""
        # 创建班次类型
        shift_type = create_shift_type()
        db_session.add(shift_type)

        # 创建规则组
        rule_set = create_rule_set(name="优先规则组", priority=10)
        db_session.add(rule_set)

        # 关联规则组和班次类型
        association = RuleSetShiftType(
            rule_set_id=rule_set.id,
            shift_type_id=shift_type.id
        )
        db_session.add(association)

        await db_session.commit()
        await db_session.refresh(rule_set)

        # 创建服务实例
        service = RuleEngineService(db_session)

        # 执行查询
        result = await service.get_applicable_rule_set(shift_type.id)

        # 验证结果
        assert result is not None
        assert result.id == rule_set.id
        assert result.name == "优先规则组"
        assert result.priority == 10

    @pytest.mark.asyncio
    async def test_get_applicable_rule_set_priority_order(self, db_session):
        """测试按优先级排序获取规则组"""
        # 创建班次类型
        shift_type = create_shift_type()
        db_session.add(shift_type)

        # 创建多个规则组，不同优先级
        rule_set_low = create_rule_set(name="低优先级", priority=100)
        rule_set_high = create_rule_set(name="高优先级", priority=10)
        rule_set_mid = create_rule_set(name="中优先级", priority=50)
        db_session.add_all([rule_set_low, rule_set_high, rule_set_mid])

        # 关联所有规则组到同一班次类型
        for rs in [rule_set_low, rule_set_high, rule_set_mid]:
            association = RuleSetShiftType(
                rule_set_id=rs.id,
                shift_type_id=shift_type.id
            )
            db_session.add(association)

        await db_session.commit()

        # 创建服务实例
        service = RuleEngineService(db_session)

        # 执行查询
        result = await service.get_applicable_rule_set(shift_type.id)

        # 验证结果：应返回优先级最高的（priority 最小）
        assert result is not None
        assert result.id == rule_set_high.id
        assert result.name == "高优先级"

    @pytest.mark.asyncio
    async def test_get_applicable_rule_set_not_found(self, db_session):
        """测试无适用规则时返回 None"""
        # 创建服务实例
        service = RuleEngineService(db_session)

        # 查询不存在的班次类型
        result = await service.get_applicable_rule_set(str(uuid4()))

        # 验证结果
        assert result is None

    @pytest.mark.asyncio
    async def test_get_applicable_rule_set_disabled(self, db_session):
        """测试禁用的规则组不匹配"""
        # 创建班次类型
        shift_type = create_shift_type()
        db_session.add(shift_type)

        # 创建禁用的规则组
        rule_set = create_rule_set(name="禁用规则组", enabled=False)
        db_session.add(rule_set)

        # 关联规则组和班次类型
        association = RuleSetShiftType(
            rule_set_id=rule_set.id,
            shift_type_id=shift_type.id
        )
        db_session.add(association)

        await db_session.commit()

        # 创建服务实例
        service = RuleEngineService(db_session)

        # 执行查询
        result = await service.get_applicable_rule_set(shift_type.id)

        # 验证结果
        assert result is None

    @pytest.mark.asyncio
    async def test_get_applicable_rule_set_shift_type_disabled(self, db_session):
        """测试禁用的班次类型不匹配"""
        # 创建禁用的班次类型
        shift_type = create_shift_type(enabled=False)
        db_session.add(shift_type)

        # 创建启用的规则组
        rule_set = create_rule_set(name="测试规则组", enabled=True)
        db_session.add(rule_set)

        # 关联规则组和班次类型
        association = RuleSetShiftType(
            rule_set_id=rule_set.id,
            shift_type_id=shift_type.id
        )
        db_session.add(association)

        await db_session.commit()

        # 创建服务实例
        service = RuleEngineService(db_session)

        # 执行查询
        result = await service.get_applicable_rule_set(shift_type.id)

        # 验证结果
        assert result is None


# ==================== 测试时间窗校验 ====================

class TestCheckActionWindow:
    """测试时间窗校验"""

    @pytest.mark.asyncio
    async def test_check_action_window_no_shift_type(self, db_session):
        """测试无班次类型时返回默认结果"""
        # 创建排班（无 shift_type_id）
        tomorrow = date.today() + timedelta(days=1)
        schedule = Schedule(
            id=str(uuid4()),
            doctor_id=str(uuid4()),
            store_id=str(uuid4()),
            schedule_date=tomorrow,
            time_slot="morning",
            start_time=time(8, 0),
            end_time=time(12, 0),
            total_slots=10,
            booked_slots=0,
            status=1,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db_session.add(schedule)
        await db_session.commit()

        # 创建服务实例
        service = RuleEngineService(db_session)

        # 执行检查
        result = await service.check_action_window(schedule, "BOOK")

        # 验证结果
        assert result["allowed"] is True
        assert result["fail_policy"] == "ALLOW"
        assert result["message"] == "使用默认配置"

    @pytest.mark.asyncio
    async def test_check_action_window_no_rule_set(self, db_session):
        """测试无规则组时返回默认结果"""
        # 创建班次类型
        shift_type = create_shift_type()
        db_session.add(shift_type)

        # 创建排班（有 shift_type_id 但无规则组）
        tomorrow = date.today() + timedelta(days=1)
        schedule = Schedule(
            id=str(uuid4()),
            doctor_id=str(uuid4()),
            store_id=str(uuid4()),
            schedule_date=tomorrow,
            time_slot="morning",
            start_time=time(8, 0),
            end_time=time(12, 0),
            total_slots=10,
            booked_slots=0,
            status=1,
            shift_type_id=shift_type.id,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db_session.add(schedule)
        await db_session.commit()

        # 创建服务实例
        service = RuleEngineService(db_session)

        # 执行检查
        result = await service.check_action_window(schedule, "BOOK")

        # 验证结果
        assert result["allowed"] is True
        assert result["fail_policy"] == "ALLOW"
        assert result["message"] == "使用默认配置"

    @pytest.mark.asyncio
    async def test_check_action_window_single_window_allowed(self, db_session):
        """测试单时间窗校验通过"""
        import pytz

        # 创建班次类型
        shift_type = create_shift_type()
        db_session.add(shift_type)

        # 创建规则组
        rule_set = create_rule_set()
        db_session.add(rule_set)

        # 关联规则组和班次类型
        association = RuleSetShiftType(
            rule_set_id=rule_set.id,
            shift_type_id=shift_type.id
        )
        db_session.add(association)

        # 创建时间窗：班次开始前3天开放，前1小时截止
        window = create_rule_window(
            rule_set_id=rule_set.id,
            action="BOOK",
            reference_point="SHIFT_START",
            open_offset_sec=-3 * 24 * 3600,  # 前3天
            close_offset_sec=-3600,  # 前1小时
        )
        db_session.add(window)

        # 创建排班
        tz = pytz.timezone('Asia/Shanghai')
        tomorrow = date.today() + timedelta(days=1)
        schedule_start = tz.localize(datetime.combine(tomorrow, time(8, 0)))
        schedule = Schedule(
            id=str(uuid4()),
            doctor_id=str(uuid4()),
            store_id=str(uuid4()),
            schedule_date=tomorrow,
            time_slot="morning",
            start_time=time(8, 0),
            end_time=time(12, 0),
            total_slots=10,
            booked_slots=0,
            status=1,
            shift_type_id=shift_type.id,
            start_at=schedule_start,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db_session.add(schedule)
        await db_session.commit()

        # 创建服务实例
        service = RuleEngineService(db_session)

        # 当前时间在窗口内（前2天）
        current_time = schedule_start - timedelta(days=2)

        # 执行检查
        result = await service.check_action_window(
            schedule, "BOOK", current_time=current_time
        )

        # 验证结果
        assert result["allowed"] is True
        assert result["fail_policy"] == "ALLOW"
        assert result["message"] == "操作允许"

    @pytest.mark.asyncio
    async def test_check_action_window_before_open(self, db_session):
        """测试未到开放时间"""
        import pytz

        # 创建班次类型
        shift_type = create_shift_type()
        db_session.add(shift_type)

        # 创建规则组
        rule_set = create_rule_set()
        db_session.add(rule_set)

        # 关联规则组和班次类型
        association = RuleSetShiftType(
            rule_set_id=rule_set.id,
            shift_type_id=shift_type.id
        )
        db_session.add(association)

        # 创建时间窗：班次开始前3天开放
        window = create_rule_window(
            rule_set_id=rule_set.id,
            action="BOOK",
            reference_point="SHIFT_START",
            open_offset_sec=-3 * 24 * 3600,  # 前3天
            close_offset_sec=-3600,  # 前1小时
        )
        db_session.add(window)

        # 创建排班
        tz = pytz.timezone('Asia/Shanghai')
        tomorrow = date.today() + timedelta(days=1)
        schedule_start = tz.localize(datetime.combine(tomorrow, time(8, 0)))
        schedule = Schedule(
            id=str(uuid4()),
            doctor_id=str(uuid4()),
            store_id=str(uuid4()),
            schedule_date=tomorrow,
            time_slot="morning",
            start_time=time(8, 0),
            end_time=time(12, 0),
            total_slots=10,
            booked_slots=0,
            status=1,
            shift_type_id=shift_type.id,
            start_at=schedule_start,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db_session.add(schedule)
        await db_session.commit()

        # 创建服务实例
        service = RuleEngineService(db_session)

        # 当前时间在开放前（前5天）
        current_time = schedule_start - timedelta(days=5)

        # 执行检查
        result = await service.check_action_window(
            schedule, "BOOK", current_time=current_time
        )

        # 验证结果
        assert result["allowed"] is False
        assert result["fail_policy"] == "REJECT"
        # 消息可能包含 "预约操作不允许" 或时间相关提示
        assert result["message"] is not None and len(result["message"]) > 0

    @pytest.mark.asyncio
    async def test_check_action_window_after_close(self, db_session):
        """测试已过截止时间"""
        import pytz

        # 创建班次类型
        shift_type = create_shift_type()
        db_session.add(shift_type)

        # 创建规则组
        rule_set = create_rule_set()
        db_session.add(rule_set)

        # 关联规则组和班次类型
        association = RuleSetShiftType(
            rule_set_id=rule_set.id,
            shift_type_id=shift_type.id
        )
        db_session.add(association)

        # 创建时间窗：班次开始前1小时截止
        window = create_rule_window(
            rule_set_id=rule_set.id,
            action="BOOK",
            reference_point="SHIFT_START",
            open_offset_sec=-3 * 24 * 3600,  # 前3天
            close_offset_sec=-3600,  # 前1小时
        )
        db_session.add(window)

        # 创建排班
        tz = pytz.timezone('Asia/Shanghai')
        tomorrow = date.today() + timedelta(days=1)
        schedule_start = tz.localize(datetime.combine(tomorrow, time(8, 0)))
        schedule = Schedule(
            id=str(uuid4()),
            doctor_id=str(uuid4()),
            store_id=str(uuid4()),
            schedule_date=tomorrow,
            time_slot="morning",
            start_time=time(8, 0),
            end_time=time(12, 0),
            total_slots=10,
            booked_slots=0,
            status=1,
            shift_type_id=shift_type.id,
            start_at=schedule_start,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db_session.add(schedule)
        await db_session.commit()

        # 创建服务实例
        service = RuleEngineService(db_session)

        # 当前时间在截止后（前30分钟）
        current_time = schedule_start - timedelta(minutes=30)

        # 执行检查
        result = await service.check_action_window(
            schedule, "BOOK", current_time=current_time
        )

        # 验证结果
        assert result["allowed"] is False
        assert result["fail_policy"] == "REJECT"
        # 消息可能包含 "预约操作不允许" 或时间相关提示
        assert result["message"] is not None and len(result["message"]) > 0

    @pytest.mark.asyncio
    async def test_check_action_window_multiple_windows_and_logic(self, db_session):
        """测试多时间窗组合（AND 逻辑）"""
        import pytz

        # 创建班次类型
        shift_type = create_shift_type()
        db_session.add(shift_type)

        # 创建规则组
        rule_set = create_rule_set()
        db_session.add(rule_set)

        # 关联规则组和班次类型
        association = RuleSetShiftType(
            rule_set_id=rule_set.id,
            shift_type_id=shift_type.id
        )
        db_session.add(association)

        # 创建两个时间窗（AND 逻辑，都需要满足）
        window1 = create_rule_window(
            rule_set_id=rule_set.id,
            action="BOOK",
            reference_point="SHIFT_START",
            open_offset_sec=-3 * 24 * 3600,  # 前3天
            close_offset_sec=-3600,  # 前1小时
        )
        window2 = create_rule_window(
            rule_set_id=rule_set.id,
            action="BOOK",
            reference_point="SHIFT_END",
            open_offset_sec=-4 * 24 * 3600,  # 班次结束前4天
            close_offset_sec=-7200,  # 班次结束前2小时
        )
        db_session.add_all([window1, window2])

        # 创建排班
        tz = pytz.timezone('Asia/Shanghai')
        tomorrow = date.today() + timedelta(days=1)
        schedule_start = tz.localize(datetime.combine(tomorrow, time(8, 0)))
        schedule_end = tz.localize(datetime.combine(tomorrow, time(12, 0)))
        schedule = Schedule(
            id=str(uuid4()),
            doctor_id=str(uuid4()),
            store_id=str(uuid4()),
            schedule_date=tomorrow,
            time_slot="morning",
            start_time=time(8, 0),
            end_time=time(12, 0),
            total_slots=10,
            booked_slots=0,
            status=1,
            shift_type_id=shift_type.id,
            start_at=schedule_start,
            end_at=schedule_end,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db_session.add(schedule)
        await db_session.commit()

        # 创建服务实例
        service = RuleEngineService(db_session)

        # 当前时间在两个窗口内（前2天）
        current_time = schedule_start - timedelta(days=2)

        # 执行检查
        result = await service.check_action_window(
            schedule, "BOOK", current_time=current_time
        )

        # 验证结果：应该通过（两个窗口都满足）
        assert result["allowed"] is True
        assert result["fail_policy"] == "ALLOW"

    @pytest.mark.asyncio
    async def test_check_action_window_boundary_inclusive(self, db_session):
        """测试边界包含"""
        import pytz

        # 创建班次类型
        shift_type = create_shift_type()
        db_session.add(shift_type)

        # 创建规则组（边界包含）
        rule_set = create_rule_set(
            default_open_inclusive=True,
            default_close_inclusive=True
        )
        db_session.add(rule_set)

        # 关联规则组和班次类型
        association = RuleSetShiftType(
            rule_set_id=rule_set.id,
            shift_type_id=shift_type.id
        )
        db_session.add(association)

        # 创建时间窗
        tz = pytz.timezone('Asia/Shanghai')
        tomorrow = date.today() + timedelta(days=1)
        schedule_start = tz.localize(datetime.combine(tomorrow, time(8, 0)))

        window = create_rule_window(
            rule_set_id=rule_set.id,
            action="BOOK",
            reference_point="SHIFT_START",
            open_offset_sec=-86400,  # 恰好1天前
            close_offset_sec=-3600,  # 恰好1小时前
            open_inclusive=True,
            close_inclusive=True,
        )
        db_session.add(window)

        # 创建排班
        schedule = Schedule(
            id=str(uuid4()),
            doctor_id=str(uuid4()),
            store_id=str(uuid4()),
            schedule_date=tomorrow,
            time_slot="morning",
            start_time=time(8, 0),
            end_time=time(12, 0),
            total_slots=10,
            booked_slots=0,
            status=1,
            shift_type_id=shift_type.id,
            start_at=schedule_start,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db_session.add(schedule)
        await db_session.commit()

        # 创建服务实例
        service = RuleEngineService(db_session)

        # 测试开放边界（恰好等于开放时间）
        current_time = schedule_start - timedelta(days=1)
        result = await service.check_action_window(
            schedule, "BOOK", current_time=current_time
        )
        assert result["allowed"] is True  # 边界包含应允许

        # 测试截止边界（恰好等于截止时间）
        current_time = schedule_start - timedelta(hours=1)
        result = await service.check_action_window(
            schedule, "BOOK", current_time=current_time
        )
        assert result["allowed"] is True  # 边界包含应允许

    @pytest.mark.asyncio
    async def test_check_action_window_null_offset_unbounded(self, db_session):
        """测试 offset 为 None 表示无限边界"""
        import pytz

        # 创建班次类型
        shift_type = create_shift_type()
        db_session.add(shift_type)

        # 创建规则组
        rule_set = create_rule_set()
        db_session.add(rule_set)

        # 关联规则组和班次类型
        association = RuleSetShiftType(
            rule_set_id=rule_set.id,
            shift_type_id=shift_type.id
        )
        db_session.add(association)

        # 创建时间窗（open_offset_sec=None 表示无下限）
        window = create_rule_window(
            rule_set_id=rule_set.id,
            action="BOOK",
            reference_point="SHIFT_START",
            open_offset_sec=None,  # 无下限
            close_offset_sec=-3600,  # 前1小时截止
        )
        db_session.add(window)

        # 创建排班
        tz = pytz.timezone('Asia/Shanghai')
        tomorrow = date.today() + timedelta(days=1)
        schedule_start = tz.localize(datetime.combine(tomorrow, time(8, 0)))
        schedule = Schedule(
            id=str(uuid4()),
            doctor_id=str(uuid4()),
            store_id=str(uuid4()),
            schedule_date=tomorrow,
            time_slot="morning",
            start_time=time(8, 0),
            end_time=time(12, 0),
            total_slots=10,
            booked_slots=0,
            status=1,
            shift_type_id=shift_type.id,
            start_at=schedule_start,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db_session.add(schedule)
        await db_session.commit()

        # 创建服务实例
        service = RuleEngineService(db_session)

        # 当前时间很早（前100天），应该仍然允许
        current_time = schedule_start - timedelta(days=100)

        # 执行检查
        result = await service.check_action_window(
            schedule, "BOOK", current_time=current_time
        )

        # 验证结果
        assert result["allowed"] is True

    @pytest.mark.asyncio
    async def test_check_action_window_fail_policy_allow_with_tag(self, db_session):
        """测试失败策略 ALLOW_WITH_TAG"""
        import pytz

        # 创建班次类型
        shift_type = create_shift_type()
        db_session.add(shift_type)

        # 创建规则组
        rule_set = create_rule_set()
        db_session.add(rule_set)

        # 关联规则组和班次类型
        association = RuleSetShiftType(
            rule_set_id=rule_set.id,
            shift_type_id=shift_type.id
        )
        db_session.add(association)

        # 创建时间窗（失败策略为 ALLOW_WITH_TAG）
        window = create_rule_window(
            rule_set_id=rule_set.id,
            action="BOOK",
            reference_point="SHIFT_START",
            open_offset_sec=-86400,  # 前1天
            close_offset_sec=-3600,  # 前1小时
            fail_policy="ALLOW_WITH_TAG",
            fail_tag="EARLY_BOOKING",
        )
        db_session.add(window)

        # 创建排班
        tz = pytz.timezone('Asia/Shanghai')
        tomorrow = date.today() + timedelta(days=1)
        schedule_start = tz.localize(datetime.combine(tomorrow, time(8, 0)))
        schedule = Schedule(
            id=str(uuid4()),
            doctor_id=str(uuid4()),
            store_id=str(uuid4()),
            schedule_date=tomorrow,
            time_slot="morning",
            start_time=time(8, 0),
            end_time=time(12, 0),
            total_slots=10,
            booked_slots=0,
            status=1,
            shift_type_id=shift_type.id,
            start_at=schedule_start,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db_session.add(schedule)
        await db_session.commit()

        # 创建服务实例
        service = RuleEngineService(db_session)

        # 当前时间在窗口外（前2天）
        current_time = schedule_start - timedelta(days=2)

        # 执行检查
        result = await service.check_action_window(
            schedule, "BOOK", current_time=current_time
        )

        # 验证结果
        assert result["allowed"] is False
        assert result["fail_policy"] == "ALLOW_WITH_TAG"
        assert result["fail_tag"] == "EARLY_BOOKING"


# ==================== 测试冲突检查 ====================

class TestCheckBookingConflicts:
    """测试预约冲突检查"""

    @pytest.mark.asyncio
    async def test_check_conflicts_per_user_per_shift(self, db_session):
        """测试每班次限约数检查"""
        # 创建班次类型
        shift_type = create_shift_type()
        db_session.add(shift_type)

        # 创建规则组
        rule_set = create_rule_set()
        db_session.add(rule_set)

        # 关联规则组和班次类型
        association = RuleSetShiftType(
            rule_set_id=rule_set.id,
            shift_type_id=shift_type.id
        )
        db_session.add(association)

        # 创建预约策略（每班次限约2次）
        policy = create_booking_policy(
            rule_set_id=rule_set.id,
            per_user_per_shift=2
        )
        db_session.add(policy)

        # 创建排班
        tomorrow = date.today() + timedelta(days=1)
        schedule = Schedule(
            id=str(uuid4()),
            doctor_id=str(uuid4()),
            store_id=str(uuid4()),
            schedule_date=tomorrow,
            time_slot="morning",
            start_time=time(8, 0),
            end_time=time(12, 0),
            total_slots=10,
            booked_slots=0,
            status=1,
            shift_type_id=shift_type.id,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db_session.add(schedule)

        # 创建用户
        user_id = str(uuid4())

        # 创建2个已有预约（达到上限）
        for i in range(2):
            appointment = Appointment(
                id=str(uuid4()),
                appointment_no=f"YY{i}",
                user_id=user_id,
                patient_id=str(uuid4()),
                doctor_id=str(uuid4()),
                schedule_id=schedule.id,
                queue_number=i + 1,
                status=1,  # 已预约
                patient_name=f"病人{i}",
                patient_phone="1380013800{i}",
                doctor_name="测试医生",
                department_name="测试科室",
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
            db_session.add(appointment)

        await db_session.commit()

        # 创建服务实例
        service = RuleEngineService(db_session)

        # 执行冲突检查
        result = await service.check_booking_conflicts(
            db=db_session,
            shift_id=schedule.id,
            user_id=user_id,
            policy=policy,
            booking_time=datetime.now(),
            schedule=schedule,
        )

        # 验证结果
        assert result["allowed"] is False
        assert "每班次最多" in result["reason"]
        assert result["conflict_with"] is None

    @pytest.mark.asyncio
    async def test_check_conflicts_same_shift_reject(self, db_session):
        """测试同班次冲突策略 REJECT"""
        # 创建班次类型
        shift_type = create_shift_type()
        db_session.add(shift_type)

        # 创建规则组
        rule_set = create_rule_set()
        db_session.add(rule_set)

        # 关联规则组和班次类型
        association = RuleSetShiftType(
            rule_set_id=rule_set.id,
            shift_type_id=shift_type.id
        )
        db_session.add(association)

        # 创建预约策略（同班次冲突策略为 REJECT，但不限制每班次次数）
        policy = create_booking_policy(
            rule_set_id=rule_set.id,
            per_user_per_shift=0,  # 0 表示不限制
            conflict_same_shift="REJECT"
        )
        db_session.add(policy)

        # 创建排班
        tomorrow = date.today() + timedelta(days=1)
        schedule = Schedule(
            id=str(uuid4()),
            doctor_id=str(uuid4()),
            store_id=str(uuid4()),
            schedule_date=tomorrow,
            time_slot="morning",
            start_time=time(8, 0),
            end_time=time(12, 0),
            total_slots=10,
            booked_slots=0,
            status=1,
            shift_type_id=shift_type.id,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db_session.add(schedule)

        # 创建用户
        user_id = str(uuid4())

        # 创建已有预约
        appointment = Appointment(
            id=str(uuid4()),
            appointment_no="YY001",
            user_id=user_id,
            patient_id=str(uuid4()),
            doctor_id=str(uuid4()),
            schedule_id=schedule.id,
            queue_number=1,
            status=1,  # 已预约
            patient_name="病人1",
            patient_phone="13800138001",
            doctor_name="测试医生",
            department_name="测试科室",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db_session.add(appointment)

        await db_session.commit()

        # 创建服务实例
        service = RuleEngineService(db_session)

        # 执行冲突检查
        result = await service.check_booking_conflicts(
            db=db_session,
            shift_id=schedule.id,
            user_id=user_id,
            policy=policy,
            booking_time=datetime.now(),
            schedule=schedule,
        )

        # 验证结果
        assert result["allowed"] is False
        assert result["reason"] is not None and len(result["reason"]) > 0

    @pytest.mark.asyncio
    async def test_check_conflicts_per_user_per_day(self, db_session):
        """测试每日限约数检查"""
        # 创建班次类型
        shift_type = create_shift_type()
        db_session.add(shift_type)

        # 创建规则组
        rule_set = create_rule_set()
        db_session.add(rule_set)

        # 关联规则组和班次类型
        association = RuleSetShiftType(
            rule_set_id=rule_set.id,
            shift_type_id=shift_type.id
        )
        db_session.add(association)

        # 创建预约策略（每日限约3次，不限制每班次次数）
        policy = create_booking_policy(
            rule_set_id=rule_set.id,
            per_user_per_shift=0,  # 0 表示不限制
            per_user_per_day=3
        )
        db_session.add(policy)

        # 创建多个排班（同一天）
        tomorrow = date.today() + timedelta(days=1)
        schedules = []
        for i in range(3):
            schedule = Schedule(
                id=str(uuid4()),
                doctor_id=str(uuid4()),
                store_id=str(uuid4()),
                schedule_date=tomorrow,
                time_slot="morning" if i < 2 else "afternoon",
                start_time=time(8 + i * 4, 0),
                end_time=time(12 + i * 4, 0),
                total_slots=10,
                booked_slots=0,
                status=1,
                shift_type_id=shift_type.id,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
            db_session.add(schedule)
            schedules.append(schedule)

        # 创建用户
        user_id = str(uuid4())

        # 创建3个已有预约（达到每日上限）
        for i, schedule in enumerate(schedules):
            appointment = Appointment(
                id=str(uuid4()),
                appointment_no=f"YY{i}",
                user_id=user_id,
                patient_id=str(uuid4()),
                doctor_id=str(uuid4()),
                schedule_id=schedule.id,
                queue_number=i + 1,
                status=1,  # 已预约
                patient_name=f"病人{i}",
                patient_phone=f"1380013800{i}",
                doctor_name="测试医生",
                department_name="测试科室",
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
            db_session.add(appointment)

        await db_session.commit()

        # 创建服务实例
        service = RuleEngineService(db_session)

        # 尝试预约第4个班次
        result = await service.check_booking_conflicts(
            db=db_session,
            shift_id=schedules[0].id,
            user_id=user_id,
            policy=policy,
            booking_time=datetime.now(),
            schedule=schedules[0],
        )

        # 验证结果
        assert result["allowed"] is False
        assert result["reason"] is not None and len(result["reason"]) > 0

    @pytest.mark.asyncio
    async def test_check_conflicts_per_user_per_week(self, db_session):
        """测试每周限约数检查"""
        # 创建班次类型
        shift_type = create_shift_type()
        db_session.add(shift_type)

        # 创建规则组
        rule_set = create_rule_set()
        db_session.add(rule_set)

        # 关联规则组和班次类型
        association = RuleSetShiftType(
            rule_set_id=rule_set.id,
            shift_type_id=shift_type.id
        )
        db_session.add(association)

        # 创建预约策略（每周限约5次，不限制每班次和每日次数）
        policy = create_booking_policy(
            rule_set_id=rule_set.id,
            per_user_per_shift=0,  # 0 表示不限制
            per_user_per_day=0,  # 0 表示不限制
            per_user_per_week=5
        )
        db_session.add(policy)

        # 创建本周的多个排班
        today = date.today()
        monday = today - timedelta(days=today.weekday())
        schedules = []
        for i in range(5):
            schedule_date = monday + timedelta(days=i)
            schedule = Schedule(
                id=str(uuid4()),
                doctor_id=str(uuid4()),
                store_id=str(uuid4()),
                schedule_date=schedule_date,
                time_slot="morning",
                start_time=time(8, 0),
                end_time=time(12, 0),
                total_slots=10,
                booked_slots=0,
                status=1,
                shift_type_id=shift_type.id,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
            db_session.add(schedule)
            schedules.append(schedule)

        # 创建用户
        user_id = str(uuid4())

        # 创建5个已有预约（达到每周上限）
        for i, schedule in enumerate(schedules):
            appointment = Appointment(
                id=str(uuid4()),
                appointment_no=f"YY{i}",
                user_id=user_id,
                patient_id=str(uuid4()),
                doctor_id=str(uuid4()),
                schedule_id=schedule.id,
                queue_number=i + 1,
                status=1,  # 已预约
                patient_name=f"病人{i}",
                patient_phone=f"1380013800{i}",
                doctor_name="测试医生",
                department_name="测试科室",
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
            db_session.add(appointment)

        await db_session.commit()

        # 创建服务实例
        service = RuleEngineService(db_session)

        # 尝试预约本周的第6个班次
        result = await service.check_booking_conflicts(
            db=db_session,
            shift_id=schedules[0].id,
            user_id=user_id,
            policy=policy,
            booking_time=datetime.now(),
            schedule=schedules[0],
        )

        # 验证结果
        assert result["allowed"] is False
        assert result["reason"] is not None and len(result["reason"]) > 0

    @pytest.mark.asyncio
    async def test_check_conflicts_overlap_time_reject(self, db_session):
        """测试时间重叠冲突检查"""
        # 创建班次类型
        shift_type = create_shift_type()
        db_session.add(shift_type)

        # 创建规则组
        rule_set = create_rule_set()
        db_session.add(rule_set)

        # 关联规则组和班次类型
        association = RuleSetShiftType(
            rule_set_id=rule_set.id,
            shift_type_id=shift_type.id
        )
        db_session.add(association)

        # 创建预约策略（时间重叠策略为 REJECT）
        policy = create_booking_policy(
            rule_set_id=rule_set.id,
            conflict_overlap_time="REJECT"
        )
        db_session.add(policy)

        # 创建两个重叠的排班
        tomorrow = date.today() + timedelta(days=1)
        schedule1 = Schedule(
            id=str(uuid4()),
            doctor_id=str(uuid4()),
            store_id=str(uuid4()),
            schedule_date=tomorrow,
            time_slot="morning",
            start_time=time(8, 0),
            end_time=time(12, 0),
            total_slots=10,
            booked_slots=0,
            status=1,
            shift_type_id=shift_type.id,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        schedule2 = Schedule(
            id=str(uuid4()),
            doctor_id=str(uuid4()),
            store_id=str(uuid4()),
            schedule_date=tomorrow,
            time_slot="morning",
            start_time=time(10, 0),  # 重叠
            end_time=time(14, 0),
            total_slots=10,
            booked_slots=0,
            status=1,
            shift_type_id=shift_type.id,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db_session.add_all([schedule1, schedule2])

        # 创建用户
        user_id = str(uuid4())

        # 创建已有预约（schedule1）
        appointment = Appointment(
            id=str(uuid4()),
            appointment_no="YY001",
            user_id=user_id,
            patient_id=str(uuid4()),
            doctor_id=str(uuid4()),
            schedule_id=schedule1.id,
            queue_number=1,
            status=1,  # 已预约
            patient_name="病人1",
            patient_phone="13800138001",
            doctor_name="测试医生",
            department_name="测试科室",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db_session.add(appointment)

        await db_session.commit()

        # 创建服务实例
        service = RuleEngineService(db_session)

        # 尝试预约 schedule2（与 schedule1 重叠）
        result = await service.check_booking_conflicts(
            db=db_session,
            shift_id=schedule2.id,
            user_id=user_id,
            policy=policy,
            booking_time=datetime.now(),
            schedule=schedule2,
        )

        # 验证结果
        assert result["allowed"] is False
        assert "时间冲突" in result["reason"] or "重叠" in result["reason"]
        assert result["conflict_with"] is not None
        assert result["conflict_with"]["schedule_id"] == schedule1.id

    @pytest.mark.asyncio
    async def test_check_conflicts_same_type_same_day_reject(self, db_session):
        """测试同类型同日冲突检查"""
        # 创建班次类型
        shift_type = create_shift_type()
        db_session.add(shift_type)

        # 创建规则组
        rule_set = create_rule_set()
        db_session.add(rule_set)

        # 关联规则组和班次类型
        association = RuleSetShiftType(
            rule_set_id=rule_set.id,
            shift_type_id=shift_type.id
        )
        db_session.add(association)

        # 创建预约策略（同类型同日策略为 REJECT）
        policy = create_booking_policy(
            rule_set_id=rule_set.id,
            conflict_same_type_same_day="REJECT"
        )
        db_session.add(policy)

        # 创建两个同类型的排班
        tomorrow = date.today() + timedelta(days=1)
        schedule1 = Schedule(
            id=str(uuid4()),
            doctor_id=str(uuid4()),
            store_id=str(uuid4()),
            schedule_date=tomorrow,
            time_slot="morning",
            start_time=time(8, 0),
            end_time=time(12, 0),
            total_slots=10,
            booked_slots=0,
            status=1,
            shift_type_id=shift_type.id,
            appointment_type="expert",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        schedule2 = Schedule(
            id=str(uuid4()),
            doctor_id=str(uuid4()),
            store_id=str(uuid4()),
            schedule_date=tomorrow,
            time_slot="afternoon",
            start_time=time(14, 0),
            end_time=time(18, 0),
            total_slots=10,
            booked_slots=0,
            status=1,
            shift_type_id=shift_type.id,
            appointment_type="expert",  # 同类型
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db_session.add_all([schedule1, schedule2])

        # 创建用户
        user_id = str(uuid4())

        # 创建已有预约（schedule1）
        appointment = Appointment(
            id=str(uuid4()),
            appointment_no="YY001",
            user_id=user_id,
            patient_id=str(uuid4()),
            doctor_id=str(uuid4()),
            schedule_id=schedule1.id,
            queue_number=1,
            status=1,  # 已预约
            patient_name="病人1",
            patient_phone="13800138001",
            doctor_name="测试医生",
            department_name="测试科室",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db_session.add(appointment)

        await db_session.commit()

        # 创建服务实例
        service = RuleEngineService(db_session)

        # 尝试预约 schedule2（同类型同日）
        result = await service.check_booking_conflicts(
            db=db_session,
            shift_id=schedule2.id,
            user_id=user_id,
            policy=policy,
            booking_time=datetime.now(),
            schedule=schedule2,
        )

        # 验证结果
        assert result["allowed"] is False
        assert "同类型" in result["reason"] or "限一次" in result["reason"]
        assert result["conflict_with"] is not None
        assert result["conflict_with"]["appointment_type"] == "expert"

    @pytest.mark.asyncio
    async def test_check_conflicts_no_conflicts(self, db_session):
        """测试无冲突情况"""
        # 创建班次类型
        shift_type = create_shift_type()
        db_session.add(shift_type)

        # 创建规则组
        rule_set = create_rule_set()
        db_session.add(rule_set)

        # 关联规则组和班次类型
        association = RuleSetShiftType(
            rule_set_id=rule_set.id,
            shift_type_id=shift_type.id
        )
        db_session.add(association)

        # 创建预约策略（宽松策略）
        policy = create_booking_policy(
            rule_set_id=rule_set.id,
            per_user_per_shift=1,
            per_user_per_day=10,
            per_user_per_week=50,
            conflict_same_shift="REJECT",
            conflict_overlap_time="ALLOW",
            conflict_same_type_same_day="ALLOW",
        )
        db_session.add(policy)

        # 创建排班
        tomorrow = date.today() + timedelta(days=1)
        schedule = Schedule(
            id=str(uuid4()),
            doctor_id=str(uuid4()),
            store_id=str(uuid4()),
            schedule_date=tomorrow,
            time_slot="morning",
            start_time=time(8, 0),
            end_time=time(12, 0),
            total_slots=10,
            booked_slots=0,
            status=1,
            shift_type_id=shift_type.id,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db_session.add(schedule)

        # 创建用户
        user_id = str(uuid4())

        await db_session.commit()

        # 创建服务实例
        service = RuleEngineService(db_session)

        # 执行冲突检查（无任何预约）
        result = await service.check_booking_conflicts(
            db=db_session,
            shift_id=schedule.id,
            user_id=user_id,
            policy=policy,
            booking_time=datetime.now(),
            schedule=schedule,
        )

        # 验证结果
        assert result["allowed"] is True
        assert result["reason"] is None
        assert result["conflict_with"] is None


# ==================== 测试容量检查 ====================

class TestCheckCapacityLimits:
    """测试容量限制检查"""

    @pytest.mark.asyncio
    async def test_check_capacity_total_capacity(self, db_session):
        """测试总容量限制检查"""
        # 创建班次类型
        shift_type = create_shift_type()
        db_session.add(shift_type)

        # 创建规则组
        rule_set = create_rule_set()
        db_session.add(rule_set)

        # 关联规则组和班次类型
        association = RuleSetShiftType(
            rule_set_id=rule_set.id,
            shift_type_id=shift_type.id
        )
        db_session.add(association)

        # 创建容量策略（总容量10）
        policy = create_capacity_policy(
            rule_set_id=rule_set.id,
            total_capacity=10,
            waitlist_enabled=False,
            overbooking_enabled=False,
        )
        db_session.add(policy)

        # 创建排班
        tomorrow = date.today() + timedelta(days=1)
        schedule = Schedule(
            id=str(uuid4()),
            doctor_id=str(uuid4()),
            store_id=str(uuid4()),
            schedule_date=tomorrow,
            time_slot="morning",
            start_time=time(8, 0),
            end_time=time(12, 0),
            total_slots=10,
            booked_slots=0,
            status=1,
            shift_type_id=shift_type.id,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db_session.add(schedule)

        # 创建10个预约（达到上限）
        user_id = str(uuid4())
        for i in range(10):
            appointment = Appointment(
                id=str(uuid4()),
                appointment_no=f"YY{i}",
                user_id=user_id if i < 5 else str(uuid4()),
                patient_id=str(uuid4()),
                doctor_id=str(uuid4()),
                schedule_id=schedule.id,
                queue_number=i + 1,
                status=1,  # 已预约
                patient_name=f"病人{i}",
                patient_phone=f"1380013800{i}",
                doctor_name="测试医生",
                department_name="测试科室",
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
            db_session.add(appointment)

        await db_session.commit()

        # 创建服务实例
        service = RuleEngineService(db_session)

        # 执行容量检查
        result = await service.check_capacity_limits(
            db=db_session,
            shift_id=schedule.id,
            user_id=str(uuid4()),
            policy=policy,
        )

        # 验证结果
        assert result["allowed"] is False
        assert "已约满" in result["reason"] or "总容量" in result["reason"]
        assert result["waitlist_position"] is None

    @pytest.mark.asyncio
    async def test_check_capacity_per_user(self, db_session):
        """测试每用户容量限制检查"""
        # 创建班次类型
        shift_type = create_shift_type()
        db_session.add(shift_type)

        # 创建规则组
        rule_set = create_rule_set()
        db_session.add(rule_set)

        # 关联规则组和班次类型
        association = RuleSetShiftType(
            rule_set_id=rule_set.id,
            shift_type_id=shift_type.id
        )
        db_session.add(association)

        # 创建容量策略（每用户容量2）
        policy = create_capacity_policy(
            rule_set_id=rule_set.id,
            total_capacity=20,
            per_user_capacity=2,
        )
        db_session.add(policy)

        # 创建排班
        tomorrow = date.today() + timedelta(days=1)
        schedule = Schedule(
            id=str(uuid4()),
            doctor_id=str(uuid4()),
            store_id=str(uuid4()),
            schedule_date=tomorrow,
            time_slot="morning",
            start_time=time(8, 0),
            end_time=time(12, 0),
            total_slots=20,
            booked_slots=0,
            status=1,
            shift_type_id=shift_type.id,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db_session.add(schedule)

        # 创建用户和2个预约（达到用户上限）
        user_id = str(uuid4())
        for i in range(2):
            appointment = Appointment(
                id=str(uuid4()),
                appointment_no=f"YY{i}",
                user_id=user_id,
                patient_id=str(uuid4()),
                doctor_id=str(uuid4()),
                schedule_id=schedule.id,
                queue_number=i + 1,
                status=1,  # 已预约
                patient_name=f"病人{i}",
                patient_phone=f"1380013800{i}",
                doctor_name="测试医生",
                department_name="测试科室",
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
            db_session.add(appointment)

        await db_session.commit()

        # 创建服务实例
        service = RuleEngineService(db_session)

        # 执行容量检查
        result = await service.check_capacity_limits(
            db=db_session,
            shift_id=schedule.id,
            user_id=user_id,
            policy=policy,
        )

        # 验证结果
        assert result["allowed"] is False
        assert "预约上限" in result["reason"] or "达到" in result["reason"]

    @pytest.mark.asyncio
    async def test_check_capacity_waitlist_enabled(self, db_session):
        """测试候补队列启用"""
        # 创建班次类型
        shift_type = create_shift_type()
        db_session.add(shift_type)

        # 创建规则组
        rule_set = create_rule_set()
        db_session.add(rule_set)

        # 关联规则组和班次类型
        association = RuleSetShiftType(
            rule_set_id=rule_set.id,
            shift_type_id=shift_type.id
        )
        db_session.add(association)

        # 创建容量策略（启用候补）
        policy = create_capacity_policy(
            rule_set_id=rule_set.id,
            total_capacity=10,
            waitlist_enabled=True,
            waitlist_max_size=50,
        )
        db_session.add(policy)

        # 创建排班
        tomorrow = date.today() + timedelta(days=1)
        schedule = Schedule(
            id=str(uuid4()),
            doctor_id=str(uuid4()),
            store_id=str(uuid4()),
            schedule_date=tomorrow,
            time_slot="morning",
            start_time=time(8, 0),
            end_time=time(12, 0),
            total_slots=10,
            booked_slots=0,
            status=1,
            shift_type_id=shift_type.id,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db_session.add(schedule)

        # 创建10个预约（达到上限）
        user_id = str(uuid4())
        for i in range(10):
            appointment = Appointment(
                id=str(uuid4()),
                appointment_no=f"YY{i}",
                user_id=str(uuid4()),
                patient_id=str(uuid4()),
                doctor_id=str(uuid4()),
                schedule_id=schedule.id,
                queue_number=i + 1,
                status=1,  # 已预约
                patient_name=f"病人{i}",
                patient_phone=f"1380013800{i}",
                doctor_name="测试医生",
                department_name="测试科室",
                created_at=datetime.now(),
            updated_at=datetime.now(),
            )
            db_session.add(appointment)

        await db_session.commit()

        # Mock 候补位置计算
        from unittest.mock import patch
        with patch.object(
            service := RuleEngineService(db_session),
            '_calculate_waitlist_position',
            new=AsyncMock(return_value=5)
        ):
            # 执行容量检查
            result = await service.check_capacity_limits(
                db=db_session,
                shift_id=schedule.id,
                user_id=user_id,
                policy=policy,
            )

        # 验证结果
        assert result["allowed"] is False
        assert "候补" in result["reason"] or "约满" in result["reason"]
        assert result["waitlist_position"] == 5

    @pytest.mark.asyncio
    async def test_check_capacity_overbooking_enabled(self, db_session):
        """测试超额预订启用"""
        # 创建班次类型
        shift_type = create_shift_type()
        db_session.add(shift_type)

        # 创建规则组
        rule_set = create_rule_set()
        db_session.add(rule_set)

        # 关联规则组和班次类型
        association = RuleSetShiftType(
            rule_set_id=rule_set.id,
            shift_type_id=shift_type.id
        )
        db_session.add(association)

        # 创建容量策略（启用超额，最多超额2个）
        policy = create_capacity_policy(
            rule_set_id=rule_set.id,
            total_capacity=10,
            overbooking_enabled=True,
            overbooking_max=2,
        )
        db_session.add(policy)

        # 创建排班
        tomorrow = date.today() + timedelta(days=1)
        schedule = Schedule(
            id=str(uuid4()),
            doctor_id=str(uuid4()),
            store_id=str(uuid4()),
            schedule_date=tomorrow,
            time_slot="morning",
            start_time=time(8, 0),
            end_time=time(12, 0),
            total_slots=10,
            booked_slots=0,
            status=1,
            shift_type_id=shift_type.id,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db_session.add(schedule)

        # 创建11个预约（超过容量但在超额范围内）
        for i in range(11):
            appointment = Appointment(
                id=str(uuid4()),
                appointment_no=f"YY{i}",
                user_id=str(uuid4()),
                patient_id=str(uuid4()),
                doctor_id=str(uuid4()),
                schedule_id=schedule.id,
                queue_number=i + 1,
                status=1,  # 已预约
                patient_name=f"病人{i}",
                patient_phone=f"1380013800{i}",
                doctor_name="测试医生",
                department_name="测试科室",
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
            db_session.add(appointment)

        await db_session.commit()

        # 创建服务实例
        service = RuleEngineService(db_session)

        # 执行容量检查
        result = await service.check_capacity_limits(
            db=db_session,
            shift_id=schedule.id,
            user_id=str(uuid4()),
            policy=policy,
        )

        # 验证结果：应该允许（11 < 10+2）
        assert result["allowed"] is True

    @pytest.mark.asyncio
    async def test_check_capacity_overbooking_exceeded(self, db_session):
        """测试超过超额限制"""
        # 创建班次类型
        shift_type = create_shift_type()
        db_session.add(shift_type)

        # 创建规则组
        rule_set = create_rule_set()
        db_session.add(rule_set)

        # 关联规则组和班次类型
        association = RuleSetShiftType(
            rule_set_id=rule_set.id,
            shift_type_id=shift_type.id
        )
        db_session.add(association)

        # 创建容量策略（启用超额，最多超额2个）
        policy = create_capacity_policy(
            rule_set_id=rule_set.id,
            total_capacity=10,
            overbooking_enabled=True,
            overbooking_max=2,
        )
        db_session.add(policy)

        # 创建排班
        tomorrow = date.today() + timedelta(days=1)
        schedule = Schedule(
            id=str(uuid4()),
            doctor_id=str(uuid4()),
            store_id=str(uuid4()),
            schedule_date=tomorrow,
            time_slot="morning",
            start_time=time(8, 0),
            end_time=time(12, 0),
            total_slots=10,
            booked_slots=0,
            status=1,
            shift_type_id=shift_type.id,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db_session.add(schedule)

        # 创建13个预约（超过超额限制：10+2=12）
        for i in range(13):
            appointment = Appointment(
                id=str(uuid4()),
                appointment_no=f"YY{i}",
                user_id=str(uuid4()),
                patient_id=str(uuid4()),
                doctor_id=str(uuid4()),
                schedule_id=schedule.id,
                queue_number=i + 1,
                status=1,  # 已预约
                patient_name=f"病人{i}",
                patient_phone=f"1380013800{i}",
                doctor_name="测试医生",
                department_name="测试科室",
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
            db_session.add(appointment)

        await db_session.commit()

        # 创建服务实例
        service = RuleEngineService(db_session)

        # 执行容量检查
        result = await service.check_capacity_limits(
            db=db_session,
            shift_id=schedule.id,
            user_id=str(uuid4()),
            policy=policy,
        )

        # 验证结果
        assert result["allowed"] is False
        assert "超额" in result["reason"] or "已满" in result["reason"]

    @pytest.mark.asyncio
    async def test_check_capacity_no_limits(self, db_session):
        """测试无容量限制"""
        # 创建班次类型
        shift_type = create_shift_type()
        db_session.add(shift_type)

        # 创建规则组
        rule_set = create_rule_set()
        db_session.add(rule_set)

        # 关联规则组和班次类型
        association = RuleSetShiftType(
            rule_set_id=rule_set.id,
            shift_type_id=shift_type.id
        )
        db_session.add(association)

        # 创建容量策略（总容量0表示不限制）
        policy = create_capacity_policy(
            rule_set_id=rule_set.id,
            total_capacity=0,  # 不限制
            per_user_capacity=0,  # 不限制
        )
        db_session.add(policy)

        # 创建排班
        tomorrow = date.today() + timedelta(days=1)
        schedule = Schedule(
            id=str(uuid4()),
            doctor_id=str(uuid4()),
            store_id=str(uuid4()),
            schedule_date=tomorrow,
            time_slot="morning",
            start_time=time(8, 0),
            end_time=time(12, 0),
            total_slots=10,
            booked_slots=0,
            status=1,
            shift_type_id=shift_type.id,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db_session.add(schedule)

        # 创建大量预约
        for i in range(100):
            appointment = Appointment(
                id=str(uuid4()),
                appointment_no=f"YY{i}",
                user_id=str(uuid4()),
                patient_id=str(uuid4()),
                doctor_id=str(uuid4()),
                schedule_id=schedule.id,
                queue_number=i + 1,
                status=1,  # 已预约
                patient_name=f"病人{i}",
                patient_phone=f"1380013800{i}",
                doctor_name="测试医生",
                department_name="测试科室",
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
            db_session.add(appointment)

        await db_session.commit()

        # 创建服务实例
        service = RuleEngineService(db_session)

        # 执行容量检查
        result = await service.check_capacity_limits(
            db=db_session,
            shift_id=schedule.id,
            user_id=str(uuid4()),
            policy=policy,
        )

        # 验证结果：应该允许（无容量限制）
        assert result["allowed"] is True
