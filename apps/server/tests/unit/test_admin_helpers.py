import json
from types import SimpleNamespace

from app.modules.admin.helpers import build_admin_response, parse_permissions


def test_parse_permissions_handles_invalid_json():
    role = SimpleNamespace(permissions="{bad-json")
    assert parse_permissions(role) == []


def test_build_admin_response_maps_store_fields_and_flags():
    role = SimpleNamespace(code="SUPER_ADMIN", name="超级管理员", permissions=json.dumps(["*"]))
    current_store = SimpleNamespace(id="store-1", name="总院", logo="logo.png", theme_style="light")
    admin = SimpleNamespace(
        id="admin-1",
        username="root",
        name="管理员",
        phone="13800000000",
        email="root@example.com",
        avatar=None,
        role_id="role-1",
        role=role,
        current_store=current_store,
        current_store_id="store-1",
        stores=[current_store],
        status=1,
        last_login_at=None,
        last_login_ip=None,
        created_at="2026-03-10T00:00:00",
    )

    response = build_admin_response(admin)

    assert response.current_store_id == "store-1"
    assert response.store_id == "store-1"
    assert response.is_super_admin is True
    assert response.can_view_all_stores is True
    assert response.stores[0].name == "总院"
