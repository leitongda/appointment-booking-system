"""停诊处置服务单元测试

覆盖 reschedule / change_date / manual 三种处置方式:
- 预约状态变更
- 号源释放
- 通知发送
- 事务回滚（通知失败不影响预约状态）
"""
import uuid
from datetime import date, datetime, time, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.appointment import Appointment
from app.models.doctor import Doctor
from app.models.schedule import Schedule
from app.models.schedule_suspension import ScheduleSuspension
from app.modules.appointments.common import APPOINTMENT_STATUS, ACTIVE_APPOINTMENT_STATUSES
from app.modules.schedule_suspensions.service_processing import SuspensionProcessingService


# ==================== Fixtures ====================


@pytest_asyncio.fixture
async def suspension(
    db_session: AsyncSession,
    test_tenant,
    test_store,
    test_doctor,
    test_schedule,
) -> ScheduleSuspension:
    """创建测试停诊记录"""
    suspension = ScheduleSuspension(
        id=str(uuid.uuid4()),
        tenant_id=test_tenant.id,
        store_id=test_store.id,
        doctor_id=test_doctor.id,
        title="医生临时停诊",
        suspension_date=test_schedule.schedule_date,
        schedule_ids=f'["{test_schedule.id}"]',
        status=1,
        suspension_type="temporary",
        processing_status="pending",
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(suspension)
    await db_session.commit()
    await db_session.refresh(suspension)
    return suspension


@pytest_asyncio.fixture
async def paid_appointment(
    db_session: AsyncSession,
    test_tenant,
    test_schedule,
    test_patient,
    test_doctor,
    test_user,
) -> Appointment:
    """创建已支付的测试预约"""
    appointment = Appointment(
        id=str(uuid.uuid4()),
        appointment_no=f"YY{datetime.now().strftime('%Y%m%d%H%M%S')}{str(uuid.uuid4())[:4].upper()}",
        user_id=test_user.id,
        patient_id=test_patient.id,
        doctor_id=test_doctor.id,
        schedule_id=test_schedule.id,
        tenant_id=test_tenant.id,
        queue_number=1,
        status=1,  # 已预约
        patient_name=test_patient.name,
        patient_phone=test_patient.phone,
        doctor_name=test_doctor.name,
        doctor_title=test_doctor.title,
        department_name="测试科室",
        payment_amount=50.00,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        created_by=test_user.id,
    )
    db_session.add(appointment)
    test_schedule.booked_slots += 1
    await db_session.commit()
    await db_session.refresh(appointment)
    return appointment


@pytest.fixture
def mock_distributed_lock():
    """Mock RedisCache.tenant_distributed_lock"""
    lock = AsyncMock()
    lock.__aenter__ = AsyncMock(return_value="lock_value")
    lock.__aexit__ = AsyncMock(return_value=None)
    with patch(
        "app.modules.schedule_suspensions.service_processing.RedisCache.tenant_distributed_lock",
        return_value=lock,
    ):
        yield lock


@pytest.fixture
def mock_message_service():
    """Mock MessageService"""
    with patch(
        "app.modules.schedule_suspensions.service_processing.MessageService",
    ) as MockService:
        instance = MockService.return_value
        instance.send_stop_clinic_notification = AsyncMock()
        instance.send_schedule_notification = AsyncMock()
        yield instance


# ==================== reschedule 测试 ====================


@pytest.mark.asyncio
async def test_reschedule_cancels_appointment(
    db_session: AsyncSession,
    suspension,
    paid_appointment,
    test_schedule,
    mock_distributed_lock,
    mock_message_service,
):
    """reschedule: 预约状态应变为 CANCELLED"""
    service = SuspensionProcessingService(db_session)
    result = await service._mark_reschedule(
        paid_appointment, suspension, "operator_1", {"appointment_id": paid_appointment.id},
    )

    assert result["success"] is True
    assert result["new_status"] == APPOINTMENT_STATUS["CANCELLED"]

    # 重新查询确认持久化
    refreshed = await db_session.get(Appointment, paid_appointment.id)
    assert refreshed.status == APPOINTMENT_STATUS["CANCELLED"]
    assert refreshed.cancel_reason is not None and "停诊转约" in refreshed.cancel_reason


@pytest.mark.asyncio
async def test_reschedule_releases_slot(
    db_session: AsyncSession,
    suspension,
    paid_appointment,
    test_schedule,
    mock_distributed_lock,
    mock_message_service,
):
    """reschedule: 号源应释放 (booked_slots -1)"""
    original_slots = test_schedule.booked_slots
    assert original_slots >= 1

    service = SuspensionProcessingService(db_session)
    await service._mark_reschedule(
        paid_appointment, suspension, "operator_1", {"appointment_id": paid_appointment.id},
    )

    refreshed_schedule = await db_session.get(Schedule, test_schedule.id)
    assert refreshed_schedule.booked_slots == original_slots - 1


@pytest.mark.asyncio
async def test_reschedule_sets_rescheduled_from_id(
    db_session: AsyncSession,
    suspension,
    paid_appointment,
    test_schedule,
    mock_distributed_lock,
    mock_message_service,
):
    """reschedule: rescheduled_from_id 应指向原预约"""
    original_id = paid_appointment.id

    service = SuspensionProcessingService(db_session)
    await service._mark_reschedule(
        paid_appointment, suspension, "operator_1", {"appointment_id": original_id},
    )

    refreshed = await db_session.get(Appointment, original_id)
    assert refreshed.rescheduled_from_id == original_id


@pytest.mark.asyncio
async def test_reschedule_appends_remark(
    db_session: AsyncSession,
    suspension,
    paid_appointment,
    test_schedule,
    mock_distributed_lock,
    mock_message_service,
):
    """reschedule: remark 应追加转约标记"""
    service = SuspensionProcessingService(db_session)
    await service._mark_reschedule(
        paid_appointment, suspension, "operator_1", {"appointment_id": paid_appointment.id},
    )

    refreshed = await db_session.get(Appointment, paid_appointment.id)
    assert "[停诊待转约]" in (refreshed.remark or "")


@pytest.mark.asyncio
async def test_reschedule_sends_notification(
    db_session: AsyncSession,
    suspension,
    paid_appointment,
    test_schedule,
    mock_distributed_lock,
    mock_message_service,
):
    """reschedule: 应发送患者通知"""
    service = SuspensionProcessingService(db_session)
    await service._mark_reschedule(
        paid_appointment, suspension, "operator_1", {"appointment_id": paid_appointment.id},
    )

    mock_message_service.send_stop_clinic_notification.assert_called_once()
    call_kwargs = mock_message_service.send_stop_clinic_notification.call_args
    assert call_kwargs.kwargs.get("user_id") == paid_appointment.user_id or \
           (call_kwargs.args and call_kwargs.args[0] == paid_appointment.user_id)


@pytest.mark.asyncio
async def test_reschedule_notification_failure_does_not_rollback(
    db_session: AsyncSession,
    suspension,
    paid_appointment,
    test_schedule,
    mock_distributed_lock,
):
    """reschedule: 通知发送失败不应回滚预约状态"""
    with patch(
        "app.modules.schedule_suspensions.service_processing.MessageService",
    ) as MockService:
        instance = MockService.return_value
        instance.send_stop_clinic_notification = AsyncMock(side_effect=Exception("通知服务异常"))

        service = SuspensionProcessingService(db_session)
        result = await service._mark_reschedule(
            paid_appointment, suspension, "operator_1", {"appointment_id": paid_appointment.id},
        )

    # 事务已 commit，通知失败不影响结果
    assert result["success"] is True

    refreshed = await db_session.get(Appointment, paid_appointment.id)
    assert refreshed.status == APPOINTMENT_STATUS["CANCELLED"]


@pytest.mark.asyncio
async def test_reschedule_skips_already_cancelled(
    db_session: AsyncSession,
    suspension,
    paid_appointment,
    test_schedule,
    mock_distributed_lock,
    mock_message_service,
):
    """reschedule: 已取消的预约不应被重复处理"""
    paid_appointment.status = APPOINTMENT_STATUS["CANCELLED"]
    await db_session.commit()

    service = SuspensionProcessingService(db_session)
    result = await service._mark_reschedule(
        paid_appointment, suspension, "operator_1", {"appointment_id": paid_appointment.id},
    )

    assert result["success"] is False
    assert "已被其他操作处理" in result["error"]


# ==================== change_date 测试 ====================


@pytest.mark.asyncio
async def test_change_date_cancels_appointment(
    db_session: AsyncSession,
    suspension,
    paid_appointment,
    test_schedule,
    mock_distributed_lock,
    mock_message_service,
):
    """change_date: 预约状态应变为 CANCELLED"""
    service = SuspensionProcessingService(db_session)
    result = await service._mark_change_date(
        paid_appointment, suspension, "operator_1", {"appointment_id": paid_appointment.id},
    )

    assert result["success"] is True
    assert result["new_status"] == APPOINTMENT_STATUS["CANCELLED"]

    refreshed = await db_session.get(Appointment, paid_appointment.id)
    assert refreshed.status == APPOINTMENT_STATUS["CANCELLED"]
    assert refreshed.cancel_reason is not None and "停诊改期" in refreshed.cancel_reason


@pytest.mark.asyncio
async def test_change_date_releases_slot(
    db_session: AsyncSession,
    suspension,
    paid_appointment,
    test_schedule,
    mock_distributed_lock,
    mock_message_service,
):
    """change_date: 号源应释放 (booked_slots -1)"""
    original_slots = test_schedule.booked_slots

    service = SuspensionProcessingService(db_session)
    await service._mark_change_date(
        paid_appointment, suspension, "operator_1", {"appointment_id": paid_appointment.id},
    )

    refreshed_schedule = await db_session.get(Schedule, test_schedule.id)
    assert refreshed_schedule.booked_slots == original_slots - 1


@pytest.mark.asyncio
async def test_change_date_sets_rescheduled_from_id(
    db_session: AsyncSession,
    suspension,
    paid_appointment,
    test_schedule,
    mock_distributed_lock,
    mock_message_service,
):
    """change_date: rescheduled_from_id 应指向原预约"""
    original_id = paid_appointment.id

    service = SuspensionProcessingService(db_session)
    await service._mark_change_date(
        paid_appointment, suspension, "operator_1", {"appointment_id": original_id},
    )

    refreshed = await db_session.get(Appointment, original_id)
    assert refreshed.rescheduled_from_id == original_id


@pytest.mark.asyncio
async def test_change_date_appends_remark(
    db_session: AsyncSession,
    suspension,
    paid_appointment,
    test_schedule,
    mock_distributed_lock,
    mock_message_service,
):
    """change_date: remark 应追加改期标记"""
    service = SuspensionProcessingService(db_session)
    await service._mark_change_date(
        paid_appointment, suspension, "operator_1", {"appointment_id": paid_appointment.id},
    )

    refreshed = await db_session.get(Appointment, paid_appointment.id)
    assert "[停诊待改期]" in (refreshed.remark or "")


@pytest.mark.asyncio
async def test_change_date_sends_notification(
    db_session: AsyncSession,
    suspension,
    paid_appointment,
    test_schedule,
    mock_distributed_lock,
    mock_message_service,
):
    """change_date: 应发送患者通知"""
    service = SuspensionProcessingService(db_session)
    await service._mark_change_date(
        paid_appointment, suspension, "operator_1", {"appointment_id": paid_appointment.id},
    )

    mock_message_service.send_stop_clinic_notification.assert_called_once()


@pytest.mark.asyncio
async def test_change_date_notification_failure_does_not_rollback(
    db_session: AsyncSession,
    suspension,
    paid_appointment,
    test_schedule,
    mock_distributed_lock,
):
    """change_date: 通知发送失败不应回滚预约状态"""
    with patch(
        "app.modules.schedule_suspensions.service_processing.MessageService",
    ) as MockService:
        instance = MockService.return_value
        instance.send_stop_clinic_notification = AsyncMock(side_effect=Exception("通知服务异常"))

        service = SuspensionProcessingService(db_session)
        result = await service._mark_change_date(
            paid_appointment, suspension, "operator_1", {"appointment_id": paid_appointment.id},
        )

    assert result["success"] is True

    refreshed = await db_session.get(Appointment, paid_appointment.id)
    assert refreshed.status == APPOINTMENT_STATUS["CANCELLED"]


# ==================== manual 测试 ====================


@pytest.mark.asyncio
async def test_manual_only_marks_remark(
    db_session: AsyncSession,
    suspension,
    paid_appointment,
    test_schedule,
    mock_message_service,
):
    """manual: 仅追加 remark，不改变预约状态"""
    original_status = paid_appointment.status
    original_slots = test_schedule.booked_slots

    service = SuspensionProcessingService(db_session)
    result = await service._mark_manual(
        paid_appointment, suspension, "operator_1", {"appointment_id": paid_appointment.id},
    )

    assert result["success"] is True

    refreshed = await db_session.get(Appointment, paid_appointment.id)
    assert refreshed.status == original_status
    assert "[停诊待人工处理]" in (refreshed.remark or "")
    assert refreshed.rescheduled_from_id is None

    refreshed_schedule = await db_session.get(Schedule, test_schedule.id)
    assert refreshed_schedule.booked_slots == original_slots


# ==================== process_suspension 集成测试 ====================


@pytest.mark.asyncio
async def test_process_suspension_reschedule_full_flow(
    db_session: AsyncSession,
    suspension,
    paid_appointment,
    test_schedule,
    test_doctor,
    mock_distributed_lock,
    mock_message_service,
):
    """process_suspension(reschedule): 完整流程测试"""
    original_slots = test_schedule.booked_slots

    service = SuspensionProcessingService(db_session)
    result = await service.process_suspension(
        suspension_id=suspension.id,
        processing_method="reschedule",
        operator_id="operator_1",
    )

    assert result["processing_status"] == "completed"
    assert result["total_affected"] == 1
    assert result["success_count"] == 1
    assert result["failed_count"] == 0

    # 预约状态已变更
    refreshed = await db_session.get(Appointment, paid_appointment.id)
    assert refreshed.status == APPOINTMENT_STATUS["CANCELLED"]
    assert refreshed.rescheduled_from_id == paid_appointment.id

    # 号源已释放
    refreshed_schedule = await db_session.get(Schedule, test_schedule.id)
    assert refreshed_schedule.booked_slots == original_slots - 1

    # 停诊记录已更新
    refreshed_suspension = await db_session.get(ScheduleSuspension, suspension.id)
    assert refreshed_suspension.processing_status == "completed"


@pytest.mark.asyncio
async def test_process_suspension_change_date_full_flow(
    db_session: AsyncSession,
    suspension,
    paid_appointment,
    test_schedule,
    test_doctor,
    mock_distributed_lock,
    mock_message_service,
):
    """process_suspension(change_date): 完整流程测试"""
    service = SuspensionProcessingService(db_session)
    result = await service.process_suspension(
        suspension_id=suspension.id,
        processing_method="change_date",
        operator_id="operator_1",
    )

    assert result["processing_status"] == "completed"
    assert result["success_count"] == 1

    refreshed = await db_session.get(Appointment, paid_appointment.id)
    assert refreshed.status == APPOINTMENT_STATUS["CANCELLED"]
    assert refreshed.rescheduled_from_id == paid_appointment.id


@pytest.mark.asyncio
async def test_process_suspension_manual_no_status_change(
    db_session: AsyncSession,
    suspension,
    paid_appointment,
    test_schedule,
    test_doctor,
    mock_message_service,
):
    """process_suspension(manual): 不改变预约状态，不释放号源"""
    original_status = paid_appointment.status
    original_slots = test_schedule.booked_slots

    service = SuspensionProcessingService(db_session)
    result = await service.process_suspension(
        suspension_id=suspension.id,
        processing_method="manual",
        operator_id="operator_1",
    )

    assert result["processing_status"] == "completed"
    assert result["success_count"] == 1

    refreshed = await db_session.get(Appointment, paid_appointment.id)
    assert refreshed.status == original_status
    assert refreshed.rescheduled_from_id is None

    refreshed_schedule = await db_session.get(Schedule, test_schedule.id)
    assert refreshed_schedule.booked_slots == original_slots
