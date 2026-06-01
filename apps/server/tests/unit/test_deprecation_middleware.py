"""
DeprecationMiddleware 单元测试
"""
from __future__ import annotations

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from starlette.responses import JSONResponse

from app.middleware.deprecation import DeprecatedEndpoint, DeprecationMiddleware


@pytest.fixture()
def app():
    """创建带 DeprecationMiddleware 的测试应用"""
    test_app = FastAPI()

    @test_app.get("/api/v1/old-feature")
    async def old_feature():
        return JSONResponse({"status": "old"})

    @test_app.get("/api/v1/new-feature")
    async def new_feature():
        return JSONResponse({"status": "new"})

    deprecated_endpoints = [
        DeprecatedEndpoint(
            path_prefix="/api/v1/old-feature",
            sunset_date="2025-12-31",
            deprecated_version="v1",
            replacement="/api/v1/new-feature",
        ),
    ]

    test_app.add_middleware(
        DeprecationMiddleware, deprecated_endpoints=deprecated_endpoints
    )

    return test_app


@pytest.mark.asyncio
async def test_deprecated_endpoint_returns_headers(app: FastAPI):
    """废弃端点应返回标准废弃头"""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get("/api/v1/old-feature")

    assert resp.status_code == 200
    assert resp.headers["deprecation"] == "true"
    assert resp.headers["sunset"] == "2025-12-31"
    assert resp.headers["x-api-deprecated-version"] == "v1"
    assert resp.headers["x-api-replacement"] == "/api/v1/new-feature"


@pytest.mark.asyncio
async def test_non_deprecated_endpoint_no_headers(app: FastAPI):
    """非废弃端点不应返回废弃头"""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get("/api/v1/new-feature")

    assert resp.status_code == 200
    assert "deprecation" not in resp.headers
    assert "sunset" not in resp.headers


@pytest.mark.asyncio
async def test_no_deprecated_endpoints_configured():
    """无废弃端点配置时，所有端点正常返回"""
    test_app = FastAPI()

    @test_app.get("/api/v1/test")
    async def test_route():
        return JSONResponse({"status": "ok"})

    test_app.add_middleware(DeprecationMiddleware)

    async with AsyncClient(
        transport=ASGITransport(app=test_app), base_url="http://test"
    ) as client:
        resp = await client.get("/api/v1/test")

    assert resp.status_code == 200
    assert "deprecation" not in resp.headers
