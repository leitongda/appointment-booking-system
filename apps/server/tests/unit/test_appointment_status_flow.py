"""
预约状态流转单元测试

测试用例覆盖：
1. 完整状态流转：已预约 -> 已签到 -> 候诊中 -> 就诊中 -> 已完成
2. 非法状态流转验证：已取消状态无法再签到

状态定义（与前端 packages/shared/src/constants/appointment.ts 保持一致）：
- PENDING: 0      待支付
- CONFIRMED: 1    已预约
- SIGNED: 2       已签到
- WAITING: 3      候诊中
- SEEING: 4       就诊中
- COMPLETED: 5    已完成
- CANCELLED: 6    已取消
- EXPIRED: 7      已过期
- CLOSED: 8       已关闭
"""
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, patch, MagicMock
from contextlib import asynccontextmanager

from app.models.appointment import Appointment
from app.modules.appointments.service import AppointmentService, APPOINTMENT_STATUS


@asynccontextmanager
async def mock_distributed_lock(*args, **kwargs):
    """Mock 分布式锁的异步上下文管理器"""
    yield None


class TestAppointmentStatusConstants:
    """验证前后端状态常量一致性"""

    def test_status_constants_match_frontend(self):
        """
        验证后端状态常量与前端定义一致
        参考: packages/shared/src/constants/appointment.ts
        """
        # 待支付
        assert APPOINTMENT_STATUS['PENDING'] == 0
        # 已预约
        assert APPOINTMENT_STATUS['CONFIRMED'] == 1
        # 已签到
        assert APPOINTMENT_STATUS['SIGNED'] == 2
        # 候诊中
        assert APPOINTMENT_STATUS['WAITING'] == 3
        # 就诊中
        assert APPOINTMENT_STATUS['SEEING'] == 4
        # 已完成
        assert APPOINTMENT_STATUS['COMPLETED'] == 5
        # 已取消
        assert APPOINTMENT_STATUS['CANCELLED'] == 6
        # 已过期
        assert APPOINTMENT_STATUS['EXPIRED'] == 7
        # 已关闭
        assert APPOINTMENT_STATUS['CLOSED'] == 8


class TestFullStatusFlow:
    """完整状态流转测试"""

    @pytest.mark.asyncio
    async def test_full_status_flow(
        self,
        db_session,
        test_appointment: Appointment,
        appointment_service: AppointmentService
    ):
        """
        测试完整状态流转: 已预约(1) -> 已签到(2) -> 就诊中(4) -> 已完成(5)

        注意: 当前实现中 call_patient 直接从 SIGNED(2) 跳到 SEEING(4)，
        WAITING(3) 状态在当前服务中未使用。
        """
        appointment = test_appointment

        # 初始状态: 已预约 (CONFIRMED = 1)
        assert appointment.status == APPOINTMENT_STATUS['CONFIRMED'], \
            f"初始状态应为已预约(1)，实际为 {appointment.status}"
        assert appointment.sign_in_time is None, "初始签到时间应为空"
        assert appointment.call_time is None, "初始叫号时间应为空"
        assert appointment.complete_time is None, "初始完成时间应为空"

        # Mock Redis 分布式锁，避免实际 Redis 连接
        with patch.object(
            appointment_service,
            '_create_checkin_log',
            new_callable=AsyncMock
        ):
            # 步骤1: 签到 - CONFIRMED(1) -> SIGNED(2)
            # 需要绕过签到时间窗口检查
            appointment.checkin_open_at = datetime.now().replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            appointment.checkin_close_at = datetime.now().replace(
                hour=23, minute=59, second=59, microsecond=0
            )
            await db_session.commit()
            await db_session.refresh(appointment)

            signed_appointment = await appointment_service.sign_in(
                appointment_id=appointment.id,
                is_admin=True,  # 使用管理员权限绕过用户校验
                operator_id='test_operator',
                operator_type='ADMIN'
            )

            assert signed_appointment is not None, "签到应成功"
            assert signed_appointment.status == APPOINTMENT_STATUS['SIGNED'], \
                f"签到后状态应为已签到(2)，实际为 {signed_appointment.status}"
            assert signed_appointment.sign_in_time is not None, "签到后应有签到时间"

            # 步骤2: 叫号 - SIGNED(2) -> SEEING(4)
            # 注意: call_patient 方法当前实现直接将状态从 SIGNED 改为 SEEING
            calling_appointment = await appointment_service.call_patient(
                appointment_id=appointment.id
            )

            assert calling_appointment is not None, "叫号应成功"
            assert calling_appointment.status == APPOINTMENT_STATUS['SEEING'], \
                f"叫号后状态应为就诊中(4)，实际为 {calling_appointment.status}"
            assert calling_appointment.call_time is not None, "叫号后应有叫号时间"

            # 步骤3: 完成就诊 - SEEING(4) -> COMPLETED(5)
            completed_appointment = await appointment_service.complete(
                appointment_id=appointment.id
            )

            assert completed_appointment is not None, "完成就诊应成功"
            assert completed_appointment.status == APPOINTMENT_STATUS['COMPLETED'], \
                f"完成后状态应为已完成(5)，实际为 {completed_appointment.status}"
            assert completed_appointment.complete_time is not None, "完成后应有完成时间"

    @pytest.mark.asyncio
    async def test_status_flow_with_sign_in_time_window(
        self,
        db_session,
        test_appointment: Appointment,
        appointment_service: AppointmentService
    ):
        """
        测试签到时间窗口验证
        """
        appointment = test_appointment

        # 设置签到时间窗口（当前时间在窗口外）
        appointment.checkin_open_at = datetime.now().replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        appointment.checkin_close_at = datetime.now().replace(
            hour=0, minute=1, second=0, microsecond=0
        )
        await db_session.commit()
        await db_session.refresh(appointment)

        with patch.object(
            appointment_service,
            '_create_checkin_log',
            new_callable=AsyncMock
        ):
            # 尝试签到（应该失败，因为已过签到时间窗口）
            with pytest.raises(ValueError) as exc_info:
                await appointment_service.sign_in(
                    appointment_id=appointment.id,
                    is_admin=True
                )

            assert "已过签到时间" in str(exc_info.value), \
                "应提示已过签到时间"


