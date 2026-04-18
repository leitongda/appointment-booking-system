from uuid import uuid4

import pytest

from app.models.admin import Permission
from app.modules.admin.permission_metadata import (
    infer_permission_control_type,
    infer_permission_control_type_for_seed,
    normalize_control_type,
)
from app.modules.admin.service_permissions import PermissionService


@pytest.mark.unit
def test_infer_permission_control_type_matches_expected_categories():
    assert infer_permission_control_type("dashboard", "menu", depth=0) == "page"
    assert infer_permission_control_type("system:role", "button", depth=1, has_children=True) == "tab"
    assert infer_permission_control_type("system:role:permission", "button", depth=2) == "action"
    assert infer_permission_control_type("appointment:detail", "button", depth=1) == "api"
    assert infer_permission_control_type("schedule:statistics", "button", depth=1) == "api"


@pytest.mark.unit
def test_infer_permission_control_type_for_seed_uses_parent_hierarchy():
    permissions = [
        {"code": "system", "type": "menu", "parent_code": None},
        {"code": "system:role", "type": "button", "parent_code": "system"},
        {"code": "system:role:permission", "type": "button", "parent_code": "system:role"},
    ]

    assert infer_permission_control_type_for_seed(permissions[0], permissions) == "page"
    assert infer_permission_control_type_for_seed(permissions[1], permissions) == "tab"
    assert infer_permission_control_type_for_seed(permissions[2], permissions) == "action"


@pytest.mark.unit
def test_normalize_control_type_rejects_unknown_values():
    assert normalize_control_type("page") == "page"
    assert normalize_control_type("api") == "api"
    assert normalize_control_type("unknown") is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_permission_service_create_resolves_nested_control_type(db_session):
    service = PermissionService(db_session)

    root = Permission(
        id=str(uuid4()),
        code="system",
        name="系统设置",
        type="menu",
        control_type="page",
        parent_code=None,
        sort=1,
    )
    parent = Permission(
        id=str(uuid4()),
        code="system:role",
        name="角色管理",
        type="button",
        control_type="tab",
        parent_code="system",
        sort=1,
    )
    db_session.add_all([root, parent])
    await db_session.commit()

    permission = await service.create(
        {
            "code": "system:role:permission",
            "name": "分配权限",
            "type": "button",
            "parent_code": "system:role",
            "sort": 1,
        }
    )

    assert permission.control_type == "action"
