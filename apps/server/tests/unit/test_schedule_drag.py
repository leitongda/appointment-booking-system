"""
排班拖拽调整功能测试

覆盖场景:
- 成功拖拽（无预约、无冲突）
- 有预约时拖拽被拒绝
- 停诊状态拖拽被拒绝
- 历史排班拖拽被拒绝
- 目标位置有冲突时返回冲突信息
- 租户隔离验证
"""
from datetime import date, time, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.modules.schedules.service import ScheduleService
from app.modules.schedules.service_mutation import ScheduleMutationMixin
from app.models.schedule import Schedule


@pytest.mark.unit
class TestScheduleDragAdjust:
    """测试排班拖拽调整功能"""

    async def test_drag_adjust_success(self, db_session, test_schedule, test_tenant):
        """成功拖拽 - 无预约、无冲突"""
        service = ScheduleService(db_session)
        target_date = test_schedule.schedule_date + timedelta(days=1)

        with patch("app.middleware.tenant_context.get_current_tenant_id", return_value=test_tenant.id), \
             patch("app.core.redis.RedisCache.tenant_distributed_lock") as mock_lock:
            # Mock 分布式锁
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__ = AsyncMock(return_value="lock_value")
            mock_ctx.__aexit__ = AsyncMock(return_value=None)
            mock_lock.return_value = mock_ctx

            result = await service.drag_adjust(
                schedule_id=test_schedule.id,
                target_date=target_date,
                target_start_time=time(9, 0),
                target_end_time=time(11, 0),
                target_time_slot="morning",
            )

        assert result["success"] is True
        assert result["schedule"] is not None
        assert result["schedule"].schedule_date == target_date
        assert result["schedule"].start_time == time(9, 0)
        assert result["schedule"].end_time == time(11, 0)
        assert result["message"] == "调整成功"

    async def test_drag_adjust_with_booked_slots(self, db_session, test_schedule_full, test_tenant):
        """有预约时拖拽被拒绝"""
        service = ScheduleService(db_session)
        target_date = test_schedule_full.schedule_date + timedelta(days=1)

        with patch("app.middleware.tenant_context.get_current_tenant_id", return_value=test_tenant.id):
            result = await service.drag_adjust(
                schedule_id=test_schedule_full.id,
                target_date=target_date,
                target_time_slot="afternoon",
            )

        assert result["success"] is False
        assert "已有" in result["message"]
        assert "预约" in result["message"]
        assert result["schedule"] is None

    async def test_drag_adjust_suspended_schedule(self, db_session, test_tenant, test_doctor, test_store):
        """停诊状态拖拽被拒绝"""
        from datetime import datetime
        tomorrow = date.today() + timedelta(days=1)
        schedule = Schedule(
            id=str(uuid4()),
            doctor_id=test_doctor.id,
            store_id=test_store.id,
            tenant_id=test_tenant.id,
            schedule_date=tomorrow,
            time_slot="morning",
            start_time=time(8, 0),
            end_time=time(12, 0),
            total_slots=10,
            booked_slots=0,
            status=0,  # 停诊
            schedule_status="suspended",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db_session.add(schedule)
        await db_session.commit()
        await db_session.refresh(schedule)

        service = ScheduleService(db_session)
        target_date = tomorrow + timedelta(days=1)

        with patch("app.middleware.tenant_context.get_current_tenant_id", return_value=test_tenant.id):
            result = await service.drag_adjust(
                schedule_id=schedule.id,
                target_date=target_date,
                target_time_slot="afternoon",
            )

        assert result["success"] is False
        assert "停诊" in result["message"]
        assert result["schedule"] is None

    async def test_drag_adjust_history_schedule(self, db_session, test_tenant, test_doctor, test_store):
        """历史排班拖拽被拒绝"""
        from datetime import datetime
        yesterday = date.today() - timedelta(days=1)
        schedule = Schedule(
            id=str(uuid4()),
            doctor_id=test_doctor.id,
            store_id=test_store.id,
            tenant_id=test_tenant.id,
            schedule_date=yesterday,
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
        await db_session.refresh(schedule)

        service = ScheduleService(db_session)
        target_date = date.today() + timedelta(days=1)

        with patch("app.middleware.tenant_context.get_current_tenant_id", return_value=test_tenant.id):
            result = await service.drag_adjust(
                schedule_id=schedule.id,
                target_date=target_date,
                target_time_slot="afternoon",
            )

        assert result["success"] is False
        assert "历史" in result["message"]
        assert result["schedule"] is None

    async def test_drag_adjust_not_found(self, db_session):
        """排班不存在时返回失败"""
        service = ScheduleService(db_session)

        with patch("app.middleware.tenant_context.get_current_tenant_id", return_value="some-tenant"):
            result = await service.drag_adjust(
                schedule_id="non-existent-id",
                target_date=date.today() + timedelta(days=1),
            )

        assert result["success"] is False
        assert "不存在" in result["message"]

    async def test_drag_adjust_tenant_isolation(
        self, db_session, test_schedule, test_tenant
    ):
        """不同租户无法拖拽排班"""
        service = ScheduleService(db_session)
        target_date = test_schedule.schedule_date + timedelta(days=1)

        with patch("app.middleware.tenant_context.get_current_tenant_id", return_value="other-tenant-id"):
            result = await service.drag_adjust(
                schedule_id=test_schedule.id,
                target_date=target_date,
                target_time_slot="afternoon",
            )

        assert result["success"] is False
        assert "无权" in result["message"]

    async def test_drag_adjust_conflict_returns_conflicts(
        self, db_session, test_schedule, test_doctor, test_store, test_tenant
    ):
        """目标位置有冲突时返回冲突信息"""
        from datetime import datetime
        # 创建一个目标位置已有的排班
        target_date = test_schedule.schedule_date + timedelta(days=1)
        existing = Schedule(
            id=str(uuid4()),
            doctor_id=test_doctor.id,
            store_id=test_store.id,
            tenant_id=test_tenant.id,
            schedule_date=target_date,
            time_slot="morning",
            start_time=time(8, 0),
            end_time=time(12, 0),
            total_slots=10,
            booked_slots=0,
            status=1,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db_session.add(existing)
        await db_session.commit()
        await db_session.refresh(existing)

        service = ScheduleService(db_session)

        with patch("app.middleware.tenant_context.get_current_tenant_id", return_value=test_tenant.id):
            result = await service.drag_adjust(
                schedule_id=test_schedule.id,
                target_date=target_date,
                target_start_time=time(9, 0),
                target_end_time=time(11, 0),
            )

        assert result["success"] is False
        assert result["conflicts"] is not None
        assert result["conflicts"].has_conflict is True
        assert result["conflicts"].blocking is True
        assert len(result["conflicts"].conflicts) > 0

    async def test_drag_adjust_same_position_no_change(
        self, db_session, test_schedule, test_tenant
    ):
        """拖拽到同一位置（日期不变、时间不变）应视为无冲突并成功"""
        service = ScheduleService(db_session)

        with patch("app.middleware.tenant_context.get_current_tenant_id", return_value=test_tenant.id), \
             patch("app.core.redis.RedisCache.tenant_distributed_lock") as mock_lock:
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__ = AsyncMock(return_value="lock_value")
            mock_ctx.__aexit__ = AsyncMock(return_value=None)
            mock_lock.return_value = mock_ctx

            result = await service.drag_adjust(
                schedule_id=test_schedule.id,
                target_date=test_schedule.schedule_date,
                target_start_time=test_schedule.start_time,
                target_end_time=test_schedule.end_time,
            )

        assert result["success"] is True
        assert result["schedule"] is not None

    async def test_drag_adjust_date_only(self, db_session, test_schedule, test_tenant):
        """只修改日期，保留原有时间"""
        service = ScheduleService(db_session)
        target_date = test_schedule.schedule_date + timedelta(days=2)

        with patch("app.middleware.tenant_context.get_current_tenant_id", return_value=test_tenant.id), \
             patch("app.core.redis.RedisCache.tenant_distributed_lock") as mock_lock:
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__ = AsyncMock(return_value="lock_value")
            mock_ctx.__aexit__ = AsyncMock(return_value=None)
            mock_lock.return_value = mock_ctx

            result = await service.drag_adjust(
                schedule_id=test_schedule.id,
                target_date=target_date,
            )

        assert result["success"] is True
        assert result["schedule"].schedule_date == target_date
        # 时间不变
        assert result["schedule"].start_time == test_schedule.start_time
        assert result["schedule"].end_time == test_schedule.end_time

    async def test_drag_adjust_time_slot_only(self, db_session, test_schedule, test_tenant):
        """只修改时段，保留原有日期"""
        service = ScheduleService(db_session)

        with patch("app.middleware.tenant_context.get_current_tenant_id", return_value=test_tenant.id), \
             patch("app.core.redis.RedisCache.tenant_distributed_lock") as mock_lock:
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__ = AsyncMock(return_value="lock_value")
            mock_ctx.__aexit__ = AsyncMock(return_value=None)
            mock_lock.return_value = mock_ctx

            result = await service.drag_adjust(
                schedule_id=test_schedule.id,
                target_date=test_schedule.schedule_date,
                target_time_slot="afternoon",
            )

        assert result["success"] is True
        assert result["schedule"].time_slot == "afternoon"

    async def test_drag_adjust_updates_audit_fields(self, db_session, test_schedule, test_tenant):
        """拖拽成功时更新审计字段"""
        service = ScheduleService(db_session)
        target_date = test_schedule.schedule_date + timedelta(days=1)
        operator_id = str(uuid4())

        with patch("app.middleware.tenant_context.get_current_tenant_id", return_value=test_tenant.id), \
             patch("app.core.redis.RedisCache.tenant_distributed_lock") as mock_lock:
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__ = AsyncMock(return_value="lock_value")
            mock_ctx.__aexit__ = AsyncMock(return_value=None)
            mock_lock.return_value = mock_ctx

            result = await service.drag_adjust(
                schedule_id=test_schedule.id,
                target_date=target_date,
                target_time_slot="afternoon",
                operator_id=operator_id,
            )

        assert result["success"] is True
        schedule = result["schedule"]
        assert schedule.updated_by == operator_id
