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
from datetime import datetime, date, time, timedelta
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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
from app.modules.appointments.service import AppointmentService


# ==================== 测试配置 ====================

# 使用内存 SQLite 进行测试（快速、隔离）
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


# ==================== 事件循环 ====================

@pytest.fixture(scope="session")
def event_loop():
    """创建会话级别的事件循环"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ==================== 数据库 Fixtures ====================

@pytest_asyncio.fixture(scope="function")
async def test_engine():
    """创建测试数据库引擎（每个测试函数独立）"""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

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

    with TestClient(app) as test_client:
        yield test_client

    # 清理依赖覆盖
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
async def test_super_admin_role(db_session: AsyncSession, test_tenant: Tenant) -> Role:
    """创建测试超级管理员角色"""
    import json
    role = Role(
        id=str(uuid4()),
        name="超级管理员",
        code="SUPER_ADMIN",
        description="系统超级管理员",
        tenant_id=test_tenant.id,
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

    # 关联班次类型
    rule_set.shift_types.append(test_shift_type)
    await db_session.commit()

    await db_session.refresh(rule_set)
    return rule_set
