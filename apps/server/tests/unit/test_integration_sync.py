"""第三方集成组织架构同步服务测试。

验证 sync_organization 的核心逻辑：
- 未配置集成时返回错误
- Provider 未注册时返回错误
- 正常同步：部门创建 + 成员匹配 + 绑定建立
- API 拉取失败时优雅降级

由于 sync_service 使用同步 Session，测试用同步 SQLite + mock Provider。
"""
import os
import sqlite3
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models.admin import Admin, Role
from app.models.department import Department
from app.models.integration import Integration, IntegrationBinding
from app.models.tenant import Tenant
from app.modules.integration.sync_service import sync_organization


@pytest.fixture
def sync_db():
    """创建同步 SQLite 测试数据库。"""
    # 用临时文件避免内存库在多连接下丢失数据
    fd, path = tempfile.mkstemp(suffix=".db")
    engine = create_engine(f"sqlite:///{path}")

    # JSONB 兼容（与 conftest 一致）
    from sqlalchemy.dialects.sqlite import base as sqlite_base

    if not hasattr(sqlite_base.SQLiteTypeCompiler, "visit_JSONB"):
        sqlite_base.SQLiteTypeCompiler.visit_JSONB = lambda self, type_, **kw: "JSON"

    # 去重索引（与 conftest._create_all_safe 一致，避免 lowcode 重复索引报错）
    seen_indexes = set()
    for table in Base.metadata.sorted_tables:
        deduped = set()
        for idx in table.indexes:
            if idx.name not in seen_indexes:
                seen_indexes.add(idx.name)
                deduped.add(idx)
        table.indexes = deduped
    Base.metadata.create_all(engine)

    session = Session(engine)
    # 预置租户 + 角色 + 管理员
    tenant = Tenant(
        id=str(uuid4()), tenant_code="sync_test", name="同步测试租户",
        status=1, created_at=None, updated_at=None,
    )
    session.add(tenant)
    role = Role(
        id=str(uuid4()), name="管理员", code="STORE_ADMIN",
        status=1, permissions="[]", tenant_id=tenant.id,
    )
    session.add(role)
    # 预置一个已存在的管理员（手机号匹配用）
    admin = Admin(
        id=str(uuid4()), username="existing_admin", name="张三",
        password_hash="$2b$12$test_hash_not_for_production",
        phone="13800001111", role_id=role.id, tenant_id=tenant.id, status=1,
    )
    session.add(admin)
    session.commit()

    yield session, tenant, admin

    session.close()
    engine.dispose()
    os.close(fd)
    os.unlink(path)


