from datetime import datetime
from io import BytesIO
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from app.api import deps
from app.main import app
from app.models.department import Department


@pytest.mark.asyncio
async def test_department_tree_public_endpoint(async_client, db_session):
    department = Department(
        id=str(uuid4()),
        name="公开科室",
        status=1,
        sort_order=1,
    )
    db_session.add(department)
    await db_session.commit()

    response = await async_client.get("/api/v1/departments/tree")

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload[0]["name"] == "公开科室"


@pytest.mark.asyncio
async def test_export_patients_endpoint(async_client):
    async def override_get_current_admin():
        return {"id": "admin-1", "is_super_admin": True, "permissions": ["*"]}

    app.dependency_overrides[deps.get_current_admin] = override_get_current_admin
    try:
        with patch("app.modules.export.router.ExportService.export_patients", new_callable=AsyncMock) as mock_export:
            mock_export.return_value = (b"excel-data", "patients.xlsx")
            response = await async_client.get("/api/v1/export/patients")
    finally:
        app.dependency_overrides.pop(deps.get_current_admin, None)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    assert "patients.xlsx" in response.headers["content-disposition"]
