"""低代码后端接口回归测试。"""

from __future__ import annotations

from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.main import app
from app.models.account import Account
from app.models.lowcode_page import LowCodePage
from app.models.lowcode_template import LowCodeTemplate

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


def _admin_override(account_id: str, tenant_id: str, permissions: list[str]):
    async def _override():
        return {
            "id": account_id,
            "tenant_id": tenant_id,
            "is_admin": True,
            "is_super_admin": False,
            "permissions": permissions,
        }

    return _override


def _unwrap_data(payload: dict) -> dict:
    if "code" in payload and "data" in payload:
        return payload["data"]
    return payload


async def _create_account(db: AsyncSession, tenant_id: str) -> Account:
    account = Account(
        id=str(uuid4()),
        tenant_id=tenant_id,
        username=f"lowcode-admin-{uuid4().hex[:8]}",
        password_hash="test",
        name="低代码测试管理员",
        status=1,
    )
    db.add(account)
    await db.commit()
    await db.refresh(account)
    return account


async def _create_page(
    db: AsyncSession,
    tenant_id: str,
    *,
    name: str = "接口回归页面",
    slug: str | None = None,
    status: int = 0,
    schema_data: dict | None = None,
) -> LowCodePage:
    page = LowCodePage(
        id=str(uuid4()),
        tenant_id=tenant_id,
        name=name,
        slug=slug or f"lowcode-regression-{uuid4().hex[:8]}",
        status=status,
        schema_data=schema_data or {"componentName": "Page", "props": {}, "children": []},
    )
    db.add(page)
    await db.commit()
    await db.refresh(page)
    return page


async def test_batch_status_endpoint_updates_pages(
    async_client: AsyncClient,
    db_session: AsyncSession,
    test_tenant,
):
    account = await _create_account(db_session, test_tenant.id)
    first = await _create_page(db_session, test_tenant.id, name="批量页面 A")
    second = await _create_page(db_session, test_tenant.id, name="批量页面 B")

    app.dependency_overrides[deps.get_current_admin] = _admin_override(
        account.id,
        test_tenant.id,
        ["lowcode:page:update"],
    )
    try:
        response = await async_client.post(
            "/api/v1/lowcode/pages/batch-status",
            params={"target_status": 2},
            json=[first.id, second.id],
        )
    finally:
        app.dependency_overrides.pop(deps.get_current_admin, None)

    assert response.status_code == 200
    assert _unwrap_data(response.json())["updated"] == 2

    await db_session.refresh(first)
    await db_session.refresh(second)
    assert first.status == 2
    assert second.status == 2


async def test_export_page_endpoint_returns_schema_json(
    async_client: AsyncClient,
    db_session: AsyncSession,
    test_tenant,
):
    account = await _create_account(db_session, test_tenant.id)
    page = await _create_page(
        db_session,
        test_tenant.id,
        slug="exportable-page",
        schema_data={
            "componentName": "Page",
            "props": {},
            "children": [{"componentName": "Text", "props": {}}],
        },
    )

    app.dependency_overrides[deps.get_current_admin] = _admin_override(
        account.id,
        test_tenant.id,
        ["lowcode:page:read"],
    )
    try:
        response = await async_client.get(f"/api/v1/lowcode/pages/{page.id}/export")
    finally:
        app.dependency_overrides.pop(deps.get_current_admin, None)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert 'filename="exportable-page.json"' in response.headers["content-disposition"]

    exported = response.json()
    assert exported["tenant_id"] == test_tenant.id
    assert exported["slug"] == "exportable-page"
    assert exported["schema_data"]["children"][0]["componentName"] == "Text"


async def test_publish_page_with_nested_data_binding_requires_advanced_feature(
    async_client: AsyncClient,
    db_session: AsyncSession,
    test_tenant,
    monkeypatch,
):
    account = await _create_account(db_session, test_tenant.id)
    page = await _create_page(
        db_session,
        test_tenant.id,
        schema_data={
            "componentName": "Page",
            "props": {},
            "children": [
                {
                    "componentName": "Container",
                    "props": {},
                    "children": [
                        {
                            "componentName": "Text",
                            "props": {},
                            "dataBinding": {"sourceId": "appointments", "field": "name"},
                        }
                    ],
                }
            ],
        },
    )

    async def _disabled(_db, tenant_id: str, feature_name: str) -> bool:
        assert tenant_id == test_tenant.id
        assert feature_name == "lowcode_advanced_components"
        return False

    monkeypatch.setattr(
        "app.modules.lowcode.feature_gate.FeatureFlagService.is_enabled",
        _disabled,
    )
    app.dependency_overrides[deps.get_current_admin] = _admin_override(
        account.id,
        test_tenant.id,
        ["lowcode:page:publish"],
    )
    try:
        response = await async_client.post(f"/api/v1/lowcode/pages/{page.id}/publish")
    finally:
        app.dependency_overrides.pop(deps.get_current_admin, None)

    assert response.status_code == 403
    await db_session.refresh(page)
    assert page.status == 0


