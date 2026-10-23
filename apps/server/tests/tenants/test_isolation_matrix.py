"""T-2：租户隔离矩阵试点（stores / doctors）

departments 条目待 P2C-7 落地后启用；其余模块随第2期各批次逐步加入注册表。
断言要求：本租户对象必须可见 + 他租户对象必须不可见（双向断言），
跨租户详情 403/404，跨租户写非 2xx 且他租户数据未被改动。
"""
import uuid
from datetime import datetime

import bcrypt
import pytest
import pytest_asyncio
from sqlalchemy import select

from app.models.department import Department
from app.models.doctor import Doctor
from app.models.store import Store
from tests.security.tenant_matrix import MATRIX_MODULES, ModuleSpec

pytestmark = [pytest.mark.security, pytest.mark.multi_tenant]

SPECS = {spec.name: spec for spec in MATRIX_MODULES}


def _auth(token: str, tenant_id: str) -> dict:
    return {"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id}


async def _create_department(db_session, tenant_id: str, store_id: str, name: str) -> Department:
    dept = Department(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        store_id=store_id,
        name=name,
        status=1,
    )
    db_session.add(dept)
    await db_session.commit()
    await db_session.refresh(dept)
    return dept


async def _create_doctor(
    db_session, tenant_id: str, store_id: str, department_id: str, name: str
) -> Doctor:
    suffix = uuid.uuid4().hex[:8]
    doctor = Doctor(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        store_id=store_id,
        department_id=department_id,
        name=name,
        username=f"matrix_doc_{suffix}",
        phone=f"134{uuid.uuid4().int % 10**8:08d}",
        password_hash=bcrypt.hashpw(uuid.uuid4().hex.encode(), bcrypt.gensalt()).decode(),
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(doctor)
    await db_session.commit()
    await db_session.refresh(doctor)
    return doctor


@pytest_asyncio.fixture
async def matrix_env(db_session, multi_tenant_env):
    """在 A/B 租户下各建一套科室与医生（stores 直接复用 multi_tenant_env）"""
    env = multi_tenant_env

    env.department_a = await _create_department(
        db_session, env.tenant_a.id, env.store_a.id, "矩阵科室A"
    )
    env.department_b = await _create_department(
        db_session, env.tenant_b.id, env.store_b.id, "矩阵科室B"
    )
    env.doctor_a = await _create_doctor(
        db_session, env.tenant_a.id, env.store_a.id, env.department_a.id, "矩阵医生A"
    )
    env.doctor_b = await _create_doctor(
        db_session, env.tenant_b.id, env.store_b.id, env.department_b.id, "矩阵医生B"
    )
    return env


def _own_and_foreign(env, module: str) -> tuple[str, str]:
    if module == "stores":
        return env.store_a.id, env.store_b.id
    if module == "doctors":
        return env.doctor_a.id, env.doctor_b.id
    raise AssertionError(f"未注册的模块: {module}")


@pytest.mark.parametrize("module", sorted(SPECS))
async def test_list_shows_only_own_tenant(
    async_client, matrix_env, admin_token_factory, module
):
    """列表：本租户对象必须可见，他租户对象必须不可见（双向断言）"""
    env = matrix_env
    spec: ModuleSpec = SPECS[module]
    own_id, foreign_id = _own_and_foreign(env, module)
    token = admin_token_factory(env.admin_a)

    response = await async_client.get(
        spec.list_path, headers=_auth(token, env.tenant_a.id)
    )
    assert response.status_code == 200, response.text

    ids = {item["id"] for item in spec.extract_items(response.json())}
    assert own_id in ids, "本租户数据必须可见"
    assert foreign_id not in ids, "他租户数据不得出现"


@pytest.mark.parametrize("module", sorted(SPECS))
async def test_cross_tenant_detail_denied(
    async_client, matrix_env, admin_token_factory, module
):
    """详情：跨租户对象返回 403/404，禁止 200+空体"""
    env = matrix_env
    spec = SPECS[module]
    _, foreign_id = _own_and_foreign(env, module)
    if not spec.detail_path:
        pytest.skip(f"{module} 无单对象详情接口")
    token = admin_token_factory(env.admin_a)

    response = await async_client.get(
        spec.detail_path.format(id=foreign_id),
        headers=_auth(token, env.tenant_a.id),
    )
    assert response.status_code in spec.cross_status, response.text


@pytest.mark.parametrize("module", sorted(SPECS))
async def test_cross_tenant_write_denied(
    async_client, db_session, matrix_env, admin_token_factory, module
):
    """写：跨租户更新非 2xx，且目标数据未被改动"""
    env = matrix_env
    spec = SPECS[module]
    _, foreign_id = _own_and_foreign(env, module)
    if not spec.write_path:
        pytest.skip(f"{module} 无写接口")
    token = admin_token_factory(env.admin_a)

    response = await async_client.put(
        spec.write_path.format(id=foreign_id),
        headers=_auth(token, env.tenant_a.id),
        json={"name": "越权改写"},
    )
    assert not response.is_success, response.text

    if module == "stores":
        stored = await db_session.get(Store, foreign_id)
    else:
        stored = await db_session.get(Doctor, foreign_id)
    assert stored is not None
    assert stored.name != "越权改写"
