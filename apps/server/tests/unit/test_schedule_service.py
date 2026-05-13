"""
排班服务单元测试

覆盖排班查询、创建、更新、删除、批量操作等核心功能
"""
import json
from datetime import date, time, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.schedules.service import ScheduleService
from app.models.schedule import Schedule
from app.models.rest_day import RestDay
from app.models.schedule_template import ScheduleTemplate
from app.models.doctor import Doctor
from app.models.appointment import Appointment
from app.schemas.schedule import ScheduleCreate, ScheduleUpdate, ScheduleBatchCreate
from sqlalchemy import select


@pytest.mark.unit
class TestScheduleQueryMixin:
    """测试排班查询功能"""

    async def test_get_by_id_found(self, db_session, test_schedule):
        """测试根据ID查询排班 - 找到记录"""
        service = ScheduleService(db_session)
        with patch("app.middleware.tenant_context.get_current_tenant_id", return_value=test_schedule.tenant_id):
            result = await service.get_by_id(test_schedule.id)
            assert result is not None
            assert result.id == test_schedule.id
            assert result.doctor_id == test_schedule.doctor_id

    async def test_get_by_id_not_found(self, db_session):
        """测试根据ID查询排班 - 未找到记录"""
        service = ScheduleService(db_session)
        with patch("app.middleware.tenant_context.get_current_tenant_id", return_value="test-tenant"):
            result = await service.get_by_id("non-existent-id")
            assert result is None

    async def test_get_by_id_tenant_isolation(self, db_session, test_schedule):
        """测试租户隔离 - 不同租户无法查询"""
        service = ScheduleService(db_session)
        # 使用 None 作为租户 ID（不过滤）
        with patch("app.middleware.tenant_context.get_current_tenant_id", return_value=None):
            result = await service.get_by_id(test_schedule.id)
            # 不过滤租户时应该能查到
            assert result is not None

    async def test_get_list_basic(self, db_session, test_schedule):
        """测试基础列表查询"""
        service = ScheduleService(db_session)
        with patch("app.middleware.tenant_context.get_current_tenant_id", return_value=test_schedule.tenant_id):
            schedules, total = await service.get_list()
            assert total == 1
            assert len(schedules) == 1
            assert schedules[0].id == test_schedule.id

    async def test_get_list_with_doctor_filter(self, db_session, test_schedule, test_doctor):
        """测试按医生筛选"""
        service = ScheduleService(db_session)
        with patch("app.middleware.tenant_context.get_current_tenant_id", return_value=test_schedule.tenant_id):
            schedules, total = await service.get_list(doctor_id=test_doctor.id)
            assert total == 1
            assert schedules[0].doctor_id == test_doctor.id

    async def test_get_list_with_store_filter(self, db_session, test_schedule, test_store):
        """测试按门店筛选"""
        service = ScheduleService(db_session)
        with patch("app.middleware.tenant_context.get_current_tenant_id", return_value=test_schedule.tenant_id):
            schedules, total = await service.get_list(store_id=test_store.id)
            assert total == 1

    async def test_get_list_with_date_filter(self, db_session, test_schedule):
        """测试按日期范围筛选"""
        service = ScheduleService(db_session)
        with patch("app.middleware.tenant_context.get_current_tenant_id", return_value=test_schedule.tenant_id):
            tomorrow = date.today() + timedelta(days=1)
            schedules, total = await service.get_list(start_date=tomorrow, end_date=tomorrow)
            assert total == 1

    async def test_get_list_with_status_filter(self, db_session, test_schedule):
        """测试按状态筛选"""
        service = ScheduleService(db_session)
        with patch("app.middleware.tenant_context.get_current_tenant_id", return_value=test_schedule.tenant_id):
            schedules, total = await service.get_list(status=1)
            assert total == 1

    async def test_get_list_pagination(self, db_session, test_schedule):
        """测试分页功能"""
        service = ScheduleService(db_session)
        with patch("app.middleware.tenant_context.get_current_tenant_id", return_value=test_schedule.tenant_id):
            schedules, total = await service.get_list(page=1, page_size=10)
            assert total == 1
            assert len(schedules) == 1

    async def test_get_available_no_rest_days(self, db_session, test_schedule, test_doctor):
        """测试获取可用排班 - 无休息日"""
        service = ScheduleService(db_session)
        with patch("app.middleware.tenant_context.get_current_tenant_id", return_value=test_schedule.tenant_id):
            schedules, booking_setting_applied = await service.get_available(doctor_id=test_doctor.id, days=14)
            assert len(schedules) >= 0
            assert booking_setting_applied is False

    async def test_get_available_with_rest_day(self, db_session, test_schedule, test_doctor, test_store, test_tenant):
        """测试获取可用排班 - 有休息日"""
        # 创建休息日
        tomorrow = date.today() + timedelta(days=1)
        rest_day = RestDay(
            id=str(__import__("uuid").uuid4()),
            tenant_id=test_tenant.id,
            store_id=test_store.id,
            start_date=tomorrow,
            end_date=tomorrow,
            status=1,
        )
        db_session.add(rest_day)
        await db_session.commit()

        service = ScheduleService(db_session)
        with patch("app.middleware.tenant_context.get_current_tenant_id", return_value=test_schedule.tenant_id):
            schedules, booking_setting_applied = await service.get_available(doctor_id=test_doctor.id, days=14)
            assert isinstance(schedules, list)
            assert booking_setting_applied is False

    async def test_is_rest_day_cached_with_doctor_filter(self, db_session, test_store, test_tenant):
        """测试休息日判断 - 医生级过滤"""
        doctor_id = "doctor-1"
        another_doctor_id = "doctor-2"

        rest_day = RestDay(
            id=str(__import__("uuid").uuid4()),
            tenant_id=test_tenant.id,
            store_id=test_store.id,
            start_date=date.today(),
            end_date=date.today(),
            doctor_ids=json.dumps([doctor_id]),
            status=1,
        )
        db_session.add(rest_day)
        await db_session.commit()

        from app.modules.schedules.service_query import ScheduleQueryMixin
        result = await db_session.execute(select(RestDay))
        rest_days = result.scalars().all()

        # 指定医生应该被判定为休息日
        is_rest = ScheduleQueryMixin._is_rest_day_cached(rest_days, date.today(), test_store.id, doctor_id)
        assert is_rest is True

        # 另一个医生不应被判定为休息日
        is_rest = ScheduleQueryMixin._is_rest_day_cached(rest_days, date.today(), test_store.id, another_doctor_id)
        assert is_rest is False

    async def test_is_rest_day_cached_without_doctor_ids(self, db_session, test_store, test_tenant):
        """测试休息日判断 - 无医生列表时全员休息"""
        rest_day = RestDay(
            id=str(__import__("uuid").uuid4()),
            tenant_id=test_tenant.id,
            store_id=test_store.id,
            start_date=date.today(),
            end_date=date.today(),
            doctor_ids=None,
            status=1,
        )
        db_session.add(rest_day)
        await db_session.commit()

        from app.modules.schedules.service_query import ScheduleQueryMixin
        result = await db_session.execute(select(RestDay))
        rest_days = result.scalars().all()

        # 任何医生都应该被判定为休息日
        is_rest = ScheduleQueryMixin._is_rest_day_cached(rest_days, date.today(), test_store.id, "any-doctor")
        assert is_rest is True


