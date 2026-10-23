"""P2A-1：统一租户锚点解析函数单测"""
import pytest
from fastapi import HTTPException

from app.common.tenant_deps import resolve_actor_tenant_anchor
from app.middleware.tenant_context import clear_tenant_context, set_tenant_context


@pytest.mark.unit
class TestResolveActorTenantAnchor:
    """管理员/患者两类 actor 的锚点语义"""

    def test_platform_admin_returns_none(self):
        assert resolve_actor_tenant_anchor({"is_super_admin": True}) is None
        assert resolve_actor_tenant_anchor({"is_platform_admin": True}) is None

    def test_tenant_admin_returns_own_tenant(self):
        actor = {
            "is_super_admin": False,
            "is_platform_admin": False,
            "is_tenant_admin": True,
            "tenant_id": "tenant-1",
        }
        assert resolve_actor_tenant_anchor(actor) == "tenant-1"

    def test_tenant_admin_without_tenant_is_403(self):
        actor = {
            "is_super_admin": False,
            "is_platform_admin": False,
            "is_store_admin": True,
            "tenant_id": None,
        }
        with pytest.raises(HTTPException) as exc_info:
            resolve_actor_tenant_anchor(actor)
        assert exc_info.value.status_code == 403

    def test_patient_uses_request_context(self):
        set_tenant_context("tenant-context")
        try:
            assert resolve_actor_tenant_anchor({"role_type": "user"}) == "tenant-context"
        finally:
            clear_tenant_context()

    @pytest.mark.parametrize("fail_close", [True, False])
    def test_patient_without_context_obeys_switch(self, monkeypatch, fail_close):
        from app.core.config import settings

        clear_tenant_context()
        monkeypatch.setattr(settings, "PATIENT_ANCHOR_FAIL_CLOSE", fail_close)
        if fail_close:
            with pytest.raises(HTTPException) as exc_info:
                resolve_actor_tenant_anchor({"role_type": "user"})
            assert exc_info.value.status_code == 400
        else:
            assert resolve_actor_tenant_anchor({"role_type": "user"}) is None
