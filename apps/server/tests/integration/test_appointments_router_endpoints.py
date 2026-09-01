import json
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
import pytest_asyncio

from app.api import deps
from app.core.security import create_access_token
from app.main import app
from app.models.appointment import Appointment
from app.models.schedule import Schedule
from app.models.store import Store
from app.models.user import Patient
from app.models.user import User


def response_data(response):
    payload = response.json()
    return payload.get("data", payload)


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
        status=1,
        patient_name=another_patient.name,
        patient_phone=another_patient.phone,
        doctor_name=test_doctor.name,
        doctor_title=test_doctor.title,
        department_name="测试科室",
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
async def test_appointments_statistics_endpoint(async_client):
    async def override_get_current_user_or_admin():
        return {"id": "admin-1", "is_super_admin": True, "permissions": ["appointment:statistics"]}

    app.dependency_overrides[deps.get_current_user_or_admin] = override_get_current_user_or_admin
    try:
        response = await async_client.get("/api/v1/appointments/query/statistics")
    finally:
        app.dependency_overrides.pop(deps.get_current_user_or_admin, None)

    assert response.status_code == 200
    payload = response.json()["data"]
    assert "total" in payload
    assert "completed" in payload


@pytest.mark.asyncio
async def test_appointments_queue_info_requires_doctor(async_client):
    async def override_get_current_user_or_admin():
        return {"id": "user-1", "is_admin": False}

    app.dependency_overrides[deps.get_current_user_or_admin] = override_get_current_user_or_admin
    try:
        response = await async_client.get("/api/v1/appointments/query/queue/info")
    finally:
        app.dependency_overrides.pop(deps.get_current_user_or_admin, None)

    assert response.status_code == 403
    assert "需要医生权限" in response.text


@pytest.mark.asyncio
async def test_appointments_query_allows_admin_large_page_size_with_date_range(async_client):
    async def override_get_current_user_or_admin():
        return {"id": "admin-1", "is_admin": True, "is_super_admin": True, "permissions": ["*"]}

    app.dependency_overrides[deps.get_current_user_or_admin] = override_get_current_user_or_admin
    try:
        response = await async_client.get(
            "/api/v1/appointments/query",
            params={
                "page": 1,
                "page_size": 500,
                "start_date": "2026-04-01",
                "end_date": "2026-04-16",
            },
        )
    finally:
        app.dependency_overrides.pop(deps.get_current_user_or_admin, None)

    assert response.status_code == 200
    payload = response.json()
    assert payload["code"] == 200


@pytest.mark.asyncio
async def test_appointments_query_rejects_non_admin_large_page_size(async_client):
    async def override_get_current_user_or_admin():
        return {"id": "user-1", "is_admin": False}

    app.dependency_overrides[deps.get_current_user_or_admin] = override_get_current_user_or_admin
    try:
        response = await async_client.get(
            "/api/v1/appointments/query",
            params={
                "page": 1,
                "page_size": 200,
                "start_date": "2026-04-01",
                "end_date": "2026-04-16",
            },
        )
    finally:
        app.dependency_overrides.pop(deps.get_current_user_or_admin, None)

    assert response.status_code == 422
    payload = response.json()
    assert payload["message"] == "page_size 超过 100 时仅管理员可请求，当前 page_size=200，普通用户上限为 100"


@pytest.mark.asyncio
async def test_appointments_query_requires_date_range_for_admin_large_page_size(async_client):
    async def override_get_current_user_or_admin():
        return {"id": "admin-1", "is_admin": True, "is_super_admin": True, "permissions": ["*"]}

    app.dependency_overrides[deps.get_current_user_or_admin] = override_get_current_user_or_admin
    try:
        response = await async_client.get(
            "/api/v1/appointments/query",
            params={"page": 1, "page_size": 200},
        )
    finally:
        app.dependency_overrides.pop(deps.get_current_user_or_admin, None)

    assert response.status_code == 422
    payload = response.json()
    assert payload["message"] == "page_size 超过 100 时必须同时提供 start_date 和 end_date，请补充日期范围以限制查询数据量"


@pytest.mark.asyncio
async def test_appointments_query_rejects_page_size_above_config_limit(async_client):
    async def override_get_current_user_or_admin():
        return {"id": "admin-1", "is_admin": True, "is_super_admin": True, "permissions": ["*"]}

    app.dependency_overrides[deps.get_current_user_or_admin] = override_get_current_user_or_admin
    try:
        response = await async_client.get(
            "/api/v1/appointments/query",
            params={
                "page": 1,
                "page_size": 501,
                "start_date": "2026-04-01",
                "end_date": "2026-04-16",
            },
        )
    finally:
        app.dependency_overrides.pop(deps.get_current_user_or_admin, None)

    assert response.status_code == 422
    payload = response.json()
    assert "page_size" in payload["message"]
    assert "500" in payload["message"]


