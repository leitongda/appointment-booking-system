"""
签到功能单元测试

测试 AppointmentService.sign_in 方法的各种场景：
1. 正常签到
2. 错误状态不可签到
3. 未到签到时间
"""
import pytest
from datetime import datetime, date, time, timedelta
from unittest.mock import AsyncMock, patch, MagicMock
import pytz

from app.middleware.exception import BusinessError
from app.modules.appointments.service import AppointmentService, APPOINTMENT_STATUS
from app.models.appointment import Appointment
from app.models.schedule import Schedule


class TestSignInSuccess:
    """测试正常签到场景"""

    @pytest.mark.asyncio
    async def test_sign_in_success(
        self,
        db_session,
        test_appointment: Appointment,
        test_user,
        appointment_service: AppointmentService
    ):
        """测试正常签到

        验证点：
        1. 状态从已预约(1)变为已签到(2)
        2. 签到时间被记录
        3. 签到次数 +1
        """
        # 1. 准备测试数据
        appointment_id = test_appointment.id
        user_id = test_user.id

        # Mock 规则引擎，确保时间窗检查通过
        with patch.object(
            AppointmentService, '_create_checkin_log', new_callable=AsyncMock
        ):
            # 设置签到时间窗为当前时间附近（允许签到）
            # 使用本地时区
            local_tz = pytz.timezone('Asia/Shanghai')
            now = datetime.now(local_tz)

            # 设置签到时间窗：1小时前开始，1小时后结束
            test_appointment.checkin_open_at = now - timedelta(hours=1)
            test_appointment.checkin_close_at = now + timedelta(hours=1)
            test_appointment.checkin_count = 0
            await db_session.commit()
            await db_session.refresh(test_appointment)

            # 2. 执行签到
            result = await appointment_service.sign_in(
                appointment_id=appointment_id,
                user_id=user_id,
                is_admin=False,
                checkin_method='MANUAL',
                device_info='test_device',
                location_info='test_location',
                operator_id=user_id,
                operator_type='USER'
            )

        # 3. 验证结果
        assert result is not None, "签到应该返回预约对象"

        # 验证状态变为已签到(2)
        assert result.status == APPOINTMENT_STATUS['SIGNED'], (
            f"签到后状态应为已签到(2)，实际为 {result.status}"
        )

        # 验证签到时间被记录
        assert result.sign_in_time is not None, "签到时间应该被记录"

        # 验证签到次数 +1
        assert result.checkin_count == 1, (
            f"签到次数应该为1，实际为 {result.checkin_count}"
        )

    @pytest.mark.asyncio
    async def test_sign_in_increments_checkin_count(
        self,
        db_session,
        test_appointment: Appointment,
        test_user,
        appointment_service: AppointmentService
    ):
        """测试签到次数累加

        验证多次签到时签到次数正确累加
        """
        appointment_id = test_appointment.id
        user_id = test_user.id

        # Mock 审计日志创建
        with patch.object(
            AppointmentService, '_create_checkin_log', new_callable=AsyncMock
        ):
            local_tz = pytz.timezone('Asia/Shanghai')
            now = datetime.now(local_tz)

            # 设置签到时间窗
            test_appointment.checkin_open_at = now - timedelta(hours=1)
            test_appointment.checkin_close_at = now + timedelta(hours=1)
            test_appointment.checkin_count = 2  # 已签到2次
            await db_session.commit()
            await db_session.refresh(test_appointment)

            # Mock 规则引擎的签到策略检查（允许签到）
            with patch(
                'app.modules.appointments.service.RuleEngineService'
            ) as mock_rule_engine:
                mock_instance = MagicMock()
                mock_rule_engine.return_value = mock_instance
                # Mock 签到策略：最多允许5次
                mock_policy = MagicMock()
                mock_policy.max_times = 5
                mock_instance.get_checkin_policy_by_rule_set_id = AsyncMock(
                    return_value=mock_policy
                )
                mock_instance.calculate_checkin_grace_period = MagicMock(
                    return_value={'is_late': False}
                )

                result = await appointment_service.sign_in(
                    appointment_id=appointment_id,
                    user_id=user_id,
                    is_admin=False,
                    checkin_method='QR_CODE'
                )

        # 验证签到次数累加到3
        assert result.checkin_count == 3, (
            f"签到次数应该为3，实际为 {result.checkin_count}"
        )


