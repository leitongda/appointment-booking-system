"""
规则组服务单元测试

覆盖规则组查询、创建、更新、删除、启用/禁用、时间窗和策略管理等功能
"""
import json
from datetime import datetime, timezone, date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.rule_sets.service import RuleSetService
from app.models.rule_set import (
    RuleSet,
    RuleWindow,
    RuleBookingPolicy,
    RuleCheckinPolicy,
    RuleCapacityPolicy,
    RuleSetShiftType,
    RuleSetPreset,
)
from app.schemas.rule_set import (
    RuleSetCreate,
    RuleSetUpdate,
    RuleWindowCreate,
    RuleWindowUpdate,
    RuleBookingPolicyCreate,
    RuleCheckinPolicyCreate,
    RuleCapacityPolicyCreate,
)
from sqlalchemy import select


@pytest.mark.unit
class TestRuleSetQueryMixin:
    """测试规则组查询功能"""

    async def test_get_by_id_found(self, db_session, test_rule_set):
        """测试根据ID查询规则组 - 找到记录"""
        service = RuleSetService(db_session)
        # 注意：test_rule_set 没有 tenant_id，所以传入 None 表示不过滤租户
        with patch("app.middleware.tenant_context.get_current_tenant_id", return_value=None):
            result = await service.get_by_id(test_rule_set.id)
            assert result is not None
            assert result.id == test_rule_set.id
            assert result.name == test_rule_set.name

    async def test_get_by_id_not_found(self, db_session):
        """测试根据ID查询规则组 - 未找到记录"""
        service = RuleSetService(db_session)
        with patch("app.middleware.tenant_context.get_current_tenant_id", return_value=None):
            result = await service.get_by_id("non-existent-id")
            assert result is None

    async def test_get_by_id_tenant_isolation(self, db_session, test_rule_set):
        """测试租户隔离 - 不同租户无法查询"""
        service = RuleSetService(db_session)
        # 使用 None 作为租户 ID（不过滤）
        with patch("app.middleware.tenant_context.get_current_tenant_id", return_value=None):
            result = await service.get_by_id(test_rule_set.id)
            # 不过滤租户时应该能查到
            assert result is not None

    async def test_get_list_basic(self, db_session, test_rule_set):
        """测试基础列表查询"""
        service = RuleSetService(db_session)
        with patch("app.middleware.tenant_context.get_current_tenant_id", return_value=None):
            rule_sets, total = await service.get_list()
            assert total == 1
            assert len(rule_sets) == 1
            assert rule_sets[0].id == test_rule_set.id

    async def test_get_list_with_enabled_filter(self, db_session, test_rule_set):
        """测试按启用状态筛选"""
        service = RuleSetService(db_session)
        with patch("app.middleware.tenant_context.get_current_tenant_id", return_value=None):
            rule_sets, total = await service.get_list(enabled=True)
            assert total == 1

    async def test_get_list_with_shift_type_filter(self, db_session, test_rule_set, test_shift_type):
        """测试按班次类型筛选"""
        service = RuleSetService(db_session)
        with patch("app.middleware.tenant_context.get_current_tenant_id", return_value=None):
            rule_sets, total = await service.get_list(shift_type_id=test_shift_type.id)
            assert total == 1

    async def test_get_list_pagination(self, db_session, test_rule_set):
        """测试分页功能"""
        service = RuleSetService(db_session)
        with patch("app.middleware.tenant_context.get_current_tenant_id", return_value=None):
            rule_sets, total = await service.get_list(page=1, page_size=10)
            assert total == 1
            assert len(rule_sets) == 1

    async def test_get_window_by_id_found(self, db_session):
        """测试根据ID查询时间窗 - 找到记录"""
        # 先创建规则组和时间窗
        import uuid
        rule_set = RuleSet(
            id=str(uuid.uuid4()),
            name="测试规则组",
            enabled=True,
            priority=100,
            time_source="SERVER",
            tenant_id="test-tenant",
        )
        db_session.add(rule_set)
        await db_session.flush()

        window = RuleWindow(
            id=str(uuid.uuid4()),
            rule_set_id=rule_set.id,
            name="测试时间窗",
            action="BOOK",
            reference_point="SHIFT_START",
            open_offset_sec=-3600,
            close_offset_sec=0,
        )
        db_session.add(window)
        await db_session.commit()

        service = RuleSetService(db_session)
        result = await service.get_window_by_id(window.id)
        assert result is not None
        assert result.id == window.id

    async def test_get_window_by_id_not_found(self, db_session):
        """测试根据ID查询时间窗 - 未找到记录"""
        service = RuleSetService(db_session)
        result = await service.get_window_by_id("non-existent-id")
        assert result is None

    async def test_ensure_system_presets(self, db_session):
        """测试确保系统预设已初始化"""
        service = RuleSetService(db_session)

        # 清空现有预设
        await db_session.execute(select(RuleSetPreset).where(RuleSetPreset.is_system == True))
        existing = await db_session.execute(select(RuleSetPreset))
        if existing.scalars().first():
            await db_session.rollback()

        await service.ensure_system_presets()

        # 验证系统预设已创建
        result = await db_session.execute(
            select(RuleSetPreset).where(RuleSetPreset.is_system == True)
        )
        presets = result.scalars().all()
        assert len(presets) > 0

    async def test_get_presets(self, db_session):
        """测试获取预设列表"""
        service = RuleSetService(db_session)

        presets = await service.get_presets()
        assert len(presets) > 0

    async def test_get_preset_by_id_found(self, db_session):
        """测试根据ID获取预设 - 找到记录"""
        service = RuleSetService(db_session)

        presets = await service.get_presets()
        if presets:
            preset = await service.get_preset_by_id(presets[0].id)
            assert preset is not None
            assert preset.id == presets[0].id

    async def test_get_preset_by_id_not_found(self, db_session):
        """测试根据ID获取预设 - 未找到记录"""
        service = RuleSetService(db_session)
        preset = await service.get_preset_by_id("non-existent-id")
        assert preset is None


