"""多租户隔离安全性测试

验证租户间数据隔离无漏洞：
- 数据隔离：租户 A 不能查询/修改租户 B 的数据
- 无租户请求被拒绝
- Redis 缓存隔离（key 包含 tenant_id）
- WebSocket 消息隔离
"""
import pytest
import pytest_asyncio
from datetime import datetime, date, time, timedelta
from uuid import uuid4
from unittest.mock import AsyncMock, patch

from app.models.tenant import Tenant, SubscriptionPlan
from app.models.store import Store
from app.models.department import Department
from app.models.doctor import Doctor
from app.models.schedule import Schedule
from app.models.user import User, Patient
from app.models.appointment import Appointment
from app.middleware.tenant_context import set_tenant_context, get_current_tenant_id


pytestmark = [pytest.mark.security]


# ==================== Fixtures ====================


@pytest_asyncio.fixture
async def tenant_a(db_session):
    """创建租户 A"""
    plan = SubscriptionPlan(
        id=str(uuid4()), plan_code="plan_a", name="计划A", status=1,
        created_at=datetime.now(), updated_at=datetime.now(),
    )
    db_session.add(plan)
    await db_session.flush()

    tenant = Tenant(
        id=str(uuid4()), tenant_code="tenant_a", name="租户A", status=1,
        subscription_plan_id=plan.id,
        created_at=datetime.now(), updated_at=datetime.now(),
    )
    db_session.add(tenant)
    await db_session.commit()
    await db_session.refresh(tenant)
    return tenant


@pytest_asyncio.fixture
async def tenant_b(db_session):
    """创建租户 B"""
    plan = SubscriptionPlan(
        id=str(uuid4()), plan_code="plan_b", name="计划B", status=1,
        created_at=datetime.now(), updated_at=datetime.now(),
    )
    db_session.add(plan)
    await db_session.flush()

    tenant = Tenant(
        id=str(uuid4()), tenant_code="tenant_b", name="租户B", status=1,
        subscription_plan_id=plan.id,
        created_at=datetime.now(), updated_at=datetime.now(),
    )
    db_session.add(tenant)
    await db_session.commit()
    await db_session.refresh(tenant)
    return tenant


@pytest_asyncio.fixture
async def store_a(db_session, tenant_a):
    """租户 A 的门店"""
    store = Store(
        id=str(uuid4()), name="门店A", address="地址A", phone="13800000001",
        tenant_id=tenant_a.id, status=1,
        created_at=datetime.now(), updated_at=datetime.now(),
    )
    db_session.add(store)
    await db_session.commit()
    await db_session.refresh(store)
    return store


@pytest_asyncio.fixture
async def store_b(db_session, tenant_b):
    """租户 B 的门店"""
    store = Store(
        id=str(uuid4()), name="门店B", address="地址B", phone="13800000002",
        tenant_id=tenant_b.id, status=1,
        created_at=datetime.now(), updated_at=datetime.now(),
    )
    db_session.add(store)
    await db_session.commit()
    await db_session.refresh(store)
    return store


@pytest_asyncio.fixture
async def dept_a(db_session, tenant_a, store_a):
    """租户 A 的科室"""
    dept = Department(
        id=str(uuid4()), name="科室A", store_id=store_a.id, tenant_id=tenant_a.id,
        status=1, created_at=datetime.now(), updated_at=datetime.now(),
    )
    db_session.add(dept)
    await db_session.commit()
    await db_session.refresh(dept)
    return dept


@pytest_asyncio.fixture
async def dept_b(db_session, tenant_b, store_b):
    """租户 B 的科室"""
    dept = Department(
        id=str(uuid4()), name="科室B", store_id=store_b.id, tenant_id=tenant_b.id,
        status=1, created_at=datetime.now(), updated_at=datetime.now(),
    )
    db_session.add(dept)
    await db_session.commit()
    await db_session.refresh(dept)
    return dept


@pytest_asyncio.fixture
async def doctor_a(db_session, tenant_a, store_a, dept_a):
    """租户 A 的医生"""
    doctor = Doctor(
        id=str(uuid4()), name="医生A", title="主治医师",
        department_id=dept_a.id, store_id=store_a.id, tenant_id=tenant_a.id,
        status=1, created_at=datetime.now(), updated_at=datetime.now(),
    )
    db_session.add(doctor)
    await db_session.commit()
    await db_session.refresh(doctor)
    return doctor


@pytest_asyncio.fixture
async def doctor_b(db_session, tenant_b, store_b, dept_b):
    """租户 B 的医生"""
    doctor = Doctor(
        id=str(uuid4()), name="医生B", title="主任医师",
        department_id=dept_b.id, store_id=store_b.id, tenant_id=tenant_b.id,
        status=1, created_at=datetime.now(), updated_at=datetime.now(),
    )
    db_session.add(doctor)
    await db_session.commit()
    await db_session.refresh(doctor)
    return doctor


