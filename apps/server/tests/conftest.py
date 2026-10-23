"""
Pytest 配置和共享 fixtures

提供测试所需的：
- 测试数据库会话（内存 SQLite 或测试 PostgreSQL）
- Redis mock
- 测试用户、医生、排班等测试数据
"""
import asyncio
import os
import sys
from dataclasses import dataclass
from datetime import datetime, date, time, timedelta
from typing import AsyncGenerator, Callable, Generator
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool, StaticPool

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ==================== SQLite 兼容性补丁 ====================
# 1. lowcode 模型使用 PostgreSQL JSONB，需要在 SQLite 测试环境中映射为 JSON
# 2. lowcode_page_version 模型有重复索引定义 (column index=True + explicit Index 同名),
#    SQLite 不允许重复索引，需要忽略
from sqlalchemy import event, JSON
from sqlalchemy.dialects.postgresql import JSONB

from sqlalchemy.dialects.sqlite import base as sqlite_base
if not hasattr(sqlite_base.SQLiteTypeCompiler, 'visit_JSONB'):
    sqlite_base.SQLiteTypeCompiler.visit_JSONB = lambda self, type_, **kw: 'JSON'

from app.db.base import Base
from app.models.user import User, Patient
from app.models.department import Department
from app.models.doctor import Doctor
from app.models.schedule import Schedule
from app.models.appointment import Appointment
from app.models.store import Store
from app.models.admin import Admin, Role
from app.models.rule_set import RuleSet, ShiftType
from app.models.tenant import Tenant, SubscriptionPlan
from app.models.refund import RefundRecord
from app.models.account import Account, AccountAdmin, AccountDoctor, AccountUser
from app.models.lowcode_audit_log import LowCodePageAuditLog
from app.models.schedule_room import ScheduleRoom
from app.modules.appointments.service import AppointmentService


# ==================== 测试配置 ====================

# 默认使用内存 SQLite（快速、隔离）；CI/本地可通过 TEST_DATABASE_URL 指向真实
# PostgreSQL（如 postgresql+asyncpg://test:test@localhost:5433/test_db），
# 以覆盖 JSONB/ILIKE/on_conflict 等 SQLite 无法验证的路径。
TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL", "sqlite+aiosqlite:///:memory:")
_IS_SQLITE = TEST_DATABASE_URL.startswith("sqlite")


# ==================== 数据库 Fixtures ====================
# 注意：不覆盖 event_loop fixture，使用 pytest-asyncio 默认的 function-scoped 循环。
# session-scoped 循环会与 TestClient 的内部事件循环冲突，导致 teardown 时
# "RuntimeError: Event loop is closed" 错误。

@pytest_asyncio.fixture(scope="function")
async def test_engine():
    """创建测试数据库引擎（每个测试函数独立）"""
    if _IS_SQLITE:
        engine = create_async_engine(
            TEST_DATABASE_URL,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            echo=False,
        )
    else:
        # PG: function 级事件循环下连接不可跨测试复用，NullPool 保证每测试独立连接
        engine = create_async_engine(
            TEST_DATABASE_URL,
            poolclass=NullPool,
            echo=False,
        )

    async with engine.begin() as conn:
        # 低代码模型有重复索引定义 (column index=True + explicit Index 同名),
        # SQLite 会报 "index already exists", 需要去重后再 create_all
        def _create_all_safe(connection):
            seen_indexes = set()
            for table in Base.metadata.sorted_tables:
                deduped = set()
                for idx in table.indexes:
                    if idx.name not in seen_indexes:
                        seen_indexes.add(idx.name)
                        deduped.add(idx)
                table.indexes = deduped
            Base.metadata.create_all(connection)

        await conn.run_sync(_create_all_safe)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """创建测试数据库会话"""
    async_session_maker = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    async with async_session_maker() as session:
        yield session


# ==================== Redis Mock ====================

@pytest.fixture
def mock_redis():
    """Mock Redis 缓存"""
    with patch("app.core.redis.RedisCache") as mock:
        # 模拟分布式锁
        mock.distributed_lock = AsyncMock()
        mock.distributed_lock.return_value.__aenter__ = AsyncMock(return_value="lock_value")
        mock.distributed_lock.return_value.__aexit__ = AsyncMock(return_value=None)

        # 模拟缓存操作
        mock.get = AsyncMock(return_value=None)
        mock.set = AsyncMock(return_value=True)
        mock.delete = AsyncMock(return_value=True)

        yield mock


