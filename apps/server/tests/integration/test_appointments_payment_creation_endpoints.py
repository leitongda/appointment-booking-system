from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest

from app.api import deps
from app.main import app


def response_data(response):
    payload = response.json()
    return payload.get("data", payload)


@pytest.fixture(autouse=True)
def mock_operation_log_task():
    with patch("app.tasks.operation_log_task.save_operation_log.delay") as mock_delay:
        yield mock_delay


@pytest.mark.asyncio
async def test_create_appointment_keeps_free_path_shape(async_client, test_appointment, test_schedule, test_user):
    test_appointment.schedule = test_schedule

    async def override_get_current_user_or_admin():
        return {"id": test_user.id, "is_admin": False}

    app.dependency_overrides[deps.get_current_user_or_admin] = override_get_current_user_or_admin
    try:
        with patch(
            "app.modules.appointments.router.AppointmentService.create",
            new_callable=AsyncMock,
        ) as mock_create, patch(
            "app.core.websocket.notify_new_appointment",
            new_callable=AsyncMock,
        ):
            mock_create.return_value = test_appointment

            response = await async_client.post(
                "/api/v1/appointments",
                json={
                    "scheduleId": test_schedule.id,
                    "patientId": test_appointment.patient_id,
                    "symptomDescription": "头痛",
                },
            )
    finally:
        app.dependency_overrides.pop(deps.get_current_user_or_admin, None)

    assert response.status_code == 200
    payload = response_data(response)
    assert payload["appointmentNo"] == test_appointment.appointment_no
    assert "appointment" not in payload


@pytest.mark.asyncio
async def test_create_appointment_returns_pending_payment_payload(async_client, test_appointment, test_schedule, test_user):
    test_appointment.status = 0
    test_appointment.payment_amount = Decimal("30.00")
    test_appointment.schedule = test_schedule

    async def override_get_current_user_or_admin():
        return {"id": test_user.id, "is_admin": False}

    app.dependency_overrides[deps.get_current_user_or_admin] = override_get_current_user_or_admin
    try:
        with patch(
            "app.modules.appointments.router.AppointmentService.create",
            new_callable=AsyncMock,
        ) as mock_create, patch(
            "app.core.websocket.notify_new_appointment",
            new_callable=AsyncMock,
        ):
            mock_create.return_value = {
                "appointment": test_appointment,
                "payment_required": True,
                "payment_amount": 30.0,
                "payment_params": {
                    "time_stamp": "1234567890",
                    "nonce_str": "nonce",
                    "package": "prepay_id=test",
                    "sign_type": "RSA",
                    "pay_sign": "signed",
                },
            }

            response = await async_client.post(
                "/api/v1/appointments",
                json={
                    "scheduleId": test_schedule.id,
                    "patientId": test_appointment.patient_id,
                    "symptomDescription": "头痛",
                },
            )
    finally:
        app.dependency_overrides.pop(deps.get_current_user_or_admin, None)

    assert response.status_code == 200
    payload = response_data(response)
    assert payload["payment_required"] is True
    assert payload["payment_amount"] == 30.0
    assert payload["appointment"]["appointmentNo"] == test_appointment.appointment_no
    assert payload["payment_params"]["timeStamp"] == "1234567890"
    assert payload["payment_params"]["paySign"] == "signed"


@pytest.mark.asyncio
async def test_get_payment_params_falls_back_to_current_user_openid(
    async_client,
    db_session,
    test_appointment,
    test_user,
):
    test_appointment.status = 0
    test_appointment.payment_amount = Decimal("30.00")
    test_user.openid = "openid-from-user"
    await db_session.commit()

    async def override_get_current_user():
        return {"id": test_user.id, "is_admin": False}

    app.dependency_overrides[deps.get_current_user] = override_get_current_user
    try:
        with patch(
            "app.modules.payments.service.PaymentService.create_payment_order",
            new_callable=AsyncMock,
        ) as mock_create_payment_order:
            mock_create_payment_order.return_value = {
                "appointment_id": test_appointment.id,
                "payment_amount": 30.0,
                "time_stamp": "1234567890",
                "nonce_str": "nonce",
                "package": "prepay_id=test",
                "sign_type": "RSA",
                "pay_sign": "signed",
            }

            response = await async_client.get(
                f"/api/v1/appointments/{test_appointment.id}/payment-params",
            )
    finally:
        app.dependency_overrides.pop(deps.get_current_user, None)

    assert response.status_code == 200
    payload = response_data(response)
    assert payload["appointment_id"] == test_appointment.id
    assert payload["pay_sign"] == "signed"
    mock_create_payment_order.assert_awaited_once_with(
        appointment_id=test_appointment.id,
        openid="openid-from-user",
        miniapp_instance_id=test_appointment.payment_miniapp_instance_id,
    )
