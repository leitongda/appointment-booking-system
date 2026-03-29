"""
AppointmentFlowService 单元测试

测试预约流程服务的核心方法：
1. call_patient - 叫号（状态流转 SIGNED -> SEEING)
2. complete - 完成就诊
状态流转 -> COMPLETED)
3. cancel_sign_in - 取消签到
4. recall - 重新叫号（过号后）
5. mark_no_show - 标记爽约
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4
import pytz

from app.models.appointment import Appointment
from app.models.schedule import Schedule
from app.modules.appointments.service import AppointmentService, APPOINTMENT_STATUS


from app.modules.appointments.service_flow import AppointmentFlowService
from contextlib import asynccontextmanager

from app.models.rule_set import AppointmentCheckin


# Mock 分布式锁的异步上下文管理器
@asynccontextmanager
async def mock_distributed_lock(*args, **kwargs):
    yield None


class TestCallPatient:
    """测试叫号功能"""

    @pytest.mark.asyncio
    async def test_call_patient_success(
        self,
        db_session,
        test_appointment: Appointment,
        appointment_service: AppointmentService
    ):
        """正常叫号: SIGNED -> SEEING"""
        # 设置为已签到状态
        test_appointment.status = APPOINTMENT_STATUS["SIGNED"]
        await db_session.commit()

        # Mock email event (同步方法)
        with patch.object(appointment_service, "_dispatch_email_event"):
            result = await appointment_service.call_patient(test_appointment.id)

        assert result is not None
        assert result.status == APPOINTMENT_STATUS["SEEING"]
        assert result.call_time is not None

    @pytest.mark.asyncio
    async def test_call_patient_not_found(
        self,
        db_session,
        appointment_service: AppointmentService
    ):
        """预约不存在"""
        result = await appointment_service.call_patient("non-existent-id")

        assert result is None

    @pytest.mark.asyncio
    async def test_call_patient_not_signed(
        self,
        db_session,
        test_appointment: Appointment,
        appointment_service: AppointmentService
    ):
        """非签到状态不可叫号"""
        # 保持为已预约状态
        test_appointment.status = APPOINTMENT_STATUS["CONFIRMED"]
        await db_session.commit()

        with pytest.raises(ValueError, match="患者未签到"):
            await appointment_service.call_patient(test_appointment.id)

    @pytest.mark.asyncio
    async def test_call_patient_from_waiting(
        self,
        db_session,
        test_appointment: Appointment,
        appointment_service: AppointmentService
    ):
        """从候诊中状态不可叫号（当前实现要求必须是 SIGNED）"""
        test_appointment.status = APPOINTMENT_STATUS["WAITING"]
        await db_session.commit()

        with pytest.raises(ValueError, match="患者未签到"):
            await appointment_service.call_patient(test_appointment.id)


class TestComplete:
    """测试完成就诊功能"""

    @pytest.mark.asyncio
    async def test_complete_success(
        self,
        db_session,
        test_appointment: Appointment,
        appointment_service: AppointmentService
    ):
        """正常完成就诊"""
        # 设置为就诊中状态
        test_appointment.status = APPOINTMENT_STATUS["SEEING"]
        await db_session.commit()

        # 创建 mock 对象
        mock_message_service = MagicMock()
        mock_message_service.send_appointment_notification = AsyncMock()
        mock_compat = MagicMock()
        mock_compat.return_value = mock_message_service

        # Mock message service and email event
        with patch.object(appointment_service, "_dispatch_email_event"), \
             patch.object(appointment_service, "_compat", return_value=mock_compat):
            result = await appointment_service.complete(test_appointment.id)

        assert result is not None
        assert result.status == APPOINTMENT_STATUS["COMPLETED"]
        assert result.complete_time is not None

    @pytest.mark.asyncio
    async def test_complete_not_found(
        self,
        db_session,
        appointment_service: AppointmentService
    ):
        """预约不存在"""
        result = await appointment_service.complete("non-existent-id")

        assert result is None

    @pytest.mark.asyncio
    async def test_complete_from_any_status(
        self,
        db_session,
        test_appointment: Appointment,
        appointment_service: AppointmentService
    ):
        """只有已签到或就诊中状态才能完成"""
        # 设置为已签到状态（前置状态检查要求 SIGNED 或 SEEING）
        test_appointment.status = APPOINTMENT_STATUS["SIGNED"]
        await db_session.commit()

        # 创建 mock 对象
        mock_message_service = MagicMock()
        mock_message_service.send_appointment_notification = AsyncMock()
        mock_compat = MagicMock()
        mock_compat.return_value = mock_message_service

        # Mock message service
        with patch.object(appointment_service, "_dispatch_email_event"), \
             patch.object(appointment_service, "_compat", return_value=mock_compat):
            result = await appointment_service.complete(test_appointment.id)

        assert result.status == APPOINTMENT_STATUS["COMPLETED"]


class TestCancelSignIn:
    """测试取消签到功能"""

    @pytest.mark.asyncio
    async def test_cancel_sign_in_success(
        self,
        db_session,
        test_appointment: Appointment,
        appointment_service: AppointmentService
    ):
        """正常取消签到: SIGNED -> CONFIRMED"""
        # 设置为已签到状态
        test_appointment.status = APPOINTMENT_STATUS["SIGNED"]
        test_appointment.sign_in_time = datetime.now()
        await db_session.commit()

        result = await appointment_service.cancel_sign_in(test_appointment.id)

        assert result is not None
        assert result.status == APPOINTMENT_STATUS["CONFIRMED"]
        assert result.sign_in_time is None

    @pytest.mark.asyncio
    async def test_cancel_sign_in_not_found(
        self,
        db_session,
        appointment_service: AppointmentService
    ):
        """预约不存在"""
        result = await appointment_service.cancel_sign_in("non-existent-id")

        assert result is None

    @pytest.mark.asyncio
    async def test_cancel_sign_in_not_signed(
        self,
        db_session,
        test_appointment: Appointment,
        appointment_service: AppointmentService
    ):
        """非签到状态不可取消签到"""
        # 保持为已预约状态
        test_appointment.status = APPOINTMENT_STATUS["CONFIRMED"]
        await db_session.commit()

        with pytest.raises(ValueError, match="只有已签到状态"):
            await appointment_service.cancel_sign_in(test_appointment.id)


class TestPassNumber:
    """测试过号功能"""

    @pytest.mark.asyncio
    async def test_pass_number_from_signed(
        self,
        db_session,
        test_appointment: Appointment,
        appointment_service: AppointmentService
    ):
        """从已签到状态过号: SIGNED -> EXPIRED"""
        test_appointment.status = APPOINTMENT_STATUS["SIGNED"]
        await db_session.commit()

        result = await appointment_service.pass_number(test_appointment.id)

        assert result is not None
        assert result.status == APPOINTMENT_STATUS["EXPIRED"]

    @pytest.mark.asyncio
    async def test_pass_number_from_seeing(
        self,
        db_session,
        test_appointment: Appointment,
        appointment_service: AppointmentService
    ):
        """从就诊中状态过号: SEEING -> EXPIRED"""
        test_appointment.status = APPOINTMENT_STATUS["SEEING"]
        await db_session.commit()

        result = await appointment_service.pass_number(test_appointment.id)

        assert result is not None
        assert result.status == APPOINTMENT_STATUS["EXPIRED"]

    @pytest.mark.asyncio
    async def test_pass_number_not_found(
        self,
        db_session,
        appointment_service: AppointmentService
    ):
        """预约不存在"""
        result = await appointment_service.pass_number("non-existent-id")

        assert result is None

    @pytest.mark.asyncio
    async def test_pass_number_invalid_status(
        self,
        db_session,
        test_appointment: Appointment,
        appointment_service: AppointmentService
    ):
        """无效状态不可过号"""
        # 设置为已预约状态
        test_appointment.status = APPOINTMENT_STATUS["CONFIRMED"]
        await db_session.commit()

        with pytest.raises(ValueError, match="当前状态不可过号"):
            await appointment_service.pass_number(test_appointment.id)


class TestRecall:
    """测试重新叫号功能"""

    @pytest.mark.asyncio
    async def test_recall_success(
        self,
        db_session,
        test_appointment: Appointment,
        appointment_service: AppointmentService
    ):
        """正常重新叫号: EXPIRED -> SEEING"""
        test_appointment.status = APPOINTMENT_STATUS["EXPIRED"]
        test_appointment.call_time = datetime.now() - timedelta(minutes=10)
        await db_session.commit()

        result = await appointment_service.recall(test_appointment.id)

        assert result is not None
        assert result.status == APPOINTMENT_STATUS["SEEING"]
        assert result.call_time is not None

    @pytest.mark.asyncio
    async def test_recall_not_found(
        self,
        db_session,
        appointment_service: AppointmentService
    ):
        """预约不存在"""
        result = await appointment_service.recall("non-existent-id")

        assert result is None

    @pytest.mark.asyncio
    async def test_recall_invalid_status(
        self,
        db_session,
        test_appointment: Appointment,
        appointment_service: AppointmentService
    ):
        """非过号状态不可重新叫号"""
        test_appointment.status = APPOINTMENT_STATUS["SIGNED"]
        await db_session.commit()

        with pytest.raises(ValueError, match="只有过号状态可以重新叫号"):
            await appointment_service.recall(test_appointment.id)


class TestMarkNoShow:
    """测试标记爽约功能"""

    @pytest.mark.asyncio
    async def test_mark_no_show_from_confirmed(
        self,
        db_session,
        test_appointment: Appointment,
        appointment_service: AppointmentService
    ):
        """从已预约状态标记爽约"""
        test_appointment.status = APPOINTMENT_STATUS["CONFIRMED"]
        await db_session.commit()

        with patch.object(appointment_service, "_dispatch_email_event"):
            result = await appointment_service.mark_no_show(test_appointment.id)

        assert result is not None
        assert result.status == APPOINTMENT_STATUS["NO_SHOW"]

    @pytest.mark.asyncio
    async def test_mark_no_show_from_expired(
        self,
        db_session,
        test_appointment: Appointment,
        appointment_service: AppointmentService
    ):
        """从过号状态标记爽约"""
        test_appointment.status = APPOINTMENT_STATUS["EXPIRED"]
        await db_session.commit()

        with patch.object(appointment_service, "_dispatch_email_event"):
            result = await appointment_service.mark_no_show(test_appointment.id)

        assert result is not None
        assert result.status == APPOINTMENT_STATUS["NO_SHOW"]

    @pytest.mark.asyncio
    async def test_mark_no_show_not_found(
        self,
        db_session,
        appointment_service: AppointmentService
    ):
        """预约不存在"""
        result = await appointment_service.mark_no_show("non-existent-id")

        assert result is None

    @pytest.mark.asyncio
    async def test_mark_no_show_invalid_status(
        self,
        db_session,
        test_appointment: Appointment,
        appointment_service: AppointmentService
    ):
        """无效状态不可标记爽约"""
        test_appointment.status = APPOINTMENT_STATUS["SIGNED"]
        await db_session.commit()

        with pytest.raises(ValueError, match="当前状态不可标记爽约"):
            await appointment_service.mark_no_show(test_appointment.id)


class TestStatusFlowIntegration:
    """测试状态流转集成"""

    @pytest.mark.asyncio
    async def test_full_flow_confirmed_to_completed(
        self,
        db_session,
        test_appointment: Appointment,
        test_user,
        appointment_service: AppointmentService
    ):
        """完整流程: CONFIRMED -> SIGNED -> SEEING -> COMPLETED"""
        # 初始状态验证
        assert test_appointment.status == APPOINTMENT_STATUS["CONFIRMED"]

        # 设置签到时间窗
        local_tz = pytz.timezone("Asia/Shanghai")
        now = datetime.now(local_tz)
        test_appointment.checkin_open_at = now - timedelta(hours=1)
        test_appointment.checkin_close_at = now + timedelta(hours=1)
        await db_session.commit()

        # 步骤1: 签到
        with patch.object(AppointmentFlowService, "_create_checkin_log", new_callable=AsyncMock):
            signed = await appointment_service.sign_in(
                appointment_id=test_appointment.id,
                user_id=test_user.id,
                is_admin=False,
                checkin_method="MANUAL",
            )
        assert signed.status == APPOINTMENT_STATUS["SIGNED"]

        # 步骤2: 叫号
        with patch.object(appointment_service, "_dispatch_email_event"):
            seeing = await appointment_service.call_patient(test_appointment.id)
        assert seeing.status == APPOINTMENT_STATUS["SEEING"]

        # 步骤3: 完成
        # 创建 mock 对象
        mock_message_service = MagicMock()
        mock_message_service.send_appointment_notification = AsyncMock()
        mock_compat = MagicMock()
        mock_compat.return_value = mock_message_service

        with patch.object(appointment_service, "_dispatch_email_event"), \
             patch.object(appointment_service, "_compat", return_value=mock_compat):
            completed = await appointment_service.complete(test_appointment.id)
        assert completed.status == APPOINTMENT_STATUS["COMPLETED"]

    @pytest.mark.asyncio
    async def test_pass_and_recall_flow(
        self,
        db_session,
        test_appointment: Appointment,
        appointment_service: AppointmentService
    ):
        """过号和重新叫号流程: SIGNED -> EXPIRED -> SEEING"""
        # 设置为已签到状态
        test_appointment.status = APPOINTMENT_STATUS["SIGNED"]
        await db_session.commit()

        # 步骤1: 过号
        passed = await appointment_service.pass_number(test_appointment.id)
        assert passed.status == APPOINTMENT_STATUS["EXPIRED"]

        # 步骤2: 重新叫号
        recalled = await appointment_service.recall(test_appointment.id)
        assert recalled.status == APPOINTMENT_STATUS["SEEING"]

    @pytest.mark.asyncio
    async def test_cancel_sign_in_resets_state(
        self,
        db_session,
        test_appointment: Appointment,
        appointment_service: AppointmentService
    ):
        """取消签到重置状态: SIGNED -> CONFIRMED"""
        # 设置为已签到状态
        test_appointment.status = APPOINTMENT_STATUS["SIGNED"]
        test_appointment.sign_in_time = datetime.now()
        await db_session.commit()

        result = await appointment_service.cancel_sign_in(test_appointment.id)

        assert result.status == APPOINTMENT_STATUS["CONFIRMED"]
        assert result.sign_in_time is None