class TestSignInWrongStatus:
    """测试错误状态不可签到场景"""

    @pytest.mark.asyncio
    async def test_sign_in_cancelled_status(
        self,
        db_session,
        test_appointment: Appointment,
        test_user,
        appointment_service: AppointmentService
    ):
        """测试已取消(6)状态的预约不可签到

        验证点：
        1. 抛出 ValueError
        2. 错误消息包含"当前状态不可签到"
        """
        # 1. 准备测试数据：将预约状态设置为已取消
        test_appointment.status = APPOINTMENT_STATUS['CANCELLED']
        await db_session.commit()
        await db_session.refresh(test_appointment)

        appointment_id = test_appointment.id
        user_id = test_user.id

        # 2. 执行签到并验证异常
        with pytest.raises(BusinessError) as exc_info:
            await appointment_service.sign_in(
                appointment_id=appointment_id,
                user_id=user_id,
                is_admin=False
            )

        # 3. 验证错误消息
        assert "当前状态不可签到" in str(exc_info.value), (
            f"错误消息应包含'当前状态不可签到'，实际为: {exc_info.value}"
        )

    @pytest.mark.asyncio
    async def test_sign_in_completed_status(
        self,
        db_session,
        test_appointment: Appointment,
        test_user,
        appointment_service: AppointmentService
    ):
        """测试已完成(5)状态的预约不可签到"""
        # 设置状态为已完成
        test_appointment.status = APPOINTMENT_STATUS['COMPLETED']
        await db_session.commit()
        await db_session.refresh(test_appointment)

        with pytest.raises(BusinessError) as exc_info:
            await appointment_service.sign_in(
                appointment_id=test_appointment.id,
                user_id=test_user.id,
                is_admin=False
            )

        assert "当前状态不可签到" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_sign_in_signed_status(
        self,
        db_session,
        test_appointment: Appointment,
        test_user,
        appointment_service: AppointmentService
    ):
        """测试已签到(2)状态的预约不可重复签到"""
        # 设置状态为已签到
        test_appointment.status = APPOINTMENT_STATUS['SIGNED']
        await db_session.commit()
        await db_session.refresh(test_appointment)

        with pytest.raises(BusinessError) as exc_info:
            await appointment_service.sign_in(
                appointment_id=test_appointment.id,
                user_id=test_user.id,
                is_admin=False
            )

        assert "当前状态不可签到" in str(exc_info.value)


class TestSignInTimeWindow:
    """测试签到时间窗场景"""

    @pytest.mark.asyncio
    async def test_sign_in_time_window_early(
        self,
        db_session,
        test_appointment: Appointment,
        test_user,
        appointment_service: AppointmentService
    ):
        """测试未到签到时间不可签到

        验证点：
        1. 抛出 ValueError
        2. 错误消息包含"未到签到时间"或返回 early 状态
        """
        # 1. 准备测试数据：设置签到时间窗在未来
        local_tz = pytz.timezone('Asia/Shanghai')
        now = datetime.now(local_tz)

        # 签到时间窗：30分钟后开始，2小时后结束
        test_appointment.checkin_open_at = now + timedelta(minutes=30)
        test_appointment.checkin_close_at = now + timedelta(hours=2)
        test_appointment.status = APPOINTMENT_STATUS['CONFIRMED']
        await db_session.commit()
        await db_session.refresh(test_appointment)

        appointment_id = test_appointment.id
        user_id = test_user.id

        # 2. 执行签到并验证异常
        with pytest.raises(BusinessError) as exc_info:
            await appointment_service.sign_in(
                appointment_id=appointment_id,
                user_id=user_id,
                is_admin=False
            )

        # 3. 验证错误消息包含"未到签到时间"
        error_msg = str(exc_info.value)
        assert "未到签到时间" in error_msg, (
            f"错误消息应包含'未到签到时间'，实际为: {error_msg}"
        )

    @pytest.mark.asyncio
    async def test_sign_in_time_window_late(
        self,
        db_session,
        test_appointment: Appointment,
        test_user,
        appointment_service: AppointmentService
    ):
        """测试已过签到时间不可签到"""
        # 1. 准备测试数据：设置签到时间窗已过期
        local_tz = pytz.timezone('Asia/Shanghai')
        now = datetime.now(local_tz)

        # 签到时间窗：2小时前开始，1小时前结束
        test_appointment.checkin_open_at = now - timedelta(hours=2)
        test_appointment.checkin_close_at = now - timedelta(hours=1)
        test_appointment.status = APPOINTMENT_STATUS['CONFIRMED']
        await db_session.commit()
        await db_session.refresh(test_appointment)

        # 2. 执行签到并验证异常
        with pytest.raises(BusinessError) as exc_info:
            await appointment_service.sign_in(
                appointment_id=test_appointment.id,
                user_id=test_user.id,
                is_admin=False
            )

        # 3. 验证错误消息包含"已过签到时间"
        error_msg = str(exc_info.value)
        assert "已过签到时间" in error_msg, (
            f"错误消息应包含'已过签到时间'，实际为: {error_msg}"
        )

    @pytest.mark.asyncio
    async def test_sign_in_time_window_valid(
        self,
        db_session,
        test_appointment: Appointment,
        test_user,
        appointment_service: AppointmentService
    ):
        """测试在有效签到时间窗内可以正常签到"""
        # 1. 准备测试数据：设置当前时间在签到时间窗内
        local_tz = pytz.timezone('Asia/Shanghai')
        now = datetime.now(local_tz)

        # 签到时间窗：30分钟前开始，30分钟后结束
        test_appointment.checkin_open_at = now - timedelta(minutes=30)
        test_appointment.checkin_close_at = now + timedelta(minutes=30)
        test_appointment.status = APPOINTMENT_STATUS['CONFIRMED']
        test_appointment.checkin_count = 0
        await db_session.commit()
        await db_session.refresh(test_appointment)

        # 2. Mock 审计日志创建
        with patch.object(
            AppointmentService, '_create_checkin_log', new_callable=AsyncMock
        ):
            # 3. 执行签到
            result = await appointment_service.sign_in(
                appointment_id=test_appointment.id,
                user_id=test_user.id,
                is_admin=False,
                checkin_method='MANUAL'
            )

        # 4. 验证签到成功
        assert result is not None
        assert result.status == APPOINTMENT_STATUS['SIGNED']
        assert result.sign_in_time is not None


