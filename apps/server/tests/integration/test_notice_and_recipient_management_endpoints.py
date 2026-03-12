from datetime import datetime
from unittest.mock import patch
from uuid import uuid4

import pytest

from app.api import deps
from app.main import app
from app.models.booking_notice import BookingNotice
from app.models.store import Store
from app.models.store_email_recipient import StoreEmailRecipient


async def _override_get_current_admin():
    return {
        "id": "admin-1",
        "is_admin": True,
        "is_super_admin": True,
        "permissions": ["*"],
    }


@pytest.mark.asyncio
async def test_booking_notice_management_endpoints(async_client, db_session):
    seeded_notice = BookingNotice(
        id=str(uuid4()),
        type="BOOKING",
        title="种子须知",
        content="种子内容",
        sort_order=1,
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(seeded_notice)
    await db_session.commit()

    app.dependency_overrides[deps.get_current_admin] = _override_get_current_admin
    try:
        with patch("app.tasks.operation_log_task.save_operation_log") as mock_task:
            mock_task.delay.return_value = None
            list_response = await async_client.get("/api/v1/booking-notices")
            detail_response = await async_client.get(f"/api/v1/booking-notices/{seeded_notice.id}")
            create_response = await async_client.post(
                "/api/v1/booking-notices",
                json={
                    "type": "VISIT",
                    "title": "新须知",
                    "content": "created",
                    "sortOrder": 2,
                    "status": 1,
                },
            )
            created_id = create_response.json()["data"]["id"]
            update_response = await async_client.put(
                f"/api/v1/booking-notices/{created_id}",
                json={
                    "title": "更新须知",
                    "content": "updated",
                    "sortOrder": 3,
                },
            )
            status_response = await async_client.patch(
                f"/api/v1/booking-notices/{created_id}/status",
                params={"status": 0},
            )
            delete_response = await async_client.delete(f"/api/v1/booking-notices/{created_id}")
    finally:
        app.dependency_overrides.pop(deps.get_current_admin, None)

    assert list_response.status_code == 200
    assert list_response.json()["data"]["data"][0]["title"] == "种子须知"

    assert detail_response.status_code == 200
    assert detail_response.json()["data"]["id"] == seeded_notice.id

    assert create_response.status_code == 201
    assert create_response.json()["data"]["title"] == "新须知"

    assert update_response.status_code == 200
    assert update_response.json()["data"]["title"] == "更新须知"
    assert update_response.json()["data"]["sortOrder"] == 3

    assert status_response.status_code == 200
    assert status_response.json()["data"]["status"] == 0

    assert delete_response.status_code == 204


@pytest.mark.asyncio
async def test_store_email_recipient_management_endpoints(async_client, db_session):
    store = Store(
        id=str(uuid4()),
        name="测试门店",
        code="store-code",
        address="测试地址",
        phone="13800138000",
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    recipient = StoreEmailRecipient(
        id=str(uuid4()),
        store_id=store.id,
        name="种子接收人",
        email="seed@example.com",
        event_types='["APPOINTMENT_CREATED"]',
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add_all([store, recipient])
    await db_session.commit()

    app.dependency_overrides[deps.get_current_admin] = _override_get_current_admin
    try:
        with patch("app.tasks.operation_log_task.save_operation_log") as mock_task:
            mock_task.delay.return_value = None
            list_response = await async_client.get("/api/v1/store-email-recipients")
            detail_response = await async_client.get(
                f"/api/v1/store-email-recipients/{recipient.id}"
            )
            create_response = await async_client.post(
                "/api/v1/store-email-recipients",
                json={
                    "storeId": store.id,
                    "name": "新接收人",
                    "email": "new@example.com",
                    "eventTypes": ["APPOINTMENT_CREATED", "CHECKIN"],
                    "status": 1,
                },
            )
            created_id = create_response.json()["data"]["id"]
            update_response = await async_client.put(
                f"/api/v1/store-email-recipients/{created_id}",
                json={
                    "name": "更新接收人",
                    "email": "updated@example.com",
                    "eventTypes": ["CHECKIN"],
                    "status": 0,
                },
            )
            delete_response = await async_client.delete(
                f"/api/v1/store-email-recipients/{created_id}"
            )
    finally:
        app.dependency_overrides.pop(deps.get_current_admin, None)

    assert list_response.status_code == 200
    assert list_response.json()["data"]["data"][0]["name"] == "种子接收人"

    assert detail_response.status_code == 200
    assert detail_response.json()["data"]["id"] == recipient.id

    assert create_response.status_code == 200
    assert create_response.json()["data"]["name"] == "新接收人"
    assert create_response.json()["data"]["storeId"] == store.id

    assert update_response.status_code == 200
    assert update_response.json()["data"]["name"] == "更新接收人"
    assert update_response.json()["data"]["status"] == 0
    assert update_response.json()["data"]["eventTypes"] == ["CHECKIN"]

    assert delete_response.status_code == 200
    assert delete_response.json()["data"]["message"] == "删除成功"