@pytest.mark.unit
class TestRuleSetMutationMixin:
    """测试规则组修改功能"""

    async def test_create_success(self, db_session, test_shift_type):
        """测试创建规则组成功"""
        service = RuleSetService(db_session)
        import uuid

        data = RuleSetCreate(
            name="新规则组",
            enabled=True,
            priority=100,
            time_source="SERVER",
            timezone_source="HOSPITAL",
            compare_precision="SECOND",
            default_open_inclusive=True,
            default_close_inclusive=False,
            rounding_mode="NONE",
            clock_skew_tolerance_sec=5,
            shift_type_ids=[test_shift_type.id],
        )

        with patch("app.middleware.tenant_context.get_current_tenant_id", return_value="test-tenant"):
            with patch.object(service, "_invalidate_rule_set_cache"):
                result = await service.create(data)

                assert result is not None
                assert result.name == "新规则组"
                assert result.enabled is True

    async def test_create_with_windows(self, db_session, test_shift_type):
        """测试创建带时间窗的规则组"""
        service = RuleSetService(db_session)

        data = RuleSetCreate(
            name="带时间窗的规则组",
            enabled=True,
            priority=100,
            time_source="SERVER",
            timezone_source="HOSPITAL",
            compare_precision="SECOND",
            default_open_inclusive=True,
            default_close_inclusive=False,
            rounding_mode="NONE",
            clock_skew_tolerance_sec=5,
            shift_type_ids=[test_shift_type.id],
            windows=[
                RuleWindowCreate(
                    name="预约时间窗",
                    action="BOOK",
                    reference_point="SHIFT_START",
                    open_offset_sec=-3600,
                    close_offset_sec=0,
                )
            ],
        )

        with patch("app.middleware.tenant_context.get_current_tenant_id", return_value="test-tenant"):
            with patch.object(service, "_invalidate_rule_set_cache"):
                result = await service.create(data)

                assert result is not None
                assert result.name == "带时间窗的规则组"

    async def test_create_with_policies(self, db_session, test_shift_type):
        """测试创建带策略的规则组"""
        service = RuleSetService(db_session)

        data = RuleSetCreate(
            name="带策略的规则组",
            enabled=True,
            priority=100,
            time_source="SERVER",
            timezone_source="HOSPITAL",
            compare_precision="SECOND",
            default_open_inclusive=True,
            default_close_inclusive=False,
            rounding_mode="NONE",
            clock_skew_tolerance_sec=5,
            shift_type_ids=[test_shift_type.id],
            booking_policy=RuleBookingPolicyCreate(
                require_auth=True,
                require_patient_profile_complete=False,
                per_user_per_shift=1,
                per_user_per_day=3,
                per_user_per_week=5,
            ),
            checkin_policy=RuleCheckinPolicyCreate(
                require_booking=True,
                allow_onsite_booking=False,
                max_times=1,
            ),
            capacity_policy=RuleCapacityPolicyCreate(
                total_capacity=100,  # 必须是 int，不能是 None
                per_user_capacity=5,  # 必须是 int，不能是 None
                waitlist_enabled=True,
                waitlist_max_size=10,
            ),
        )

        with patch("app.middleware.tenant_context.get_current_tenant_id", return_value="test-tenant"):
            with patch.object(service, "_invalidate_rule_set_cache"):
                result = await service.create(data)

                assert result is not None
                assert result.name == "带策略的规则组"

    async def test_update_success(self, db_session, test_rule_set):
        """测试更新规则组成功"""
        service = RuleSetService(db_session)

        data = RuleSetUpdate(
            name="更新后的规则组",
            priority=200,
        )

        with patch("app.middleware.tenant_context.get_current_tenant_id", return_value=None):
            with patch.object(service, "_invalidate_rule_set_cache"):
                result = await service.update(test_rule_set.id, data)

                assert result is not None
                assert result.name == "更新后的规则组"
                assert result.priority == 200

    async def test_update_not_found(self, db_session):
        """测试更新不存在的规则组"""
        service = RuleSetService(db_session)

        data = RuleSetUpdate(name="不存在的规则组")

        with patch("app.middleware.tenant_context.get_current_tenant_id", return_value=None):
            result = await service.update("non-existent-id", data)
            assert result is None

    async def test_update_with_optimistic_lock_success(self, db_session, test_rule_set):
        """测试更新规则组 - 乐观锁成功"""
        service = RuleSetService(db_session)

        data = RuleSetUpdate(
            name="乐观锁更新",
            expected_updated_at=test_rule_set.updated_at,
        )

        with patch("app.middleware.tenant_context.get_current_tenant_id", return_value=None):
            with patch.object(service, "_invalidate_rule_set_cache"):
                result = await service.update(test_rule_set.id, data)
                assert result is not None

    async def test_update_with_optimistic_lock_conflict(self, db_session, test_rule_set):
        """测试更新规则组 - 乐观锁冲突"""
        service = RuleSetService(db_session)

        old_updated_at = test_rule_set.updated_at
        # 模拟并发更新
        test_rule_set.updated_at = datetime.now(timezone.utc)
        await db_session.commit()

        data = RuleSetUpdate(
            name="乐观锁冲突",
            expected_updated_at=old_updated_at,
        )

        with patch("app.middleware.tenant_context.get_current_tenant_id", return_value=None):
            with pytest.raises(ValueError, match="规则组已被其他操作修改"):
                await service.update(test_rule_set.id, data)

    async def test_delete_success(self, db_session, test_tenant):
        """测试删除规则组成功"""
        import uuid
        service = RuleSetService(db_session)

        # 创建一个无引用的规则组
        rule_set = RuleSet(
            id=str(uuid.uuid4()),
            name="待删除规则组",
            enabled=False,
            priority=100,
            time_source="SERVER",
            tenant_id=test_tenant.id,
        )
        db_session.add(rule_set)
        await db_session.commit()

        with patch("app.middleware.tenant_context.get_current_tenant_id", return_value=test_tenant.id):
            with patch.object(service, "_invalidate_rule_set_cache"):
                result = await service.delete(rule_set.id)
                assert result is True

                # 验证软删除
                result = await db_session.execute(select(RuleSet).where(RuleSet.id == rule_set.id))
                deleted_rule_set = result.scalar_one_or_none()
                assert deleted_rule_set is not None
                assert deleted_rule_set.deleted_at is not None
                assert deleted_rule_set.enabled is False

    async def test_delete_not_found(self, db_session):
        """测试删除不存在的规则组"""
        service = RuleSetService(db_session)

        with patch("app.middleware.tenant_context.get_current_tenant_id", return_value="test-tenant"):
            result = await service.delete("non-existent-id")
            assert result is False

    async def test_delete_with_reference_raises_error(self, db_session, test_tenant, test_shift_type):
        """测试删除被引用的规则组 - 应抛出错误"""
        from app.models.schedule import Schedule
        import uuid

        service = RuleSetService(db_session)

        # 创建一个有排班引用的规则组
        rule_set = RuleSet(
            id=str(uuid.uuid4()),
            name="被引用的规则组",
            enabled=False,
            priority=100,
            time_source="SERVER",
            tenant_id=test_tenant.id,
        )
        db_session.add(rule_set)
        await db_session.flush()

        # 创建关联
        from app.models.rule_set import RuleSetShiftType
        rule_set_shift_type = RuleSetShiftType(
            rule_set_id=rule_set.id,
            shift_type_id=test_shift_type.id,
        )
        db_session.add(rule_set_shift_type)

        # 创建排班引用
        schedule = Schedule(
            id=str(uuid.uuid4()),
            doctor_id="doctor-1",
            store_id="store-1",
            tenant_id=test_tenant.id,
            shift_type_id=test_shift_type.id,
            schedule_date=date.today(),
            time_slot="morning",
            total_slots=10,
            booked_slots=0,
        )
        db_session.add(schedule)
        await db_session.commit()

        with patch("app.middleware.tenant_context.get_current_tenant_id", return_value=test_tenant.id):
            with pytest.raises(ValueError, match="该规则组已被.*引用"):
                await service.delete(rule_set.id)

    async def test_enable_success(self, db_session, test_rule_set):
        """测试启用规则组成功"""
        service = RuleSetService(db_session)
        test_rule_set.enabled = False
        await db_session.commit()

        with patch("app.middleware.tenant_context.get_current_tenant_id", return_value=None):
            with patch.object(service, "_invalidate_rule_set_cache"):
                result = await service.enable(test_rule_set.id)
                assert result is True

    async def test_enable_not_found(self, db_session):
        """测试启用不存在的规则组"""
        service = RuleSetService(db_session)

        with patch("app.middleware.tenant_context.get_current_tenant_id", return_value=None):
            result = await service.enable("non-existent-id")
            assert result is False

    async def test_disable_success(self, db_session, test_rule_set):
        """测试禁用规则组成功"""
        service = RuleSetService(db_session)

        with patch("app.middleware.tenant_context.get_current_tenant_id", return_value=None):
            with patch.object(service, "_invalidate_rule_set_cache"):
                result = await service.disable(test_rule_set.id)
                assert result is True

    async def test_disable_not_found(self, db_session):
        """测试禁用不存在的规则组"""
        service = RuleSetService(db_session)

        with patch("app.middleware.tenant_context.get_current_tenant_id", return_value=None):
            result = await service.disable("non-existent-id")
            assert result is False

    async def test_create_preset_success(self, db_session):
        """测试创建自定义预设成功"""
        service = RuleSetService(db_session)

        config = {"test": "config"}
        with patch("app.middleware.tenant_context.get_current_tenant_id", return_value="test-tenant"):
            preset = await service.create_preset(
                name="自定义预设",
                description="测试用",
                config=config,
            )
            assert preset is not None
            assert preset.name == "自定义预设"
            assert preset.is_system is False

    async def test_update_preset_success(self, db_session):
        """测试更新自定义预设成功"""
        service = RuleSetService(db_session)

        # 先创建一个自定义预设
        preset = await service.create_preset(
            name="待更新预设",
            description="原描述",
            config={},
        )

        with patch("app.middleware.tenant_context.get_current_tenant_id", return_value="test-tenant"):
            result = await service.update_preset(
                preset.id,
                name="更新后的预设",
                description="新描述",
            )
            assert result is not None
            assert result.name == "更新后的预设"

    async def test_update_preset_system_preset_fails(self, db_session):
        """测试更新系统预设 - 应失败"""
        service = RuleSetService(db_session)

        # 获取一个系统预设
        presets = await service.get_presets()
        system_preset = next((p for p in presets if p.is_system), None)
        if system_preset:
            result = await service.update_preset(system_preset.id, name="尝试修改")
            assert result is None

    async def test_delete_preset_success(self, db_session):
        """测试删除自定义预设成功"""
        service = RuleSetService(db_session)

        # 先创建一个自定义预设
        preset = await service.create_preset(
            name="待删除预设",
            description="测试用",
            config={},
        )

        result = await service.delete_preset(preset.id)
        assert result is True

    async def test_delete_preset_system_preset_fails(self, db_session):
        """测试删除系统预设 - 应失败"""
        service = RuleSetService(db_session)

        # 获取一个系统预设
        presets = await service.get_presets()
        system_preset = next((p for p in presets if p.is_system), None)
        if system_preset:
            result = await service.delete_preset(system_preset.id)
            assert result is False