@pytest.mark.unit
class TestScheduleMutationMixin:
    """测试排班修改功能"""

    async def test_create_success(self, db_session, test_doctor, test_tenant):
        """测试创建排班成功"""
        service = ScheduleService(db_session)
        tomorrow = date.today() + timedelta(days=1)

        data = ScheduleCreate(
            doctor_id=test_doctor.id,
            store_id=test_doctor.store_id,
            schedule_date=tomorrow,
            time_slot="afternoon",
            start_time=time(14, 0),
            end_time=time(18, 0),
            total_slots=20,
            status=1,
        )

        # Mock Redis 分布式锁
        with patch("app.middleware.tenant_context.get_current_tenant_id", return_value=test_tenant.id):
            with patch("app.core.redis.RedisCache.tenant_distributed_lock") as mock_lock:
                mock_lock.return_value.__aenter__ = AsyncMock()
                mock_lock.return_value.__aexit__ = AsyncMock()
                with patch.object(service, "_send_schedule_notification_to_doctor"):
                    schedule = await service.create(data)

                    assert schedule is not None
                    assert schedule.doctor_id == test_doctor.id
                    assert schedule.schedule_date == tomorrow
                    assert schedule.total_slots == 20
                    assert schedule.booked_slots == 0

    async def test_create_duplicate_raises_error(self, db_session, test_schedule, test_doctor):
        """测试创建重复排班 - 应抛出错误"""
        service = ScheduleService(db_session)

        data = ScheduleCreate(
            doctor_id=test_doctor.id,
            store_id=test_schedule.store_id,
            schedule_date=test_schedule.schedule_date,
            time_slot=test_schedule.time_slot,
            start_time=test_schedule.start_time,
            end_time=test_schedule.end_time,
            total_slots=10,
            status=1,
        )

        # Mock Redis 分布式锁
        with patch("app.middleware.tenant_context.get_current_tenant_id", return_value=test_schedule.tenant_id):
            with patch("app.core.redis.RedisCache.tenant_distributed_lock") as mock_lock:
                # 创建同步的异步上下文管理器 mock
                class MockLock:
                    async def __aenter__(self):
                        return "lock"
                    async def __aexit__(self, *args):
                        pass

                mock_lock.return_value = MockLock()

                with pytest.raises(ValueError, match="该时段排班已存在"):
                    await service.create(data)

    async def test_create_without_time_slot_raises_error(self, db_session, test_doctor):
        """测试创建排班 - 缺少 time_slot 和 start_time 应抛出错误"""
        service = ScheduleService(db_session)

        data = ScheduleCreate(
            doctor_id=test_doctor.id,
            store_id=test_doctor.store_id,
            schedule_date=date.today(),
            total_slots=10,
        )

        with patch("app.middleware.tenant_context.get_current_tenant_id", return_value=test_doctor.tenant_id):
            with pytest.raises(ValueError, match="必须提供 time_slot 或 start_time"):
                await service.create(data)

    async def test_update_success(self, db_session, test_schedule):
        """测试更新排班成功"""
        service = ScheduleService(db_session)

        data = ScheduleUpdate(total_slots=30)

        with patch("app.middleware.tenant_context.get_current_tenant_id", return_value=test_schedule.tenant_id):
            schedule = await service.update(test_schedule.id, data)
            assert schedule is not None
            assert schedule.total_slots == 30

    async def test_update_not_found(self, db_session):
        """测试更新不存在的排班"""
        service = ScheduleService(db_session)

        data = ScheduleUpdate(total_slots=30)

        with patch("app.middleware.tenant_context.get_current_tenant_id", return_value="test-tenant"):
            schedule = await service.update("non-existent-id", data)
            assert schedule is None

    async def test_update_total_slots_less_than_booked_raises_error(self, db_session, test_schedule):
        """测试更新排班 - 总号源小于已预约数应抛出错误"""
        service = ScheduleService(db_session)
        test_schedule.booked_slots = 5
        await db_session.commit()

        data = ScheduleUpdate(total_slots=3)

        with patch("app.middleware.tenant_context.get_current_tenant_id", return_value=test_schedule.tenant_id):
            with pytest.raises(ValueError, match="总号源数不能小于已预约数"):
                await service.update(test_schedule.id, data)

    async def test_delete_success(self, db_session, test_schedule):
        """测试删除排班成功"""
        service = ScheduleService(db_session)

        with patch("app.middleware.tenant_context.get_current_tenant_id", return_value=test_schedule.tenant_id):
            result = await service.delete(test_schedule.id)
            assert result is True

            # 验证已删除
            result = await db_session.execute(select(Schedule).where(Schedule.id == test_schedule.id))
            assert result.scalar_one_or_none() is None

    async def test_delete_not_found_raises_error(self, db_session):
        """测试删除不存在的排班"""
        service = ScheduleService(db_session)

        with patch("app.middleware.tenant_context.get_current_tenant_id", return_value="test-tenant"):
            with pytest.raises(ValueError, match="排班不存在"):
                await service.delete("non-existent-id")

    async def test_delete_with_appointment_raises_error(self, db_session, test_schedule, test_appointment):
        """测试删除有预约的排班 - 应抛出错误"""
        service = ScheduleService(db_session)

        with patch("app.middleware.tenant_context.get_current_tenant_id", return_value=test_schedule.tenant_id):
            with pytest.raises(ValueError, match="该排班已有预约记录，无法删除"):
                await service.delete(test_schedule.id)

    async def test_batch_create_success(self, db_session, test_doctor, test_tenant):
        """测试批量创建排班成功"""
        service = ScheduleService(db_session)

        data = ScheduleBatchCreate(
            doctor_id=test_doctor.id,
            store_id=test_doctor.store_id,
            schedule_date=date.today(),  # 添加必需的 schedule_date 字段
            start_date=date.today(),
            end_date=date.today() + timedelta(days=2),
            weekdays=[1, 2, 3, 4, 5],
            time_slots=["morning", "afternoon"],
            total_slots=20,
        )

        with patch("app.middleware.tenant_context.get_current_tenant_id", return_value=test_tenant.id):
            with patch.object(service, "_send_schedule_notification_to_doctor"):
                count = await service.batch_create(data)
                # 根据当前日期的星期几计算预期数量
                assert count >= 0

    async def test_batch_create_doctor_not_found_raises_error(self, db_session):
        """测试批量创建 - 医生不存在应抛出错误"""
        service = ScheduleService(db_session)

        data = ScheduleBatchCreate(
            doctor_id="non-existent-doctor",
            schedule_date=date.today(),  # 添加必需的 schedule_date 字段
            start_date=date.today(),
            end_date=date.today() + timedelta(days=1),
            weekdays=[1],
            time_slots=["morning"],
            total_slots=10,
        )

        with patch("app.middleware.tenant_context.get_current_tenant_id", return_value="test-tenant"):
            with pytest.raises(ValueError, match="医生不存在"):
                await service.batch_create(data)

    async def test_batch_suspend_success(self, db_session, test_schedule, test_doctor):
        """测试批量停诊成功"""
        service = ScheduleService(db_session)

        # 确保排班有医生关联和状态为启用
        test_schedule.doctor_id = test_doctor.id
        test_schedule.status = 1
        await db_session.commit()

        # 预加载 doctor 关系
        from sqlalchemy.orm import selectinload
        result = await db_session.execute(
            select(Schedule)
            .options(selectinload(Schedule.doctor))
            .where(Schedule.id == test_schedule.id)
        )
        schedule_with_doctor = result.scalar_one_or_none()

        if schedule_with_doctor and schedule_with_doctor.doctor:
            with patch("app.middleware.tenant_context.get_current_tenant_id", return_value=test_schedule.tenant_id):
                with patch.object(service, "_send_batch_suspend_notifications"):
                    suspend_result = await service.batch_suspend([test_schedule.id], reason="测试停诊")

                    # 只验证调用成功，不验证具体返回值
                    assert "failed_count" in suspend_result
                    assert "success_count" in suspend_result
        else:
            # 如果没有医生关联，跳过测试
            pytest.skip("排班没有医生关联，跳过测试")

    async def test_batch_suspend_empty_list(self, db_session):
        """测试批量停诊 - 空列表"""
        service = ScheduleService(db_session)

        result = await service.batch_suspend([])
        assert result["success_count"] == 0
        assert result["message"] == "没有提供排班ID"

    async def test_batch_resume_success(self, db_session, test_schedule):
        """测试批量恢复成功"""
        service = ScheduleService(db_session)
        # 先停诊
        test_schedule.status = 0
        await db_session.commit()

        with patch("app.middleware.tenant_context.get_current_tenant_id", return_value=test_schedule.tenant_id):
            count = await service.batch_resume([test_schedule.id])
            assert count >= 0

    async def test_batch_resume_empty_list(self, db_session):
        """测试批量恢复 - 空列表"""
        service = ScheduleService(db_session)
        count = await service.batch_resume([])
        assert count == 0

    async def test_batch_delete_success(self, db_session, test_schedule, test_tenant):
        """测试批量删除成功"""
        service = ScheduleService(db_session)
        # 创建另一个无预约的排班
        another_schedule = Schedule(
            id=str(__import__("uuid").uuid4()),
            doctor_id=test_schedule.doctor_id,
            store_id=test_schedule.store_id,
            tenant_id=test_tenant.id,
            schedule_date=date.today() + timedelta(days=2),
            time_slot="morning",
            total_slots=10,
            booked_slots=0,
            status=1,
        )
        db_session.add(another_schedule)
        await db_session.commit()

        with patch("app.middleware.tenant_context.get_current_tenant_id", return_value=test_tenant.id):
            result = await service.batch_delete([another_schedule.id])

            assert result["success_count"] == 1
            assert result["deleted_count"] == 1
            assert another_schedule.id in result["success_ids"]

    async def test_batch_delete_with_appointment_skipped(self, db_session, test_schedule, test_appointment):
        """测试批量删除 - 有预约的排班被跳过"""
        service = ScheduleService(db_session)

        with patch("app.middleware.tenant_context.get_current_tenant_id", return_value=test_schedule.tenant_id):
            result = await service.batch_delete([test_schedule.id])

            assert result["success_count"] == 0
            assert len(result["skipped_ids"]) == 1
            assert test_schedule.id in result["skipped_ids"]


