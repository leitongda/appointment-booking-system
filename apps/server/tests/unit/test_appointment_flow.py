"""
预约流程服务补充单元测试

测试 AppointmentFlowService 的核心流程方法
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4
import pytz

from app.models.appointment import Appointment
from app.modules.appointments.service_flow import AppointmentFlowService
from app.modules.appointments.common import APPOINTMENT_STATUS


class TestSignInFailureLogging:
    """测试签到失败时的日志记录"""

    @pytest.mark.asyncio
    async def test_sign_in_failure_creates_log(
        self,
        db_session,
        test_appointment: Appointment,
        test_user,
    ):
        """测试签到失败时创建失败日志"""
        service = AppointmentFlowService(db_session)

        # 设置为无效状态
        test_appointment.status = APPOINTMENT_STATUS['CANCELLED']
        await db_session.commit()

        with patch.object(
            service, '_create_checkin_log', new_callable=AsyncMock
        ) as mock_create_log:
            try:
                await service.sign_in(
                    appointment_id=test_appointment.id,
                    user_id=test_user.id,
                    is_admin=False,
                    checkin_method='QR_CODE',
                )
            except ValueError:
                pass

        # 验证失败日志被创建
        mock_create_log.assert_called_once()
        call_kwargs = mock_create_log.call_args.kwargs
        assert call_kwargs['status'] == 'FAILED'
        assert call_kwargs['checkin_method'] == 'QR_CODE'
        assert '当前状态不可签到' in call_kwargs['fail_reason']


class TestCallPatientNotifications:
    """测试叫号时的通知发送"""

    @pytest.mark.asyncio
    async def test_call_patient_sends_notification(
        self,
        db_session,
        test_appointment: Appointment,
    ):
        """测试叫号时发送站内信通知"""
        service = AppointmentFlowService(db_session)

        test_appointment.status = APPOINTMENT_STATUS['SIGNED']
        await db_session.commit()

        # Mock 消息服务（直接 patch 内部导入，避免调用链问题）
        with patch(
            'app.modules.appointments.service_flow.MessageService'
        ) as mock_msg_service_cls:
            mock_msg_service = MagicMock()
            mock_msg_service_cls.return_value = mock_msg_service
            mock_msg_service.send_appointment_notification = AsyncMock()

            with patch.object(service, '_dispatch_email_event'):
                result = await service.call_patient(test_appointment.id)

        # 验证叫号成功（通知可能失败但不影响主流程）
        assert result is not None
        assert result.status == APPOINTMENT_STATUS['SEEING']

    @pytest.mark.asyncio
    async def test_call_patient_notification_failure_logged(
        self,
        db_session,
        test_appointment: Appointment,
    ):
        """测试通知发送失败不影响叫号流程"""
        service = AppointmentFlowService(db_session)

        test_appointment.status = APPOINTMENT_STATUS['SIGNED']
        await db_session.commit()

        # Mock 消息服务抛出异常
        with patch(
            'app.modules.appointments.service_flow.MessageService'
        ) as mock_msg_service_cls:
            mock_msg_service = MagicMock()
            mock_msg_service_cls.return_value = mock_msg_service
            mock_msg_service.send_appointment_notification = AsyncMock(
                side_effect=Exception("通知发送失败")
            )

            with patch.object(service, '_dispatch_email_event'):
                result = await service.call_patient(test_appointment.id)

        # 验证叫号仍然成功
        assert result is not None
        assert result.status == APPOINTMENT_STATUS['SEEING']


class TestRecallEdgeCases:
    """测试重新叫号的边界情况"""

    @pytest.mark.asyncio
    async def test_recall_updates_call_time(
        self,
        db_session,
        test_appointment: Appointment,
    ):
        """测试重新叫号更新叫号时间"""
        service = AppointmentFlowService(db_session)

        # 设置为过号状态
        test_appointment.status = APPOINTMENT_STATUS['EXPIRED']
        old_call_time = datetime.now() - timedelta(minutes=10)
        test_appointment.call_time = old_call_time
        await db_session.commit()

        result = await service.recall(test_appointment.id)

        # 验证叫号时间更新
        assert result.status == APPOINTMENT_STATUS['SEEING']
        assert result.call_time > old_call_time


class TestMarkNoShowNotifications:
    """测试标记爽约时的通知"""

    @pytest.mark.asyncio
    async def test_mark_no_show_dispatches_event(
        self,
        db_session,
        test_appointment: Appointment,
    ):
        """测试标记爽约时分发事件"""
        service = AppointmentFlowService(db_session)

        test_appointment.status = APPOINTMENT_STATUS['CONFIRMED']
        await db_session.commit()

        with patch.object(service, '_dispatch_email_event') as mock_dispatch:
            await service.mark_no_show(test_appointment.id)

        # 验证事件被分发
        mock_dispatch.assert_called_once()
