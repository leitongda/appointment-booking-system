import pytest

from app.api import deps
from app.main import app


@pytest.mark.asyncio
async def test_import_export_template_download(async_client):
    async def override_get_current_admin():
        return {"id": "admin-1", "is_super_admin": True, "permissions": ["*"]}

    app.dependency_overrides[deps.get_current_admin] = override_get_current_admin
    try:
        response = await async_client.get("/api/v1/data/template/doctors")
    finally:
        app.dependency_overrides.pop(deps.get_current_admin, None)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    assert "doctor_import_template.xlsx" in response.headers["content-disposition"]
    assert len(response.content) > 100
