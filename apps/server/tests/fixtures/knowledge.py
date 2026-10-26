"""知识库测试共用 fixture：同租户三个普通管理员 + 一个 manage 管理员 + 另一租户管理员

A：owner（knowledge:read/create/update/delete/share）
B：同事，与 A 同权限码，用于共享级别矩阵
C：只读角色（knowledge:read），用于按角色共享
M：治理者（knowledge:read/update/manage）
X：另一租户，用于跨租户 404
"""
import json
from dataclasses import dataclass
from datetime import datetime
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

import app.infrastructure.storage as storage_module
import app.modules.knowledge.service_base as service_base_module
from app.core.config import settings
from app.core.security import create_access_token
from app.models.admin import Admin, Role
from app.models.tenant import SubscriptionPlan, Tenant

KB_FULL = ["knowledge:read", "knowledge:create", "knowledge:update", "knowledge:delete", "knowledge:share"]
KB_READ = ["knowledge:read"]
KB_MANAGE = ["knowledge:read", "knowledge:update", "knowledge:manage"]


def auth(admin: Admin) -> dict[str, str]:
    token = create_access_token({"sub": admin.id, "type": "admin"})
    return {"Authorization": f"Bearer {token}"}


async def make_role(db: AsyncSession, tenant_id: str | None, code: str, permissions: list[str]) -> Role:
    role = Role(
        id=str(uuid4()),
        name=code,
        code=code,
        tenant_id=tenant_id,
        status=1,
        role_type="admin",
        permissions=json.dumps(permissions),
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db.add(role)
    await db.flush()
    return role


async def make_admin(db: AsyncSession, tenant_id: str | None, role: Role, username: str) -> Admin:
    admin = Admin(
        id=str(uuid4()),
        username=username,
        password_hash="not-used-in-tests",
        name=username,
        role_id=role.id,
        tenant_id=tenant_id,
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db.add(admin)
    await db.flush()
    return admin


async def make_tenant(db: AsyncSession, code: str) -> Tenant:
    plan = SubscriptionPlan(
        id=str(uuid4()), plan_code=f"plan_{code}", name=f"计划 {code}", status=1,
        created_at=datetime.now(), updated_at=datetime.now(),
    )
    db.add(plan)
    await db.flush()
    tenant = Tenant(
        id=str(uuid4()), tenant_code=code, name=f"租户 {code}", status=1, subscription_plan_id=plan.id,
        created_at=datetime.now(), updated_at=datetime.now(),
    )
    db.add(tenant)
    await db.flush()
    return tenant


@dataclass
class KnowledgeEnv:
    tenant: Tenant
    other_tenant: Tenant
    owner: Admin
    colleague: Admin
    reader: Admin
    reader_role: Role
    manager: Admin
    outsider: Admin
    enqueued: list[str]

    def h(self, admin: Admin) -> dict[str, str]:
        return auth(admin)


@pytest.fixture
def kb_settings(monkeypatch, tmp_path):
    """开启知识库、本地存储指向临时目录、重置存储单例、处理任务改为记录而不投递"""
    monkeypatch.setattr(settings, "KB_ENABLED", True)
    monkeypatch.setattr(settings, "STORAGE_TYPE", "local")
    monkeypatch.setattr(settings, "LOCAL_UPLOAD_DIR", str(tmp_path / "uploads"))
    monkeypatch.setattr(settings, "KB_TMP_DIR", str(tmp_path / "kb-tmp"))
    monkeypatch.setattr(storage_module, "_storage_instance", None)
    enqueued: list[str] = []
    monkeypatch.setattr(service_base_module, "enqueue_process_document", enqueued.append)
    yield enqueued
    monkeypatch.setattr(storage_module, "_storage_instance", None)


@pytest_asyncio.fixture
async def kb_env(db_session: AsyncSession, test_tenant: Tenant, kb_settings) -> KnowledgeEnv:
    role_full = await make_role(db_session, test_tenant.id, "KB_FULL", KB_FULL)
    role_read = await make_role(db_session, test_tenant.id, "KB_READ", KB_READ)
    role_manage = await make_role(db_session, test_tenant.id, "KB_MANAGE", KB_MANAGE)
    owner = await make_admin(db_session, test_tenant.id, role_full, "kb_owner")
    colleague = await make_admin(db_session, test_tenant.id, role_full, "kb_colleague")
    reader = await make_admin(db_session, test_tenant.id, role_read, "kb_reader")
    manager = await make_admin(db_session, test_tenant.id, role_manage, "kb_manager")

    other_tenant = await make_tenant(db_session, "kb_other")
    other_role = await make_role(db_session, other_tenant.id, "KB_FULL_OTHER", KB_FULL)
    outsider = await make_admin(db_session, other_tenant.id, other_role, "kb_outsider")
    await db_session.commit()

    return KnowledgeEnv(
        tenant=test_tenant,
        other_tenant=other_tenant,
        owner=owner,
        colleague=colleague,
        reader=reader,
        reader_role=role_read,
        manager=manager,
        outsider=outsider,
        enqueued=kb_settings,
    )