class TestInvalidStatusTransition:
    """非法状态流转测试"""

    @pytest.mark.asyncio
    async def test_cancelled_appointment_cannot_sign_in(
        self,
        db_session,
        test_appointment: Appointment,
        appointment_service: AppointmentService
    ):
        """
        测试已取消(6)状态的预约无法签到

        业务规则: 已取消的预约不能再进行任何状态变更操作
        """
        appointment = test_appointment

        # 将预约状态设置为已取消
        appointment.status = APPOINTMENT_STATUS['CANCELLED']
        appointment.cancel_time = datetime.now()
        appointment.cancel_reason = "测试取消"
        await db_session.commit()
        await db_session.refresh(appointment)

        # 验证当前状态为已取消
        assert appointment.status == APPOINTMENT_STATUS['CANCELLED'], \
            f"状态应为已取消(6)，实际为 {appointment.status}"

        # 尝试签到（应该抛出 ValueError）
        with pytest.raises(ValueError) as exc_info:
            await appointment_service.sign_in(
                appointment_id=appointment.id,
                is_admin=True
            )

        # 验证错误消息
        assert "当前状态不可签到" in str(exc_info.value), \
            f"应提示'当前状态不可签到'，实际错误: {exc_info.value}"

    @pytest.mark.asyncio
    async def test_completed_appointment_cannot_sign_in(
        self,
        db_session,
        test_appointment: Appointment,
        appointment_service: AppointmentService
    ):
        """
        测试已完成(5)状态的预约无法签到
        """
        appointment = test_appointment

        # 将预约状态设置为已完成
        appointment.status = APPOINTMENT_STATUS['COMPLETED']
        appointment.complete_time = datetime.now()
        await db_session.commit()
        await db_session.refresh(appointment)

        # 尝试签到（应该抛出 ValueError）
        with pytest.raises(ValueError) as exc_info:
            await appointment_service.sign_in(
                appointment_id=appointment.id,
                is_admin=True
            )

        assert "当前状态不可签到" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_expired_appointment_cannot_sign_in(
        self,
        db_session,
        test_appointment: Appointment,
        appointment_service: AppointmentService
    ):
        """
        测试已过期(7)状态的预约无法签到
        """
        appointment = test_appointment

        # 将预约状态设置为已过期
        appointment.status = APPOINTMENT_STATUS['EXPIRED']
        await db_session.commit()
        await db_session.refresh(appointment)

        # 尝试签到（应该抛出 ValueError）
        with pytest.raises(ValueError) as exc_info:
            await appointment_service.sign_in(
                appointment_id=appointment.id,
                is_admin=True
            )

        assert "当前状态不可签到" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_unsigned_appointment_cannot_call(
        self,
        db_session,
        test_appointment: Appointment,
        appointment_service: AppointmentService
    ):
        """
        测试未签到(状态为已预约)的预约无法叫号

        业务规则: 叫号前必须先签到
        """
        appointment = test_appointment

        # 确保状态为已预约
        assert appointment.status == APPOINTMENT_STATUS['CONFIRMED']

        # 尝试叫号（应该抛出 ValueError）
        with pytest.raises(ValueError) as exc_info:
            await appointment_service.call_patient(
                appointment_id=appointment.id
            )

        assert "患者未签到" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_cancelled_appointment_cannot_be_cancelled_again(
        self,
        db_session,
        test_appointment: Appointment,
        appointment_service: AppointmentService
    ):
        """
        测试已取消的预约不能再次取消
        """
        appointment = test_appointment

        # 将预约状态设置为已取消
        appointment.status = APPOINTMENT_STATUS['CANCELLED']
        appointment.cancel_time = datetime.now()
        await db_session.commit()
        await db_session.refresh(appointment)

        # 尝试再次取消（应该抛出 ValueError）
        with pytest.raises(ValueError) as exc_info:
            await appointment_service.cancel(
                appointment_id=appointment.id,
                user_id=appointment.user_id,
                is_admin=True
            )

        assert "当前状态不可取消" in str(exc_info.value)


