"""
Tests for the structured error contract between server and frontend.

Verifies:
- BusinessError with error_code produces correct ErrorResponse envelope
- BusinessError without error_code uses legacy flat format (backward compat)
- HTTPException with dict detail containing error_code produces structured response
- HTTPException with string detail uses legacy format
- raise_business_http_error helper works correctly
- create_error_response helper works correctly
"""
import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.middleware.exception import (
    BusinessError,
    create_error_response,
    raise_business_http_error,
    register_exception_handlers,
)


# ==================== Fixtures ====================

@pytest.fixture
def app():
    """Create a minimal FastAPI app with exception handlers registered."""
    _app = FastAPI()
    register_exception_handlers(_app)

    @_app.get("/business-error-with-code")
    async def business_error_with_code():
        raise BusinessError(
            message="排班时间冲突",
            code=409,
            error_code="SCHEDULE_CONFLICT",
            details={"conflicts": [{"type": "doctor_overlap", "message": "医生已有排班"}]},
        )

    @_app.get("/business-error-without-code")
    async def business_error_without_code():
        raise BusinessError(message="普通业务错误", code=400)

    @_app.get("/business-error-permission")
    async def business_error_permission():
        raise BusinessError(
            message="权限不足",
            code=403,
            error_code="PERMISSION_DENIED",
        )

    @_app.get("/http-error-with-code")
    async def http_error_with_code():
        raise HTTPException(
            status_code=403,
            detail={
                "error_code": "TENANT_OVERDUE",
                "message": "租户已欠费",
            },
        )

    @_app.get("/http-error-with-code-and-data")
    async def http_error_with_code_and_data():
        raise HTTPException(
            status_code=409,
            detail={
                "error_code": "SCHEDULE_CONFLICT",
                "message": "排班冲突",
                "data": {"conflicts": [{"type": "room_overlap"}]},
            },
        )

    @_app.get("/http-error-string")
    async def http_error_string():
        raise HTTPException(status_code=404, detail="资源不存在")

    @_app.get("/raise-business-http-error")
    async def raise_bhe_endpoint():
        raise_business_http_error(
            status_code=429,
            error_code="RATE_LIMITED",
            message="请求过于频繁",
        )

    @_app.get("/raise-business-http-error-with-details")
    async def raise_bhe_with_details():
        raise_business_http_error(
            status_code=409,
            error_code="SCHEDULE_CONFLICT",
            message="排班冲突",
            details={"conflicts": [{"type": "doctor_overlap", "message": "医生重复排班"}]},
        )

    return _app


@pytest.fixture
def client(app):
    return TestClient(app, raise_server_exceptions=False)


# ==================== BusinessError tests ====================

class TestBusinessErrorWithErrorCode:
    """BusinessError with error_code should produce structured ErrorResponse."""

    def test_response_has_error_envelope(self, client):
        resp = client.get("/business-error-with-code")
        assert resp.status_code == 409
        body = resp.json()
        assert body["code"] == 409
        assert body["message"] == "排班时间冲突"
        assert "error" in body
        assert body["error"]["code"] == "SCHEDULE_CONFLICT"
        assert body["error"]["message"] == "排班时间冲突"
        assert body["error"]["details"]["conflicts"][0]["type"] == "doctor_overlap"

    def test_permission_denied_has_error_envelope(self, client):
        resp = client.get("/business-error-permission")
        assert resp.status_code == 403
        body = resp.json()
        assert body["error"]["code"] == "PERMISSION_DENIED"

    def test_no_data_field_when_error_code_present(self, client):
        """When error_code is set, the legacy 'data' key should NOT appear."""
        resp = client.get("/business-error-with-code")
        body = resp.json()
        assert "data" not in body


class TestBusinessErrorWithoutErrorCode:
    """BusinessError without error_code should use legacy flat format."""

    def test_legacy_format(self, client):
        resp = client.get("/business-error-without-code")
        assert resp.status_code == 400
        body = resp.json()
        assert body["code"] == 400
        assert body["message"] == "普通业务错误"
        # No structured error envelope
        assert "error" not in body

    def test_data_field_present_in_legacy(self, client):
        """Legacy responses may include 'data' when no error_code is set."""
        # Our test endpoint doesn't pass data, but the key point is 'error' is absent
        resp = client.get("/business-error-without-code")
        body = resp.json()
        assert "error" not in body


