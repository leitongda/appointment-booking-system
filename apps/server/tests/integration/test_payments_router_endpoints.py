import json
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
import pytest_asyncio

from app.core.security import create_access_token
from app.models.appointment import Appointment
from app.models.schedule import Schedule
from app.models.store import Store
from app.models.user import Patient, User


def response_data(response):
    payload = response.json()
    return payload.get("data", payload)


def response_message(response):
    payload = response.json()
    return payload.get("message") or payload.get("detail")


@pytest.fixture(autouse=True)
def mock_operation_log_task():
    with patch("app.tasks.operation_log_task.save_operation_log.delay") as mock_delay:
        yield mock_delay


@pytest_asyncio.fixture
async def another_store(db_session, test_tenant):
    store = Store(
        id=str(uuid4()),
        name="另一家门店",
        address="另一家门店地址",
        phone="13800138123",
        tenant_id=test_tenant.id,
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(store)
    await db_session.commit()
    await db_session.refresh(store)
    return store


@pytest_asyncio.fixture
async def another_user(db_session, test_tenant):
    user = User(
        id=str(uuid4()),
        phone="13800138124",
        password_hash="$2b$12$test_hash_not_for_production",
        nickname="另一位用户",
        tenant_id=test_tenant.id,
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def another_patient(db_session, test_tenant, another_user):
    patient = Patient(
        id=str(uuid4()),
        user_id=another_user.id,
        name="另一位就诊人",
        phone="13800138125",
        id_card="110101199101011234",
        is_default=True,
        tenant_id=test_tenant.id,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(patient)
    await db_session.commit()
    await db_session.refresh(patient)
    return patient


@pytest_asyncio.fixture
async def another_schedule(db_session, test_tenant, test_doctor, another_store):
    schedule = Schedule(
        id=str(uuid4()),
        doctor_id=test_doctor.id,
        store_id=another_store.id,
        tenant_id=test_tenant.id,
        schedule_date=date.today() + timedelta(days=2),
        time_slot="afternoon",
        start_time=time(13, 0),
        end_time=time(17, 0),
        total_slots=10,
        booked_slots=0,
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(schedule)
    await db_session.commit()
    await db_session.refresh(schedule)
    return schedule


@pytest_asyncio.fixture
async def another_appointment(
    db_session,
    test_tenant,
    another_schedule,
    another_patient,
    test_doctor,
    another_user,
):
    appointment = Appointment(
        id=str(uuid4()),
        appointment_no=f"YY{datetime.now().strftime('%Y%m%d%H%M%S')}{str(uuid4())[:4].upper()}",
        user_id=another_user.id,
        patient_id=another_patient.id,
        doctor_id=test_doctor.id,
        schedule_id=another_schedule.id,
        tenant_id=test_tenant.id,
        queue_number=2,
        status=0,
        patient_name=another_patient.name,
        patient_phone=another_patient.phone,
        doctor_name=test_doctor.name,
        doctor_title=test_doctor.title,
        department_name="测试科室",
        payment_amount=Decimal("30.00"),
        created_at=datetime.now(),
        updated_at=datetime.now(),
        created_by=another_user.id,
    )
    db_session.add(appointment)
    another_schedule.booked_slots += 1
    await db_session.commit()
    await db_session.refresh(appointment)
    return appointment


@pytest.mark.asyncio
async def test_create_payment_order_requires_auth(async_client, test_appointment):
    response = await async_client.post(
        "/api/v1/payments/orders",
        json={"appointment_id": test_appointment.id, "openid": "openid-1"},
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_create_payment_order_rejects_non_owner(async_client, test_user, another_appointment):
    token = create_access_token({"sub": test_user.id})

    response = await async_client.post(
        "/api/v1/payments/orders",
        headers={"Authorization": f"Bearer {token}"},
        json={"appointment_id": another_appointment.id, "openid": "openid-1"},
    )

    assert response.status_code == 403
    assert response_message(response) == "无权操作此预约"


@pytest.mark.asyncio
async def test_create_payment_order_allows_owner(async_client, db_session, test_user, test_appointment):
    test_appointment.status = 0
    test_appointment.payment_amount = Decimal("30.00")
    await db_session.commit()

    token = create_access_token({"sub": test_user.id})

    with patch(
        "app.modules.payments.router.PaymentService.create_payment_order",
        new_callable=AsyncMock,
    ) as mock_create_payment_order:
        mock_create_payment_order.return_value = {
            "appointment_id": test_appointment.id,
            "payment_amount": Decimal("30.00"),
            "time_stamp": "1234567890",
            "nonce_str": "nonce",
            "package": "prepay_id=test",
            "sign_type": "RSA",
            "pay_sign": "sign",
        }

        response = await async_client.post(
            "/api/v1/payments/orders",
            headers={"Authorization": f"Bearer {token}"},
            json={"appointment_id": test_appointment.id, "openid": "openid-1"},
        )

    assert response.status_code == 200
    payload = response_data(response)
    assert payload["appointment_id"] == test_appointment.id
    mock_create_payment_order.assert_awaited_once_with(
        appointment_id=test_appointment.id,
        openid="openid-1",
        miniapp_instance_id=None,
    )


@pytest.mark.asyncio
async def test_get_payment_order_status_requires_auth(async_client, test_appointment):
    response = await async_client.get(f"/api/v1/payments/orders/{test_appointment.id}")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_payment_order_status_rejects_non_owner(async_client, test_user, another_appointment):
    token = create_access_token({"sub": test_user.id})

    response = await async_client.get(
        f"/api/v1/payments/orders/{another_appointment.id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403
    assert response_message(response) == "无权操作此预约"


@pytest.mark.asyncio
async def test_get_payment_order_status_allows_owner(async_client, test_user, test_appointment):
    token = create_access_token({"sub": test_user.id})

    response = await async_client.get(
        f"/api/v1/payments/orders/{test_appointment.id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response_data(response)
    assert payload["appointment_id"] == test_appointment.id
    assert payload["status"] == test_appointment.status


@pytest.mark.asyncio
async def test_get_payment_order_status_rejects_cross_store_admin(
    async_client,
    db_session,
    store_admin_token,
    test_store_admin_role,
    another_appointment,
):
    test_store_admin_role.permissions = json.dumps(["appointment:detail"])
    await db_session.commit()

    response = await async_client.get(
        f"/api/v1/payments/orders/{another_appointment.id}",
        headers={"Authorization": f"Bearer {store_admin_token}"},
    )

    assert response.status_code == 403
    assert response_message(response) == "您无权操作此门店的预约"


@pytest.mark.asyncio
async def test_create_refund_requires_auth(async_client, test_appointment):
    response = await async_client.post(
        "/api/v1/payments/refunds",
        json={"appointment_id": test_appointment.id, "refund_amount": "10.00", "reason": "用户申请"},
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_create_refund_rejects_admin_without_permission(
    async_client,
    store_admin_token,
    test_appointment,
):
    response = await async_client.post(
        "/api/v1/payments/refunds",
        headers={"Authorization": f"Bearer {store_admin_token}"},
        json={"appointment_id": test_appointment.id, "refund_amount": "10.00", "reason": "用户申请"},
    )

    assert response.status_code == 403
    assert response_message(response) == "需要权限: appointment:refund"


@pytest.mark.asyncio
async def test_create_refund_rejects_patient_actor(async_client, test_user, test_appointment):
    token = create_access_token({"sub": test_user.id})

    response = await async_client.post(
        "/api/v1/payments/refunds",
        headers={"Authorization": f"Bearer {token}"},
        json={"appointment_id": test_appointment.id, "refund_amount": "10.00", "reason": "用户申请"},
    )

    assert response.status_code == 403
    assert response_message(response) == "需要管理员权限"


@pytest.mark.asyncio
async def test_create_refund_rejects_cross_store_admin_even_with_permission(
    async_client,
    db_session,
    store_admin_token,
    test_store_admin_role,
    another_appointment,
):
    test_store_admin_role.permissions = json.dumps(["appointment:refund"])
    await db_session.commit()

    response = await async_client.post(
        "/api/v1/payments/refunds",
        headers={"Authorization": f"Bearer {store_admin_token}"},
        json={"appointment_id": another_appointment.id, "refund_amount": "10.00", "reason": "用户申请"},
    )

    assert response.status_code == 403
    assert response_message(response) == "您无权操作此门店的预约"


@pytest.mark.asyncio
async def test_create_refund_allows_super_admin(async_client, super_admin_token, test_appointment):
    with patch(
        "app.modules.payments.router.PaymentService.create_refund",
        new_callable=AsyncMock,
    ) as mock_create_refund:
        mock_create_refund.return_value = {
            "appointment_id": test_appointment.id,
            "refund_amount": Decimal("10.00"),
            "refund_status": "pending",
            "refund_id": "refund-1",
            "out_refund_no": "refund-no-1",
        }

        response = await async_client.post(
            "/api/v1/payments/refunds",
            headers={"Authorization": f"Bearer {super_admin_token}"},
            json={"appointment_id": test_appointment.id, "refund_amount": "10.00", "reason": "用户申请"},
        )

    assert response.status_code == 200
    payload = response_data(response)
    assert payload["appointment_id"] == test_appointment.id
    mock_create_refund.assert_awaited_once_with(
        appointment_id=test_appointment.id,
        refund_amount=Decimal("10.00"),
        reason="用户申请",
    )