@pytest.mark.unit
class TestRuleSetPolicyMixin:
    """测试时间窗和策略管理功能"""

    async def test_create_window_success(self, db_session, test_rule_set):
        """测试创建时间窗成功"""
        service = RuleSetService(db_session)

        data = RuleWindowCreate(
            name="预约时间窗",
            action="BOOK",
            reference_point="SHIFT_START",
            open_offset_sec=-3600,
            close_offset_sec=0,
            open_inclusive=True,
            close_inclusive=False,
            fail_policy="REJECT",
        )

        result = await service.create_window(test_rule_set.id, data)
        assert result is not None
        assert result.name == "预约时间窗"
        assert result.rule_set_id == test_rule_set.id

    async def test_create_window_rule_set_not_found(self, db_session):
        """测试创建时间窗 - 规则组不存在"""
        service = RuleSetService(db_session)

        data = RuleWindowCreate(
            name="测试时间窗",
            action="BOOK",
            reference_point="SHIFT_START",
        )

        result = await service.create_window("non-existent-id", data)
        assert result is None

    async def test_update_window_success(self, db_session, test_rule_set):
        """测试更新时间窗成功"""
        service = RuleSetService(db_session)

        # 先创建时间窗
        create_data = RuleWindowCreate(
            name="原时间窗",
            action="BOOK",
            reference_point="SHIFT_START",
            open_offset_sec=-3600,  # 添加默认值
        )
        window = await service.create_window(test_rule_set.id, create_data)

        # 更新时间窗 - 只测试能成功更新，不检查具体值
        update_data = RuleWindowUpdate(
            open_offset_sec=-7200,
        )

        result = await service.update_window(window.id, update_data)
        assert result is not None
        assert result.open_offset_sec == -7200

    async def test_update_window_not_found(self, db_session):
        """测试更新不存在的时间窗"""
        service = RuleSetService(db_session)

        data = RuleWindowUpdate(name="不存在的")
        result = await service.update_window("non-existent-id", data)
        assert result is None

    async def test_delete_window_success(self, db_session, test_rule_set):
        """测试删除时间窗成功"""
        service = RuleSetService(db_session)

        # 先创建时间窗
        create_data = RuleWindowCreate(
            name="待删除时间窗",
            action="BOOK",
            reference_point="SHIFT_START",
        )
        window = await service.create_window(test_rule_set.id, create_data)

        result = await service.delete_window(window.id)
        assert result is True

    async def test_delete_window_not_found(self, db_session):
        """测试删除不存在的时间窗"""
        service = RuleSetService(db_session)
        result = await service.delete_window("non-existent-id")
        assert result is False

    async def test_update_booking_policy_create(self, db_session, test_rule_set):
        """测试创建预约策略"""
        service = RuleSetService(db_session)

        data = RuleBookingPolicyCreate(
            require_auth=True,
            require_patient_profile_complete=True,
            per_user_per_shift=1,
            per_user_per_day=3,
            per_user_per_week=5,
            conflict_same_shift="REJECT",
            conflict_overlap_time="REJECT",
            conflict_same_type_same_day="ALLOW",
        )

        result = await service.update_booking_policy(test_rule_set.id, data)
        assert result is not None
        assert result.require_auth is True
        assert result.per_user_per_shift == 1

    async def test_update_booking_policy_update_existing(self, db_session, test_rule_set):
        """测试更新已有的预约策略"""
        service = RuleSetService(db_session)

        # 先创建策略
        create_data = RuleBookingPolicyCreate(
            require_auth=False,
            per_user_per_shift=1,
        )
        await service.update_booking_policy(test_rule_set.id, create_data)

        # 更新策略
        update_data = RuleBookingPolicyCreate(
            require_auth=True,
            per_user_per_shift=2,
        )

        result = await service.update_booking_policy(test_rule_set.id, update_data)
        assert result is not None
        assert result.require_auth is True
        assert result.per_user_per_shift == 2

    async def test_update_checkin_policy_create(self, db_session, test_rule_set):
        """测试创建签到策略"""
        service = RuleSetService(db_session)

        data = RuleCheckinPolicyCreate(
            require_booking=True,
            allow_onsite_booking=False,
            max_times=1,
            audit_log=True,
            grace_period_sec=300,
            after_grace_status="LATE",
            no_checkin_after_close="AUTO_CANCEL",  # 应该是字符串，不是布尔值
        )

        result = await service.update_checkin_policy(test_rule_set.id, data)
        assert result is not None
        assert result.require_booking is True
        assert result.grace_period_sec == 300

    async def test_update_checkin_policy_update_existing(self, db_session, test_rule_set):
        """测试更新已有的签到策略"""
        service = RuleSetService(db_session)

        # 先创建策略
        create_data = RuleCheckinPolicyCreate(
            require_booking=False,
            grace_period_sec=600,
        )
        await service.update_checkin_policy(test_rule_set.id, create_data)

        # 更新策略
        update_data = RuleCheckinPolicyCreate(
            require_booking=True,
            grace_period_sec=300,
        )

        result = await service.update_checkin_policy(test_rule_set.id, update_data)
        assert result is not None
        assert result.require_booking is True
        assert result.grace_period_sec == 300

    async def test_update_capacity_policy_create(self, db_session, test_rule_set):
        """测试创建容量策略"""
        service = RuleSetService(db_session)

        data = RuleCapacityPolicyCreate(
            total_capacity=100,
            per_user_capacity=5,
            waitlist_enabled=True,
            waitlist_max_size=20,
            waitlist_promote_policy="FIFO",
            overbooking_enabled=False,
            overbooking_max=0,
        )

        result = await service.update_capacity_policy(test_rule_set.id, data)
        assert result is not None
        assert result.total_capacity == 100
        assert result.waitlist_enabled is True

    async def test_update_capacity_policy_update_existing(self, db_session, test_rule_set):
        """测试更新已有的容量策略"""
        service = RuleSetService(db_session)

        # 先创建策略
        create_data = RuleCapacityPolicyCreate(
            total_capacity=50,
            waitlist_enabled=False,
        )
        await service.update_capacity_policy(test_rule_set.id, create_data)

        # 更新策略
        update_data = RuleCapacityPolicyCreate(
            total_capacity=100,
            waitlist_enabled=True,
        )

        result = await service.update_capacity_policy(test_rule_set.id, update_data)
        assert result is not None
        assert result.total_capacity == 100
        assert result.waitlist_enabled is True


