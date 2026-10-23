"""data_scope 租户分支 fail-close 单元测试（B4 / R1-3）

- 有 tenant_id：生成 tenant_id 等值条件；
- 缺 tenant_id 且 TENANT_FILTER_FAIL_CLOSE=True：生成永假条件（查询空结果）；
- 缺 tenant_id 且开关关闭：保持旧行为（不过滤）。
"""
from sqlalchemy import false, select

from app.common.data_scope import DataScopeFilter, apply_data_scope
from app.core.config import settings
from app.models.doctor import Doctor


def _tenant_admin(tenant_id: str | None) -> dict:
    admin = {"id": "admin-1", "role": {"data_scope": {"scope_type": "tenant"}}}
    if tenant_id:
        admin["tenant_id"] = tenant_id
    return admin


def _compiled(query) -> str:
    return str(query.compile(compile_kwargs={"literal_binds": True}))


def test_tenant_scope_with_anchor_adds_tenant_condition():
    query = apply_data_scope(select(Doctor), Doctor, _tenant_admin("tenant-a"))
    sql = _compiled(query)
    assert "doctors.tenant_id = 'tenant-a'" in sql


def test_tenant_scope_missing_anchor_fail_close(monkeypatch):
    monkeypatch.setattr(settings, "TENANT_FILTER_FAIL_CLOSE", True)
    query = apply_data_scope(select(Doctor), Doctor, _tenant_admin(None))
    sql = _compiled(query)
    assert "false" in sql.lower()
    assert "tenant_id =" not in sql


def test_tenant_scope_missing_anchor_lenient_by_default(monkeypatch):
    monkeypatch.setattr(settings, "TENANT_FILTER_FAIL_CLOSE", False)
    query = apply_data_scope(select(Doctor), Doctor, _tenant_admin(None))
    sql = _compiled(query)
    assert "WHERE" not in sql


def test_tenant_scope_model_without_tenant_column_fail_close(monkeypatch):
    """模型无 tenant_id 列时同样 fail-close，而不是放行全量"""

    class NoTenantModel:
        __name__ = "NoTenantModel"

    monkeypatch.setattr(settings, "TENANT_FILTER_FAIL_CLOSE", True)
    condition = DataScopeFilter.build_filter(_tenant_admin("tenant-a"), NoTenantModel)
    assert str(condition) == str(false())


def test_all_scope_returns_none():
    admin = {"id": "admin-1", "role": {"data_scope": {"scope_type": "all"}}}
    assert DataScopeFilter.build_filter(admin, Doctor) is None


def test_store_scope_uses_current_store(monkeypatch):
    monkeypatch.setattr(settings, "TENANT_FILTER_FAIL_CLOSE", True)
    admin = {
        "id": "admin-1",
        "current_store_id": "store-1",
        "role": {"data_scope": {"scope_type": "store"}},
    }
    sql = _compiled(apply_data_scope(select(Doctor), Doctor, admin))
    assert "doctors.store_id = 'store-1'" in sql


def test_custom_scope_uses_store_ids(monkeypatch):
    monkeypatch.setattr(settings, "TENANT_FILTER_FAIL_CLOSE", True)
    admin = {
        "id": "admin-1",
        "role": {"data_scope": {"scope_type": "custom", "store_ids": ["store-1"]}},
    }
    sql = _compiled(apply_data_scope(select(Doctor), Doctor, admin))
    assert "doctors.store_id IN ('store-1')" in sql