@pytest_asyncio.fixture
async def redis_client():
    """创建 Redis 客户端 Mock（用于缓存隔离测试）"""
    from redis.asyncio import Redis
    client = AsyncMock(spec=Redis)
    client.get.return_value = "mock_value"
    client.set.return_value = True
    client.eval.return_value = 1
    client.delete.return_value = True
    client.keys.return_value = []
    client.scan.return_value = (0, [])
    # 模拟 keys 方法返回匹配的键
    async def mock_keys(pattern):
        return []
    client.keys = mock_keys
    yield client


# ==================== 测试数据 Fixtures ====================

@pytest_asyncio.fixture
async def test_tenant(db_session: AsyncSession) -> Tenant:
    """创建测试租户"""
    plan = SubscriptionPlan(
        id=str(uuid4()),
        plan_code="test_plan",
        name="测试计划",
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(plan)
    await db_session.flush()

    tenant = Tenant(
        id=str(uuid4()),
        tenant_code="test_tenant",
        name="测试租户",
        status=1,
        subscription_plan_id=plan.id,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(tenant)
    await db_session.commit()
    await db_session.refresh(tenant)
    return tenant


@pytest_asyncio.fixture
async def test_store(db_session: AsyncSession, test_tenant: Tenant) -> Store:
    """创建测试门店"""
    store = Store(
        id=str(uuid4()),
        name="测试门店",
        address="测试地址",
        phone="13800138000",
        tenant_id=test_tenant.id,
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(store)
    await db_session.commit()
    await db_session.refresh(store)
    return store


@pytest_asyncio.fixture
async def test_department(db_session: AsyncSession, test_tenant: Tenant, test_store: Store) -> Department:
    """创建测试科室"""
    dept = Department(
        id=str(uuid4()),
        name="测试科室",
        store_id=test_store.id,
        tenant_id=test_tenant.id,
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(dept)
    await db_session.commit()
    await db_session.refresh(dept)
    return dept


@pytest_asyncio.fixture
async def test_doctor(db_session: AsyncSession, test_tenant: Tenant, test_department: Department, test_store: Store) -> Doctor:
    """创建测试医生"""
    doctor = Doctor(
        id=str(uuid4()),
        name="测试医生",
        title="主治医师",
        department_id=test_department.id,
        store_id=test_store.id,
        tenant_id=test_tenant.id,
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(doctor)
    await db_session.commit()
    await db_session.refresh(doctor)
    return doctor


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession, test_tenant: Tenant) -> User:
    """创建测试用户"""
    user = User(
        id=str(uuid4()),
        phone="13800138001",
        password_hash="$2b$12$test_hash_not_for_production",  # 测试用密码哈希
        nickname="测试用户",
        tenant_id=test_tenant.id,
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_patient(db_session: AsyncSession, test_tenant: Tenant, test_user: User) -> Patient:
    """创建测试就诊人"""
    patient = Patient(
        id=str(uuid4()),
        user_id=test_user.id,
        name="测试就诊人",
        phone="13800138002",
        id_card="110101199001011234",
        is_default=True,
        tenant_id=test_tenant.id,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(patient)
    await db_session.commit()
    await db_session.refresh(patient)
    return patient


@pytest_asyncio.fixture
async def test_schedule(db_session: AsyncSession, test_tenant: Tenant, test_doctor: Doctor, test_store: Store) -> Schedule:
    """创建测试排班（明天上午）"""
    tomorrow = date.today() + timedelta(days=1)
    schedule = Schedule(
        id=str(uuid4()),
        doctor_id=test_doctor.id,
        store_id=test_store.id,
        tenant_id=test_tenant.id,
        schedule_date=tomorrow,
        time_slot="morning",
        start_time=time(8, 0),
        end_time=time(12, 0),
        total_slots=10,
        booked_slots=0,
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(schedule)
    await db_session.commit()
    await db_session.refresh(schedule)
    return schedule


@pytest_asyncio.fixture
async def test_schedule_full(db_session: AsyncSession, test_tenant: Tenant, test_doctor: Doctor, test_store: Store) -> Schedule:
    """创建已满的测试排班"""
    tomorrow = date.today() + timedelta(days=1)
    schedule = Schedule(
        id=str(uuid4()),
        doctor_id=test_doctor.id,
        store_id=test_store.id,
        tenant_id=test_tenant.id,
        schedule_date=tomorrow,
        time_slot="morning",
        start_time=time(8, 0),
        end_time=time(12, 0),
        total_slots=10,
        booked_slots=10,  # 已满
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(schedule)
    await db_session.commit()
    await db_session.refresh(schedule)
    return schedule


@pytest_asyncio.fixture
async def test_appointment(
    db_session: AsyncSession,
    test_tenant: Tenant,
    test_schedule: Schedule,
    test_patient: Patient,
    test_doctor: Doctor,
    test_user: User,
) -> Appointment:
    """创建测试预约"""
    appointment = Appointment(
        id=str(uuid4()),
        appointment_no=f"YY{datetime.now().strftime('%Y%m%d%H%M%S')}{str(uuid4())[:4].upper()}",
        user_id=test_user.id,
        patient_id=test_patient.id,
        doctor_id=test_doctor.id,
        schedule_id=test_schedule.id,
        tenant_id=test_tenant.id,
        queue_number=1,
        status=1,  # 已预约
        patient_name=test_patient.name,
        patient_phone=test_patient.phone,
        doctor_name=test_doctor.name,
        doctor_title=test_doctor.title,
        department_name="测试科室",
        created_at=datetime.now(),
        updated_at=datetime.now(),
        created_by=test_user.id,
    )
    db_session.add(appointment)

    # 更新排班已预约数
    test_schedule.booked_slots += 1

    await db_session.commit()
    await db_session.refresh(appointment)
    return appointment


# ==================== 服务 Fixtures ====================

@pytest.fixture
def appointment_service(db_session: AsyncSession) -> AppointmentService:
    """创建预约服务实例"""
    return AppointmentService(db_session)


# ==================== FastAPI Test Client ====================

@pytest.fixture
def client(db_session: AsyncSession):
    """创建测试客户端"""
    from fastapi.testclient import TestClient
    from app.main import app

    # Override 数据库依赖
    async def override_get_db():
        yield db_session

    from app.db.session import get_db
    app.dependency_overrides[get_db] = override_get_db

    test_client = TestClient(app, raise_server_exceptions=False)
    yield test_client

    # 关闭客户端并清理依赖覆盖
    try:
        test_client.close()
    except RuntimeError:
        # 忽略 "Event loop is closed" — lifespan shutdown 在异步测试环境中
        # 可能因事件循环已关闭而失败，不影响测试结果
        pass
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def async_client(db_session: AsyncSession):
    """创建异步测试客户端（用于权限测试）"""
    from httpx import AsyncClient, ASGITransport
    from app.main import app
    from app.db.session import get_db

    # Override 数据库依赖
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    # 清理依赖覆盖
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def super_admin_token(async_client: AsyncClient, test_super_admin: Admin) -> str:
    """获取超级管理员 token"""
    from app.core.security import create_access_token

    # 使用与登录 API 相同的格式：sub 字段存储 admin_id
    token = create_access_token({"sub": test_super_admin.id, "type": "admin"})
    return token


@pytest_asyncio.fixture
async def store_admin_token(async_client: AsyncClient, test_store_admin: Admin) -> str:
    """获取门店管理员 token"""
    from app.core.security import create_access_token

    # 使用与登录 API 相同的格式：sub 字段存储 admin_id
    token = create_access_token({"sub": test_store_admin.id, "type": "admin"})
    return token


@pytest.fixture
def test_rule_set_dict(db_session: AsyncSession, test_shift_type: ShiftType) -> dict:
    """创建测试规则组（返回 dict）- 使用已有的 test_rule_set"""
    import asyncio

    async def create():
        rule_set = RuleSet(
            id=str(uuid4()),
            name="测试规则组",
            enabled=True,
            priority=100,
            time_source="SERVER",
            timezone_source="HOSPITAL",
            compare_precision="SECOND",
            default_open_inclusive=True,
            default_close_inclusive=False,
            rounding_mode="NONE",
            clock_skew_tolerance_sec=5,
            description="测试规则组",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            created_by=str(uuid4()),
            updated_by=str(uuid4()),
        )
        db_session.add(rule_set)
        await db_session.commit()

        # 创建新的班次类型关联，避免依赖异步 fixture
        shift_type = ShiftType(
            id=str(uuid4()),
            code="TEST",
            name="测试班次",
            enabled=True,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db_session.add(shift_type)
        await db_session.commit()

        rule_set.shift_types.append(shift_type)
        await db_session.commit()

        await db_session.refresh(rule_set)

        return {
            "id": rule_set.id,
            "name": rule_set.name,
            "enabled": rule_set.enabled,
            "priority": rule_set.priority,
        }

    return asyncio.run(create())


@pytest.fixture
def test_window_dict(test_rule_set_dict: dict) -> dict:
    """创建测试时间窗（返回 dict）- 返回模拟数据"""
    return {
        "id": str(uuid4()),
        "rule_set_id": test_rule_set_dict["id"],
        "action": "BOOK",
        "reference_point": "SHIFT_START",
    }


# ==================== 工具函数 ====================

def generate_appointment_no() -> str:
    """生成预约号"""
    return f"YY{datetime.now().strftime('%Y%m%d%H%M%S')}{str(uuid4())[:4].upper()}"


def assert_appointment_status(appointment: Appointment, expected_status: int):
    """断言预约状态"""
    assert appointment.status == expected_status, (
        f"Expected status {expected_status}, got {appointment.status}"
    )


def assert_schedule_booked_slots(schedule: Schedule, expected: int):
    """断言排班已预约数"""
    assert schedule.booked_slots == expected, (
        f"Expected booked_slots {expected}, got {schedule.booked_slots}"
    )


# ==================== 管理员和角色 Fixtures ====================

@pytest_asyncio.fixture
async def test_super_admin_role(db_session: AsyncSession) -> Role:
    """创建测试超级管理员角色（平台级：tenant_id=NULL）"""
    import json
    role = Role(
        id=str(uuid4()),
        name="超级管理员",
        code="SUPER_ADMIN",
        description="系统超级管理员",
        tenant_id=None,
        status=1,
        permissions=json.dumps(["*"]),
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(role)
    await db_session.commit()
    await db_session.refresh(role)
    return role


@pytest_asyncio.fixture
async def test_store_admin_role(db_session: AsyncSession, test_tenant: Tenant) -> Role:
    """创建测试门店管理员角色"""
    import json
    role = Role(
        id=str(uuid4()),
        name="门店管理员",
        code="STORE_ADMIN",
        description="门店管理员",
        tenant_id=test_tenant.id,
        status=1,
        permissions=json.dumps([]),
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(role)
    await db_session.commit()
    await db_session.refresh(role)
    return role


@pytest_asyncio.fixture
async def test_super_admin(db_session: AsyncSession, test_tenant: Tenant, test_super_admin_role: Role, test_store: Store) -> Admin:
    """创建测试超级管理员"""
    import bcrypt
    admin = Admin(
        id=str(uuid4()),
        username="superadmin",
        password_hash=bcrypt.hashpw("password123".encode(), bcrypt.gensalt()).decode(),
        name="超级管理员",
        phone="13800138888",
        role_id=test_super_admin_role.id,
        current_store_id=test_store.id,
        tenant_id=test_tenant.id,
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(admin)
    await db_session.commit()
    await db_session.refresh(admin)
    return admin


@pytest_asyncio.fixture
async def test_store_admin(db_session: AsyncSession, test_tenant: Tenant, test_store_admin_role: Role, test_store: Store) -> Admin:
    """创建测试门店管理员"""
    import bcrypt
    admin = Admin(
        id=str(uuid4()),
        username="storeadmin",
        password_hash=bcrypt.hashpw("password123".encode(), bcrypt.gensalt()).decode(),
        name="门店管理员",
        phone="13800138999",
        role_id=test_store_admin_role.id,
        current_store_id=test_store.id,
        tenant_id=test_tenant.id,
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(admin)
    await db_session.commit()
    await db_session.refresh(admin)
    return admin


# ==================== 多租户测试基建（T-1） ====================

@dataclass
class MultiTenantEnv:
    """两个互相隔离的租户环境 + 平台管理员"""
    tenant_a: Tenant
    tenant_b: Tenant
    store_a: Store
    store_b: Store
    role_a: Role
    role_b: Role
    admin_a: Admin
    admin_b: Admin
    platform_admin: Admin


async def _create_tenant_admin(
    db_session: AsyncSession,
    tenant: Tenant,
    store: Store,
    *,
    role_code: str = "TENANT_ADMIN",
    role_name: str = "租户管理员",
) -> tuple[Role, Admin]:
    """创建租户内的角色与管理员账号（角色 tenant_id 指向本租户）"""
    import bcrypt
    import json

    suffix = uuid4().hex[:8]
    role = Role(
        id=str(uuid4()),
        name=role_name,
        code=role_code,
        description=f"测试用{role_name}",
        tenant_id=tenant.id,
        status=1,
        permissions=json.dumps(["*"]),
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(role)
    await db_session.commit()
    await db_session.refresh(role)

    admin = Admin(
        id=str(uuid4()),
        username=f"tenant_admin_{suffix}",
        password_hash=bcrypt.hashpw("password123".encode(), bcrypt.gensalt()).decode(),
        name=f"{tenant.name}管理员",
        phone=f"139{uuid4().int % 10**8:08d}",
        role_id=role.id,
        current_store_id=store.id,
        tenant_id=tenant.id,
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(admin)
    await db_session.commit()
    await db_session.refresh(admin)
    return role, admin


@pytest_asyncio.fixture
async def test_platform_admin_role(db_session: AsyncSession) -> Role:
    """平台级超级管理员角色：tenant_id=NULL 是平台特权的唯一凭据"""
    import json
    role = Role(
        id=str(uuid4()),
        name="超级管理员",
        code="SUPER_ADMIN",
        description="平台超级管理员（不属于任何租户）",
        tenant_id=None,
        status=1,
        permissions=json.dumps(["*"]),
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(role)
    await db_session.commit()
    await db_session.refresh(role)
    return role


@pytest_asyncio.fixture
async def test_platform_admin(db_session: AsyncSession, test_platform_admin_role: Role) -> Admin:
    """平台管理员：不属于任何租户"""
    import bcrypt
    admin = Admin(
        id=str(uuid4()),
        username=f"platform_admin_{uuid4().hex[:8]}",
        password_hash=bcrypt.hashpw("password123".encode(), bcrypt.gensalt()).decode(),
        name="平台管理员",
        phone=f"137{uuid4().int % 10**8:08d}",
        role_id=test_platform_admin_role.id,
        current_store_id=None,
        tenant_id=None,
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(admin)
    await db_session.commit()
    await db_session.refresh(admin)
    return admin


@pytest_asyncio.fixture
async def platform_admin_token(test_platform_admin: Admin) -> str:
    """平台管理员 token"""
    from app.core.security import create_access_token
    return create_access_token({"sub": test_platform_admin.id, "type": "admin"})


@pytest.fixture
def admin_token_factory() -> Callable[[Admin], str]:
    """闭包工厂：为任意 Admin 生成 admin 类型 access token"""
    from app.core.security import create_access_token

    def _make(admin: Admin) -> str:
        return create_access_token({"sub": admin.id, "type": "admin"})

    return _make


@pytest_asyncio.fixture
async def multi_tenant_env(
    db_session: AsyncSession,
    test_platform_admin: Admin,
) -> MultiTenantEnv:
    """两个互不可见的租户环境（A/B）+ 各自门店与租户管理员 + 平台管理员"""
    from app.middleware.tenant_context import clear_tenant_context

    try:
        suffix = uuid4().hex[:8]
        plan = SubscriptionPlan(
            id=str(uuid4()),
            plan_code=f"plan_{suffix}",
            name="测试计划",
            status=1,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db_session.add(plan)
        await db_session.commit()

        tenants: list[Tenant] = []
        stores: list[Store] = []
        roles: list[Role] = []
        admins: list[Admin] = []
        for label in ("a", "b"):
            tenant = Tenant(
                id=str(uuid4()),
                tenant_code=f"tenant_{label}_{suffix}",
                name=f"测试租户{label.upper()}",
                status=1,
                subscription_plan_id=plan.id,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
            db_session.add(tenant)
            await db_session.commit()
            await db_session.refresh(tenant)

            store = Store(
                id=str(uuid4()),
                tenant_id=tenant.id,
                name=f"测试门店{label.upper()}",
                code=f"STORE_{label.upper()}_{suffix}",
                address="测试地址",
                phone="13800138000",
                status=1,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
            db_session.add(store)
            await db_session.commit()
            await db_session.refresh(store)

            role, admin = await _create_tenant_admin(db_session, tenant, store)
            tenants.append(tenant)
            stores.append(store)
            roles.append(role)
            admins.append(admin)

        return MultiTenantEnv(
            tenant_a=tenants[0],
            tenant_b=tenants[1],
            store_a=stores[0],
            store_b=stores[1],
            role_a=roles[0],
            role_b=roles[1],
            admin_a=admins[0],
            admin_b=admins[1],
            platform_admin=test_platform_admin,
        )
    finally:
        clear_tenant_context()


# ==================== 规则组 Fixtures ====================

@pytest_asyncio.fixture
async def test_shift_type(db_session: AsyncSession) -> ShiftType:
    """创建测试班次类型"""
    shift_type = ShiftType(
        id=str(uuid4()),
        code="OPD",
        name="门诊",
        description="普通门诊",
        enabled=True,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(shift_type)
    await db_session.commit()
    await db_session.refresh(shift_type)
    return shift_type


@pytest_asyncio.fixture
async def test_rule_set(db_session: AsyncSession, test_shift_type: ShiftType) -> RuleSet:
    """创建测试规则组"""
    from app.models.rule_set import RuleSetShiftType

    rule_set = RuleSet(
        id=str(uuid4()),
        name="默认规则组",
        enabled=True,
        priority=100,
        time_source="SERVER",
        timezone_source="HOSPITAL",
        compare_precision="SECOND",
        default_open_inclusive=True,
        default_close_inclusive=False,
        rounding_mode="NONE",
        clock_skew_tolerance_sec=5,
        description="默认规则组",
        created_at=datetime.now(),
        updated_at=datetime.now(),
        created_by=str(uuid4()),
        updated_by=str(uuid4()),
    )
    db_session.add(rule_set)
    await db_session.commit()

    # 使用 RuleSetShiftType 关联表来建立关联，避免 lazy loading
    rule_set_shift_type = RuleSetShiftType(
        rule_set_id=rule_set.id,
        shift_type_id=test_shift_type.id,
    )
    db_session.add(rule_set_shift_type)
    await db_session.commit()

    await db_session.refresh(rule_set)
    return rule_set


# ==================== 统一账号 Fixtures ====================


@pytest_asyncio.fixture
async def sample_account(db_session: AsyncSession, test_tenant: Tenant) -> Account:
    """创建基础 Account 记录"""
    account = Account(
        id=str(uuid4()),
        tenant_id=test_tenant.id,
        phone="13800000001",
        username="test_account",
        password_hash="$2b$12$test_hash_not_for_production",
        nickname="测试账号",
        name="测试账号",
        gender=0,
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(account)
    await db_session.commit()
    await db_session.refresh(account)
    return account


@pytest_asyncio.fixture
async def sample_admin_account(
    db_session: AsyncSession,
    test_tenant: Tenant,
    test_store: Store,
    test_super_admin_role: Role,
) -> Account:
    """创建 Account + AccountAdmin 记录"""
    account_id = str(uuid4())
    account = Account(
        id=account_id,
        tenant_id=test_tenant.id,
        phone="13800000010",
        username="test_admin_account",
        password_hash="$2b$12$test_hash_not_for_production",
        nickname="管理员账号",
        name="管理员账号",
        gender=0,
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(account)
    await db_session.flush()

    account_admin = AccountAdmin(
        account_id=account_id,
        role_id=test_super_admin_role.id,
        current_store_id=test_store.id,
        email="admin@example.com",
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(account_admin)
    await db_session.commit()
    await db_session.refresh(account)
    return account


@pytest_asyncio.fixture
async def sample_doctor_account(
    db_session: AsyncSession,
    test_tenant: Tenant,
    test_store: Store,
    test_department: Department,
) -> Account:
    """创建 Account + AccountDoctor 记录"""
    account_id = str(uuid4())
    account = Account(
        id=account_id,
        tenant_id=test_tenant.id,
        phone="13800000020",
        username="test_doctor_account",
        password_hash="$2b$12$test_hash_not_for_production",
        nickname="医生账号",
        name="医生账号",
        gender=1,
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(account)
    await db_session.flush()

    account_doctor = AccountDoctor(
        account_id=account_id,
        store_id=test_store.id,
        department_id=test_department.id,
        title="主治医师",
        years_of_experience=5,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(account_doctor)
    await db_session.commit()
    await db_session.refresh(account)
    return account


@pytest_asyncio.fixture
async def sample_user_account(
    db_session: AsyncSession,
    test_tenant: Tenant,
) -> Account:
    """创建 Account + AccountUser 记录"""
    account_id = str(uuid4())
    account = Account(
        id=account_id,
        tenant_id=test_tenant.id,
        phone="13800000030",
        username="13800000030",
        password_hash="$2b$12$test_hash_not_for_production",
        nickname="用户账号",
        name="用户账号",
        gender=0,
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(account)
    await db_session.flush()

    account_user = AccountUser(
        account_id=account_id,
        tenant_id=test_tenant.id,
        openid="test_openid_fixture",
        points=50,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(account_user)
    await db_session.commit()
    await db_session.refresh(account)
    return account


# ==================== TestDataFactory ====================

class TestDataFactory:
    """测试数据工厂 — 用单个调用替代 6 层 fixture 链。

    用法:
        async def test_something(factory):
            data = await factory.create_full_chain()
            # data.tenant, data.store, data.department, data.doctor,
            # data.schedule, data.patient, data.appointment 全部可用

            # 或只创建需要的:
            doctor = await factory.create_doctor(name="张医生")
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self._tenant = None
        self._store = None
        self._department = None

    async def create_tenant(self, **overrides) -> Tenant:
        plan = SubscriptionPlan(
            id=str(uuid4()), plan_code="test_plan", name="测试计划",
            status=1, created_at=datetime.now(), updated_at=datetime.now(),
        )
        self.db.add(plan)
        await self.db.flush()

        defaults = dict(
            id=str(uuid4()), tenant_code=f"tenant_{uuid4().hex[:8]}",
            name="测试租户", status=1, subscription_plan_id=plan.id,
            created_at=datetime.now(), updated_at=datetime.now(),
        )
        defaults.update(overrides)
        tenant = Tenant(**defaults)
        self.db.add(tenant)
        await self.db.commit()
        await self.db.refresh(tenant)
        self._tenant = tenant
        return tenant

    async def create_store(self, tenant_id: str = None, **overrides) -> Store:
        if tenant_id is None:
            if self._tenant is None:
                await self.create_tenant()
            tenant_id = self._tenant.id

        defaults = dict(
            id=str(uuid4()), name="测试门店", address="测试地址",
            phone="13800138000", tenant_id=tenant_id, status=1,
            created_at=datetime.now(), updated_at=datetime.now(),
        )
        defaults.update(overrides)
        store = Store(**defaults)
        self.db.add(store)
        await self.db.commit()
        await self.db.refresh(store)
        self._store = store
        return store

    async def create_department(self, tenant_id: str = None, store_id: str = None, **overrides) -> Department:
        if tenant_id is None:
            if self._tenant is None:
                await self.create_tenant()
            tenant_id = self._tenant.id
        if store_id is None:
            if self._store is None:
                await self.create_store(tenant_id)
            store_id = self._store.id

        defaults = dict(
            id=str(uuid4()), name="测试科室", store_id=store_id,
            tenant_id=tenant_id, status=1,
            created_at=datetime.now(), updated_at=datetime.now(),
        )
        defaults.update(overrides)
        dept = Department(**defaults)
        self.db.add(dept)
        await self.db.commit()
        await self.db.refresh(dept)
        self._department = dept
        return dept

    async def create_doctor(self, tenant_id: str = None, store_id: str = None,
                            department_id: str = None, **overrides) -> Doctor:
        if tenant_id is None:
            if self._tenant is None:
                await self.create_tenant()
            tenant_id = self._tenant.id
        if store_id is None:
            if self._store is None:
                await self.create_store(tenant_id)
            store_id = self._store.id
        if department_id is None:
            if self._department is None:
                await self.create_department(tenant_id, store_id)
            department_id = self._department.id

        defaults = dict(
            id=str(uuid4()), name="测试医生", title="主治医师",
            department_id=department_id, store_id=store_id,
            tenant_id=tenant_id, status=1,
            created_at=datetime.now(), updated_at=datetime.now(),
        )
        defaults.update(overrides)
        doctor = Doctor(**defaults)
        self.db.add(doctor)
        await self.db.commit()
        await self.db.refresh(doctor)
        return doctor

    async def create_user(self, tenant_id: str = None, **overrides) -> User:
        if tenant_id is None:
            if self._tenant is None:
                await self.create_tenant()
            tenant_id = self._tenant.id

        defaults = dict(
            id=str(uuid4()), phone=f"138{uuid4().hex[:8]}",
            password_hash="$2b$12$test_hash_not_for_production",
            nickname="测试用户", tenant_id=tenant_id, status=1,
            created_at=datetime.now(), updated_at=datetime.now(),
        )
        defaults.update(overrides)
        user = User(**defaults)
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def create_patient(self, tenant_id: str = None, user_id: str = None, **overrides) -> tuple[User, Patient]:
        if tenant_id is None:
            if self._tenant is None:
                await self.create_tenant()
            tenant_id = self._tenant.id
        if user_id is None:
            user = await self.create_user(tenant_id)
            user_id = user.id
        else:
            user = None

        defaults = dict(
            id=str(uuid4()), user_id=user_id, name="测试就诊人",
            phone="13800138002", id_card="110101199001011234",
            is_default=True, tenant_id=tenant_id,
            created_at=datetime.now(), updated_at=datetime.now(),
        )
        defaults.update(overrides)
        patient = Patient(**defaults)
        self.db.add(patient)
        await self.db.commit()
        await self.db.refresh(patient)
        return user, patient

    async def create_schedule(self, tenant_id: str = None, doctor_id: str = None,
                              store_id: str = None, **overrides) -> Schedule:
        if tenant_id is None:
            if self._tenant is None:
                await self.create_tenant()
            tenant_id = self._tenant.id
        if store_id is None:
            if self._store is None:
                await self.create_store(tenant_id)
            store_id = self._store.id
        if doctor_id is None:
            doctor = await self.create_doctor(tenant_id, store_id)
            doctor_id = doctor.id

        tomorrow = date.today() + timedelta(days=1)
        defaults = dict(
            id=str(uuid4()), doctor_id=doctor_id, store_id=store_id,
            tenant_id=tenant_id, schedule_date=tomorrow, time_slot="morning",
            start_time=time(8, 0), end_time=time(12, 0),
            total_slots=10, booked_slots=0, status=1,
            created_at=datetime.now(), updated_at=datetime.now(),
        )
        defaults.update(overrides)
        schedule = Schedule(**defaults)
        self.db.add(schedule)
        await self.db.commit()
        await self.db.refresh(schedule)
        return schedule

    async def create_appointment(self, tenant_id: str = None, doctor_id: str = None,
                                 schedule_id: str = None, patient_id: str = None,
                                 user_id: str = None, **overrides) -> Appointment:
        if tenant_id is None:
            if self._tenant is None:
                await self.create_tenant()
            tenant_id = self._tenant.id

        if user_id is None or patient_id is None:
            user, patient = await self.create_patient(tenant_id)
            if user_id is None:
                user_id = user.id
            if patient_id is None:
                patient_id = patient.id

        if schedule_id is None:
            schedule = await self.create_schedule(tenant_id, doctor_id)
            schedule_id = schedule.id
            doctor_id = schedule.doctor_id

        if doctor_id is None:
            schedule = await self.db.get(Schedule, schedule_id)
            doctor_id = schedule.doctor_id

        doctor = await self.db.get(Doctor, doctor_id)

        defaults = dict(
            id=str(uuid4()),
            appointment_no=generate_appointment_no(),
            user_id=user_id, patient_id=patient_id,
            doctor_id=doctor_id, schedule_id=schedule_id,
            tenant_id=tenant_id, queue_number=1, status=1,
            patient_name="测试就诊人", patient_phone="13800138002",
            doctor_name=doctor.name if doctor else "测试医生",
            doctor_title=doctor.title if doctor else "主治医师",
            department_name="测试科室",
            created_at=datetime.now(), updated_at=datetime.now(),
            created_by=user_id,
        )
        defaults.update(overrides)
        appointment = Appointment(**defaults)
        self.db.add(appointment)

        schedule = await self.db.get(Schedule, schedule_id)
        if schedule:
            schedule.booked_slots += 1

        await self.db.commit()
        await self.db.refresh(appointment)
        return appointment

    async def create_full_chain(self):
        """创建完整的 tenant → store → department → doctor → schedule → patient → appointment 链"""

        class ChainResult:
            pass

        result = ChainResult()
        result.tenant = await self.create_tenant()
        result.store = await self.create_store()
        result.department = await self.create_department()
        result.doctor = await self.create_doctor()
        result.user, result.patient = await self.create_patient()
        result.schedule = await self.create_schedule(doctor_id=result.doctor.id)
        result.appointment = await self.create_appointment(
            schedule_id=result.schedule.id,
            doctor_id=result.doctor.id,
            user_id=result.user.id,
            patient_id=result.patient.id,
        )
        return result


@pytest_asyncio.fixture
async def factory(db_session: AsyncSession) -> TestDataFactory:
    """测试数据工厂 fixture — 替代深层嵌套 fixture 链"""
    return TestDataFactory(db_session)
