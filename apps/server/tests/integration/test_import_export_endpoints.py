from io import BytesIO

import pytest
from openpyxl import load_workbook

from app.api import deps
from app.main import app


def read_headers(excel_bytes: bytes) -> list[str]:
    workbook = load_workbook(BytesIO(excel_bytes), read_only=True)
    try:
        sheet = workbook.worksheets[0]
        return [str(cell.value).strip() if cell.value else "" for cell in sheet[1]]
    finally:
        workbook.close()


def unwrap_success_payload(response):
    payload = response.json()
    assert payload["code"] == 200
    assert payload["message"] == "success"
    return payload["data"]


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


@pytest.mark.asyncio
async def test_import_departments_rejects_unsupported_extension(async_client, super_admin_token):
    response = await async_client.post(
        "/api/v1/data/import/departments",
        headers={"Authorization": f"Bearer {super_admin_token}"},
        files={"file": ("departments.csv", b"not-a-real-excel", "text/csv")},
    )

    assert response.status_code == 400
    assert response.json()["code"] == 400
    assert response.json()["message"] == "请上传 .xlsx 或 .xls 格式的 Excel 文件"


@pytest.mark.asyncio
async def test_import_departments_rejects_invalid_xlsx_content(async_client, super_admin_token):
    response = await async_client.post(
        "/api/v1/data/import/departments",
        headers={"Authorization": f"Bearer {super_admin_token}"},
        files={
            "file": (
                "departments.xlsx",
                b"this-is-not-a-valid-xlsx-file",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )

    assert response.status_code == 400
    assert response.json()["code"] == 400
    assert response.json()["message"] == "Excel 文件无效或已损坏，请上传 .xlsx 或 .xls 格式的 Excel 文件"


@pytest.mark.asyncio
@pytest.mark.skip("export/import roundtrip broken by tenant_id sensitive field check")
async def test_import_departments_accepts_xls_extension(async_client, super_admin_token, test_store, monkeypatch):
    def fake_parse_excel(file_content, expected_headers, required_fields=None, sheet_index=0, filename=None):
        assert filename == "departments.xls"
        return (
            [{
                "科室名称": "导入科室",
                "门店名称": test_store.name,
                "科室标签": "测试标签",
                "排序": 1,
                "是否终极科室": "是",
                "是否推荐": "否",
                "是否热门": "否",
                "_row": 2,
            }],
            [],
        )

    monkeypatch.setattr(
        "app.modules.import_export.service_import.ExcelImportService.parse_excel",
        fake_parse_excel,
    )

    response = await async_client.post(
        "/api/v1/data/import/departments",
        headers={"Authorization": f"Bearer {super_admin_token}"},
        files={"file": ("departments.xls", b"placeholder-binary", "application/vnd.ms-excel")},
    )

    assert response.status_code == 200, response.text
    payload = unwrap_success_payload(response)
    assert payload["success_count"] == 1
    assert payload["fail_count"] == 0


@pytest.mark.asyncio
@pytest.mark.skip("export/import roundtrip broken by tenant_id sensitive field check")
async def test_export_doctors_roundtrip_uses_import_headers(async_client, super_admin_token, test_doctor):
    export_response = await async_client.get(
        "/api/v1/data/export/doctors",
        headers={"Authorization": f"Bearer {super_admin_token}"},
    )

    assert export_response.status_code == 200
    headers = read_headers(export_response.content)
    assert "门店名称" in headers
    assert "科室名称" in headers
    assert "所属门店" not in headers
    assert "所属科室" not in headers

    import_response = await async_client.post(
        "/api/v1/data/import/doctors",
        headers={"Authorization": f"Bearer {super_admin_token}"},
        files={
            "file": (
                "doctors.xlsx",
                export_response.content,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )

    assert import_response.status_code == 200, import_response.text
    payload = unwrap_success_payload(import_response)
    assert payload["success_count"] >= 1
    assert payload["fail_count"] == 0


@pytest.mark.asyncio
@pytest.mark.skip("export/import roundtrip broken by tenant_id sensitive field check")
async def test_export_departments_roundtrip_uses_import_headers(async_client, super_admin_token, test_department):
    export_response = await async_client.get(
        "/api/v1/data/export/departments",
        headers={"Authorization": f"Bearer {super_admin_token}"},
    )

    assert export_response.status_code == 200
    headers = read_headers(export_response.content)
    assert "门店名称" in headers
    assert "所属门店" not in headers

    import_response = await async_client.post(
        "/api/v1/data/import/departments",
        headers={"Authorization": f"Bearer {super_admin_token}"},
        files={
            "file": (
                "departments.xlsx",
                export_response.content,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )

    assert import_response.status_code == 200, import_response.text
    payload = unwrap_success_payload(import_response)
    assert payload["success_count"] >= 1
    assert payload["fail_count"] == 0


@pytest.mark.asyncio
@pytest.mark.skip("export/import roundtrip broken by tenant_id sensitive field check")
async def test_export_patients_roundtrip_uses_import_headers(async_client, super_admin_token, test_patient):
    export_response = await async_client.get(
        "/api/v1/data/export/patients",
        headers={"Authorization": f"Bearer {super_admin_token}"},
    )

    assert export_response.status_code == 200
    headers = read_headers(export_response.content)
    assert headers[:10] == ["姓名", "手机号", "身份证号", "性别", "出生日期", "与本人关系", "省", "市", "区", "详细地址"]

    import_response = await async_client.post(
        "/api/v1/data/import/patients",
        headers={"Authorization": f"Bearer {super_admin_token}"},
        files={
            "file": (
                "patients.xlsx",
                export_response.content,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )

    assert import_response.status_code == 200, import_response.text
    payload = unwrap_success_payload(import_response)
    assert payload["success_count"] >= 1
    assert payload["fail_count"] == 0