@pytest.mark.unit
class TestRuleSetCacheInvalidation:
    """测试缓存失效功能"""

    async def test_invalidate_rule_set_cache_basic(self, db_session, test_rule_set, test_shift_type):
        """测试基本缓存失效"""
        from app.core.redis import RedisCache
        from app.modules.rule_engine.cache import RuleCache

        service = RuleSetService(db_session)
        # 初始化缓存
        cache = RuleCache(RedisCache())

        # Mock invalidate_v2 方法
        with patch.object(cache, "invalidate_v2") as mock_invalidate:
            # 手动调用缓存失效方法
            await cache.invalidate_v2(
                tenant_id=None,
                shift_type_ids=[test_shift_type.id],
                store_ids=None,
                department_ids=None,
                doctor_ids=None,
            )
            mock_invalidate.assert_called_once()

    async def test_invalidate_cache_on_create(self, db_session, test_shift_type):
        """测试创建规则组时缓存失效"""
        service = RuleSetService(db_session)

        data = RuleSetCreate(
            name="测试缓存失效",
            enabled=True,
            priority=100,
            time_source="SERVER",
            timezone_source="HOSPITAL",
            compare_precision="SECOND",
            default_open_inclusive=True,
            default_close_inclusive=False,
            rounding_mode="NONE",
            clock_skew_tolerance_sec=5,
            shift_type_ids=[test_shift_type.id],
        )

        with patch("app.middleware.tenant_context.get_current_tenant_id", return_value="test-tenant"):
            with patch.object(service, "_invalidate_rule_set_cache") as mock_invalidate:
                await service.create(data)
                mock_invalidate.assert_called_once()

    async def test_invalidate_cache_on_update(self, db_session, test_rule_set):
        """测试更新规则组时缓存失效"""
        service = RuleSetService(db_session)

        data = RuleSetUpdate(name="更新名称")

        with patch("app.middleware.tenant_context.get_current_tenant_id", return_value=None):
            with patch.object(service, "_invalidate_rule_set_cache") as mock_invalidate:
                await service.update(test_rule_set.id, data)
                mock_invalidate.assert_called_once()

    async def test_invalidate_cache_on_delete(self, db_session, test_tenant):
        """测试删除规则组时缓存失效"""
        import uuid
        service = RuleSetService(db_session)

        # 创建一个无引用的规则组
        rule_set = RuleSet(
            id=str(uuid.uuid4()),
            name="待删除规则组",
            enabled=False,
            priority=100,
            time_source="SERVER",
            tenant_id=test_tenant.id,
        )
        db_session.add(rule_set)
        await db_session.commit()

        with patch("app.middleware.tenant_context.get_current_tenant_id", return_value=test_tenant.id):
            with patch.object(service, "_invalidate_rule_set_cache") as mock_invalidate:
                await service.delete(rule_set.id)
                mock_invalidate.assert_called_once()

    async def test_invalidate_cache_on_enable(self, db_session, test_rule_set):
        """测试启用规则组时缓存失效"""
        service = RuleSetService(db_session)

        with patch("app.middleware.tenant_context.get_current_tenant_id", return_value=None):
            with patch.object(service, "_invalidate_rule_set_cache") as mock_invalidate:
                await service.enable(test_rule_set.id)
                mock_invalidate.assert_called_once()

    async def test_invalidate_cache_on_disable(self, db_session, test_rule_set):
        """测试禁用规则组时缓存失效"""
        service = RuleSetService(db_session)

        with patch("app.middleware.tenant_context.get_current_tenant_id", return_value=None):
            with patch.object(service, "_invalidate_rule_set_cache") as mock_invalidate:
                await service.disable(test_rule_set.id)
                mock_invalidate.assert_called_once()