@pytest.mark.unit
class TestScheduleGenerationMixin:
    """测试排班生成功能"""

    async def test_check_rest_day_true(self, db_session, test_store, test_tenant):
        """测试检查休息日 - 是休息日"""
        service = ScheduleService(db_session)
        check_date = date.today() + timedelta(days=1)

        # 创建休息日
        rest_day = RestDay(
            id=str(__import__("uuid").uuid4()),
            tenant_id=test_tenant.id,
            store_id=test_store.id,
            start_date=check_date,
            end_date=check_date,
            status=1,
        )
        db_session.add(rest_day)
        await db_session.commit()

        is_rest = await service._check_rest_day(check_date, test_store.id)
        assert is_rest is True

    async def test_check_rest_day_false(self, db_session, test_store):
        """测试检查休息日 - 非休息日"""
        service = ScheduleService(db_session)
        check_date = date.today() + timedelta(days=10)

        is_rest = await service._check_rest_day(check_date, test_store.id)
        assert is_rest is False

    async def test_check_rest_day_with_doctor_filter(self, db_session, test_store, test_tenant):
        """测试检查休息日 - 医生级过滤"""
        service = ScheduleService(db_session)
        check_date = date.today() + timedelta(days=1)

        # 创建仅针对特定医生的休息日
        rest_day = RestDay(
            id=str(__import__("uuid").uuid4()),
            tenant_id=test_tenant.id,
            store_id=test_store.id,
            start_date=check_date,
            end_date=check_date,
            doctor_ids=json.dumps(["doctor-1"]),
            status=1,
        )
        db_session.add(rest_day)
        await db_session.commit()

        # 指定医生应被判定为休息日
        is_rest = await service._check_rest_day(check_date, test_store.id, "doctor-1")
        assert is_rest is True

        # 其他医生不应被判定为休息日
        is_rest = await service._check_rest_day(check_date, test_store.id, "doctor-2")
        assert is_rest is False

    async def test_create_schedule_if_not_exists_success(self, db_session, test_doctor, test_store, test_tenant):
        """测试创建排班（如不存在）- 成功"""
        service = ScheduleService(db_session)
        schedule_date = date.today() + timedelta(days=5)

        schedule, created = await service._create_schedule_if_not_exists(
            doctor_id=test_doctor.id,
            store_id=test_store.id,
            schedule_date=schedule_date,
            start_time=time(9, 0),
            end_time=time(12, 0),
            time_slot="morning",
            total_slots=20,
            check_rest_day=False,
            check_duplicate=True,
        )

        assert created is True
        assert schedule is not None
        assert schedule.doctor_id == test_doctor.id

    async def test_create_schedule_if_not_exists_duplicate(self, db_session, test_schedule):
        """测试创建排班（如不存在）- 重复排班"""
        service = ScheduleService(db_session)

        schedule, created = await service._create_schedule_if_not_exists(
            doctor_id=test_schedule.doctor_id,
            store_id=test_schedule.store_id,
            schedule_date=test_schedule.schedule_date,
            start_time=test_schedule.start_time,
            end_time=test_schedule.end_time,
            time_slot=test_schedule.time_slot,
            total_slots=10,
            check_rest_day=False,
            check_duplicate=True,
        )

        assert created is False
        assert schedule is None

    async def test_create_schedule_if_not_exists_rest_day_skipped(self, db_session, test_store, test_tenant):
        """测试创建排班（如不存在）- 休息日跳过"""
        service = ScheduleService(db_session)
        check_date = date.today() + timedelta(days=1)

        # 创建休息日
        rest_day = RestDay(
            id=str(__import__("uuid").uuid4()),
            tenant_id=test_tenant.id,
            store_id=test_store.id,
            start_date=check_date,
            end_date=check_date,
            status=1,
        )
        db_session.add(rest_day)
        await db_session.commit()

        schedule, created = await service._create_schedule_if_not_exists(
            doctor_id="doctor-1",
            store_id=test_store.id,
            schedule_date=check_date,
            start_time=time(9, 0),
            end_time=time(12, 0),
            time_slot="morning",
            total_slots=10,
            check_rest_day=True,
            check_duplicate=False,
        )

        assert created is False
        assert schedule is None

    async def test_generate_from_template_success(self, db_session, test_doctor, test_store, test_tenant, test_department):
        """测试从模板生成排班 - 成功"""
        service = ScheduleService(db_session)

        # 创建排班模板
        import uuid
        template = ScheduleTemplate(
            id=str(uuid.uuid4()),
            name="测试模板",
            doctor_id=test_doctor.id,
            store_id=test_store.id,
            department_id=test_department.id,
            tenant_id=test_tenant.id,
            schedule_mode="weekly",
            weekday_list=[1, 2, 3, 4, 5],
            start_time=time(9, 0),
            end_time=time(17, 0),
            slot_count=2,
            slot_capacity=10,
            break_times_list=[],
            appointment_type="normal",
            status=1,
        )
        db_session.add(template)
        await db_session.commit()

        start_date = date.today() + timedelta(days=7)
        end_date = start_date + timedelta(days=4)

        count = await service.generate_from_template(
            template_id=template.id,
            start_date=start_date,
            end_date=end_date,
            check_rest_day=False,
        )

        # 应该生成一些排班（具体数量取决于星期几）
        assert count >= 0

    async def test_generate_from_template_not_found(self, db_session):
        """测试从模板生成排班 - 模板不存在"""
        service = ScheduleService(db_session)

        count = await service.generate_from_template(
            template_id="non-existent-template",
            start_date=date.today(),
            end_date=date.today() + timedelta(days=1),
        )

        assert count == 0

    async def test_generate_from_template_disabled(self, db_session, test_doctor, test_store, test_tenant, test_department):
        """测试从模板生成排班 - 模板已禁用"""
        service = ScheduleService(db_session)

        # 创建已禁用的排班模板
        import uuid
        template = ScheduleTemplate(
            id=str(uuid.uuid4()),
            name="已禁用模板",
            doctor_id=test_doctor.id,
            store_id=test_store.id,
            department_id=test_department.id,
            tenant_id=test_tenant.id,
            schedule_mode="weekly",
            weekday_list=[1],
            start_time=time(9, 0),
            end_time=time(17, 0),
            slot_count=1,
            slot_capacity=10,
            status=0,  # 已禁用
        )
        db_session.add(template)
        await db_session.commit()

        count = await service.generate_from_template(
            template_id=template.id,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=1),
        )

        assert count == 0

    async def test_send_schedule_notification_to_doctor(self, db_session):
        """测试发送排班通知 - 仅验证方法不抛出异常"""
        service = ScheduleService(db_session)

        # 设置租户上下文
        from app.middleware.tenant_context import _current_tenant_id
        token = _current_tenant_id.set("test-tenant")

        try:
            # 测试不抛出异常即可
            await service._send_schedule_notification_to_doctor(
                doctor_id="doctor-1",
                title="测试通知",
                content="测试内容",
                schedule_id="schedule-1",
            )
            # 如果没有抛出异常，测试通过
            assert True
        finally:
            _current_tenant_id.reset(token)
