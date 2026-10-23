"""
配额实时检查测试

测试用例覆盖：
1. 门店配额检查：创建门店时检查配额
2. 管理员配额检查：创建管理员时检查配额
3. 医生配额检查：创建医生时检查配额
4. 预约配额检查：创建预约时检查配额（月度限制）
5. 配额未超限时正常创建
6. 配额覆盖（租户级别覆盖订阅计划默认值）
7. 无租户上下文时不做配额检查（平台级操作）
"""
import pytest
import pytest_asyncio
from datetime import datetime, date, time, timedelta
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.common.quota import (
    QuotaChecker,
    QuotaCheckError,
    check_quota,
)
from app.models.tenant import Tenant, SubscriptionPlan
from app.models.store import Store
from app.models.admin import Admin, Role
from app.models.doctor import Doctor
from app.models.department import Department
from app.models.appointment import Appointment
from app.models.user import User, Patient
from app.core.security import get_password_hash


# ==================== Fixtures ====================

@pytest.fixture
def quota_checker(db_session: AsyncSession) -> QuotaChecker:
    """创建配额检查器"""
    return QuotaChecker(db_session)


@pytest_asyncio.fixture
async def subscription_plan_basic(db_session: AsyncSession) -> SubscriptionPlan:
    """创建基础订阅计划"""
    plan = SubscriptionPlan(
        id=str(uuid4()),
        plan_code="basic",
        name="基础版",
        max_stores=2,
        max_admins=3,
        max_doctors=10,
        max_appointments_per_month=100,
        status=1,
        is_default=True,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(plan)
    await db_session.commit()
    await db_session.refresh(plan)
    return plan


@pytest_asyncio.fixture
async def tenant_with_quota(
    db_session: AsyncSession,
    subscription_plan_basic: SubscriptionPlan
) -> Tenant:
    """创建有配额限制的租户"""
    tenant = Tenant(
        id=str(uuid4()),
        tenant_code="quota_test",
        name="配额测试租户",
        status=1,
        subscription_plan_id=subscription_plan_basic.id,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(tenant)
    await db_session.commit()
    await db_session.refresh(tenant)
    return tenant


@pytest_asyncio.fixture
async def tenant_with_custom_quota(db_session: AsyncSession) -> Tenant:
    """创建有自定义配额的租户（覆盖计划默认值）"""
    tenant = Tenant(
        id=str(uuid4()),
        tenant_code="custom_quota",
        name="自定义配额租户",
        status=1,
        max_stores=1,  # 自定义限制为1个门店
        max_admins=1,  # 自定义限制为1个管理员
        max_doctors=2,  # 自定义限制为2个医生
        max_appointments_per_month=10,  # 自定义限制为10个预约/月
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(tenant)
    await db_session.commit()
    await db_session.refresh(tenant)
    return tenant


@pytest_asyncio.fixture
async def tenant_store(
    db_session: AsyncSession,
    tenant_with_quota: Tenant
) -> Store:
    """创建租户的门店"""
    store = Store(
        id=str(uuid4()),
        tenant_id=tenant_with_quota.id,
        name="配额测试门店",
        code="quota_store",
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(store)
    await db_session.commit()
    await db_session.refresh(store)
    return store


@pytest_asyncio.fixture
async def tenant_department(
    db_session: AsyncSession,
    tenant_with_quota: Tenant,
    tenant_store: Store
) -> Department:
    """创建租户的科室"""
    dept = Department(
        id=str(uuid4()),
        tenant_id=tenant_with_quota.id,
        store_id=tenant_store.id,
        name="测试科室",
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(dept)
    await db_session.commit()
    await db_session.refresh(dept)
    return dept


@pytest_asyncio.fixture
async def tenant_role(db_session: AsyncSession, tenant_with_quota: Tenant) -> Role:
    """创建租户角色"""
    import json
    role = Role(
        id=str(uuid4()),
        tenant_id=tenant_with_quota.id,
        name="测试角色",
        code="TEST_ROLE",
        permissions=json.dumps([]),
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(role)
    await db_session.commit()
    await db_session.refresh(role)
    return role


# ==================== 门店配额测试 ====================

@pytest.mark.asyncio
async def test_store_quota_check_pass(
    db_session: AsyncSession,
    quota_checker: QuotaChecker,
    tenant_with_quota: Tenant
):
    """测试门店配额检查通过（未达上限）"""
    # 基础计划允许2个门店，当前0个，应该通过
    await quota_checker.check_stores_quota(tenant_with_quota.id)


@pytest.mark.asyncio
async def test_store_quota_check_fail(
    db_session: AsyncSession,
    quota_checker: QuotaChecker,
    tenant_with_quota: Tenant
):
    """测试门店配额检查失败（已达上限）"""
    # 创建2个门店（达到上限）
    for i in range(2):
        store = Store(
            id=str(uuid4()),
            tenant_id=tenant_with_quota.id,
            name=f"门店{i+1}",
            code=f"store_{i+1}",
            status=1,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db_session.add(store)
    await db_session.commit()

    # 第3个门店应该触发配额错误
    with pytest.raises(QuotaCheckError) as exc_info:
        await quota_checker.check_stores_quota(tenant_with_quota.id)

    assert exc_info.value.quota_type == "stores"
    assert exc_info.value.current == 2
    assert exc_info.value.limit == 2
    assert "门店数量已达上限" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_store_quota_custom_override(
    db_session: AsyncSession,
    quota_checker: QuotaChecker,
    tenant_with_custom_quota: Tenant
):
    """测试租户自定义配额覆盖计划默认值"""
    # 自定义配额只允许1个门店
    store = Store(
        id=str(uuid4()),
        tenant_id=tenant_with_custom_quota.id,
        name="唯一门店",
        code="only_store",
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(store)
    await db_session.commit()

    # 第2个门店应该触发配额错误
    with pytest.raises(QuotaCheckError) as exc_info:
        await quota_checker.check_stores_quota(tenant_with_custom_quota.id)

    assert exc_info.value.limit == 1


# ==================== 管理员配额测试 ====================

@pytest.mark.asyncio
async def test_admin_quota_check_pass(
    db_session: AsyncSession,
    quota_checker: QuotaChecker,
    tenant_with_quota: Tenant
):
    """测试管理员配额检查通过（未达上限）"""
    await quota_checker.check_admins_quota(tenant_with_quota.id)


@pytest.mark.asyncio
async def test_admin_quota_check_fail(
    db_session: AsyncSession,
    quota_checker: QuotaChecker,
    tenant_with_quota: Tenant,
    tenant_role: Role
):
    """测试管理员配额检查失败（已达上限）"""
    # 创建3个管理员（达到上限）
    for i in range(3):
        admin = Admin(
            id=str(uuid4()),
            tenant_id=tenant_with_quota.id,
            username=f"admin_{i+1}",
            password_hash=get_password_hash("password123"),
            name=f"管理员{i+1}",
            role_id=tenant_role.id,
            status=1,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db_session.add(admin)
    await db_session.commit()

    # 第4个管理员应该触发配额错误
    with pytest.raises(QuotaCheckError) as exc_info:
        await quota_checker.check_admins_quota(tenant_with_quota.id)

    assert exc_info.value.quota_type == "admins"
    assert exc_info.value.current == 3
    assert exc_info.value.limit == 3


# ==================== 医生配额测试 ====================

@pytest.mark.asyncio
async def test_doctor_quota_check_pass(
    db_session: AsyncSession,
    quota_checker: QuotaChecker,
    tenant_with_quota: Tenant
):
    """测试医生配额检查通过（未达上限）"""
    await quota_checker.check_doctors_quota(tenant_with_quota.id)


@pytest.mark.asyncio
async def test_doctor_quota_check_fail(
    db_session: AsyncSession,
    quota_checker: QuotaChecker,
    tenant_with_quota: Tenant,
    tenant_department: Department,
    tenant_store: Store
):
    """测试医生配额检查失败（已达上限）"""
    # 创建10个医生（达到上限）
    for i in range(10):
        doctor = Doctor(
            id=str(uuid4()),
            tenant_id=tenant_with_quota.id,
            store_id=tenant_store.id,
            department_id=tenant_department.id,
            name=f"医生{i+1}",
            username=f"doctor_{i+1}",
            phone=f"1390013{str(i).zfill(4)}",
            password_hash=get_password_hash("password123"),
            status=1,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db_session.add(doctor)
    await db_session.commit()

    # 第11个医生应该触发配额错误
    with pytest.raises(QuotaCheckError) as exc_info:
        await quota_checker.check_doctors_quota(tenant_with_quota.id)

    assert exc_info.value.quota_type == "doctors"
    assert exc_info.value.current == 10
    assert exc_info.value.limit == 10


# ==================== 预约配额测试 ====================

@pytest_asyncio.fixture
async def tenant_user(db_session: AsyncSession, tenant_with_quota: Tenant) -> User:
    """创建租户用户"""
    user = User(
        id=str(uuid4()),
        tenant_id=tenant_with_quota.id,
        phone="13800138000",
        password_hash=get_password_hash("password123"),
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
async def tenant_patient(
    db_session: AsyncSession,
    tenant_user: User,
    tenant_with_quota: Tenant,
    tenant_store: Store
) -> Patient:
    """创建租户患者"""
    patient = Patient(
        id=str(uuid4()),
        tenant_id=tenant_with_quota.id,
        store_id=tenant_store.id,
        user_id=tenant_user.id,
        name="测试患者",
        phone="13800138000",
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(patient)
    await db_session.commit()
    await db_session.refresh(patient)
    return patient


@pytest_asyncio.fixture
async def tenant_doctor(
    db_session: AsyncSession,
    tenant_with_quota: Tenant,
    tenant_store: Store,
    tenant_department: Department
) -> Doctor:
    """创建租户医生"""
    doctor = Doctor(
        id=str(uuid4()),
        tenant_id=tenant_with_quota.id,
        store_id=tenant_store.id,
        department_id=tenant_department.id,
        name="测试医生",
        username="test_doctor",
        phone="13900130000",
        password_hash=get_password_hash("password123"),
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(doctor)
    await db_session.commit()
    await db_session.refresh(doctor)
    return doctor


@pytest_asyncio.fixture
async def tenant_schedule(
    db_session: AsyncSession,
    tenant_with_quota: Tenant,
    tenant_store: Store,
    tenant_doctor: Doctor
):
    """创建租户排班"""
    from app.models.schedule import Schedule
    tomorrow = date.today() + timedelta(days=1)
    schedule = Schedule(
        id=str(uuid4()),
        tenant_id=tenant_with_quota.id,
        doctor_id=tenant_doctor.id,
        store_id=tenant_store.id,
        schedule_date=tomorrow,
        time_slot="morning",
        start_time=time(8, 0),
        end_time=time(12, 0),
        total_slots=50,
        booked_slots=0,
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(schedule)
    await db_session.commit()
    await db_session.refresh(schedule)
    return schedule


@pytest.mark.asyncio
async def test_appointment_quota_check_pass(
    db_session: AsyncSession,
    quota_checker: QuotaChecker,
    tenant_with_quota: Tenant
):
    """测试预约配额检查通过（未达月度上限）"""
    await quota_checker.check_appointments_quota(tenant_with_quota.id)


@pytest.mark.asyncio
async def test_appointment_quota_check_fail(
    db_session: AsyncSession,
    quota_checker: QuotaChecker,
    tenant_with_quota: Tenant,
    tenant_schedule,
    tenant_patient: Patient,
    tenant_doctor: Doctor,
    tenant_user: User
):
    """测试预约配额检查失败（已达月度上限）"""
    # 创建100个预约（达到上限）
    for i in range(100):
        appointment = Appointment(
            id=str(uuid4()),
            tenant_id=tenant_with_quota.id,
            appointment_no=f"YY{uuid4().hex[:12].upper()}",
            user_id=tenant_user.id,
            patient_id=tenant_patient.id,
            doctor_id=tenant_doctor.id,
            schedule_id=tenant_schedule.id,
            queue_number=i + 1,
            status=1,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db_session.add(appointment)
    await db_session.commit()

    # 第101个预约应该触发配额错误
    with pytest.raises(QuotaCheckError) as exc_info:
        await quota_checker.check_appointments_quota(tenant_with_quota.id)

    assert exc_info.value.quota_type == "appointments_per_month"
    assert exc_info.value.current == 100
    assert exc_info.value.limit == 100


# ==================== 通用 check_quota 函数测试 ====================

@pytest.mark.asyncio
async def test_check_quota_function_stores(
    db_session: AsyncSession,
    tenant_with_custom_quota: Tenant
):
    """测试通用 check_quota 函数 - 门店"""
    # 创建1个门店
    store = Store(
        id=str(uuid4()),
        tenant_id=tenant_with_custom_quota.id,
        name="门店",
        code="store",
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(store)
    await db_session.commit()

    with pytest.raises(QuotaCheckError):
        await check_quota(tenant_with_custom_quota.id, "stores", db_session)


@pytest.mark.asyncio
async def test_check_quota_function_admins(
    db_session: AsyncSession,
    tenant_with_custom_quota: Tenant,
    tenant_role: Role
):
    """测试通用 check_quota 函数 - 管理员"""
    # 创建1个管理员
    admin = Admin(
        id=str(uuid4()),
        tenant_id=tenant_with_custom_quota.id,
        username="admin",
        password_hash=get_password_hash("password123"),
        name="管理员",
        role_id=tenant_role.id,
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(admin)
    await db_session.commit()

    with pytest.raises(QuotaCheckError):
        await check_quota(tenant_with_custom_quota.id, "admins", db_session)


@pytest.mark.asyncio
async def test_check_quota_function_doctors(
    db_session: AsyncSession,
    tenant_with_custom_quota: Tenant,
    tenant_store: Store,
    tenant_department: Department
):
    """测试通用 check_quota 函数 - 医生"""
    # 创建2个医生
    for i in range(2):
        doctor = Doctor(
            id=str(uuid4()),
            tenant_id=tenant_with_custom_quota.id,
            store_id=tenant_store.id,
            department_id=tenant_department.id,
            name=f"医生{i+1}",
            username=f"doctor_{i+1}",
            phone=f"1390013{str(i).zfill(4)}",
            password_hash=get_password_hash("password123"),
            status=1,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db_session.add(doctor)

    # 为自定义配额租户创建门店和科室
    store = Store(
        id=str(uuid4()),
        tenant_id=tenant_with_custom_quota.id,
        name="自定义配额门店",
        code="custom_store",
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(store)

    dept = Department(
        id=str(uuid4()),
        tenant_id=tenant_with_custom_quota.id,
        store_id=store.id,
        name="科室",
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(dept)
    await db_session.commit()

    with pytest.raises(QuotaCheckError):
        await check_quota(tenant_with_custom_quota.id, "doctors", db_session)


@pytest.mark.asyncio
async def test_check_quota_function_invalid_type(
    db_session: AsyncSession,
    tenant_with_quota: Tenant
):
    """测试通用 check_quota 函数 - 不支持的资源类型"""
    with pytest.raises(ValueError) as exc_info:
        await check_quota(tenant_with_quota.id, "invalid_type", db_session)

    assert "不支持的资源类型" in str(exc_info.value)


# ==================== 无租户上下文测试 ====================

@pytest.mark.asyncio
async def test_quota_check_no_tenant(
    db_session: AsyncSession,
    quota_checker: QuotaChecker
):
    """测试无租户上下文时不做配额检查（平台级操作）"""
    # 不传租户ID，应该不抛出错误
    await quota_checker.check_stores_quota(None)
    await quota_checker.check_admins_quota(None)
    await quota_checker.check_doctors_quota(None)
    await quota_checker.check_appointments_quota(None)


@pytest.mark.asyncio
async def test_check_quota_no_tenant(
    db_session: AsyncSession
):
    """测试通用 check_quota 函数 - 无租户"""
    # 不传租户ID，应该不抛出错误
    await check_quota(None, "stores", db_session)
    await check_quota(None, "admins", db_session)
    await check_quota(None, "doctors", db_session)
    await check_quota(None, "appointments", db_session)


# ==================== 配额使用情况查询测试 ====================

@pytest.mark.asyncio
async def test_get_quota_usage(
    db_session: AsyncSession,
    quota_checker: QuotaChecker,
    tenant_with_quota: Tenant,
    tenant_store: Store,
    tenant_role: Role
):
    """测试获取配额使用情况"""
    # 创建一些资源
    admin = Admin(
        id=str(uuid4()),
        tenant_id=tenant_with_quota.id,
        username="admin",
        password_hash=get_password_hash("password123"),
        name="管理员",
        role_id=tenant_role.id,
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(admin)
    await db_session.commit()

    usage = await quota_checker.get_quota_usage(tenant_with_quota.id)

    assert "stores" in usage
    assert "admins" in usage
    assert "doctors" in usage
    assert "appointments_per_month" in usage

    assert usage["stores"]["current"] == 1
    assert usage["stores"]["limit"] == 2
    assert usage["admins"]["current"] == 1
    assert usage["admins"]["limit"] == 3


@pytest.mark.asyncio
async def test_get_quota_usage_no_tenant(
    db_session: AsyncSession,
    quota_checker: QuotaChecker
):
    """测试无租户时获取配额使用情况返回空字典"""
    usage = await quota_checker.get_quota_usage(None)
    assert usage == {}


# ==================== 订阅计划配额测试 ====================

@pytest.mark.asyncio
async def test_tenant_without_subscription_plan(
    db_session: AsyncSession,
    quota_checker: QuotaChecker
):
    """测试没有订阅计划的租户使用默认配额"""
    tenant = Tenant(
        id=str(uuid4()),
        tenant_code="no_plan",
        name="无计划租户",
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(tenant)
    await db_session.commit()
    await db_session.refresh(tenant)

    # 没有订阅计划时，使用模型中定义的默认值
    assert tenant.get_effective_max_stores() == 1
    assert tenant.get_effective_max_admins() == 5
    assert tenant.get_effective_max_doctors() == 50
    assert tenant.get_effective_max_appointments() == 1000

    # 可以正常进行配额检查
    await quota_checker.check_stores_quota(tenant.id)


# ==================== 错误信息格式测试 ====================

@pytest.mark.asyncio
async def test_quota_error_format(
    db_session: AsyncSession,
    quota_checker: QuotaChecker,
    tenant_with_custom_quota: Tenant
):
    """测试配额错误信息格式"""
    # 创建1个门店（达到自定义上限）
    store = Store(
        id=str(uuid4()),
        tenant_id=tenant_with_custom_quota.id,
        name="唯一门店",
        code="only_store",
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(store)
    await db_session.commit()

    with pytest.raises(QuotaCheckError) as exc_info:
        await quota_checker.check_stores_quota(tenant_with_custom_quota.id)

    error = exc_info.value
    assert error.status_code == 403
    assert "门店数量已达上限" in error.detail
    assert "当前：1" in error.detail
    assert "上限：1" in error.detail