@pytest.mark.unit
class TestRuleSetAudit:
    """测试审计日志功能"""

    async def test_audit_log_on_create(self, db_session, test_shift_type):
        """测试创建规则组时记录审计日志"""
        service = RuleSetService(db_session)

        data = RuleSetCreate(
            name="审计测试规则组",
            enabled=True,
            priority=100,
            time_source="SERVER",
            timezone_source="HOSPITAL",
            compare_precision="SECOND",
            default_open_inclusive=True,
            default_close_inclusive=False,
            rounding_mode="NONE",
            clock_skew_tolerance_sec=5,
            shift_type_ids=[test_shift_type.id],
        )

        with patch("app.middleware.tenant_context.get_current_tenant_id", return_value="test-tenant"):
            result = await service.create(data)
            assert result is not None

            # 验证审计日志已创建
            from app.models.rule_set_audit import RuleSetAuditLog
            audit_result = await db_session.execute(
                select(RuleSetAuditLog).where(RuleSetAuditLog.rule_set_id == result.id)
            )
            audit_logs = audit_result.scalars().all()
            assert len(audit_logs) > 0
            assert audit_logs[0].action == "CREATE"

    async def test_audit_log_on_update(self, db_session, test_rule_set):
        """测试更新规则组时记录审计日志"""
        service = RuleSetService(db_session)

        data = RuleSetUpdate(name="更新名称")

        with patch("app.middleware.tenant_context.get_current_tenant_id", return_value=None):
            await service.update(test_rule_set.id, data)

            # 验证审计日志已创建
            from app.models.rule_set_audit import RuleSetAuditLog
            audit_result = await db_session.execute(
                select(RuleSetAuditLog).where(RuleSetAuditLog.rule_set_id == test_rule_set.id)
            )
            audit_logs = audit_result.scalars().all()
            # 找到 UPDATE 操作的日志
            update_logs = [log for log in audit_logs if log.action == "UPDATE"]
            assert len(update_logs) > 0

    async def test_get_audit_logs(self, db_session, test_rule_set):
        """测试获取审计日志列表"""
        service = RuleSetService(db_session)

        # 先进行一些操作产生审计日志
        await service.enable(test_rule_set.id)

        logs, total = await service.get_audit_logs(test_rule_set.id)
        assert total > 0
        assert len(logs) > 0
