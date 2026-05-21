"""排队流程集成测试

覆盖：预约 → 签到 → 叫号 → 过号 → 重叫 → 完成 → 爽约
"""
import pytest
from datetime import date, time, timedelta

from app.modules.appointments.common import APPOINTMENT_STATUS


pytestmark = [pytest.mark.integration]


@pytest.fixture
async def setup_schedule(db_session, test_tenant, test_store, test_department, test_doctor):
    """创建测试排班"""
    from app.models.schedule import Schedule
    import uuid

    schedule = Schedule(
        id=str(uuid.uuid4()),
        tenant_id=test_tenant.id,
        store_id=test_store.id,
        doctor_id=test_doctor.id,
        schedule_date=date.today() + timedelta(days=1),
        time_slot="morning",
        start_time=time(8, 0),
        end_time=time(12, 0),
        total_slots=10,
        booked_slots=0,
        status=1,
    )
    db_session.add(schedule)
    await db_session.commit()
    await db_session.refresh(schedule)
    return schedule


@pytest.fixture
async def setup_appointment(db_session, test_tenant, test_user, test_patient, setup_schedule):
    """创建测试预约"""
    from app.models.appointment import Appointment
    import uuid

    appointment = Appointment(
        id=str(uuid.uuid4()),
        tenant_id=test_tenant.id,
        user_id=test_user.id,
        patient_id=test_patient.id,
        schedule_id=setup_schedule.id,
        doctor_id=setup_schedule.doctor_id,
        appointment_no=f"TEST{uuid.uuid4().hex[:8].upper()}",
        status=APPOINTMENT_STATUS["CONFIRMED"],
        queue_number=1,
    )
    db_session.add(appointment)
    await db_session.commit()
    await db_session.refresh(appointment)
    return appointment


@pytest.mark.asyncio
async def test_sign_in_flow(db_session, setup_appointment):
    """测试签到流程"""
    from app.modules.appointments.service_flow import AppointmentFlowService

    appointment = setup_appointment
    service = AppointmentFlowService(db_session)

    # 签到（设置签到时间窗口包含当前时间，跳过排班时间校验）
    from datetime import datetime
    now = datetime.now()
    appointment.checkin_open_at = now - timedelta(hours=1)
    appointment.checkin_close_at = now + timedelta(hours=1)
    await db_session.commit()

    result = await service.sign_in(
        appointment_id=appointment.id,
        user_id=appointment.user_id,
        checkin_method="PHONE",
    )
    assert result is not None
    assert result.status == APPOINTMENT_STATUS["SIGNED"]
    assert result.sign_in_time is not None


@pytest.mark.asyncio
async def test_call_patient_flow(db_session, setup_appointment):
    """测试叫号流程"""
    from app.modules.appointments.service_flow import AppointmentFlowService

    appointment = setup_appointment
    service = AppointmentFlowService(db_session)

    # 先签到
    appointment.status = APPOINTMENT_STATUS["SIGNED"]
    await db_session.commit()

    result = await service.call_patient(appointment.id)
    assert result is not None
    assert result.status == APPOINTMENT_STATUS["SEEING"]
    assert result.call_time is not None


@pytest.mark.asyncio
async def test_pass_number_flow(db_session, setup_appointment):
    """测试过号流程"""
    from app.modules.appointments.service_flow import AppointmentFlowService

    appointment = setup_appointment
    service = AppointmentFlowService(db_session)

    # 先签到
    appointment.status = APPOINTMENT_STATUS["SIGNED"]
    await db_session.commit()

    result = await service.pass_number(appointment.id)
    assert result is not None
    assert result.status == APPOINTMENT_STATUS["EXPIRED"]


@pytest.mark.asyncio
async def test_recall_flow(db_session, setup_appointment):
    """测试重新叫号流程"""
    from app.modules.appointments.service_flow import AppointmentFlowService

    appointment = setup_appointment
    service = AppointmentFlowService(db_session)

    # 先过号
    appointment.status = APPOINTMENT_STATUS["EXPIRED"]
    await db_session.commit()

    result = await service.recall(appointment.id)
    assert result is not None
    assert result.status == APPOINTMENT_STATUS["SEEING"]
    assert result.call_time is not None


@pytest.mark.asyncio
async def test_complete_flow(db_session, setup_appointment):
    """测试完成就诊流程"""
    from app.modules.appointments.service_flow import AppointmentFlowService

    appointment = setup_appointment
    service = AppointmentFlowService(db_session)

    # 先叫号
    appointment.status = APPOINTMENT_STATUS["SEEING"]
    await db_session.commit()

    result = await service.complete(appointment.id)
    assert result is not None
    assert result.status == APPOINTMENT_STATUS["COMPLETED"]
    assert result.complete_time is not None


@pytest.mark.asyncio
async def test_mark_no_show_flow(db_session, setup_appointment):
    """测试标记爽约流程"""
    from app.modules.appointments.service_flow import AppointmentFlowService

    appointment = setup_appointment
    service = AppointmentFlowService(db_session)

    result = await service.mark_no_show(appointment.id)
    assert result is not None
    assert result.status == APPOINTMENT_STATUS["NO_SHOW"]


@pytest.mark.asyncio
async def test_sign_in_wrong_status(db_session, setup_appointment):
    """测试非已预约状态不能签到"""
    from app.modules.appointments.service_flow import AppointmentFlowService

    appointment = setup_appointment
    service = AppointmentFlowService(db_session)

    # 已签到状态不能再签到
    appointment.status = APPOINTMENT_STATUS["SIGNED"]
    await db_session.commit()

    with pytest.raises(ValueError, match="当前状态不可签到"):
        await service.sign_in(appointment_id=appointment.id, user_id=appointment.user_id)


@pytest.mark.asyncio
async def test_call_wrong_status(db_session, setup_appointment):
    """测试非已签到状态不能叫号"""
    from app.modules.appointments.service_flow import AppointmentFlowService

    appointment = setup_appointment
    service = AppointmentFlowService(db_session)

    # 已预约状态不能叫号
    with pytest.raises(ValueError, match="患者未签到"):
        await service.call_patient(appointment.id)


@pytest.mark.asyncio
async def test_recall_wrong_status(db_session, setup_appointment):
    """测试非过号状态不能重叫"""
    from app.modules.appointments.service_flow import AppointmentFlowService

    appointment = setup_appointment
    service = AppointmentFlowService(db_session)

    # 已签到状态不能重叫
    appointment.status = APPOINTMENT_STATUS["SIGNED"]
    await db_session.commit()

    with pytest.raises(ValueError, match="只有过号状态可以重新叫号"):
        await service.recall(appointment.id)