async def test_publish_to_marketplace_creates_template_without_page_status_three(
    async_client: AsyncClient,
    db_session: AsyncSession,
    test_tenant,
    monkeypatch,
):
    account = await _create_account(db_session, test_tenant.id)
    page = await _create_page(
        db_session,
        test_tenant.id,
        status=0,
        schema_data={
            "componentName": "Page",
            "props": {},
            "dataSources": [
                {
                    "id": "appointments",
                    "url": "https://api.example.test/list",
                    "method": "GET",
                }
            ],
            "children": [],
        },
    )

    async def _enabled(_db, tenant_id: str, feature_name: str) -> bool:
        assert tenant_id == test_tenant.id
        assert feature_name == "lowcode_marketplace"
        return True

    monkeypatch.setattr(
        "app.modules.lowcode.feature_gate.FeatureFlagService.is_enabled",
        _enabled,
    )
    app.dependency_overrides[deps.get_current_admin] = _admin_override(
        account.id,
        test_tenant.id,
        ["lowcode:marketplace:publish"],
    )
    try:
        response = await async_client.post(
            f"/api/v1/lowcode/pages/{page.id}/publish-to-marketplace",
            json={
                "name": "预约列表模板",
                "category": "预约挂号",
                "shortDescription": "短描述",
                "description": "用于预约列表的市场模板",
                "tags": ["预约", "列表"],
                "thumbnailUrl": "https://example.test/thumbnail.png",
                "isPublic": True,
            },
        )
    finally:
        app.dependency_overrides.pop(deps.get_current_admin, None)

    assert response.status_code == 200
    data = _unwrap_data(response.json())
    assert data["id"] == page.id

    await db_session.refresh(page)
    assert page.status == 0

    result = await db_session.execute(
        select(LowCodeTemplate).where(LowCodeTemplate.source_page_id == page.id)
    )
    template = result.scalar_one()
    assert template.name == "预约列表模板"
    assert template.category == "预约挂号"
    assert template.is_public is True
    assert template.created_by == account.id


async def test_public_template_detail_sanitizes_datasource_secrets(
    async_client: AsyncClient,
    db_session: AsyncSession,
    test_tenant,
):
    account = await _create_account(db_session, test_tenant.id)
    template = LowCodeTemplate(
        id=str(uuid4()),
        source_tenant_id=test_tenant.id,
        name="公开脱敏模板",
        description="公开模板不应暴露后端数据源地址和请求头",
        category="表单收集",
        tags=["公开"],
        schema_data={
            "componentName": "Page",
            "props": {},
            "dataSources": [
                {
                    "id": "patients",
                    "name": "患者列表",
                    "method": "GET",
                    "url": "https://internal.example.test/patients",
                    "headers": {"Authorization": "Bearer secret"},
                }
            ],
            "children": [
                {
                    "componentName": "List",
                    "props": {
                        "api": "https://internal.example.test/patients",
                        "children": [],
                    },
                }
            ],
        },
        data_sources=[
            {
                "id": "patients",
                "method": "GET",
                "url": "https://internal.example.test/patients",
                "headers": {"Authorization": "Bearer secret"},
                "dataPath": "data.items",
            }
        ],
        version="1.0.0",
        is_public=True,
        status=1,
        created_by=account.id,
    )
    db_session.add(template)
    await db_session.commit()

    response = await async_client.get(f"/api/v1/lowcode/templates/{template.id}")

    assert response.status_code == 200
    data = _unwrap_data(response.json())

    schema_source = data["schemaData"]["dataSources"][0]
    assert schema_source["id"] == "patients"
    assert "url" not in schema_source
    assert "headers" not in schema_source

    list_props = data["schemaData"]["children"][0]["props"]
    assert "api" not in list_props

    datasource = data["dataSources"][0]
    assert datasource["id"] == "patients"
    assert datasource["dataPath"] == "data.items"
    assert "url" not in datasource
    assert "headers" not in datasource
