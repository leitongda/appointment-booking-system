"""
预约取消功能单元测试

测试 AppointmentService.cancel 方法的各种场景：
1. 正常取消预约
2. 错误状态不可取消
3. 并发取消预约（验证分布式锁缺失问题）
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch, MagicMock
import pytz
from contextlib import asynccontextmanager

from app.middleware.exception import BusinessError
from app.modules.appointments.service import AppointmentService, APPOINTMENT_STATUS
from app.models.appointment import Appointment
from app.models.schedule import Schedule


@asynccontextmanager
async def mock_distributed_lock(*args, **kwargs):
    """Mock 分布式锁的异步上下文管理器"""
    yield None


class TestCancelAppointmentSuccess:
    """测试正常取消预约场景"""

    @pytest.mark.asyncio
    async def test_cancel_appointment_success(
        self,
        db_session,
        test_appointment: Appointment,
        test_user,
        appointment_service: AppointmentService
    ):
        """测试正常取消预约

        验证点：
        1. 状态变为已取消(6)
        2. 排班号源+1
        3. 取消时间被记录
        """
        # 记录取消前的已预约数
        schedule_result = await db_session.execute(
            Schedule.__table__.select().where(Schedule.id == test_appointment.schedule_id)
        )
        schedule_row = schedule_result.first()
        booked_slots_before = schedule_row.booked_slots

        appointment_id = test_appointment.id
        user_id = test_user.id

        # 设置取消时间窗（允许取消）
        local_tz = pytz.timezone('Asia/Shanghai')
        now = datetime.now(local_tz)
        test_appointment.cancel_open_at = now - timedelta(hours=1)
        test_appointment.cancel_close_at = now + timedelta(hours=1)
        await db_session.commit()

        # Mock 候补递补事件分发与消息服务（候补递补已改为事件驱动，不再同步调用 WaitlistService）
        # Mock Redis 分布式锁（测试环境无 Redis）
        with patch('app.modules.appointments.service_booking.dispatch_appointment_event') as mock_dispatch, \
             patch('app.modules.messages.service_messages.MessageService') as mock_msg_cls, \
             patch('app.core.redis.RedisCache.tenant_distributed_lock', return_value=mock_distributed_lock()):

            mock_msg = MagicMock()
            mock_msg_cls.return_value = mock_msg
            mock_msg.send_appointment_notification = AsyncMock()

            # 执行取消
            result = await appointment_service.cancel(
                appointment_id=appointment_id,
                user_id=user_id,
                reason="测试取消",
                is_admin=False
            )

        # 验证结果
        assert result is not None, "取消应返回预约对象"
        assert result.status == APPOINTMENT_STATUS['CANCELLED'], \
            f"取消后状态应为已取消(6)，实际为 {result.status}"
        assert result.cancel_time is not None, "取消时间应被记录"
        assert result.cancel_reason == "测试取消", "取消原因应保存"

        # 验证：已确认预约取消后投递 APPOINTMENT_CANCELLED 事件（异步触发候补递补）
        mock_dispatch.assert_called_once()
        _, kwargs = mock_dispatch.call_args
        assert kwargs["event_type"] == "appointment_cancelled"
        assert kwargs["payload"]["schedule_id"] == test_appointment.schedule_id
        assert kwargs["payload"]["appointment_id"] == appointment_id
        assert kwargs["payload"]["reason"] == "APPOINTMENT_CANCELLED"

        # 验证排班号源+1
        await db_session.refresh(test_appointment)
        schedule_result = await db_session.execute(
            Schedule.__table__.select().where(Schedule.id == test_appointment.schedule_id)
        )
        schedule_row = schedule_result.first()
        assert schedule_row.booked_slots == booked_slots_before - 1, \
            f"预期已预约数 {booked_slots_before - 1}，实际为 {schedule_row.booked_slots}"

    @pytest.mark.asyncio
    async def test_cancel_appointment_by_admin(
        self,
        db_session,
        test_appointment: Appointment,
        appointment_service: AppointmentService
    ):
        """测试管理员取消预约（无需时间窗检查）"""
        appointment_id = test_appointment.id

        # Mock 候补递补事件分发与消息服务（候补递补已改为事件驱动）
        # Mock Redis 分布式锁（测试环境无 Redis）
        with patch('app.modules.appointments.service_booking.dispatch_appointment_event') as mock_dispatch, \
             patch('app.modules.messages.service_messages.MessageService') as mock_msg_cls, \
             patch('app.core.redis.RedisCache.tenant_distributed_lock', return_value=mock_distributed_lock()):

            mock_msg = MagicMock()
            mock_msg_cls.return_value = mock_msg
            mock_msg.send_appointment_notification = AsyncMock()

            # 管理员取消（跳过时间窗检查）
            result = await appointment_service.cancel(
                appointment_id=appointment_id,
                user_id="admin_user_id",
                reason="管理员取消",
                is_admin=True
            )

        # 验证取消成功
        assert result is not None
        assert result.status == APPOINTMENT_STATUS['CANCELLED']
        assert result.cancel_reason == "管理员取消"

        # 验证：管理员取消已确认预约同样投递事件
        mock_dispatch.assert_called_once()

    @pytest.mark.asyncio
    async def test_cancel_pending_appointment_success(
        self,
        db_session,
        test_appointment: Appointment,
        test_user,
        appointment_service: AppointmentService
    ):
        """测试待支付预约可以正常取消并释放号源"""
        test_appointment.status = 0
        await db_session.commit()

        schedule_result = await db_session.execute(
            Schedule.__table__.select().where(Schedule.id == test_appointment.schedule_id)
        )
        schedule_row = schedule_result.first()
        booked_slots_before = schedule_row.booked_slots

        mock_lock = AsyncMock()
        mock_lock.__aenter__ = AsyncMock(return_value=None)
        mock_lock.__aexit__ = AsyncMock(return_value=None)

        with patch('app.modules.appointments.service_booking.dispatch_appointment_event') as mock_dispatch, \
             patch('app.modules.messages.service_messages.MessageService') as mock_msg_cls, \
             patch('app.core.redis.RedisCache.tenant_distributed_lock', return_value=mock_lock) as mock_dist_lock:
            mock_msg = MagicMock()
            mock_msg_cls.return_value = mock_msg
            mock_msg.send_appointment_notification = AsyncMock()

            result = await appointment_service.cancel(
                appointment_id=test_appointment.id,
                user_id=test_user.id,
                reason="待支付取消",
                is_admin=False
            )

        assert result is not None
        assert result.status == APPOINTMENT_STATUS['CANCELLED']
        assert result.cancel_reason == "待支付取消"
        mock_dist_lock.assert_called_once()
        assert mock_dist_lock.call_args.args[0] == f"appointment:cancel:{test_appointment.id}"

        # 验证：待支付取消不触发候补递补事件（待支付早 return 分支不发事件）
        mock_dispatch.assert_not_called()

        schedule_result = await db_session.execute(
            Schedule.__table__.select().where(Schedule.id == test_appointment.schedule_id)
        )
        schedule_row = schedule_result.first()
        assert schedule_row.booked_slots == booked_slots_before - 1


class TestCancelAppointmentWrongStatus:
    """测试错误状态不可取消场景"""

    @pytest.mark.asyncio
    async def test_cancel_appointment_completed_status(
        self,
        db_session,
        test_appointment: Appointment,
        test_user,
        appointment_service: AppointmentService
    ):
        """测试已完成(5)状态的预约不可取消"""
        # 设置状态为已完成
        test_appointment.status = APPOINTMENT_STATUS['COMPLETED']
        await db_session.commit()

        with pytest.raises(BusinessError) as exc_info:
            await appointment_service.cancel(
                appointment_id=test_appointment.id,
                user_id=test_user.id,
                is_admin=False
            )

        assert "当前状态不可取消" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_cancel_appointment_already_cancelled(
        self,
        db_session,
        test_appointment: Appointment,
        test_user,
        appointment_service: AppointmentService
    ):
        """测试已取消(6)状态的预约不可再次取消"""
        # 设置状态为已取消
        test_appointment.status = APPOINTMENT_STATUS['CANCELLED']
        await db_session.commit()

        with pytest.raises(BusinessError) as exc_info:
            await appointment_service.cancel(
                appointment_id=test_appointment.id,
                user_id=test_user.id,
                is_admin=False
            )

        assert "当前状态不可取消" in str(exc_info.value)


class TestCancelAppointmentTimeWindow:
    """测试取消预约时间窗场景"""

    @pytest.mark.asyncio
    async def test_cancel_appointment_time_window_early(
        self,
        db_session,
        test_appointment: Appointment,
        test_user,
        appointment_service: AppointmentService
    ):
        """测试未到取消时间窗不可取消"""
        local_tz = pytz.timezone('Asia/Shanghai')
        now = datetime.now(local_tz)

        # 设置取消时间窗：1小时后开始
        test_appointment.cancel_open_at = now + timedelta(hours=1)
        test_appointment.cancel_close_at = now + timedelta(hours=24)
        await db_session.commit()

        with pytest.raises(BusinessError) as exc_info:
            await appointment_service.cancel(
                appointment_id=test_appointment.id,
                user_id=test_user.id,
                is_admin=False
            )

        assert "未到取消时间" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_cancel_appointment_time_window_late(
        self,
        db_session,
        test_appointment: Appointment,
        test_user,
        appointment_service: AppointmentService
    ):
        """测试已过取消时间窗不可取消"""
        local_tz = pytz.timezone('Asia/Shanghai')
        now = datetime.now(local_tz)

        # 设置取消时间窗：已过期
        test_appointment.cancel_open_at = now - timedelta(hours=24)
        test_appointment.cancel_close_at = now - timedelta(hours=1)
        await db_session.commit()

        with pytest.raises(BusinessError) as exc_info:
            await appointment_service.cancel(
                appointment_id=test_appointment.id,
                user_id=test_user.id,
                is_admin=False
            )

        assert "已过取消时间" in str(exc_info.value)


class TestCancelAppointmentPermission:
    """测试取消预约权限场景"""

    @pytest.mark.asyncio
    async def test_cancel_appointment_wrong_user(
        self,
        db_session,
        test_appointment: Appointment,
        appointment_service: AppointmentService
    ):
        """测试非预约用户不可取消"""
        wrong_user_id = "wrong_user_id_12345"

        with pytest.raises(BusinessError) as exc_info:
            await appointment_service.cancel(
                appointment_id=test_appointment.id,
                user_id=wrong_user_id,
                is_admin=False
            )

        assert "无权操作" in str(exc_info.value)


class TestCancelAppointmentConcurrent:
    """测试并发取消预约场景

    P0-1 修复：已添加分布式锁保护
    位置：apps/server/app/services/appointment_service.py:522-526
    """

    @pytest.mark.asyncio
    async def test_cancel_appointment_uses_distributed_lock(
        self,
        db_session,
        test_appointment: Appointment,
        test_user
    ):
        """测试取消预约使用分布式锁保护

        验证点：
        1. 取消操作使用分布式锁
        2. 锁名为 schedule_id 级别
        3. 取消成功
        """
        service = AppointmentService(db_session)

        # 设置取消时间窗
        local_tz = pytz.timezone('Asia/Shanghai')
        now = datetime.now(local_tz)
        test_appointment.cancel_open_at = now - timedelta(hours=1)
        test_appointment.cancel_close_at = now + timedelta(hours=1)
        await db_session.commit()

        # Mock 分布式锁，验证锁被调用
        mock_lock = AsyncMock()
        mock_lock.__aenter__ = AsyncMock(return_value=None)
        mock_lock.__aexit__ = AsyncMock(return_value=None)

        with patch('app.modules.appointments.service_booking.dispatch_appointment_event') as mock_dispatch, \
             patch('app.modules.messages.service_messages.MessageService') as mock_msg_cls, \
             patch('app.core.redis.RedisCache.tenant_distributed_lock', return_value=mock_lock) as mock_dist_lock:

            mock_msg = MagicMock()
            mock_msg_cls.return_value = mock_msg
            mock_msg.send_appointment_notification = AsyncMock()

            result = await service.cancel(
                appointment_id=test_appointment.id,
                user_id=test_user.id,
                is_admin=False
            )

        # 验证取消成功
        assert result.status == APPOINTMENT_STATUS['CANCELLED']

        # 验证分布式锁被调用
        mock_dist_lock.assert_called_once()
        call_args = mock_dist_lock.call_args
        assert 'appointment:cancel:' in call_args[0][0], "锁名应包含 appointment:cancel:"

        # 验证：已确认预约取消后投递候补递补事件（与分布式锁共同验证取消主路径）
        mock_dispatch.assert_called_once()


class TestCancelAppointmentNonExistent:
    """测试预约不存在场景"""

    @pytest.mark.asyncio
    async def test_cancel_appointment_non_existent(
        self,
        appointment_service: AppointmentService
    ):
        """测试不存在的预约不可取消"""
        non_existent_id = "non_existent_appointment_id_12345"

        result = await appointment_service.cancel(
            appointment_id=non_existent_id,
            user_id="any_user_id",
            is_admin=False
        )

        # 验证返回 None
        assert result is None, "不存在的预约应返回 None"
