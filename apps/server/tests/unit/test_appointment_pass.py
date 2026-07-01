"""
过号功能单元测试

测试 AppointmentFlowService.pass_number 方法的各种场景：
1. 已签到状态过号成功
2. 就诊中状态过号成功
3. 已预约状态不能过号
4. 已完成状态不能过号
"""
import pytest
import pytest_asyncio
from datetime import datetime

from app.modules.appointments.service_flow import AppointmentFlowService
from app.modules.appointments.common import APPOINTMENT_STATUS
from app.middleware.exception import BusinessError
from app.models.appointment import Appointment


class TestPassNumberSuccess:
    """测试过号成功场景"""

    @pytest.mark.asyncio
    async def test_pass_number_success_signed_in(
        self,
        db_session,
        test_appointment: Appointment,
        appointment_flow_service: AppointmentFlowService
    ):
        """测试已签到状态过号成功

        验证点：
        1. 状态从已签到(2)变为过号(7)
        2. 返回更新后的预约对象
        """
        # 1. 准备测试数据：将预约状态设置为已签到
        test_appointment.status = APPOINTMENT_STATUS['SIGNED']
        test_appointment.sign_in_time = datetime.now()
        await db_session.commit()
        await db_session.refresh(test_appointment)

        appointment_id = test_appointment.id

        # 2. 执行过号
        result = await appointment_flow_service.pass_number(appointment_id)

        # 3. 验证结果
        assert result is not None, "过号应该返回预约对象"
        assert result.status == APPOINTMENT_STATUS['EXPIRED'], (
            f"过号后状态应为过号(7)，实际为 {result.status}"
        )

    @pytest.mark.asyncio
    async def test_pass_number_success_in_progress(
        self,
        db_session,
        test_appointment: Appointment,
        appointment_flow_service: AppointmentFlowService
    ):
        """测试就诊中状态过号成功

        验证点：
        1. 状态从就诊中(4)变为过号(7)
        2. 返回更新后的预约对象
        """
        # 1. 准备测试数据：将预约状态设置为就诊中
        test_appointment.status = APPOINTMENT_STATUS['SEEING']
        test_appointment.call_time = datetime.now()
        await db_session.commit()
        await db_session.refresh(test_appointment)

        appointment_id = test_appointment.id

        # 2. 执行过号
        result = await appointment_flow_service.pass_number(appointment_id)

        # 3. 验证结果
        assert result is not None, "过号应该返回预约对象"
        assert result.status == APPOINTMENT_STATUS['EXPIRED'], (
            f"过号后状态应为过号(7)，实际为 {result.status}"
        )


class TestPassNumberWrongStatus:
    """测试错误状态不可过号场景"""

    @pytest.mark.asyncio
    async def test_pass_number_wrong_status_pending(
        self,
        db_session,
        test_appointment: Appointment,
        appointment_flow_service: AppointmentFlowService
    ):
        """测试已预约(1)状态的预约不能过号

        验证点：
        1. 抛出 ValueError
        2. 错误消息包含"当前状态不可过号"
        """
        # 1. 准备测试数据：将预约状态设置为已预约
        test_appointment.status = APPOINTMENT_STATUS['CONFIRMED']
        await db_session.commit()
        await db_session.refresh(test_appointment)

        appointment_id = test_appointment.id

        # 2. 执行过号并验证异常
        with pytest.raises(BusinessError) as exc_info:
            await appointment_flow_service.pass_number(appointment_id)

        # 3. 验证错误消息
        assert "当前状态不可过号" in str(exc_info.value), (
            f"错误消息应包含'当前状态不可过号'，实际为: {exc_info.value}"
        )

    @pytest.mark.asyncio
    async def test_pass_number_wrong_status_completed(
        self,
        db_session,
        test_appointment: Appointment,
        appointment_flow_service: AppointmentFlowService
    ):
        """测试已完成(5)状态的预约不能过号"""
        # 设置状态为已完成
        test_appointment.status = APPOINTMENT_STATUS['COMPLETED']
        test_appointment.complete_time = datetime.now()
        await db_session.commit()
        await db_session.refresh(test_appointment)

        with pytest.raises(BusinessError) as exc_info:
            await appointment_flow_service.pass_number(test_appointment.id)

        assert "当前状态不可过号" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_pass_number_wrong_status_cancelled(
        self,
        db_session,
        test_appointment: Appointment,
        appointment_flow_service: AppointmentFlowService
    ):
        """测试已取消(6)状态的预约不能过号"""
        # 设置状态为已取消
        test_appointment.status = APPOINTMENT_STATUS['CANCELLED']
        test_appointment.cancel_time = datetime.now()
        await db_session.commit()
        await db_session.refresh(test_appointment)

        with pytest.raises(BusinessError) as exc_info:
            await appointment_flow_service.pass_number(test_appointment.id)

        assert "当前状态不可过号" in str(exc_info.value)


class TestPassNumberNonExistent:
    """测试预约不存在场景"""

    @pytest.mark.asyncio
    async def test_pass_number_non_existent_appointment(
        self,
        appointment_flow_service: AppointmentFlowService
    ):
        """测试不存在的预约不能过号

        验证点：
        1. 返回 None（由上层处理 404 错误）
        """
        # 使用一个不存在的预约ID
        non_existent_id = "non_existent_appointment_id_12345"

        result = await appointment_flow_service.pass_number(non_existent_id)

        # 验证返回 None
        assert result is None, "不存在的预约应返回 None"


# ==================== Fixtures ====================

@pytest_asyncio.fixture
async def appointment_flow_service(db_session) -> AppointmentFlowService:
    """创建预约流程服务实例"""
    return AppointmentFlowService(db_session)