class TestStatusTransitionEdgeCases:
    """状态流转边界情况测试"""

    @pytest.mark.asyncio
    async def test_signed_appointment_can_be_cancelled(
        self,
        db_session,
        test_appointment: Appointment,
        appointment_service: AppointmentService
    ):
        """
        测试已签到(2)状态的预约可以被取消

        业务规则: 已签到状态仍然可以取消预约
        """
        appointment = test_appointment

        # 先签到
        appointment.status = APPOINTMENT_STATUS['SIGNED']
        appointment.sign_in_time = datetime.now()
        appointment.checkin_open_at = datetime.now().replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        appointment.checkin_close_at = datetime.now().replace(
            hour=23, minute=59, second=59, microsecond=0
        )
        await db_session.commit()
        await db_session.refresh(appointment)

        # 取消预约（需要 mock Redis 分布式锁）
        with patch('app.modules.waitlist.service.WaitlistService') as mock_waitlist_cls, \
             patch('app.modules.messages.service_messages.MessageService') as mock_msg_cls, \
             patch('app.core.redis.RedisCache.tenant_distributed_lock', return_value=mock_distributed_lock()):

            mock_waitlist = MagicMock()
            mock_waitlist_cls.return_value = mock_waitlist
            mock_waitlist.auto_promote = AsyncMock()

            mock_msg = MagicMock()
            mock_msg_cls.return_value = mock_msg
            mock_msg.send_appointment_notification = AsyncMock()

            cancelled_appointment = await appointment_service.cancel(
                appointment_id=appointment.id,
                user_id=appointment.user_id,
                reason="测试取消已签到预约",
                is_admin=True
            )

        assert cancelled_appointment is not None
        assert cancelled_appointment.status == APPOINTMENT_STATUS['CANCELLED']
        assert cancelled_appointment.cancel_time is not None
        assert cancelled_appointment.cancel_reason == "测试取消已签到预约"

    @pytest.mark.asyncio
    async def test_pass_number_changes_status_to_expired(
        self,
        db_session,
        test_appointment: Appointment,
        appointment_service: AppointmentService
    ):
        """
        测试过号操作将状态改为已过期(7)

        业务规则: 患者未到被跳过时，状态变为 EXPIRED
        """
        appointment = test_appointment

        # 设置为已签到状态
        appointment.status = APPOINTMENT_STATUS['SIGNED']
        appointment.sign_in_time = datetime.now()
        await db_session.commit()
        await db_session.refresh(appointment)

        # 执行过号
        passed_appointment = await appointment_service.pass_number(
            appointment_id=appointment.id
        )

        assert passed_appointment is not None
        assert passed_appointment.status == APPOINTMENT_STATUS['EXPIRED'], \
            f"过号后状态应为已过期(7)，实际为 {passed_appointment.status}"

    @pytest.mark.asyncio
    async def test_recall_changes_status_to_seeing(
        self,
        db_session,
        test_appointment: Appointment,
        appointment_service: AppointmentService
    ):
        """
        测试重新叫号将状态从已过期(7)改为就诊中(4)

        业务规则: 过号后可以重新叫号
        """
        appointment = test_appointment

        # 设置为已过期状态（过号）
        appointment.status = APPOINTMENT_STATUS['EXPIRED']
        await db_session.commit()
        await db_session.refresh(appointment)

        # 重新叫号
        recalled_appointment = await appointment_service.recall(
            appointment_id=appointment.id
        )

        assert recalled_appointment is not None
        assert recalled_appointment.status == APPOINTMENT_STATUS['SEEING'], \
            f"重新叫号后状态应为就诊中(4)，实际为 {recalled_appointment.status}"
        assert recalled_appointment.call_time is not None