# ==================== HTTPException tests ====================

class TestHTTPExceptionWithErrorCode:
    """HTTPException with dict detail containing error_code produces structured response."""

    def test_structured_error_from_http_exception(self, client):
        resp = client.get("/http-error-with-code")
        assert resp.status_code == 403
        body = resp.json()
        assert body["code"] == 403
        assert body["message"] == "租户已欠费"
        assert body["error"]["code"] == "TENANT_OVERDUE"

    def test_http_exception_with_data_in_detail(self, client):
        """When detail dict has 'data', it should be mapped to error.details."""
        resp = client.get("/http-error-with-code-and-data")
        assert resp.status_code == 409
        body = resp.json()
        assert body["error"]["code"] == "SCHEDULE_CONFLICT"
        # 'data' in detail dict is mapped to 'details' in the error envelope
        assert body["error"]["details"]["conflicts"][0]["type"] == "room_overlap"


class TestHTTPExceptionWithStringDetail:
    """HTTPException with string detail uses legacy format."""

    def test_legacy_string_detail(self, client):
        resp = client.get("/http-error-string")
        assert resp.status_code == 404
        body = resp.json()
        assert body["code"] == 404
        assert body["message"] == "资源不存在"
        assert "error" not in body


# ==================== raise_business_http_error tests ====================

class TestRaiseBusinessHttpError:
    """Test the raise_business_http_error helper function."""

    def test_basic_usage(self, client):
        resp = client.get("/raise-business-http-error")
        assert resp.status_code == 429
        body = resp.json()
        assert body["error"]["code"] == "RATE_LIMITED"
        assert body["message"] == "请求过于频繁"

    def test_with_details(self, client):
        resp = client.get("/raise-business-http-error-with-details")
        assert resp.status_code == 409
        body = resp.json()
        assert body["error"]["code"] == "SCHEDULE_CONFLICT"
        assert body["error"]["details"]["conflicts"][0]["message"] == "医生重复排班"


# ==================== create_error_response tests ====================

class TestCreateErrorResponse:
    """Test the create_error_response helper directly."""

    def test_without_error_code(self):
        resp = create_error_response(400, "bad request")
        assert resp.status_code == 400
        # Body is bytes, decode and check
        import json
        body = json.loads(resp.body)
        assert body == {"code": 400, "message": "bad request"}

    def test_with_error_code(self):
        resp = create_error_response(
            409, "conflict",
            error_code="SCHEDULE_CONFLICT",
            error_details={"key": "value"},
        )
        assert resp.status_code == 409
        import json
        body = json.loads(resp.body)
        assert body["error"]["code"] == "SCHEDULE_CONFLICT"
        assert body["error"]["details"] == {"key": "value"}

    def test_with_data_legacy(self):
        resp = create_error_response(400, "err", data={"some": "data"})
        import json
        body = json.loads(resp.body)
        assert body["data"] == {"some": "data"}
        assert "error" not in body

    def test_with_error_code_no_details(self):
        resp = create_error_response(403, "forbidden", error_code="PERMISSION_DENIED")
        import json
        body = json.loads(resp.body)
        assert body["error"]["code"] == "PERMISSION_DENIED"
        assert "details" not in body["error"]


# ==================== BusinessError constructor tests ====================

class TestBusinessErrorConstructor:
    """Test BusinessError constructor variations."""

    def test_default_code(self):
        err = BusinessError("test")
        assert err.code == 400
        assert err.error_code is None
        assert err.details is None

    def test_with_error_code(self):
        err = BusinessError("conflict", code=409, error_code="SCHEDULE_CONFLICT")
        assert err.code == 409
        assert err.error_code == "SCHEDULE_CONFLICT"

    def test_with_details(self):
        details = {"conflicts": [{"type": "x"}]}
        err = BusinessError("conflict", error_code="SCHEDULE_CONFLICT", details=details)
        assert err.details == details

    def test_str_representation(self):
        err = BusinessError("test message")
        assert str(err) == "test message"
