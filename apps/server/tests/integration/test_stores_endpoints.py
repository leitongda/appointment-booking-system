from uuid import uuid4

import pytest

from app.models.store import Store


@pytest.mark.asyncio
async def test_store_by_code_public_endpoint(async_client, db_session):
    store = Store(
        id=str(uuid4()),
        name="测试门店公开",
        code="store-public-code",
        status=1,
    )
    db_session.add(store)
    await db_session.commit()

    response = await async_client.get(f"/api/v1/stores/by-code/{store.code}")

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["id"] == store.id
    assert payload["code"] == "store-public-code"
