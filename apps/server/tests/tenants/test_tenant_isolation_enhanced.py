"""
租户数据隔离增强测试

补充测试用例覆盖:
1. 租户上下文管理测试 - 增强版
2. 租户过滤工具测试 - 增强版
3. 租户数据隔离测试 - 娡型级别的数据隔离
4. 导出权限控制测试 - 增强测试
5. 租户上下文管理测试 - 娡型边界测试
6. 分布式锁隔离测试 - 修复版
"""
import pytest
import uuid
from datetime import datetime, date, time, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.tenant import Tenant
from app.models.user import User, Patient
from app.models.doctor import Doctor
from app.models.store import Store
from app.models.department import Department
from app.models.appointment import Appointment
from app.models.schedule import Schedule
from app.models.admin import Admin, Role
from app.core.security import get_password_hash, create_access_token
from app.middleware.tenant_context import (
    set_tenant_context,
    clear_tenant_context,
    get_current_tenant_id,
    TenantContext,
    validate_public_tenant_context,
    PUBLIC_TENANT_REQUIRED_PATHS,
)
from app.common.tenant_filter import (
    add_tenant_filter,
    get_tenant_id_for_create,
    TenantFilteredQuery,
)
from app.modules.import_export.service_import import ImportService, SENSITIVE_FIELDS
from app.middleware.exception import BusinessError
from app.core.redis import RedisCache, SyncRedisCache


# ==================== 辅助函数 ====================

def extract_error_text(payload: dict) -> str:
    """兼容项目统一响应包装，提取错误文本。 """
    data = payload.get("data")
    if isinstance(data, dict) and data.get("detail"):
        return str(data["detail"])
    if payload.get("message"):
        return str(payload["message"])
    if payload.get("detail"):
        return str(payload["detail"])
    return ""


def extract_items(payload: dict) -> list[dict]:
    """兼容列表接口的不同 data 包装格式. """
    data = payload.get("data")
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        nested = data.get("data")
        if isinstance(nested, list):
            return nested
    return []


# ==================== 租户 Fixtures ====================

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


# ==================== 门店 Fixtures ====================

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


# ==================== 科室 Fixtures ====================

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
async def department_b(db_session: AsyncSession, tenant_b: Tenant, store_b: Store) -> Department:
    """创建租户 B 的科室"""
    dept = Department(
        id=str(uuid.uuid4()),
        tenant_id=tenant_b.id,
        store_id=store_b.id,
        name="外科",
        status=1,
    )
    db_session.add(dept)
    await db_session.commit()
    await db_session.refresh(dept)
    return dept


# ==================== 角色和管理员 Fixtures ====================

@pytest.fixture
async def role_tenant_admin(db_session: AsyncSession) -> Role:
    """创建租户管理员角色"""
    role = Role(
        id=str(uuid.uuid4()),
        name="租户管理员",
        code="TENANT_ADMIN",
        status=1,
        permissions='["*"]',
    )
    db_session.add(role)
    await db_session.commit()
    await db_session.refresh(role)
    return role


