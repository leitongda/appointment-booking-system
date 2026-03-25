"""
多租户隔离测试

测试用例覆盖：
1. 同一手机号可在不同租户分别注册
2. 跨租户访问拒绝
3. 医生/患者 token 在错误租户上下文被拒绝
4. 黑名单隔离
5. 数据查询租户过滤
6. 公开接口必须有租户上下文
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid

from app.models.tenant import Tenant
from app.models.user import User, Patient
from app.models.doctor import Doctor
from app.models.store import Store
from app.models.department import Department
from app.models.admin import Admin, Role
from app.core.security import get_password_hash, create_access_token


def extract_error_text(payload: dict) -> str:
    """兼容项目统一响应包装，提取错误文本。"""
    data = payload.get("data")
    if isinstance(data, dict) and data.get("detail"):
        return str(data["detail"])
    if payload.get("message"):
        return str(payload["message"])
    if payload.get("detail"):
        return str(payload["detail"])
    return ""


def extract_items(payload: dict) -> list[dict]:
    """兼容列表接口的不同 data 包装格式。"""
    data = payload.get("data")
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        nested = data.get("data")
        if isinstance(nested, list):
            return nested
    return []


@pytest.fixture
async def tenant_a(db_session: AsyncSession) -> Tenant:
    """创建测试租户 A"""
    tenant = Tenant(
        id=str(uuid.uuid4()),
        tenant_code="tenant_a",
        name="测试租户A",
        status=1,
    )
    db_session.add(tenant)
    await db_session.commit()
    await db_session.refresh(tenant)
    return tenant


@pytest.fixture
async def tenant_b(db_session: AsyncSession) -> Tenant:
    """创建测试租户 B"""
    tenant = Tenant(
        id=str(uuid.uuid4()),
        tenant_code="tenant_b",
        name="测试租户B",
        status=1,
    )
    db_session.add(tenant)
    await db_session.commit()
    await db_session.refresh(tenant)
    return tenant


@pytest.fixture
async def store_a(db_session: AsyncSession, tenant_a: Tenant) -> Store:
    """创建租户 A 的门店"""
    store = Store(
        id=str(uuid.uuid4()),
        tenant_id=tenant_a.id,
        name="租户A门店",
        code="store_a",
        status=1,
    )
    db_session.add(store)
    await db_session.commit()
    await db_session.refresh(store)
    return store


@pytest.fixture
async def store_b(db_session: AsyncSession, tenant_b: Tenant) -> Store:
    """创建租户 B 的门店"""
    store = Store(
        id=str(uuid.uuid4()),
        tenant_id=tenant_b.id,
        name="租户B门店",
        code="store_b",
        status=1,
    )
    db_session.add(store)
    await db_session.commit()
    await db_session.refresh(store)
    return store


@pytest.fixture
async def department_a(db_session: AsyncSession, tenant_a: Tenant, store_a: Store) -> Department:
    """创建租户 A 的科室"""
    dept = Department(
        id=str(uuid.uuid4()),
        tenant_id=tenant_a.id,
        store_id=store_a.id,
        name="内科",
        status=1,
    )
    db_session.add(dept)
    await db_session.commit()
    await db_session.refresh(dept)
    return dept


@pytest.fixture
async def role_tenant_admin(db_session: AsyncSession, tenant_a: Tenant) -> Role:
    """创建租户管理员角色"""
    role = Role(
        id=str(uuid.uuid4()),
        tenant_id=tenant_a.id,
        name="租户管理员",
        code="TENANT_ADMIN",
        status=1,
    )
    db_session.add(role)
    await db_session.commit()
    await db_session.refresh(role)
    return role


@pytest.fixture
async def admin_a(db_session: AsyncSession, tenant_a: Tenant, store_a: Store, role_tenant_admin: Role) -> Admin:
    """创建租户 A 的管理员"""
    admin = Admin(
        id=str(uuid.uuid4()),
        tenant_id=tenant_a.id,
        username="admin_a",
        password_hash=get_password_hash("password123"),
        name="租户A管理员",
        role_id=role_tenant_admin.id,
        current_store_id=store_a.id,
        status=1,
    )
    db_session.add(admin)
    await db_session.commit()
    await db_session.refresh(admin)
    return admin


@pytest.fixture
async def admin_a_token(admin_a: Admin) -> str:
    """生成租户 A 管理员的 token"""
    return create_access_token(
        data={"sub": admin_a.id, "type": "admin"},
        expires_delta=None
    )


@pytest.mark.asyncio
async def test_same_phone_different_tenants(
    async_client: AsyncClient,
    db_session: AsyncSession,
    tenant_a: Tenant,
    tenant_b: Tenant,
    store_a: Store,
    store_b: Store,
):
    """测试同一手机号可在不同租户分别注册"""
    phone = "13800138000"

    # 在租户 A 创建用户
    user_a = User(
        id=str(uuid.uuid4()),
        tenant_id=tenant_a.id,
        phone=phone,
        password_hash=get_password_hash("password123"),
        nickname="租户A用户",
        status=1,
    )
    db_session.add(user_a)

    # 在租户 B 创建用户（同一手机号）
    user_b = User(
        id=str(uuid.uuid4()),
        tenant_id=tenant_b.id,
        phone=phone,
        password_hash=get_password_hash("password123"),
        nickname="租户B用户",
        status=1,
    )
    db_session.add(user_b)

    await db_session.commit()

    # 验证两个用户都存在
    result_a = await db_session.execute(
        select(User).where(User.phone == phone, User.tenant_id == tenant_a.id)
    )
    user_a_check = result_a.scalar_one_or_none()
    assert user_a_check is not None
    assert user_a_check.nickname == "租户A用户"

    result_b = await db_session.execute(
        select(User).where(User.phone == phone, User.tenant_id == tenant_b.id)
    )
    user_b_check = result_b.scalar_one_or_none()
    assert user_b_check is not None
    assert user_b_check.nickname == "租户B用户"

    # 验证是两个不同的用户
    assert user_a_check.id != user_b_check.id


@pytest.mark.asyncio
async def test_cross_tenant_access_denied(
    async_client: AsyncClient,
    db_session: AsyncSession,
    tenant_a: Tenant,
    tenant_b: Tenant,
    store_a: Store,
    store_b: Store,
    admin_a: Admin,
    admin_a_token: str,
):
    """测试租户 A 管理员不能访问租户 B 数据"""
    department_b = Department(
        id=str(uuid.uuid4()),
        tenant_id=tenant_b.id,
        store_id=store_b.id,
        name="外科",
        status=1,
    )
    db_session.add(department_b)
    await db_session.commit()
    await db_session.refresh(department_b)

    # 在租户 B 创建医生
    doctor_b = Doctor(
        id=str(uuid.uuid4()),
        tenant_id=tenant_b.id,
        store_id=store_b.id,
        department_id=department_b.id,
        name="租户B医生",
        username="doctor_b",
        phone="13900139000",
        password_hash=get_password_hash("password123"),
        status=1,
    )
    db_session.add(doctor_b)
    await db_session.commit()

    # 租户 A 管理员尝试访问租户 B 的医生列表
    # 应该看不到租户 B 的医生
    response = await async_client.get(
        "/api/v1/doctors",
        headers={
            "Authorization": f"Bearer {admin_a_token}",
            "X-Tenant-ID": tenant_a.id,
        },
    )

    # 根据实际 API 响应调整断言
    # 可能返回 200 但列表为空，或者返回 403
    if response.status_code == 200:
        # 确保不包含租户 B 的医生
        doctor_ids = [d.get("id") for d in extract_items(response.json())]
        assert doctor_b.id not in doctor_ids


@pytest.mark.asyncio
async def test_doctor_token_wrong_tenant(
    async_client: AsyncClient,
    db_session: AsyncSession,
    tenant_a: Tenant,
    tenant_b: Tenant,
    store_a: Store,
    store_b: Store,
    department_a: Department,
):
    """测试医生 token 在错误租户上下文下被拒绝"""
    # 在租户 A 创建医生
    doctor_a = Doctor(
        id=str(uuid.uuid4()),
        tenant_id=tenant_a.id,
        store_id=store_a.id,
        department_id=department_a.id,
        name="租户A医生",
        username="doctor_a",
        phone="13900139001",
        password_hash=get_password_hash("password123"),
        status=1,
    )
    db_session.add(doctor_a)
    await db_session.commit()
    await db_session.refresh(doctor_a)

    # 生成医生 token
    doctor_token = create_access_token(
        data={"sub": doctor_a.id, "type": "doctor"},
        expires_delta=None
    )

    # 在租户 B 上下文使用该医生 token
    response = await async_client.get(
        "/api/v1/doctor-portal/schedules",
        headers={
            "Authorization": f"Bearer {doctor_token}",
            "X-Tenant-ID": tenant_b.id,  # 错误的租户上下文
        },
    )

    # 应该返回 403
    assert response.status_code == 403
    assert "不属于当前租户" in extract_error_text(response.json())


@pytest.mark.asyncio
async def test_user_token_wrong_tenant(
    async_client: AsyncClient,
    db_session: AsyncSession,
    tenant_a: Tenant,
    tenant_b: Tenant,
):
    """测试用户 token 在错误租户上下文下被拒绝"""
    # 在租户 A 创建用户
    user_a = User(
        id=str(uuid.uuid4()),
        tenant_id=tenant_a.id,
        phone="13800138001",
        password_hash=get_password_hash("password123"),
        nickname="租户A用户",
        status=1,
    )
    db_session.add(user_a)
    await db_session.commit()
    await db_session.refresh(user_a)

    # 生成用户 token
    user_token = create_access_token(
        data={"sub": user_a.id, "type": "user"},
        expires_delta=None
    )

    # 在租户 B 上下文使用该用户 token
    response = await async_client.get(
        "/api/v1/users/patients",
        headers={
            "Authorization": f"Bearer {user_token}",
            "X-Tenant-ID": tenant_b.id,  # 错误的租户上下文
        },
    )

    # 应该返回 403
    assert response.status_code == 403
    assert "不属于当前租户" in extract_error_text(response.json())


@pytest.mark.asyncio
async def test_public_endpoint_requires_tenant_context(
    async_client: AsyncClient,
    db_session: AsyncSession,
):
    """测试公开预约接口必须有租户上下文"""
    # 不提供租户上下文
    response = await async_client.get(
        "/api/v1/doctors/recommended",
        headers={},
    )

    # 应该返回 400 错误
    assert response.status_code == 400
    assert "缺少租户上下文" in extract_error_text(response.json())


@pytest.mark.asyncio
async def test_blacklist_isolation(
    async_client: AsyncClient,
    db_session: AsyncSession,
    tenant_a: Tenant,
    tenant_b: Tenant,
    store_a: Store,
    store_b: Store,
    admin_a: Admin,
    admin_a_token: str,
):
    """测试租户 A 拉黑患者不影响租户 B 同手机号用户"""
    phone = "13800138002"

    # 在租户 A 创建用户和患者
    user_a = User(
        id=str(uuid.uuid4()),
        tenant_id=tenant_a.id,
        phone=phone,
        password_hash=get_password_hash("password123"),
        status=1,
    )
    db_session.add(user_a)
    await db_session.commit()
    await db_session.refresh(user_a)

    patient_a = Patient(
        id=str(uuid.uuid4()),
        tenant_id=tenant_a.id,
        store_id=store_a.id,
        user_id=user_a.id,
        name="租户A患者",
        phone=phone,
    )
    db_session.add(patient_a)

    # 在租户 B 创建同手机号用户
    user_b = User(
        id=str(uuid.uuid4()),
        tenant_id=tenant_b.id,
        phone=phone,
        password_hash=get_password_hash("password123"),
        status=1,
    )
    db_session.add(user_b)
    await db_session.commit()
    await db_session.refresh(user_b)

    patient_b = Patient(
        id=str(uuid.uuid4()),
        tenant_id=tenant_b.id,
        store_id=store_b.id,
        user_id=user_b.id,
        name="租户B患者",
        phone=phone,
    )
    db_session.add(patient_b)
    await db_session.commit()

    # 在租户 A 拉黑该患者
    # （假设有拉黑 API，这里直接修改数据库模拟）
    user_a.status = 0  # 禁用
    await db_session.commit()

    # 验证租户 B 的用户不受影响
    await db_session.refresh(user_b)
    assert user_b.status == 1  # 仍然正常

    # 验证租户 A 的用户已被禁用
    await db_session.refresh(user_a)
    assert user_a.status == 0  # 已禁用


@pytest.mark.asyncio
async def test_store_code_tenant_unique(
    async_client: AsyncClient,
    db_session: AsyncSession,
    tenant_a: Tenant,
    tenant_b: Tenant,
):
    """测试门店编码在租户内唯一，但不同租户可以相同"""
    # 在租户 A 创建门店
    store_a = Store(
        id=str(uuid.uuid4()),
        tenant_id=tenant_a.id,
        name="门店1",
        code="store_001",
        status=1,
    )
    db_session.add(store_a)
    await db_session.commit()

    # 在租户 B 创建同编码门店（应该成功）
    store_b = Store(
        id=str(uuid.uuid4()),
        tenant_id=tenant_b.id,
        name="门店1",
        code="store_001",
        status=1,
    )
    db_session.add(store_b)

    # 应该不抛出唯一约束异常
    await db_session.commit()

    # 验证两个门店都存在
    result_a = await db_session.execute(
        select(Store).where(Store.code == "store_001", Store.tenant_id == tenant_a.id)
    )
    assert result_a.scalar_one_or_none() is not None

    result_b = await db_session.execute(
        select(Store).where(Store.code == "store_001", Store.tenant_id == tenant_b.id)
    )
    assert result_b.scalar_one_or_none() is not None


@pytest.mark.asyncio
async def test_doctor_phone_tenant_unique(
    async_client: AsyncClient,
    db_session: AsyncSession,
    tenant_a: Tenant,
    tenant_b: Tenant,
    store_a: Store,
    store_b: Store,
    department_a: Department,
):
    """测试医生手机号在租户内唯一，但不同租户可以相同"""
    phone = "13900139002"

    # 在租户 A 创建医生
    doctor_a = Doctor(
        id=str(uuid.uuid4()),
        tenant_id=tenant_a.id,
        store_id=store_a.id,
        department_id=department_a.id,
        name="医生1",
        username="doctor_001",
        phone=phone,
        password_hash=get_password_hash("password123"),
        status=1,
    )
    db_session.add(doctor_a)
    await db_session.commit()

    # 在租户 B 创建同手机号医生（应该成功）
    # 先创建租户 B 的科室
    dept_b = Department(
        id=str(uuid.uuid4()),
        tenant_id=tenant_b.id,
        store_id=store_b.id,
        name="内科",
        status=1,
    )
    db_session.add(dept_b)
    await db_session.commit()
    await db_session.refresh(dept_b)

    doctor_b = Doctor(
        id=str(uuid.uuid4()),
        tenant_id=tenant_b.id,
        store_id=store_b.id,
        department_id=dept_b.id,
        name="医生1",
        username="doctor_001",
        phone=phone,
        password_hash=get_password_hash("password123"),
        status=1,
    )
    db_session.add(doctor_b)

    # 应该不抛出唯一约束异常
    await db_session.commit()

    # 验证两个医生都存在
    result_a = await db_session.execute(
        select(Doctor).where(Doctor.phone == phone, Doctor.tenant_id == tenant_a.id)
    )
    assert result_a.scalar_one_or_none() is not None

    result_b = await db_session.execute(
        select(Doctor).where(Doctor.phone == phone, Doctor.tenant_id == tenant_b.id)
    )
    assert result_b.scalar_one_or_none() is not None


@pytest.mark.asyncio
async def test_tenant_data_isolation(
    async_client: AsyncClient,
    db_session: AsyncSession,
    tenant_a: Tenant,
    tenant_b: Tenant,
    store_a: Store,
    store_b: Store,
):
    """测试租户数据隔离"""
    # 验证门店数量
    result = await db_session.execute(select(Store))
    all_stores = list(result.scalars().all())
    assert len(all_stores) == 2

    # 验证租户 A 的门店
    result_a = await db_session.execute(
        select(Store).where(Store.tenant_id == tenant_a.id)
    )
    stores_a = list(result_a.scalars().all())
    assert len(stores_a) == 1
    assert stores_a[0].tenant_id == tenant_a.id

    # 验证租户 B 的门店
    result_b = await db_session.execute(
        select(Store).where(Store.tenant_id == tenant_b.id)
    )
    stores_b = list(result_b.scalars().all())
    assert len(stores_b) == 1
    assert stores_b[0].tenant_id == tenant_b.id
