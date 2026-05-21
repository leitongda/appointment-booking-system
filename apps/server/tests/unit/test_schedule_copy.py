"""
排班批量复制功能测试

覆盖场景:
- 成功复制（skip 策略，无冲突）
- 成功复制（overwrite 策略，覆盖旧排班）
- 冲突收集（manual 策略）
- 指定医生复制
- 跳过节假日
- 日期偏移计算正确
- 租户隔离
- copy_quota=False 重置号源
- copy_fee=False 重置费用
- 空源周期返回零结果
"""
from datetime import date, time, timedelta, datetime
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from app.modules.schedules.service import ScheduleService
from app.schemas.schedule import ScheduleBatchCopyRequest
from app.models.schedule import Schedule


@pytest.mark.unit
class TestScheduleBatchCopy:
    """测试排班批量复制功能"""

    def _make_source_schedules(self, db_session, tenant_id, doctor_id, store_id, start_date, count=3):
        """辅助方法：创建源周期排班"""
        schedules = []
        for i in range(count):
            s = Schedule(
                id=str(uuid4()),
                doctor_id=doctor_id,
                store_id=store_id,
                tenant_id=tenant_id,
                schedule_date=start_date + timedelta(days=i),
                time_slot="morning",
                start_time=time(8, 0),
                end_time=time(12, 0),
                total_slots=20,
                booked_slots=0,
                online_quota=10,
                offline_quota=5,
                reserved_quota=3,
                extra_quota=2,
                fee=5000,
                appointment_type="normal",
                status=1,
                schedule_status="published",
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
            db_session.add(s)
            schedules.append(s)
        return schedules

    async def test_copy_skip_strategy_no_conflict(
        self, db_session, test_tenant, test_doctor, test_store,
    ):
        """成功复制 - skip 策略，无冲突"""
        source_start = date.today() + timedelta(days=10)
        source_end = source_start + timedelta(days=2)
        target_start = source_start + timedelta(days=30)
        target_end = source_start + timedelta(days=32)

        sources = self._make_source_schedules(
            db_session, test_tenant.id, test_doctor.id, test_store.id, source_start, count=3,
        )
        await db_session.commit()

        service = ScheduleService(db_session)
        request = ScheduleBatchCopyRequest(
            sourceStartDate=source_start,
            sourceEndDate=source_end,
            targetStartDate=target_start,
            targetEndDate=target_end,
            copyQuota=True,
            copyRoom=True,
            copyFee=True,
            skipHolidays=False,
            conflictStrategy="skip",
        )

        with patch("app.middleware.tenant_context.get_current_tenant_id", return_value=test_tenant.id), \
             patch("app.core.redis.RedisCache.tenant_distributed_lock") as mock_lock:
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__ = AsyncMock(return_value="lock_value")
            mock_ctx.__aexit__ = AsyncMock(return_value=None)
            mock_lock.return_value = mock_ctx

            result = await service.batch_copy(request)

        assert result.total_source == 3
        assert result.copied == 3
        assert result.skipped == 0
        assert result.failed == 0
        assert result.overwritten == 0
        assert len(result.conflicts) == 0

        # 验证目标排班确实被创建
        for i in range(3):
            target_date = target_start + timedelta(days=i)
            query = await db_session.execute(
                __import__("sqlalchemy", fromlist=["select"]).select(Schedule).where(
                    Schedule.doctor_id == test_doctor.id,
                    Schedule.schedule_date == target_date,
                    Schedule.tenant_id == test_tenant.id,
                )
            )
            created = query.scalars().all()
            assert len(created) >= 1, f"目标日期 {target_date} 应有排班"

    async def test_copy_overwrite_strategy(
        self, db_session, test_tenant, test_doctor, test_store,
    ):
        """成功复制 - overwrite 策略，覆盖已有排班"""
        source_start = date.today() + timedelta(days=10)
        target_start = source_start + timedelta(days=30)

        # 创建源排班
        self._make_source_schedules(
            db_session, test_tenant.id, test_doctor.id, test_store.id, source_start, count=1,
        )

        # 在目标位置创建一个旧排班（无预约）
        old_schedule = Schedule(
            id=str(uuid4()),
            doctor_id=test_doctor.id,
            store_id=test_store.id,
            tenant_id=test_tenant.id,
            schedule_date=target_start,
            time_slot="morning",
            start_time=time(8, 0),
            end_time=time(12, 0),
            total_slots=5,
            booked_slots=0,
            online_quota=5,
            status=1,
            schedule_status="published",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db_session.add(old_schedule)
        await db_session.commit()

        service = ScheduleService(db_session)
        request = ScheduleBatchCopyRequest(
            sourceStartDate=source_start,
            sourceEndDate=source_start,
            targetStartDate=target_start,
            targetEndDate=target_start,
            skipHolidays=False,
            conflictStrategy="overwrite",
        )

        with patch("app.middleware.tenant_context.get_current_tenant_id", return_value=test_tenant.id), \
             patch("app.core.redis.RedisCache.tenant_distributed_lock") as mock_lock:
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__ = AsyncMock(return_value="lock_value")
            mock_ctx.__aexit__ = AsyncMock(return_value=None)
            mock_lock.return_value = mock_ctx

            result = await service.batch_copy(request)

        assert result.total_source == 1
        assert result.copied == 1
        assert result.overwritten == 1
        assert result.failed == 0

    async def test_copy_manual_strategy_collects_conflicts(
        self, db_session, test_tenant, test_doctor, test_store,
    ):
        """manual 策略 - 收集冲突信息返回"""
        source_start = date.today() + timedelta(days=10)
        target_start = source_start + timedelta(days=30)

        self._make_source_schedules(
            db_session, test_tenant.id, test_doctor.id, test_store.id, source_start, count=1,
        )

        # 在目标位置创建一个旧排班
        old_schedule = Schedule(
            id=str(uuid4()),
            doctor_id=test_doctor.id,
            store_id=test_store.id,
            tenant_id=test_tenant.id,
            schedule_date=target_start,
            time_slot="morning",
            start_time=time(8, 0),
            end_time=time(12, 0),
            total_slots=5,
            booked_slots=0,
            online_quota=5,
            status=1,
            schedule_status="published",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db_session.add(old_schedule)
        await db_session.commit()

        service = ScheduleService(db_session)
        request = ScheduleBatchCopyRequest(
            sourceStartDate=source_start,
            sourceEndDate=source_start,
            targetStartDate=target_start,
            targetEndDate=target_start,
            skipHolidays=False,
            conflictStrategy="manual",
        )

        with patch("app.middleware.tenant_context.get_current_tenant_id", return_value=test_tenant.id), \
             patch("app.core.redis.RedisCache.tenant_distributed_lock") as mock_lock:
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__ = AsyncMock(return_value="lock_value")
            mock_ctx.__aexit__ = AsyncMock(return_value=None)
            mock_lock.return_value = mock_ctx

            result = await service.batch_copy(request)

        assert result.total_source == 1
        assert result.copied == 0  # manual 策略不自动创建
        assert len(result.conflicts) == 1
        assert result.conflicts[0]["target_date"] == str(target_start)
        assert len(result.conflicts[0]["conflicts"]) > 0

    async def test_copy_with_specific_doctors(
        self, db_session, test_tenant, test_doctor, test_store, test_department,
    ):
        """指定医生复制 - 只复制指定医生的排班"""
        from app.models.doctor import Doctor

        source_start = date.today() + timedelta(days=10)
        target_start = source_start + timedelta(days=30)

        # 创建另一个医生
        other_doctor = Doctor(
            id=str(uuid4()),
            name="其他医生",
            title="副主任医师",
            department_id=test_department.id,
            store_id=test_store.id,
            tenant_id=test_tenant.id,
            status=1,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db_session.add(other_doctor)

        # 为两个医生各创建 1 条源排班
        self._make_source_schedules(
            db_session, test_tenant.id, test_doctor.id, test_store.id, source_start, count=1,
        )
        self._make_source_schedules(
            db_session, test_tenant.id, other_doctor.id, test_store.id, source_start, count=1,
        )
        await db_session.commit()

        service = ScheduleService(db_session)
        request = ScheduleBatchCopyRequest(
            sourceStartDate=source_start,
            sourceEndDate=source_start,
            targetStartDate=target_start,
            targetEndDate=target_start,
            doctorIds=[test_doctor.id],  # 只复制 test_doctor
            skipHolidays=False,
            conflictStrategy="skip",
        )

        with patch("app.middleware.tenant_context.get_current_tenant_id", return_value=test_tenant.id), \
             patch("app.core.redis.RedisCache.tenant_distributed_lock") as mock_lock:
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__ = AsyncMock(return_value="lock_value")
            mock_ctx.__aexit__ = AsyncMock(return_value=None)
            mock_lock.return_value = mock_ctx

            result = await service.batch_copy(request)

        assert result.total_source == 1  # 只查到 test_doctor 的排班
        assert result.copied == 1

    async def test_copy_date_offset_correct(
        self, db_session, test_tenant, test_doctor, test_store,
    ):
        """日期偏移计算正确 - 验证目标日期 = 源日期 + 偏移"""
        source_start = date(2026, 6, 1)
        source_end = date(2026, 6, 3)
        target_start = date(2026, 7, 6)  # 偏移 35 天
        target_end = date(2026, 7, 8)

        self._make_source_schedules(
            db_session, test_tenant.id, test_doctor.id, test_store.id, source_start, count=3,
        )
        await db_session.commit()

        service = ScheduleService(db_session)
        request = ScheduleBatchCopyRequest(
            sourceStartDate=source_start,
            sourceEndDate=source_end,
            targetStartDate=target_start,
            targetEndDate=target_end,
            skipHolidays=False,
            conflictStrategy="skip",
        )

        with patch("app.middleware.tenant_context.get_current_tenant_id", return_value=test_tenant.id), \
             patch("app.core.redis.RedisCache.tenant_distributed_lock") as mock_lock:
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__ = AsyncMock(return_value="lock_value")
            mock_ctx.__aexit__ = AsyncMock(return_value=None)
            mock_lock.return_value = mock_ctx

            result = await service.batch_copy(request)

        assert result.copied == 3

        # 验证每个目标排班的日期
        from sqlalchemy import select as sa_select
        for i in range(3):
            expected_date = target_start + timedelta(days=i)
            query_result = await db_session.execute(
                sa_select(Schedule).where(
                    Schedule.doctor_id == test_doctor.id,
                    Schedule.schedule_date == expected_date,
                    Schedule.tenant_id == test_tenant.id,
                )
            )
            schedules = query_result.scalars().all()
            assert len(schedules) >= 1, f"日期 {expected_date} 应存在排班"
            # 验证其他字段被正确复制
            copied = schedules[0]
            assert copied.time_slot == "morning"
            assert copied.start_time == time(8, 0)
            assert copied.end_time == time(12, 0)

    async def test_copy_empty_source_returns_zero(
        self, db_session, test_tenant, test_doctor, test_store,
    ):
        """空源周期返回零结果"""
        source_start = date.today() + timedelta(days=100)
        source_end = source_start + timedelta(days=5)
        target_start = source_start + timedelta(days=30)
        target_end = source_start + timedelta(days=35)

        service = ScheduleService(db_session)
        request = ScheduleBatchCopyRequest(
            sourceStartDate=source_start,
            sourceEndDate=source_end,
            targetStartDate=target_start,
            targetEndDate=target_end,
            skipHolidays=False,
            conflictStrategy="skip",
        )

        with patch("app.middleware.tenant_context.get_current_tenant_id", return_value=test_tenant.id):
            result = await service.batch_copy(request)

        assert result.total_source == 0
        assert result.copied == 0
        assert result.skipped == 0
        assert result.failed == 0

    async def test_copy_quota_not_copied(
        self, db_session, test_tenant, test_doctor, test_store,
    ):
        """copy_quota=False 时号源重置为默认值"""
        source_start = date.today() + timedelta(days=10)
        target_start = source_start + timedelta(days=30)

        self._make_source_schedules(
            db_session, test_tenant.id, test_doctor.id, test_store.id, source_start, count=1,
        )
        await db_session.commit()

        service = ScheduleService(db_session)
        request = ScheduleBatchCopyRequest(
            sourceStartDate=source_start,
            sourceEndDate=source_start,
            targetStartDate=target_start,
            targetEndDate=target_start,
            copyQuota=False,
            copyFee=True,
            skipHolidays=False,
            conflictStrategy="skip",
        )

        with patch("app.middleware.tenant_context.get_current_tenant_id", return_value=test_tenant.id), \
             patch("app.core.redis.RedisCache.tenant_distributed_lock") as mock_lock:
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__ = AsyncMock(return_value="lock_value")
            mock_ctx.__aexit__ = AsyncMock(return_value=None)
            mock_lock.return_value = mock_ctx

            result = await service.batch_copy(request)

        assert result.copied == 1

        # 验证号源被重置
        from sqlalchemy import select as sa_select
        query_result = await db_session.execute(
            sa_select(Schedule).where(
                Schedule.doctor_id == test_doctor.id,
                Schedule.schedule_date == target_start,
                Schedule.tenant_id == test_tenant.id,
            )
        )
        copied = query_result.scalars().first()
        assert copied is not None
        assert copied.offline_quota == 0
        assert copied.reserved_quota == 0
        assert copied.extra_quota == 0

    async def test_copy_fee_not_copied(
        self, db_session, test_tenant, test_doctor, test_store,
    ):
        """copy_fee=False 时费用重置为 0"""
        source_start = date.today() + timedelta(days=10)
        target_start = source_start + timedelta(days=30)

        self._make_source_schedules(
            db_session, test_tenant.id, test_doctor.id, test_store.id, source_start, count=1,
        )
        await db_session.commit()

        service = ScheduleService(db_session)
        request = ScheduleBatchCopyRequest(
            sourceStartDate=source_start,
            sourceEndDate=source_start,
            targetStartDate=target_start,
            targetEndDate=target_start,
            copyQuota=True,
            copyFee=False,
            skipHolidays=False,
            conflictStrategy="skip",
        )

        with patch("app.middleware.tenant_context.get_current_tenant_id", return_value=test_tenant.id), \
             patch("app.core.redis.RedisCache.tenant_distributed_lock") as mock_lock:
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__ = AsyncMock(return_value="lock_value")
            mock_ctx.__aexit__ = AsyncMock(return_value=None)
            mock_lock.return_value = mock_ctx

            result = await service.batch_copy(request)

        assert result.copied == 1

        from sqlalchemy import select as sa_select
        query_result = await db_session.execute(
            sa_select(Schedule).where(
                Schedule.doctor_id == test_doctor.id,
                Schedule.schedule_date == target_start,
                Schedule.tenant_id == test_tenant.id,
            )
        )
        copied = query_result.scalars().first()
        assert copied is not None
        assert copied.fee == 0

    async def test_copy_skip_strategy_skips_conflicts(
        self, db_session, test_tenant, test_doctor, test_store,
    ):
        """skip 策略下冲突排班被跳过"""
        source_start = date.today() + timedelta(days=10)
        target_start = source_start + timedelta(days=30)

        self._make_source_schedules(
            db_session, test_tenant.id, test_doctor.id, test_store.id, source_start, count=1,
        )

        # 在目标位置创建一个旧排班（有冲突）
        old_schedule = Schedule(
            id=str(uuid4()),
            doctor_id=test_doctor.id,
            store_id=test_store.id,
            tenant_id=test_tenant.id,
            schedule_date=target_start,
            time_slot="morning",
            start_time=time(8, 0),
            end_time=time(12, 0),
            total_slots=5,
            booked_slots=0,
            online_quota=5,
            status=1,
            schedule_status="published",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db_session.add(old_schedule)
        await db_session.commit()

        service = ScheduleService(db_session)
        request = ScheduleBatchCopyRequest(
            sourceStartDate=source_start,
            sourceEndDate=source_start,
            targetStartDate=target_start,
            targetEndDate=target_start,
            skipHolidays=False,
            conflictStrategy="skip",
        )

        with patch("app.middleware.tenant_context.get_current_tenant_id", return_value=test_tenant.id), \
             patch("app.core.redis.RedisCache.tenant_distributed_lock") as mock_lock:
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__ = AsyncMock(return_value="lock_value")
            mock_ctx.__aexit__ = AsyncMock(return_value=None)
            mock_lock.return_value = mock_ctx

            result = await service.batch_copy(request)

        assert result.total_source == 1
        assert result.copied == 0
        assert result.skipped == 1
        assert result.failed == 0

    async def test_copy_tenant_isolation(
        self, db_session, test_tenant, test_doctor, test_store,
    ):
        """租户隔离 - 不同租户的排班不会被复制"""
        from app.models.tenant import Tenant, SubscriptionPlan

        # 创建另一个租户
        plan = SubscriptionPlan(
            id=str(uuid4()),
            plan_code="other_plan",
            name="其他计划",
            status=1,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db_session.add(plan)
        await db_session.flush()

        other_tenant = Tenant(
            id=str(uuid4()),
            tenant_code="other_tenant",
            name="其他租户",
            status=1,
            subscription_plan_id=plan.id,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db_session.add(other_tenant)
        await db_session.flush()

        source_start = date.today() + timedelta(days=10)
        target_start = source_start + timedelta(days=30)

        # 为 test_tenant 创建源排班
        self._make_source_schedules(
            db_session, test_tenant.id, test_doctor.id, test_store.id, source_start, count=1,
        )
        await db_session.commit()

        service = ScheduleService(db_session)
        request = ScheduleBatchCopyRequest(
            sourceStartDate=source_start,
            sourceEndDate=source_start,
            targetStartDate=target_start,
            targetEndDate=target_start,
            skipHolidays=False,
            conflictStrategy="skip",
        )

        # 使用 other_tenant 的上下文 - 应该查不到源排班
        with patch("app.middleware.tenant_context.get_current_tenant_id", return_value=other_tenant.id):
            result = await service.batch_copy(request)

        assert result.total_source == 0
        assert result.copied == 0

    async def test_copy_preserves_appointment_type(
        self, db_session, test_tenant, test_doctor, test_store,
    ):
        """复制后保留预约类型"""
        source_start = date.today() + timedelta(days=10)
        target_start = source_start + timedelta(days=30)

        # 创建专家排班
        s = Schedule(
            id=str(uuid4()),
            doctor_id=test_doctor.id,
            store_id=test_store.id,
            tenant_id=test_tenant.id,
            schedule_date=source_start,
            time_slot="afternoon",
            start_time=time(14, 0),
            end_time=time(17, 0),
            total_slots=5,
            booked_slots=0,
            online_quota=5,
            fee=10000,
            appointment_type="expert",
            status=1,
            schedule_status="published",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db_session.add(s)
        await db_session.commit()

        service = ScheduleService(db_session)
        request = ScheduleBatchCopyRequest(
            sourceStartDate=source_start,
            sourceEndDate=source_start,
            targetStartDate=target_start,
            targetEndDate=target_start,
            skipHolidays=False,
            conflictStrategy="skip",
        )

        with patch("app.middleware.tenant_context.get_current_tenant_id", return_value=test_tenant.id), \
             patch("app.core.redis.RedisCache.tenant_distributed_lock") as mock_lock:
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__ = AsyncMock(return_value="lock_value")
            mock_ctx.__aexit__ = AsyncMock(return_value=None)
            mock_lock.return_value = mock_ctx

            result = await service.batch_copy(request)

        assert result.copied == 1

        from sqlalchemy import select as sa_select
        query_result = await db_session.execute(
            sa_select(Schedule).where(
                Schedule.doctor_id == test_doctor.id,
                Schedule.schedule_date == target_start,
                Schedule.tenant_id == test_tenant.id,
            )
        )
        copied = query_result.scalars().first()
        assert copied is not None
        assert copied.appointment_type == "expert"
        assert copied.fee == 10000