class TestSyncOrganization:
    """sync_organization 同步逻辑测试。"""

    def test_returns_error_when_no_integration(self, sync_db):
        """未配置集成时应返回错误且不崩溃。"""
        session, tenant, _ = sync_db
        result = sync_organization(session, tenant.id, "dingtalk")
        assert result["provider"] == "dingtalk"
        assert len(result["errors"]) > 0
        assert "未配置" in result["errors"][0]

    def test_returns_error_when_provider_not_registered(self, sync_db):
        """集成已配置但 Provider 未注册时返回错误。"""
        session, tenant, _ = sync_db
        integration = Integration(
            id=str(uuid4()), tenant_id=tenant.id, provider="dingtalk",
            name="测试", app_id="app", status=1,
        )
        session.add(integration)
        session.commit()

        with patch(
            "app.modules.integration.sync_service.get_provider", return_value=None
        ):
            result = sync_organization(session, tenant.id, "dingtalk")
        assert "未注册" in result["errors"][0]

    def test_sync_creates_departments_and_bindings(self, sync_db):
        """正常同步：创建部门 + 匹配已有成员 + 建立绑定。"""
        session, tenant, admin = sync_db
        integration = Integration(
            id=str(uuid4()), tenant_id=tenant.id, provider="dingtalk",
            name="测试", app_id="app", app_secret_ref="env:SECRET",
            status=1,
        )
        session.add(integration)
        session.commit()

        # mock Provider 返回部门和成员（异步方法用 AsyncMock）
        mock_provider = MagicMock()
        mock_provider.get_department_list = AsyncMock(
            return_value=[
                {"dept_id": "dt_dept_1", "name": "研发部", "parent_id": None},
                {"dept_id": "dt_dept_2", "name": "产品部", "parent_id": "dt_dept_1"},
            ]
        )
        mock_provider.get_department_users = AsyncMock(
            return_value=[
                # 这个成员的手机号匹配已存在的 admin
                {
                    "external_id": "dt_user_1", "name": "张三",
                    "phone": "13800001111", "email": "zhang@ex.com",
                    "dept_id": "dt_dept_1", "union_id": "union_1",
                },
                # 这个成员手机号不匹配（不会创建 admin，仅记录日志）
                {
                    "external_id": "dt_user_2", "name": "李四",
                    "phone": "13900002222", "email": "li@ex.com",
                    "dept_id": "dt_dept_1",
                },
            ]
        )

        with patch(
            "app.modules.integration.sync_service.get_provider", return_value=mock_provider
        ), patch(
            "app.common.secret_refs.resolve_secret_ref", return_value="decrypted_secret"
        ):
            result = sync_organization(session, tenant.id, "dingtalk", store_id=None)

        # 部门应被创建
        assert result["departments_created"] == 2
        depts = session.execute(
            select(Department).where(Department.tenant_id == tenant.id)
        ).scalars().all()
        assert len(depts) == 2
        dept_names = {d.name for d in depts}
        assert {"研发部", "产品部"} == dept_names

        # 父子关系应建立
        product_dept = next(d for d in depts if d.name == "产品部")
        dev_dept = next(d for d in depts if d.name == "研发部")
        assert product_dept.parent_id == dev_dept.id

        # 张三（手机号匹配）应建立绑定
        bindings = session.execute(
            select(IntegrationBinding).where(
                IntegrationBinding.tenant_id == tenant.id,
                IntegrationBinding.provider == "dingtalk",
            )
        ).scalars().all()
        assert len(bindings) == 1
        assert bindings[0].external_id == "dt_user_1"
        assert bindings[0].user_id == admin.id
        assert bindings[0].name == "张三"

    def test_sync_handles_fetch_failure_gracefully(self, sync_db):
        """API 拉取失败时应优雅降级，返回错误而非崩溃。"""
        session, tenant, _ = sync_db
        integration = Integration(
            id=str(uuid4()), tenant_id=tenant.id, provider="feishu",
            name="测试", app_id="app", status=1,
        )
        session.add(integration)
        session.commit()

        mock_provider = MagicMock()
        mock_provider.get_department_list = AsyncMock(
            side_effect=Exception("网络超时")
        )

        with patch(
            "app.modules.integration.sync_service.get_provider", return_value=mock_provider
        ):
            result = sync_organization(session, tenant.id, "feishu")

        assert result["departments_total"] == 0
        assert any("拉取组织数据失败" in e for e in result["errors"])

    def test_sync_is_idempotent_for_departments(self, sync_db):
        """重复同步不应创建重复部门。"""
        session, tenant, _ = sync_db
        integration = Integration(
            id=str(uuid4()), tenant_id=tenant.id, provider="wecom",
            name="测试", app_id="app", status=1,
        )
        session.add(integration)
        session.commit()

        mock_provider = MagicMock()
        mock_provider.get_department_list = AsyncMock(
            return_value=[{"dept_id": "wx_1", "name": "运营部", "parent_id": None}]
        )
        mock_provider.get_department_users = AsyncMock(return_value=[])

        with patch(
            "app.modules.integration.sync_service.get_provider", return_value=mock_provider
        ):
            sync_organization(session, tenant.id, "wecom")
            result2 = sync_organization(session, tenant.id, "wecom")

        # 第二次不应重复创建
        assert result2["departments_created"] == 0
        depts = session.execute(
            select(Department).where(
                Department.tenant_id == tenant.id,
                Department.name == "运营部",
            )
        ).scalars().all()
        assert len(depts) == 1
