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
from app.services.appointment_service import AppointmentService


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


# ==================== 测试数据 Fixtures ====================

@pytest_asyncio.fixture
async def test_store(db_session: AsyncSession) -> Store:
    """创建测试门店"""
    store = Store(
        id=str(uuid4()),
        name="测试门店",
        address="测试地址",
        phone="13800138000",
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(store)
    await db_session.commit()
    await db_session.refresh(store)
    return store


@pytest_asyncio.fixture
async def test_department(db_session: AsyncSession, test_store: Store) -> Department:
    """创建测试科室"""
    dept = Department(
        id=str(uuid4()),
        name="测试科室",
        store_id=test_store.id,
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(dept)
    await db_session.commit()
    await db_session.refresh(dept)
    return dept


@pytest_asyncio.fixture
async def test_doctor(db_session: AsyncSession, test_department: Department, test_store: Store) -> Doctor:
    """创建测试医生"""
    doctor = Doctor(
        id=str(uuid4()),
        name="测试医生",
        title="主治医师",
        department_id=test_department.id,
        store_id=test_store.id,
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(doctor)
    await db_session.commit()
    await db_session.refresh(doctor)
    return doctor


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    """创建测试用户"""
    user = User(
        id=str(uuid4()),
        phone="13800138001",
        password_hash="$2b$12$test_hash_not_for_production",  # 测试用密码哈希
        nickname="测试用户",
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_patient(db_session: AsyncSession, test_user: User) -> Patient:
    """创建测试就诊人"""
    patient = Patient(
        id=str(uuid4()),
        user_id=test_user.id,
        name="测试就诊人",
        phone="13800138002",
        id_card="110101199001011234",
        is_default=True,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(patient)
    await db_session.commit()
    await db_session.refresh(patient)
    return patient


@pytest_asyncio.fixture
async def test_schedule(db_session: AsyncSession, test_doctor: Doctor, test_store: Store) -> Schedule:
    """创建测试排班（明天上午）"""
    tomorrow = date.today() + timedelta(days=1)
    schedule = Schedule(
        id=str(uuid4()),
        doctor_id=test_doctor.id,
        store_id=test_store.id,
        schedule_date=tomorrow,
        time_slot="AM",
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
async def test_schedule_full(db_session: AsyncSession, test_doctor: Doctor, test_store: Store) -> Schedule:
    """创建已满的测试排班"""
    tomorrow = date.today() + timedelta(days=1)
    schedule = Schedule(
        id=str(uuid4()),
        doctor_id=test_doctor.id,
        store_id=test_store.id,
        schedule_date=tomorrow,
        time_slot="AM",
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
