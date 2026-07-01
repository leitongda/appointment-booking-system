"""
预约创建服务单元测试

测试 AppointmentBookingService 的核心方法：
1. cancel - 预约取消逻辑
2. 边界情况和错误处理
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4
from decimal import Decimal
import pytz

from app.middleware.exception import BusinessError
from app.models.appointment import Appointment
from app.schemas.appointment import AppointmentCreate
from app.modules.appointments.service_booking import AppointmentBookingService
from app.modules.appointments.common import APPOINTMENT_STATUS


class TestCancelPendingPayment:
    """测试取消待支付预约"""

    @pytest.mark.asyncio
    async def test_cancel_pending_payment_success(
        self,
        db_session,
        test_schedule,
        test_patient,
        test_user,
        test_tenant,
    ):
        """测试取消待支付预约成功"""
        # 创建待支付预约
        appointment = Appointment(
            id=str(uuid4()),
            appointment_no=f"YY{datetime.now().strftime('%Y%m%d%H%M%S')}{str(uuid4())[:4].upper()}",
            user_id=test_user.id,
            patient_id=test_patient.id,
            doctor_id=test_schedule.doctor_id,
            schedule_id=test_schedule.id,
            tenant_id=test_tenant.id,
            queue_number=1,
            status=0,  # 待支付
            patient_name=test_patient.name,
            patient_phone=test_patient.phone,
            doctor_name="测试医生",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db_session.add(appointment)
        test_schedule.booked_slots = 1
        await db_session.commit()

        service = AppointmentBookingService(db_session)

        # Mock 分布式锁
        with patch('app.core.redis.RedisCache.tenant_distributed_lock') as mock_lock, \
             patch('app.modules.appointments.service_booking.MessageService') as mock_msg_service_cls:

            mock_lock_context = AsyncMock()
            mock_lock_context.__aenter__ = AsyncMock(return_value="lock_value")
            mock_lock_context.__aexit__ = AsyncMock(return_value=None)
            mock_lock.return_value = mock_lock_context

            mock_msg_service = MagicMock()
            mock_msg_service_cls.return_value = mock_msg_service
            mock_msg_service.send_appointment_notification = AsyncMock()

            result = await service.cancel(
                appointment_id=appointment.id,
                user_id=test_user.id,
                reason="不需要了",
            )

        assert result is not None
        assert result.status == APPOINTMENT_STATUS['CANCELLED']

        # 验证排班已预约数减少
        await db_session.refresh(test_schedule)
        assert test_schedule.booked_slots == 0


class TestCancelPermission:
    """测试取消权限"""

    @pytest.mark.asyncio
    async def test_cancel_wrong_user(
        self,
        db_session,
        test_appointment: Appointment,
        test_user,
    ):
        """测试非本人取消预约失败"""
        service = AppointmentBookingService(db_session)

        with pytest.raises(BusinessError, match="无权操作此预约"):
            await service.cancel(
                appointment_id=test_appointment.id,
                user_id="other_user_id",
                is_admin=False,
            )

    @pytest.mark.asyncio
    async def test_cancel_by_admin(
        self,
        db_session,
        test_appointment: Appointment,
    ):
        """测试管理员可以取消任何预约"""
        service = AppointmentBookingService(db_session)

        # Mock 分布式锁和消息服务
        with patch('app.core.redis.RedisCache.tenant_distributed_lock') as mock_lock, \
             patch('app.modules.appointments.service_booking.MessageService') as mock_msg_service_cls:

            mock_lock_context = AsyncMock()
            mock_lock_context.__aenter__ = AsyncMock(return_value="lock_value")
            mock_lock_context.__aexit__ = AsyncMock(return_value=None)
            mock_lock.return_value = mock_lock_context

            mock_msg_service = MagicMock()
            mock_msg_service_cls.return_value = mock_msg_service
            mock_msg_service.send_appointment_notification = AsyncMock()

            result = await service.cancel(
                appointment_id=test_appointment.id,
                user_id="admin_user_id",
                is_admin=True,
            )

        assert result is not None
        assert result.status == APPOINTMENT_STATUS['CANCELLED']


class TestCancelTimeWindow:
    """测试取消时间窗"""

    @pytest.mark.asyncio
    async def test_cancel_before_time_window(
        self,
        db_session,
        test_appointment: Appointment,
        test_user,
    ):
        """测试未到取消时间窗"""
        service = AppointmentBookingService(db_session)

        # 设置取消时间窗在未来
        local_tz = pytz.timezone('Asia/Shanghai')
        now = datetime.now(local_tz)

        test_appointment.cancel_open_at = now + timedelta(hours=1)
        test_appointment.cancel_close_at = now + timedelta(hours=2)
        await db_session.commit()

        with pytest.raises(BusinessError, match="未到取消时间窗口"):
            await service.cancel(
                appointment_id=test_appointment.id,
                user_id=test_user.id,
                is_admin=False,
            )

    @pytest.mark.asyncio
    async def test_cancel_after_time_window(
        self,
        db_session,
        test_appointment: Appointment,
        test_user,
    ):
        """测试已过取消时间窗"""
        service = AppointmentBookingService(db_session)

        # 设置取消时间窗已过期
        local_tz = pytz.timezone('Asia/Shanghai')
        now = datetime.now(local_tz)

        test_appointment.cancel_open_at = now - timedelta(hours=2)
        test_appointment.cancel_close_at = now - timedelta(hours=1)
        await db_session.commit()

        with pytest.raises(BusinessError, match="已过取消时间窗口"):
            await service.cancel(
                appointment_id=test_appointment.id,
                user_id=test_user.id,
                is_admin=False,
            )


class TestTenantConsistency:
    """测试租户一致性校验"""

    @pytest.mark.asyncio
    async def test_create_schedule_tenant_mismatch(
        self,
        db_session,
        test_schedule,
        test_patient,
        test_user,
    ):
        """测试排班租户不匹配时创建失败"""
        service = AppointmentBookingService(db_session)

        appointment_data = AppointmentCreate(
            schedule_id=test_schedule.id,
            patient_id=test_patient.id,
        )

        # Mock 返回不同的租户ID
        with patch('app.middleware.tenant_context.get_current_tenant_id', return_value=str(uuid4())), \
             patch('app.common.quota.check_quota', new_callable=AsyncMock):

            with pytest.raises(BusinessError, match="排班不属于当前租户"):
                await service.create(
                    user_id=test_user.id,
                    data=appointment_data,
                )

    @pytest.mark.asyncio
    async def test_create_patient_tenant_mismatch(
        self,
        db_session,
        test_schedule,
        test_user,
        test_tenant,
    ):
        """测试就诊人租户不匹配时创建失败"""
        # 创建属于其他租户的就诊人
        from app.models.user import Patient
        other_patient = Patient(
            id=str(uuid4()),
            user_id=test_user.id,
            name="其他租户就诊人",
            phone="13800138999",
            is_default=False,
            tenant_id=str(uuid4()),  # 不同租户
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db_session.add(other_patient)
        await db_session.commit()

        service = AppointmentBookingService(db_session)

        appointment_data = AppointmentCreate(
            schedule_id=test_schedule.id,
            patient_id=other_patient.id,
        )

        with patch('app.middleware.tenant_context.get_current_tenant_id', return_value=test_tenant.id), \
             patch('app.common.quota.check_quota', new_callable=AsyncMock), \
             patch('app.modules.appointments.service_booking.RuleEngineService') as mock_rule_engine_cls:

            mock_rule_engine = MagicMock()
            mock_rule_engine_cls.return_value = mock_rule_engine
            mock_rule_engine.check_action_window = AsyncMock(
                return_value={
                    'allowed': True,
                    'open_at': datetime.now() - timedelta(days=1),
                    'close_at': datetime.now() + timedelta(days=1),
                }
            )
            mock_rule_engine.get_applicable_rule_set = AsyncMock(return_value=None)

            with pytest.raises(BusinessError, match="就诊人不属于当前租户"):
                await service.create(
                    user_id=test_user.id,
                    data=appointment_data,
                )