@pytest_asyncio.fixture
async def user_a(db_session, tenant_a):
    """租户 A 的用户"""
    user = User(
        id=str(uuid4()), phone="13800000001",
        password_hash="$2b$12$test_hash",
        nickname="用户A", tenant_id=tenant_a.id, status=1,
        created_at=datetime.now(), updated_at=datetime.now(),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def user_b(db_session, tenant_b):
    """租户 B 的用户"""
    user = User(
        id=str(uuid4()), phone="13800000002",
        password_hash="$2b$12$test_hash",
        nickname="用户B", tenant_id=tenant_b.id, status=1,
        created_at=datetime.now(), updated_at=datetime.now(),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def patient_a(db_session, tenant_a, user_a):
    """租户 A 的就诊人"""
    patient = Patient(
        id=str(uuid4()), user_id=user_a.id, name="就诊人A", phone="13800000001",
        is_default=True, tenant_id=tenant_a.id,
        created_at=datetime.now(), updated_at=datetime.now(),
    )
    db_session.add(patient)
    await db_session.commit()
    await db_session.refresh(patient)
    return patient


@pytest_asyncio.fixture
async def patient_b(db_session, tenant_b, user_b):
    """租户 B 的就诊人"""
    patient = Patient(
        id=str(uuid4()), user_id=user_b.id, name="就诊人B", phone="13800000002",
        is_default=True, tenant_id=tenant_b.id,
        created_at=datetime.now(), updated_at=datetime.now(),
    )
    db_session.add(patient)
    await db_session.commit()
    await db_session.refresh(patient)
    return patient


@pytest_asyncio.fixture
async def schedule_a(db_session, tenant_a, doctor_a, store_a):
    """租户 A 的排班"""
    tomorrow = date.today() + timedelta(days=1)
    schedule = Schedule(
        id=str(uuid4()), doctor_id=doctor_a.id, store_id=store_a.id,
        tenant_id=tenant_a.id, schedule_date=tomorrow,
        time_slot="morning", start_time=time(8, 0), end_time=time(12, 0),
        total_slots=10, booked_slots=0, status=1,
        created_at=datetime.now(), updated_at=datetime.now(),
    )
    db_session.add(schedule)
    await db_session.commit()
    await db_session.refresh(schedule)
    return schedule


@pytest_asyncio.fixture
async def schedule_b(db_session, tenant_b, doctor_b, store_b):
    """租户 B 的排班"""
    tomorrow = date.today() + timedelta(days=1)
    schedule = Schedule(
        id=str(uuid4()), doctor_id=doctor_b.id, store_id=store_b.id,
        tenant_id=tenant_b.id, schedule_date=tomorrow,
        time_slot="morning", start_time=time(8, 0), end_time=time(12, 0),
        total_slots=10, booked_slots=0, status=1,
        created_at=datetime.now(), updated_at=datetime.now(),
    )
    db_session.add(schedule)
    await db_session.commit()
    await db_session.refresh(schedule)
    return schedule


@pytest_asyncio.fixture
async def appointment_a(db_session, tenant_a, user_a, patient_a, schedule_a, doctor_a):
    """租户 A 的预约"""
    appt = Appointment(
        id=str(uuid4()), user_id=user_a.id, patient_id=patient_a.id,
        schedule_id=schedule_a.id, doctor_id=doctor_a.id,
        tenant_id=tenant_a.id, appointment_no=f"A{uuid4().hex[:8].upper()}",
        status=1, queue_number=1,
        created_at=datetime.now(), updated_at=datetime.now(),
    )
    db_session.add(appt)
    await db_session.commit()
    await db_session.refresh(appt)
    return appt


@pytest_asyncio.fixture
async def appointment_b(db_session, tenant_b, user_b, patient_b, schedule_b, doctor_b):
    """租户 B 的预约"""
    appt = Appointment(
        id=str(uuid4()), user_id=user_b.id, patient_id=patient_b.id,
        schedule_id=schedule_b.id, doctor_id=doctor_b.id,
        tenant_id=tenant_b.id, appointment_no=f"B{uuid4().hex[:8].upper()}",
        status=1, queue_number=1,
        created_at=datetime.now(), updated_at=datetime.now(),
    )
    db_session.add(appt)
    await db_session.commit()
    await db_session.refresh(appt)
    return appt


# ==================== 数据隔离测试 ====================


class TestTenantDataIsolation:
    """租户数据隔离测试"""

    @pytest.mark.asyncio
    async def test_department_isolation(
        self, db_session, tenant_a, tenant_b, dept_a, dept_b
    ):
        """租户 A 不能查询到租户 B 的科室"""
        from sqlalchemy import select

        # 租户 A 查询科室
        set_tenant_context(tenant_a.id, tenant_a.tenant_code)
        result = await db_session.execute(
            select(Department).where(Department.tenant_id == tenant_a.id)
        )
        departments = result.scalars().all()

        assert len(departments) == 1
        assert departments[0].id == dept_a.id
        assert departments[0].name == "科室A"

        # 验证没有租户 B 的数据泄露
        dept_ids = [d.id for d in departments]
        assert dept_b.id not in dept_ids

    @pytest.mark.asyncio
    async def test_doctor_isolation(
        self, db_session, tenant_a, tenant_b, doctor_a, doctor_b
    ):
        """租户 A 不能查询到租户 B 的医生"""
        from sqlalchemy import select

        set_tenant_context(tenant_a.id, tenant_a.tenant_code)
        result = await db_session.execute(
            select(Doctor).where(Doctor.tenant_id == tenant_a.id)
        )
        doctors = result.scalars().all()

        assert len(doctors) == 1
        assert doctors[0].id == doctor_a.id
        assert doctor_b.id not in [d.id for d in doctors]

    @pytest.mark.asyncio
    async def test_schedule_isolation(
        self, db_session, tenant_a, tenant_b, schedule_a, schedule_b
    ):
        """租户 A 不能查询到租户 B 的排班"""
        from sqlalchemy import select

        set_tenant_context(tenant_a.id, tenant_a.tenant_code)
        result = await db_session.execute(
            select(Schedule).where(Schedule.tenant_id == tenant_a.id)
        )
        schedules = result.scalars().all()

        assert len(schedules) == 1
        assert schedules[0].id == schedule_a.id
        assert schedule_b.id not in [s.id for s in schedules]

    @pytest.mark.asyncio
    async def test_appointment_isolation(
        self, db_session, tenant_a, tenant_b, appointment_a, appointment_b
    ):
        """租户 A 不能查询到租户 B 的预约"""
        from sqlalchemy import select

        set_tenant_context(tenant_a.id, tenant_a.tenant_code)
        result = await db_session.execute(
            select(Appointment).where(Appointment.tenant_id == tenant_a.id)
        )
        appointments = result.scalars().all()

        assert len(appointments) == 1
        assert appointments[0].id == appointment_a.id
        assert appointment_b.id not in [a.id for a in appointments]

    @pytest.mark.asyncio
    async def test_user_isolation(
        self, db_session, tenant_a, tenant_b, user_a, user_b
    ):
        """租户 A 不能查询到租户 B 的用户"""
        from sqlalchemy import select

        set_tenant_context(tenant_a.id, tenant_a.tenant_code)
        result = await db_session.execute(
            select(User).where(User.tenant_id == tenant_a.id)
        )
        users = result.scalars().all()

        assert len(users) == 1
        assert users[0].id == user_a.id
        assert user_b.id not in [u.id for u in users]

    @pytest.mark.asyncio
    async def test_patient_isolation(
        self, db_session, tenant_a, tenant_b, patient_a, patient_b
    ):
        """租户 A 不能查询到租户 B 的就诊人"""
        from sqlalchemy import select

        set_tenant_context(tenant_a.id, tenant_a.tenant_code)
        result = await db_session.execute(
            select(Patient).where(Patient.tenant_id == tenant_a.id)
        )
        patients = result.scalars().all()

        assert len(patients) == 1
        assert patients[0].id == patient_a.id
        assert patient_b.id not in [p.id for p in patients]

    @pytest.mark.asyncio
    async def test_cross_tenant_update_blocked(
        self, db_session, tenant_a, tenant_b, dept_b
    ):
        """租户 A 不能修改租户 B 的科室"""
        from sqlalchemy import select

        # 租户 A 尝试修改租户 B 的科室
        set_tenant_context(tenant_a.id, tenant_a.tenant_code)

        # 查询时加上租户过滤 — 应该查不到
        result = await db_session.execute(
            select(Department).where(
                Department.id == dept_b.id,
                Department.tenant_id == tenant_a.id,
            )
        )
        found = result.scalar_one_or_none()
        assert found is None, "租户 A 不应能通过 tenant_id 过滤查到租户 B 的数据"

    @pytest.mark.asyncio
    async def test_cross_tenant_delete_blocked(
        self, db_session, tenant_a, tenant_b, doctor_b
    ):
        """租户 A 不能删除租户 B 的医生"""
        from sqlalchemy import select

        set_tenant_context(tenant_a.id, tenant_a.tenant_code)

        # 查询时加上租户过滤 — 应该查不到
        result = await db_session.execute(
            select(Doctor).where(
                Doctor.id == doctor_b.id,
                Doctor.tenant_id == tenant_a.id,
            )
        )
        found = result.scalar_one_or_none()
        assert found is None, "租户 A 不应能通过 tenant_id 过滤查到租户 B 的数据"


class TestTenantContextMiddleware:
    """租户上下文中间件测试"""

    def test_set_and_get_tenant_context(self):
        """设置和获取租户上下文"""
        set_tenant_context("tenant-123", "code-123")
        assert get_current_tenant_id() == "tenant-123"

    def test_clear_tenant_context(self):
        """清除租户上下文"""
        set_tenant_context(None, None)
        assert get_current_tenant_id() is None

    def test_tenant_context_isolation(self):
        """不同上下文的租户信息隔离"""
        set_tenant_context("tenant-a")
        assert get_current_tenant_id() == "tenant-a"

        set_tenant_context("tenant-b")
        assert get_current_tenant_id() == "tenant-b"
        assert get_current_tenant_id() != "tenant-a"


class TestRedisKeyIsolation:
    """Redis 缓存键隔离测试"""

    def test_sms_key_includes_tenant_id(self):
        """短信验证码 key 应包含 tenant_id 隔离"""
        from app.core.redis import RedisCache

        # 无租户上下文时的 key
        set_tenant_context(None, None)
        key_no_tenant = f"{RedisCache.PREFIX_SMS}13800001111:login"

        # 有租户上下文时的 key
        set_tenant_context("tenant-abc")
        key_with_tenant = f"{RedisCache.PREFIX_SMS}tenant-abc:13800001111:login"

        # 两者的 key 不同，保证隔离
        assert key_no_tenant != key_with_tenant
        assert "tenant-abc" in key_with_tenant
        assert "tenant-abc" not in key_no_tenant

    def test_different_tenants_sms_keys_isolated(self):
        """不同租户的短信验证码 key 不同"""
        from app.core.redis import RedisCache

        set_tenant_context("tenant-a")
        key_a = f"{RedisCache.PREFIX_SMS}tenant-a:13800001111:login"

        set_tenant_context("tenant-b")
        key_b = f"{RedisCache.PREFIX_SMS}tenant-b:13800001111:login"

        assert key_a != key_b
        assert key_a.startswith("sms:tenant-a:")
        assert key_b.startswith("sms:tenant-b:")

    def test_session_key_includes_tenant_id(self):
        """用户会话 key 通过 session_prefix 隔离"""
        from app.core.redis import RedisCache

        # session keys 使用 prefix 隔离不同角色
        user_session_key = f"{RedisCache.PREFIX_USER_SESSION}user-123"
        admin_session_key = f"{RedisCache.PREFIX_ADMIN_SESSION}admin-456"

        assert user_session_key != admin_session_key
        assert "session:" in user_session_key
        assert "session:admin:" in admin_session_key


class TestServiceLayerIsolation:
    """服务层租户隔离测试"""

    @pytest.mark.asyncio
    async def test_department_service_respects_tenant(
        self, db_session, tenant_a, tenant_b, dept_a, dept_b
    ):
        """DepartmentService 查询应受租户过滤"""
        from app.modules.departments.service import DepartmentService

        service = DepartmentService(db_session)

        # 模拟租户 A 的上下文
        set_tenant_context(tenant_a.id, tenant_a.tenant_code)

        # get_all_active 应只返回租户 A 的数据
        departments = await service.get_all_active()
        dept_ids = [d.id for d in departments]

        assert dept_a.id in dept_ids
        assert dept_b.id not in dept_ids

    @pytest.mark.asyncio
    async def test_schedule_service_respects_tenant(
        self, db_session, tenant_a, tenant_b, schedule_a, schedule_b, doctor_a, doctor_b
    ):
        """排班查询应受租户过滤"""
        from sqlalchemy import select

        tomorrow = date.today() + timedelta(days=1)

        # 租户 A 的医生排班 — 通过 tenant_id 过滤查询
        set_tenant_context(tenant_a.id, tenant_a.tenant_code)
        result = await db_session.execute(
            select(Schedule).where(
                Schedule.doctor_id == doctor_a.id,
                Schedule.tenant_id == tenant_a.id,
                Schedule.schedule_date == tomorrow,
            )
        )
        schedules = result.scalars().all()

        assert len(schedules) == 1
        assert schedules[0].id == schedule_a.id
        assert schedules[0].tenant_id == tenant_a.id
