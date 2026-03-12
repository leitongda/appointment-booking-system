import pytest


@pytest.mark.asyncio
async def test_consultation_fee_types_endpoint(async_client):
    response = await async_client.get("/api/v1/consultation-fees/types")

    assert response.status_code == 200
    assert response.json()["data"] == []