class TestSignInPermission:
    """测试签到权限场景"""

    @pytest.mark.asyncio
    async def test_sign_in_wrong_user(
        self,
        db_session,
        test_appointment: Appointment,
        appointment_service: AppointmentService
    ):
        """测试非预约用户不可签到

        验证点：
        1. 抛出 ValueError
        2. 错误消息包含"无权操作"
        """
        # 使用一个不存在的用户ID
        wrong_user_id = "wrong_user_id_12345"

        with pytest.raises(BusinessError) as exc_info:
            await appointment_service.sign_in(
                appointment_id=test_appointment.id,
                user_id=wrong_user_id,
                is_admin=False
            )

        assert "无权操作" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_sign_in_by_admin(
        self,
        db_session,
        test_appointment: Appointment,
        appointment_service: AppointmentService
    ):
        """测试管理员可以帮用户签到"""
        # 1. 准备测试数据
        local_tz = pytz.timezone('Asia/Shanghai')
        now = datetime.now(local_tz)

        test_appointment.checkin_open_at = now - timedelta(minutes=30)
        test_appointment.checkin_close_at = now + timedelta(minutes=30)
        test_appointment.status = APPOINTMENT_STATUS['CONFIRMED']
        test_appointment.checkin_count = 0
        await db_session.commit()
        await db_session.refresh(test_appointment)

        # 2. Mock 审计日志创建
        with patch.object(
            AppointmentService, '_create_checkin_log', new_callable=AsyncMock
        ):
            # 3. 管理员签到（使用不同的 admin_user_id）
            result = await appointment_service.sign_in(
                appointment_id=test_appointment.id,
                user_id="admin_user_id",  # 管理员ID，不同于预约用户ID
                is_admin=True,  # 标记为管理员操作
                operator_id="admin_user_id",
                operator_type='ADMIN'
            )

        # 4. 验证签到成功
        assert result is not None
        assert result.status == APPOINTMENT_STATUS['SIGNED']


class TestSignInNonExistent:
    """测试预约不存在场景"""

    @pytest.mark.asyncio
    async def test_sign_in_non_existent_appointment(
        self,
        appointment_service: AppointmentService
    ):
        """测试不存在的预约不可签到

        验证点：
        1. 返回 None（由上层处理 404 错误）
        """
        # 使用一个不存在的预约ID
        non_existent_id = "non_existent_appointment_id_12345"

        result = await appointment_service.sign_in(
            appointment_id=non_existent_id,
            user_id="any_user_id",
            is_admin=False
        )

        # 验证返回 None
        assert result is None, "不存在的预约应返回 None"