@pytest.mark.asyncio
async def test_appointments_query_includes_payment_fields(async_client, db_session, test_appointment):
    test_appointment.payment_amount = Decimal("30.00")
    test_appointment.payment_transaction_id = "txn-123"
    test_appointment.refund_status = "partial_refunded"
    test_appointment.refund_amount = Decimal("5.00")
    await db_session.commit()

    async def override_get_current_user_or_admin():
        return {"id": test_appointment.user_id, "is_admin": False}

    app.dependency_overrides[deps.get_current_user_or_admin] = override_get_current_user_or_admin
    try:
        response = await async_client.get("/api/v1/appointments/query", params={"page": 1, "page_size": 20})
    finally:
        app.dependency_overrides.pop(deps.get_current_user_or_admin, None)

    assert response.status_code == 200
    page_payload = response_data(response)
    items = page_payload["data"] if isinstance(page_payload, dict) else page_payload
    appointment = next(item for item in items if item["id"] == test_appointment.id)
    assert appointment["paymentAmount"] == 30.0
    assert appointment["paymentTransactionId"] == "txn-123"
    assert appointment["refundStatus"] == "partial_refunded"
    assert appointment["refundedAmount"] == 5.0


@pytest.mark.asyncio
async def test_get_appointment_detail_rejects_non_owner(async_client, test_user, another_appointment):
    token = create_access_token({"sub": test_user.id})

    response = await async_client.get(
        f"/api/v1/appointments/query/{another_appointment.id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403
    assert response.json()["message"] == "无权查看此预约"


@pytest.mark.asyncio
async def test_get_appointment_detail_rejects_cross_store_admin(
    async_client,
    db_session,
    store_admin_token,
    test_store_admin_role,
    another_appointment,
):
    test_store_admin_role.permissions = json.dumps(["appointment:detail"])
    await db_session.commit()

    response = await async_client.get(
        f"/api/v1/appointments/query/{another_appointment.id}",
        headers={"Authorization": f"Bearer {store_admin_token}"},
    )

    assert response.status_code == 403
    assert response.json()["message"] == "您无权查看此门店的预约"


@pytest.mark.asyncio
async def test_get_appointment_by_no_rejects_cross_store_admin(
    async_client,
    db_session,
    store_admin_token,
    test_store_admin_role,
    another_appointment,
):
    test_store_admin_role.permissions = json.dumps(["appointment:detail"])
    await db_session.commit()

    response = await async_client.get(
        f"/api/v1/appointments/query/by-no/{another_appointment.appointment_no}",
        headers={"Authorization": f"Bearer {store_admin_token}"},
    )

    assert response.status_code == 403
    assert response.json()["message"] == "您无权查看此门店的预约"


@pytest.mark.asyncio
async def test_get_appointment_detail_includes_store_and_checkin_fields(
    async_client,
    db_session,
    test_user,
    test_appointment,
):
    from app.models.rule_set import AppointmentCheckin

    checkin_log = AppointmentCheckin(
        id=str(uuid4()),
        appointment_id=test_appointment.id,
        checkin_method="QR_CODE",
        status="SUCCESS",
        checkin_time=datetime.now(),
    )
    db_session.add(checkin_log)
    test_appointment.sign_in_time = datetime.now()
    await db_session.commit()

    token = create_access_token({"sub": test_user.id})
    response = await async_client.get(
        f"/api/v1/appointments/query/{test_appointment.id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response_data(response)
    assert payload["storeName"] == "测试门店"
    assert payload["checkInMethod"] == "QR_CODE"


@pytest.mark.asyncio
async def test_get_payment_params_uses_bound_user_openid(async_client, db_session, test_user, test_appointment):
    test_user.openid = "user-openid-1"
    test_appointment.status = 0
    test_appointment.payment_amount = Decimal("30.00")
    await db_session.commit()

    token = create_access_token({"sub": test_user.id})

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
            "pay_sign": "sign",
        }

        response = await async_client.get(
            f"/api/v1/appointments/{test_appointment.id}/payment-params",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200
    payload = response_data(response)
    assert payload["appointment_id"] == test_appointment.id
    mock_create_payment_order.assert_awaited_once_with(
        appointment_id=test_appointment.id,
        openid="user-openid-1",
        miniapp_instance_id=test_appointment.payment_miniapp_instance_id,
    )


@pytest.mark.asyncio
async def test_get_payment_params_rejects_non_owner(async_client, db_session, test_tenant, test_appointment):
    another_user = User(
        id=str(uuid4()),
        phone="13800139009",
        password_hash="$2b$12$test_hash_not_for_production",
        nickname="其他用户",
        tenant_id=test_tenant.id,
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(another_user)
    test_appointment.status = 0
    test_appointment.payment_amount = Decimal("30.00")
    await db_session.commit()

    token = create_access_token({"sub": another_user.id})

    response = await async_client.get(
        f"/api/v1/appointments/{test_appointment.id}/payment-params",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403
    payload = response.json()
    assert payload["message"] == "无权操作此预约"


@pytest.mark.asyncio
async def test_get_payment_params_rejects_non_pending_appointment(async_client, db_session, test_user, test_appointment):
    test_user.openid = "user-openid-2"
    test_appointment.status = 1
    test_appointment.payment_amount = Decimal("30.00")
    await db_session.commit()

    token = create_access_token({"sub": test_user.id})

    response = await async_client.get(
        f"/api/v1/appointments/{test_appointment.id}/payment-params",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 400
    payload = response.json()
    assert "当前状态不支持支付" in payload["message"]


@pytest.mark.asyncio
async def test_check_duplicate_endpoint_rejects_foreign_patient(async_client, db_session, test_tenant, test_schedule, test_user):
    another_user = User(
        id=str(uuid4()),
        phone="13800139010",
        password_hash="$2b$12$test_hash_not_for_production",
        nickname="其他用户",
        tenant_id=test_tenant.id,
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    another_patient = Patient(
        id=str(uuid4()),
        user_id=another_user.id,
        name="其他就诊人",
        phone="13800139011",
        id_card="110101199001019999",
        is_default=True,
        tenant_id=test_tenant.id,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add_all([another_user, another_patient])
    await db_session.commit()

    token = create_access_token({"sub": test_user.id})
    response = await async_client.get(
        "/api/v1/appointments/query/check-duplicate",
        params={"schedule_id": test_schedule.id, "patient_id": another_patient.id},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403
    payload = response.json()
    assert payload["message"] == "无权查询该就诊人"


@pytest.mark.asyncio
@pytest.mark.skip("requires PostgreSQL partial unique index; SQLite enforces unconditional unique on (doctor_id, schedule_date, time_slot)")
async def test_check_duplicate_endpoint_includes_pending_own_appointment(
    async_client,
    db_session,
    test_tenant,
    test_schedule,
    test_doctor,
    test_store,
    test_user,
    test_patient,
):
    # 使用不同的 time_slot 以避免 SQLite 中部分唯一索引的约束冲突
    # （postgresql_where 子句在 SQLite 中被忽略，导致索引变为无条件唯一）
    duplicate_schedule = Schedule(
        id=str(uuid4()),
        doctor_id=test_doctor.id,
        store_id=test_store.id,
        tenant_id=test_tenant.id,
        schedule_date=test_schedule.schedule_date,
        time_slot="afternoon",
        start_time=time(10, 0),
        end_time=time(11, 0),
        total_slots=10,
        booked_slots=1,
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    duplicate_appointment = Appointment(
        id=str(uuid4()),
        appointment_no=f"YY{datetime.now().strftime('%Y%m%d%H%M%S')}{str(uuid4())[:4].upper()}",
        user_id=test_user.id,
        patient_id=test_patient.id,
        doctor_id=test_doctor.id,
        schedule_id=duplicate_schedule.id,
        tenant_id=test_tenant.id,
        queue_number=1,
        status=0,
        patient_name=test_patient.name,
        patient_phone=test_patient.phone,
        doctor_name=test_doctor.name,
        doctor_title=test_doctor.title,
        department_name="测试科室",
        created_at=datetime.now(),
        updated_at=datetime.now(),
        created_by=test_user.id,
    )
    db_session.add_all([duplicate_schedule, duplicate_appointment])
    await db_session.commit()

    token = create_access_token({"sub": test_user.id})
    response = await async_client.get(
        "/api/v1/appointments/query/check-duplicate",
        params={"schedule_id": test_schedule.id, "patient_id": test_patient.id},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response_data(response)
    assert payload["hasDuplicate"] is True
    assert payload["appointments"][0]["id"] == duplicate_appointment.id