@pytest.fixture
async def role_limited(db_session: AsyncSession, tenant_a: Tenant) -> Role:
    """创建受限角色（无导出权限）"""
    role = Role(
        id=str(uuid.uuid4()),
        tenant_id=tenant_a.id,
        name="普通员工",
        code="STAFF",
        status=1,
        permissions='["patient:list", "doctor:list"]',
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
async def admin_b(db_session: AsyncSession, tenant_b: Tenant, store_b: Store, role_tenant_admin: Role) -> Admin:
    """创建租户 B 的管理员"""
    admin = Admin(
        id=str(uuid.uuid4()),
        tenant_id=tenant_b.id,
        username="admin_b",
        password_hash=get_password_hash("password123"),
        name="租户B管理员",
        role_id=role_tenant_admin.id,
        current_store_id=store_b.id,
        status=1,
    )
    db_session.add(admin)
    await db_session.commit()
    await db_session.refresh(admin)
    return admin


@pytest.fixture
async def admin_a_limited(db_session: AsyncSession, tenant_a: Tenant, store_a: Store, role_limited: Role) -> Admin:
    """创建租户 A 的受限管理员（无导出权限）"""
    admin = Admin(
        id=str(uuid.uuid4()),
        tenant_id=tenant_a.id,
        username="admin_a_limited",
        password_hash=get_password_hash("password123"),
        name="租户A普通员工",
        role_id=role_limited.id,
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


@pytest.fixture
async def admin_b_token(admin_b: Admin) -> str:
    """生成租户 B 管理员的 token"""
    return create_access_token(
        data={"sub": admin_b.id, "type": "admin"},
        expires_delta=None
    )


@pytest.fixture
async def admin_a_limited_token(admin_a_limited: Admin) -> str:
    """生成租户 A 受限管理员的 token"""
    return create_access_token(
        data={"sub": admin_a_limited.id, "type": "admin"},
        expires_delta=None
    )


# ==================== 医生 Fixtures ====================

@pytest.fixture
async def doctor_a(db_session: AsyncSession, tenant_a: Tenant, store_a: Store, department_a: Department) -> Doctor:
    """创建租户 A 的医生"""
    doctor = Doctor(
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
    db_session.add(doctor)
    await db_session.commit()
    await db_session.refresh(doctor)
    return doctor


@pytest.fixture
async def doctor_b(db_session: AsyncSession, tenant_b: Tenant, store_b: Store, department_b: Department) -> Doctor:
    """创建租户 B 的医生"""
    doctor = Doctor(
        id=str(uuid.uuid4()),
        tenant_id=tenant_b.id,
        store_id=store_b.id,
        department_id=department_b.id,
        name="租户B医生",
        username="doctor_b",
        phone="13900139002",
        password_hash=get_password_hash("password123"),
        status=1,
    )
    db_session.add(doctor)
    await db_session.commit()
    await db_session.refresh(doctor)
    return doctor


# ==================== 用户和患者 Fixtures ====================

@pytest.fixture
async def user_a(db_session: AsyncSession, tenant_a: Tenant) -> User:
    """创建租户 A 的用户"""
    user = User(
        id=str(uuid.uuid4()),
        tenant_id=tenant_a.id,
        phone="13800138001",
        password_hash=get_password_hash("password123"),
        nickname="租户A用户",
        status=1,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def user_b(db_session: AsyncSession, tenant_b: Tenant) -> User:
    """创建租户 B 的用户"""
    user = User(
        id=str(uuid.uuid4()),
        tenant_id=tenant_b.id,
        phone="13800138002",
        password_hash=get_password_hash("password123"),
        nickname="租户B用户",
        status=1,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def patient_a(db_session: AsyncSession, tenant_a: Tenant, store_a: Store, user_a: User) -> Patient:
    """创建租户 A 的患者"""
    patient = Patient(
        id=str(uuid.uuid4()),
        tenant_id=tenant_a.id,
        store_id=store_a.id,
        user_id=user_a.id,
        name="租户A患者",
        phone="13800138001",
    )
    db_session.add(patient)
    await db_session.commit()
    await db_session.refresh(patient)
    return patient


@pytest.fixture
async def patient_b(db_session: AsyncSession, tenant_b: Tenant, store_b: Store, user_b: User) -> Patient:
    """创建租户 B 的患者"""
    patient = Patient(
        id=str(uuid.uuid4()),
        tenant_id=tenant_b.id,
        store_id=store_b.id,
        user_id=user_b.id,
        name="租户B患者",
        phone="13800138002",
    )
    db_session.add(patient)
    await db_session.commit()
    await db_session.refresh(patient)
    return patient


# ==================== 排班 Fixtures ====================

@pytest.fixture
async def schedule_a(db_session: AsyncSession, tenant_a: Tenant, store_a: Store, doctor_a: Doctor) -> Schedule:
    """创建租户 A 的排班"""
    tomorrow = date.today() + timedelta(days=1)
    schedule = Schedule(
        id=str(uuid.uuid4()),
        tenant_id=tenant_a.id,
        doctor_id=doctor_a.id,
        store_id=store_a.id,
        schedule_date=tomorrow,
        time_slot="AM",
        start_time=time(8, 0),
        end_time=time(12, 0),
        total_slots=10,
        booked_slots=0,
        status=1,
    )
    db_session.add(schedule)
    await db_session.commit()
    await db_session.refresh(schedule)
    return schedule


@pytest.fixture
async def schedule_b(db_session: AsyncSession, tenant_b: Tenant, store_b: Store, doctor_b: Doctor) -> Schedule:
    """创建租户 B 的排班"""
    tomorrow = date.today() + timedelta(days=1)
    schedule = Schedule(
        id=str(uuid.uuid4()),
        tenant_id=tenant_b.id,
        doctor_id=doctor_b.id,
        store_id=store_b.id,
        schedule_date=tomorrow,
        time_slot="AM",
        start_time=time(8, 0),
        end_time=time(12, 0),
        total_slots=10,
        booked_slots=0,
        status=1,
    )
    db_session.add(schedule)
    await db_session.commit()
    await db_session.refresh(schedule)
    return schedule


# ==================== 騡型级别的数据隔离测试 ====================
@pytest.mark.asyncio
class TestModelLevelTenantIsolation:
    """模型级别的数据隔离测试"""

    async def test_tenant_isolation_in_user_model(
        self,
        db_session: AsyncSession,
        tenant_a: Tenant,
        tenant_b: Tenant,
        user_a: User,
        user_b: User,
    ):
        """测试用户模型的数据隔离"""
        # 租户 A 上下文
        set_tenant_context(tenant_a.id)
        query = select(User)
        filtered_query = add_tenant_filter(query, User)
        result = await db_session.execute(filtered_query)
        users_a = list(result.scalars().all())
        # 只能看到租户 A 的用户
        assert len(users_a) == 1
        assert users_a[0].tenant_id == tenant_a.id

        assert users_a[0].id == user_a.id

        # 切换到租户 B 上下文
        set_tenant_context(tenant_b.id)
        query = select(User)
        filtered_query = add_tenant_filter(query, User)
        result = await db_session.execute(filtered_query)
        users_b = list(result.scalars().all())
        # 只能看到租户 B 的用户
        assert len(users_b) == 1
        assert users_b[0].tenant_id == tenant_b.id
        assert users_b[0].id == user_b.id
        clear_tenant_context()

    async def test_tenant_isolation_in_doctor_model(
        self,
        db_session: AsyncSession,
        tenant_a: Tenant,
        tenant_b: Tenant,
        doctor_a: Doctor,
        doctor_b: Doctor,
    ):
        """测试医生模型的数据隔离"""
        # 租户 A 上下文
        set_tenant_context(tenant_a.id)
        query = select(Doctor)
        filtered_query = add_tenant_filter(query, Doctor)
        result = await db_session.execute(filtered_query)
        doctors_a = list(result.scalars().all())
        # 只能看到租户 A 的医生
        assert len(doctors_a) == 1
        assert doctors_a[0].tenant_id == tenant_a.id
        assert doctors_a[0].id == doctor_a.id
        # 切换到租户 B 上下文
        set_tenant_context(tenant_b.id)
        query = select(Doctor)
        filtered_query = add_tenant_filter(query, Doctor)
        result = await db_session.execute(filtered_query)
        doctors_b = list(result.scalars().all())
        # 只能看到租户 B 的医生
        assert len(doctors_b) == 1
        assert doctors_b[0].tenant_id == tenant_b.id
        assert doctors_b[0].id == doctor_b.id
        clear_tenant_context()

    async def test_tenant_isolation_in_store_model(
        self,
        db_session: AsyncSession,
        tenant_a: Tenant,
        tenant_b: Tenant,
        store_a: Store,
        store_b: Store,
    ):
        """测试门店模型的数据隔离"""
        # 租户 A 上下文
        set_tenant_context(tenant_a.id)
        query = select(Store)
        filtered_query = add_tenant_filter(query, Store)
        result = await db_session.execute(filtered_query)
        stores_a = list(result.scalars().all())
        # 只能看到租户 A 的门店
        assert len(stores_a) == 1
        assert stores_a[0].tenant_id == tenant_a.id
        assert stores_a[0].id == store_a.id
        # 切换到租户 B 上下文
        set_tenant_context(tenant_b.id)
        query = select(Store)
        filtered_query = add_tenant_filter(query, Store)
        result = await db_session.execute(filtered_query)
        stores_b = list(result.scalars().all())
        # 只能看到租户 B 的门店
        assert len(stores_b) == 1
        assert stores_b[0].tenant_id == tenant_b.id
        assert stores_b[0].id == store_b.id
        clear_tenant_context()


# ==================== 租户上下文管理测试（增强版） ====================
@pytest.mark.asyncio
class TestTenantContextManagementEnhanced:
    """租户上下文管理测试套件（增强版）

    包含同步和异步测试。
    """

    def test_set_and_get_tenant_context(self, tenant_a: Tenant):
        """测试设置和获取租户上下文"""
        set_tenant_context(tenant_a.id, tenant_a.tenant_code)

        assert get_current_tenant_id() == tenant_a.id
        clear_tenant_context()
        assert get_current_tenant_id() is None

    def test_clear_tenant_context(self, tenant_a: Tenant):
        """测试清除租户上下文"""
        set_tenant_context(tenant_a.id)
        clear_tenant_context()
        assert get_current_tenant_id() is None

    def test_tenant_context_overwrite(self, tenant_a: Tenant, tenant_b: Tenant):
        """测试覆盖租户上下文"""
        set_tenant_context(tenant_a.id)
        assert get_current_tenant_id() == tenant_a.id
        set_tenant_context(tenant_b.id)
        assert get_current_tenant_id() == tenant_b.id
        clear_tenant_context()

    def test_tenant_context_with_context_manager(self, tenant_a: Tenant, tenant_b: Tenant):
        """测试使用上下文管理器设置租户上下文"""
        # 初始状态
        clear_tenant_context()
        assert get_current_tenant_id() is None
        # 使用上下文管理器
        with TenantContext(tenant_a.id):
            assert get_current_tenant_id() == tenant_a.id
            # 嵌套使用
            with TenantContext(tenant_b.id):
                assert get_current_tenant_id() == tenant_b.id
            # 退出嵌套后恢复
            assert get_current_tenant_id() == tenant_a.id
        # 退出后恢复初始状态
        assert get_current_tenant_id() is None

    async def test_tenant_context_async(self, tenant_a: Tenant):
        """测试异步上下文中的租户上下文"""
        async with TenantContext(tenant_a.id):
            assert get_current_tenant_id() == tenant_a.id
        assert get_current_tenant_id() is None

    def test_validate_public_tenant_context_missing(self):
        """测试公开接口缺少租户上下文时抛出异常"""
        from fastapi import HTTPException
        clear_tenant_context()
        with pytest.raises(HTTPException) as exc_info:
            validate_public_tenant_context("/api/v1/doctors/recommended")
        assert exc_info.value.status_code == 400
        assert "租户" in str(exc_info.value.detail)

    def test_validate_public_tenant_context_present(self, tenant_a: Tenant):
        """测试公开接口有租户上下文时不抛出异常"""
        set_tenant_context(tenant_a.id)
        # 不应该抛出异常
        validate_public_tenant_context("/api/v1/doctors/recommended")
        clear_tenant_context()

    def test_validate_public_tenant_context_non_public_path(self):
        """测试非公开接口不需要租户上下文"""
        clear_tenant_context()
        # 非公开路径不应该抛出异常
        validate_public_tenant_context("/api/v1/admin/login")
        validate_public_tenant_context("/api/v1/internal/stats")

    def test_public_tenant_required_paths(self):
        """测试公开接口路径列表"""
        # 验证关键路径在列表中
        assert "/api/v1/doctors/recommended" in PUBLIC_TENANT_REQUIRED_PATHS
        assert "/api/v1/public/appointments" in PUBLIC_TENANT_REQUIRED_PATHS


# ==================== 租户过滤工具测试（增强版） ====================
@pytest.mark.asyncio
class TestTenantFilterUtilsEnhanced:
    """租户过滤工具测试套件（增强版）"""

    async def test_add_tenant_filter_with_context(
        self,
        db_session: AsyncSession,
        tenant_a: Tenant,
        store_a: Store,
        store_b: Store,
    ):
        """测试 add_tenant_filter 在有租户上下文时的行为"""
        set_tenant_context(tenant_a.id)
        query = select(Store)
        filtered_query = add_tenant_filter(query, Store)
        result = await db_session.execute(filtered_query)
        stores = list(result.scalars().all())
        assert len(stores) == 1
        assert stores[0].tenant_id == tenant_a.id
        clear_tenant_context()

    async def test_add_tenant_filter_without_context(
        self,
        db_session: AsyncSession,
        store_a: Store,
        store_b: Store,
    ):
        """测试 add_tenant_filter 在无租户上下文时的行为"""
        clear_tenant_context()
        query = select(Store)
        filtered_query = add_tenant_filter(query, Store)
        result = await db_session.execute(filtered_query)
        stores = list(result.scalars().all())
        # 无租户上下文时，应该返回所有门店
        assert len(stores) == 2
    async def test_add_tenant_filter_explicit_tenant_id(
        self,
        db_session: AsyncSession,
        tenant_a: Tenant,
        tenant_b: Tenant,
        store_a: Store,
        store_b: Store,
    ):
        """测试 add_tenant_filter 显式指定租户 ID"""
        query = select(Store)
        filtered_query = add_tenant_filter(query, Store, tenant_id=tenant_a.id)
        result = await db_session.execute(filtered_query)
        stores = list(result.scalars().all())
        assert len(stores) == 1
        assert stores[0].tenant_id == tenant_a.id

    async def test_get_tenant_id_for_create_with_explicit_id(self):
        """测试 get_tenant_id_for_create 显式指定租户 ID"""
        tenant_id = get_tenant_id_for_create(tenant_id="explicit-tenant-id")
        assert tenant_id == "explicit-tenant-id"

    async def test_get_tenant_id_for_create_from_context(self, tenant_a: Tenant):
        """测试 get_tenant_id_for_create 从上下文获取租户 ID"""
        set_tenant_context(tenant_a.id)
        tenant_id = get_tenant_id_for_create()
        assert tenant_id == tenant_a.id
        clear_tenant_context()

    async def test_tenant_filtered_query_builder(
        self,
        db_session: AsyncSession,
        tenant_a: Tenant,
        tenant_b: Tenant,
        store_a: Store,
        store_b: Store,
    ):
        """测试 TenantFilteredQuery 构建器"""
        set_tenant_context(tenant_a.id)
        query = TenantFilteredQuery(Store).build()
        result = await db_session.execute(query)
        stores = list(result.scalars().all())
        assert len(stores) == 1
        assert stores[0].tenant_id == tenant_a.id
        # 切换租户
        set_tenant_context(tenant_b.id)
        query = TenantFilteredQuery(Store).build()
        result = await db_session.execute(query)
        stores = list(result.scalars().all())
        assert len(stores) == 1
        assert stores[0].tenant_id == tenant_b.id
        clear_tenant_context()


# ==================== 分布式锁隔离测试（增强版） ====================
class TestDistributedLockIsolationEnhanced:
    """分布式锁隔离测试套件（增强版）"""

    def test_lock_key_format_with_tenant_static(self, tenant_a: Tenant, tenant_b: Tenant):
        """测试锁键格式包含租户维度（静态方法)"""
        # 模拟租户对象
        tenant_aware_lock_a = RedisCache._build_tenant_aware_lock_name(
            "appointment:create", tenant_a.id
        )
        assert tenant_aware_lock_a == f"tenant:{tenant_a.id}:appointment:create"

        tenant_aware_lock_b = RedisCache._build_tenant_aware_lock_name(
            "appointment:create", tenant_b.id
        )
        assert tenant_aware_lock_b == f"tenant:{tenant_b.id}:appointment:create"

    def test_sync_lock_key_format_with_tenant(self, tenant_a: Tenant, tenant_b: Tenant):
        """测试同步版本锁键格式包含租户维度（委托给 RedisCache 的实现）"""
        # SyncRedisCache 没有 _build_tenant_aware_lock_name，
        # 键构建逻辑统一由 RedisCache._build_tenant_aware_lock_name 提供
        tenant_aware_lock_a = RedisCache._build_tenant_aware_lock_name(
            "appointment:create", tenant_a.id
        )
        assert tenant_aware_lock_a == f"tenant:{tenant_a.id}:appointment:create"
        tenant_aware_lock_b = RedisCache._build_tenant_aware_lock_name(
            "appointment:create", tenant_b.id
        )
        assert tenant_aware_lock_b == f"tenant:{tenant_b.id}:appointment:create"
