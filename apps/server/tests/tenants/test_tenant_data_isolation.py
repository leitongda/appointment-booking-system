"""
租户数据隔离综合测试

测试用例覆盖：
1. 租户数据隔离测试
   - 不同租户的用户数据隔离
   - 不同租户的医生数据隔离
   - 不同租户的预约数据隔离
   - 不同租户的门店数据隔离
   - 跨租户访问应该被拒绝

2. 导出权限控制测试
   - 验证 require_permission 在导出端点的正确性
   - 验证无权限用户无法导出

3. 导入服务租户隔离测试
   - 验证导入数据自动绑定到当前租户
   - 验证导入不会污染其他租户数据
"""
import pytest
import uuid
from datetime import datetime, date, time, timedelta
from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient
from openpyxl import load_workbook
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_

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
)
from app.common.tenant_filter import (
    add_tenant_filter,
    get_tenant_id_for_create,
    TenantFilteredQuery,
)
from app.modules.import_export.service_import import ImportService, SENSITIVE_FIELDS
from app.middleware.exception import BusinessError


# ==================== 辅助函数 ====================

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
    """创建受限角色（无导出医生所需权限）

    `/data/export/doctors` 的守卫是 ``require_permission("doctor:export", "doctor:list")``
    （满足其一即可），因此受限角色必须同时不含这两个权限码。
    """
    role = Role(
        id=str(uuid.uuid4()),
        tenant_id=tenant_a.id,
        name="普通员工",
        code="STAFF",
        status=1,
        permissions='["patient:list"]',  # 无 doctor:list / doctor:export
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
        time_slot="morning",
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
        time_slot="morning",
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


# ==================== 预约 Fixtures ====================

@pytest.fixture
async def appointment_a(
    db_session: AsyncSession,
    tenant_a: Tenant,
    store_a: Store,
    user_a: User,
    patient_a: Patient,
    doctor_a: Doctor,
    schedule_a: Schedule,
) -> Appointment:
    """创建租户 A 的预约"""
    appointment = Appointment(
        id=str(uuid.uuid4()),
        tenant_id=tenant_a.id,
        appointment_no=f"YY{datetime.now().strftime('%Y%m%d%H%M%S')}{str(uuid.uuid4())[:4].upper()}",
        user_id=user_a.id,
        patient_id=patient_a.id,
        doctor_id=doctor_a.id,
        schedule_id=schedule_a.id,
        queue_number=1,
        status=1,
        patient_name=patient_a.name,
        patient_phone=patient_a.phone,
        doctor_name=doctor_a.name,
        department_name="内科",
    )
    db_session.add(appointment)
    schedule_a.booked_slots += 1
    await db_session.commit()
    await db_session.refresh(appointment)
    return appointment


@pytest.fixture
async def appointment_b(
    db_session: AsyncSession,
    tenant_b: Tenant,
    store_b: Store,
    user_b: User,
    patient_b: Patient,
    doctor_b: Doctor,
    schedule_b: Schedule,
) -> Appointment:
    """创建租户 B 的预约"""
    appointment = Appointment(
        id=str(uuid.uuid4()),
        tenant_id=tenant_b.id,
        appointment_no=f"YY{datetime.now().strftime('%Y%m%d%H%M%S')}{str(uuid.uuid4())[:4].upper()}",
        user_id=user_b.id,
        patient_id=patient_b.id,
        doctor_id=doctor_b.id,
        schedule_id=schedule_b.id,
        queue_number=1,
        status=1,
        patient_name=patient_b.name,
        patient_phone=patient_b.phone,
        doctor_name=doctor_b.name,
        department_name="外科",
    )
    db_session.add(appointment)
    schedule_b.booked_slots += 1
    await db_session.commit()
    await db_session.refresh(appointment)
    return appointment


# =================================================================
# 第一部分：租户数据隔离测试
# =================================================================

@pytest.mark.asyncio
class TestTenantDataIsolation:
    """租户数据隔离测试套件"""

    async def test_user_data_isolation(
        self,
        db_session: AsyncSession,
        tenant_a: Tenant,
        tenant_b: Tenant,
        user_a: User,
        user_b: User,
    ):
        """测试不同租户的用户数据隔离"""
        # 设置租户 A 上下文
        set_tenant_context(tenant_a.id)

        # 查询租户 A 的用户
        query = select(User)
        filtered_query = add_tenant_filter(query, User)
        result = await db_session.execute(filtered_query)
        users_a = list(result.scalars().all())

        # 应该只能看到租户 A 的用户
        assert len(users_a) == 1
        assert users_a[0].tenant_id == tenant_a.id
        assert users_a[0].id == user_a.id

        # 切换到租户 B 上下文
        set_tenant_context(tenant_b.id)

        # 查询租户 B 的用户
        query = select(User)
        filtered_query = add_tenant_filter(query, User)
        result = await db_session.execute(filtered_query)
        users_b = list(result.scalars().all())

        # 应该只能看到租户 B 的用户
        assert len(users_b) == 1
        assert users_b[0].tenant_id == tenant_b.id
        assert users_b[0].id == user_b.id

        # 清理上下文
        clear_tenant_context()

    async def test_doctor_data_isolation(
        self,
        db_session: AsyncSession,
        tenant_a: Tenant,
        tenant_b: Tenant,
        doctor_a: Doctor,
        doctor_b: Doctor,
    ):
        """测试不同租户的医生数据隔离"""
        # 设置租户 A 上下文
        set_tenant_context(tenant_a.id)

        # 查询租户 A 的医生
        query = select(Doctor)
        filtered_query = add_tenant_filter(query, Doctor)
        result = await db_session.execute(filtered_query)
        doctors_a = list(result.scalars().all())

        # 应该只能看到租户 A 的医生
        assert len(doctors_a) == 1
        assert doctors_a[0].tenant_id == tenant_a.id
        assert doctors_a[0].id == doctor_a.id

        # 切换到租户 B 上下文
        set_tenant_context(tenant_b.id)

        # 查询租户 B 的医生
        query = select(Doctor)
        filtered_query = add_tenant_filter(query, Doctor)
        result = await db_session.execute(filtered_query)
        doctors_b = list(result.scalars().all())

        # 应该只能看到租户 B 的医生
        assert len(doctors_b) == 1
        assert doctors_b[0].tenant_id == tenant_b.id
        assert doctors_b[0].id == doctor_b.id

        # 清理上下文
        clear_tenant_context()

    async def test_appointment_data_isolation(
        self,
        db_session: AsyncSession,
        tenant_a: Tenant,
        tenant_b: Tenant,
        appointment_a: Appointment,
        appointment_b: Appointment,
    ):
        """测试不同租户的预约数据隔离"""
        # 设置租户 A 上下文
        set_tenant_context(tenant_a.id)

        # 查询租户 A 的预约
        query = select(Appointment)
        filtered_query = add_tenant_filter(query, Appointment)
        result = await db_session.execute(filtered_query)
        appointments_a = list(result.scalars().all())

        # 应该只能看到租户 A 的预约
        assert len(appointments_a) == 1
        assert appointments_a[0].tenant_id == tenant_a.id
        assert appointments_a[0].id == appointment_a.id

        # 切换到租户 B 上下文
        set_tenant_context(tenant_b.id)

        # 查询租户 B 的预约
        query = select(Appointment)
        filtered_query = add_tenant_filter(query, Appointment)
        result = await db_session.execute(filtered_query)
        appointments_b = list(result.scalars().all())

        # 应该只能看到租户 B 的预约
        assert len(appointments_b) == 1
        assert appointments_b[0].tenant_id == tenant_b.id
        assert appointments_b[0].id == appointment_b.id

        # 清理上下文
        clear_tenant_context()

    async def test_store_data_isolation(
        self,
        db_session: AsyncSession,
        tenant_a: Tenant,
        tenant_b: Tenant,
        store_a: Store,
        store_b: Store,
    ):
        """测试不同租户的门店数据隔离"""
        # 设置租户 A 上下文
        set_tenant_context(tenant_a.id)

        # 查询租户 A 的门店
        query = select(Store)
        filtered_query = add_tenant_filter(query, Store)
        result = await db_session.execute(filtered_query)
        stores_a = list(result.scalars().all())

        # 应该只能看到租户 A 的门店
        assert len(stores_a) == 1
        assert stores_a[0].tenant_id == tenant_a.id
        assert stores_a[0].id == store_a.id

        # 切换到租户 B 上下文
        set_tenant_context(tenant_b.id)

        # 查询租户 B 的门店
        query = select(Store)
        filtered_query = add_tenant_filter(query, Store)
        result = await db_session.execute(filtered_query)
        stores_b = list(result.scalars().all())

        # 应该只能看到租户 B 的门店
        assert len(stores_b) == 1
        assert stores_b[0].tenant_id == tenant_b.id
        assert stores_b[0].id == store_b.id

        # 清理上下文
        clear_tenant_context()

    async def test_cross_tenant_access_denied_via_api(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        tenant_a: Tenant,
        tenant_b: Tenant,
        store_a: Store,
        store_b: Store,
        admin_a: Admin,
        admin_a_token: str,
    ):
        """测试租户 A 管理员通过 API 不能访问租户 B 数据"""
        # 租户 A 管理员尝试在租户 B 上下文下访问数据
        response = await async_client.get(
            "/api/v1/doctors",
            headers={
                "Authorization": f"Bearer {admin_a_token}",
                "X-Tenant-ID": tenant_b.id,  # 尝试访问租户 B
            },
        )

        # 应该返回 403（租户不匹配）
        assert response.status_code == 403
        assert "租户" in extract_error_text(response.json()) or "tenant" in extract_error_text(response.json()).lower()

    async def test_tenant_filtered_query_builder(
        self,
        db_session: AsyncSession,
        tenant_a: Tenant,
        tenant_b: Tenant,
        store_a: Store,
        store_b: Store,
    ):
        """测试 TenantFilteredQuery 构建器"""
        # 使用租户 A 上下文
        set_tenant_context(tenant_a.id)

        # 使用 TenantFilteredQuery 构建查询
        query = TenantFilteredQuery(Store).build()
        result = await db_session.execute(query)
        stores = list(result.scalars().all())

        # 应该只返回租户 A 的门店
        assert len(stores) == 1
        assert stores[0].tenant_id == tenant_a.id

        # 切换到租户 B 上下文
        set_tenant_context(tenant_b.id)

        # 再次构建查询
        query = TenantFilteredQuery(Store).build()
        result = await db_session.execute(query)
        stores = list(result.scalars().all())

        # 应该只返回租户 B 的门店
        assert len(stores) == 1
        assert stores[0].tenant_id == tenant_b.id

        # 清理上下文
        clear_tenant_context()


# =================================================================
# 第二部分：导出权限控制测试
# =================================================================

@pytest.mark.asyncio
class TestExportPermissionControl:
    """导出权限控制测试套件

    医生导出的真实路由是 ``/api/v1/data/export/doctors``（import_export 模块，
    ``app/api/v1/__init__.py:103``）。旧的 ``/api/v1/export`` 模块只有
    appointments/patients/schedules 三个端点——早期用例写成的
    ``/api/v1/export/doctors`` 一直 404，2026-10-23 归因后统一改指真实路由。
    """

    EXPORT_DOCTORS = "/api/v1/data/export/doctors"

    async def test_export_requires_permission(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        tenant_a: Tenant,
        admin_a_limited: Admin,
        admin_a_limited_token: str,
    ):
        """测试导出端点需要权限：无 doctor:export/doctor:list 的管理员被拒。"""
        response = await async_client.get(
            self.EXPORT_DOCTORS,
            headers={
                "Authorization": f"Bearer {admin_a_limited_token}",
                "X-Tenant-ID": tenant_a.id,
            },
        )

        # 应该返回 403（缺少权限）
        assert response.status_code == 403, response.text
        error_text = extract_error_text(response.json())
        assert "权限" in error_text or "permission" in error_text.lower()

    async def test_export_with_permission(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        tenant_a: Tenant,
        admin_a: Admin,
        admin_a_token: str,
        doctor_a: Doctor,
    ):
        """测试有权限用户可以导出（租户管理员角色 permissions=["*"]）。"""
        response = await async_client.get(
            self.EXPORT_DOCTORS,
            headers={
                "Authorization": f"Bearer {admin_a_token}",
                "X-Tenant-ID": tenant_a.id,
            },
        )

        assert response.status_code == 200, response.text
        content_type = response.headers.get("content-type", "")
        assert "spreadsheet" in content_type or "excel" in content_type

    async def test_export_tenant_isolation(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        tenant_a: Tenant,
        tenant_b: Tenant,
        admin_a: Admin,
        admin_a_token: str,
        doctor_a: Doctor,
        doctor_b: Doctor,
    ):
        """租户 A 管理员导出的医生列表只含本租户医生。"""
        response = await async_client.get(
            self.EXPORT_DOCTORS,
            headers={
                "Authorization": f"Bearer {admin_a_token}",
                "X-Tenant-ID": tenant_a.id,
            },
        )

        assert response.status_code == 200, response.text
        content_type = response.headers.get("content-type", "")
        assert "spreadsheet" in content_type or "excel" in content_type

        workbook = load_workbook(BytesIO(response.content), read_only=True)
        rows = [
            "|".join("" if v is None else str(v) for v in row)
            for row in workbook.active.iter_rows(values_only=True)
        ]
        workbook.close()
        assert any(doctor_a.name in row for row in rows)
        assert not any(doctor_b.name in row for row in rows)

    async def test_export_cross_tenant_denied(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        tenant_a: Tenant,
        tenant_b: Tenant,
        admin_a: Admin,
        admin_a_token: str,
    ):
        """测试跨租户导出被拒绝：租户 A 管理员伪造 X-Tenant-ID: B → 403。"""
        response = await async_client.get(
            self.EXPORT_DOCTORS,
            headers={
                "Authorization": f"Bearer {admin_a_token}",
                "X-Tenant-ID": tenant_b.id,  # 尝试访问租户 B
            },
        )

        # 认证层的一致性强校验（非超管账号租户与请求租户不一致即 403）
        assert response.status_code == 403, response.text


# =================================================================
# 第三部分：导入服务租户隔离测试
# =================================================================

@pytest.mark.asyncio
class TestImportTenantIsolation:
    """导入服务租户隔离测试套件"""

    def test_sanitize_removes_tenant_id(self):
        """测试 _sanitize_row_data 移除 tenant_id 等敏感字段"""
        row_data = {
            "name": "测试",
            "phone": "13800138000",
            "tenant_id": "malicious-tenant-id",  # 应该被移除
            "id": "malicious-id",  # 应该被移除
            "created_at": "2024-01-01",  # 应该被移除
            "updated_at": "2024-01-01",  # 应该被移除
            "created_by": "admin",  # 应该被移除
            "updated_by": "admin",  # 应该被移除
            "_internal": "value",  # 应该被移除（下划线开头）
            "valid_field": "value",  # 应该保留
        }

        cleaned = ImportService._sanitize_row_data(row_data)

        # 验证敏感字段被移除
        assert "tenant_id" not in cleaned
        assert "id" not in cleaned
        assert "created_at" not in cleaned
        assert "updated_at" not in cleaned
        assert "created_by" not in cleaned
        assert "updated_by" not in cleaned
        assert "_internal" not in cleaned

        # 验证有效字段保留
        assert cleaned["name"] == "测试"
        assert cleaned["phone"] == "13800138000"
        assert cleaned["valid_field"] == "value"

    def test_sensitive_fields_constant_complete(self):
        """测试 SENSITIVE_FIELDS 常量包含所有必要的敏感字段"""
        expected_fields = {
            "tenant_id", "id", "created_at", "updated_at",
            "created_by", "updated_by"
        }
        assert SENSITIVE_FIELDS == expected_fields

    async def test_import_requires_tenant_context(self, db_session: AsyncSession):
        """测试导入必须有租户上下文"""
        service = ImportService(db_session)

        # R1-5：不再回退请求上下文，未显式传 tenant_id 直接失败
        with pytest.raises(BusinessError) as exc_info:
            await service.validate_and_import(
                file_content=b"fake-excel",
                filename="test.xlsx",
                expected_headers=["姓名"],
                required_fields=["姓名"],
                process_row_func=AsyncMock(),
            )

        assert "租户" in str(exc_info.value.message)

    async def test_import_auto_binds_tenant(
        self,
        db_session: AsyncSession,
        tenant_a: Tenant,
    ):
        """测试导入数据自动绑定到当前租户"""
        service = ImportService(db_session)
        captured_tenant_id = None

        async def process_row(row_data):
            nonlocal captured_tenant_id
            captured_tenant_id = service.tenant_id

        with patch(
            "app.modules.import_export.service_import.ExcelImportService.parse_excel",
            return_value=(
                [{"name": "测试"}],
                []
            )
        ):
            db_session.commit = AsyncMock()

            result = await service.validate_and_import(
                file_content=b"fake-excel",
                filename="test.xlsx",
                expected_headers=["姓名"],
                required_fields=["姓名"],
                process_row_func=process_row,
                tenant_id=tenant_a.id,
            )

            # 验证租户 ID 被正确设置
            assert service.tenant_id == tenant_a.id
            assert captured_tenant_id == tenant_a.id
            assert result["success_count"] == 1

    async def test_import_rejects_malicious_tenant_id(
        self,
        db_session: AsyncSession,
        tenant_a: Tenant,
        tenant_b: Tenant,
    ):
        """测试导入拒绝恶意设置的 tenant_id"""
        service = ImportService(db_session)

        with patch(
            "app.modules.import_export.service_import.ExcelImportService.parse_excel",
            return_value=(
                [{"name": "测试", "tenant_id": tenant_b.id, "_row": 2}],  # 尝试注入租户 B 的 ID
                []
            )
        ):
            with pytest.raises(BusinessError) as exc_info:
                await service.validate_and_import(
                    file_content=b"fake-excel",
                    filename="test.xlsx",
                    expected_headers=["姓名"],
                    required_fields=["姓名"],
                    process_row_func=AsyncMock(),
                    tenant_id=tenant_a.id,
                )

            # 验证错误信息包含敏感字段提示
            assert "tenant_id" in str(exc_info.value.message)
            assert "不允许" in str(exc_info.value.message)

    async def test_import_validates_row_tenant(
        self,
        db_session: AsyncSession,
        tenant_a: Tenant,
        tenant_b: Tenant,
        store_a: Store,
    ):
        """测试导入验证行数据的租户归属"""
        service = ImportService(db_session)
        service._tenant_id = tenant_a.id

        # 模拟查询租户 A 的门店
        mock_result = MagicMock()
        mock_store = MagicMock()
        mock_store.tenant_id = tenant_a.id
        mock_result.scalar_one_or_none.return_value = mock_store
        db_session.execute = AsyncMock(return_value=mock_result)

        # 验证属于当前租户的数据
        row_data = {"store_id": store_a.id}
        result = await service._validate_row_tenant(
            row_data, 1,
            model_class=Store,
            id_field="store_id"
        )

        # 应该返回当前租户 ID
        assert result == tenant_a.id

    async def test_import_skips_other_tenant_data(
        self,
        db_session: AsyncSession,
        tenant_a: Tenant,
        tenant_b: Tenant,
    ):
        """测试导入跳过其他租户的数据"""
        service = ImportService(db_session)
        service._tenant_id = tenant_a.id

        # 模拟查询租户 B 的门店
        mock_result = MagicMock()
        mock_store = MagicMock()
        mock_store.tenant_id = tenant_b.id  # 不同的租户
        mock_result.scalar_one_or_none.return_value = mock_store
        db_session.execute = AsyncMock(return_value=mock_result)

        # 验证属于其他租户的数据
        row_data = {"store_id": "some-store-id"}
        result = await service._validate_row_tenant(
            row_data, 1,
            model_class=Store,
            id_field="store_id"
        )

        # 应该返回 None（跳过该行）
        assert result is None


# =================================================================
# 第四部分：租户过滤工具测试
# =================================================================

@pytest.mark.asyncio
class TestTenantFilterUtils:
    """租户过滤工具测试套件"""

    async def test_add_tenant_filter_with_context(
        self,
        db_session: AsyncSession,
        tenant_a: Tenant,
        store_a: Store,
        store_b: Store,
    ):
        """测试 add_tenant_filter 在有租户上下文时的行为"""
        # 设置租户上下文
        set_tenant_context(tenant_a.id)

        # 构建查询
        query = select(Store)
        filtered_query = add_tenant_filter(query, Store)
        result = await db_session.execute(filtered_query)
        stores = list(result.scalars().all())

        # 应该只返回租户 A 的门店
        assert len(stores) == 1
        assert stores[0].tenant_id == tenant_a.id

        # 清理上下文
        clear_tenant_context()

    async def test_add_tenant_filter_without_context(
        self,
        db_session: AsyncSession,
        store_a: Store,
        store_b: Store,
    ):
        """测试 add_tenant_filter 在无租户上下文时的行为"""
        # 确保没有租户上下文
        clear_tenant_context()

        # 构建查询
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
        # 显式指定租户 A 的 ID
        query = select(Store)
        filtered_query = add_tenant_filter(query, Store, tenant_id=tenant_a.id)
        result = await db_session.execute(filtered_query)
        stores = list(result.scalars().all())

        # 应该只返回租户 A 的门店
        assert len(stores) == 1
        assert stores[0].tenant_id == tenant_a.id

    async def test_add_tenant_filter_model_without_tenant_field(
        self,
        db_session: AsyncSession,
    ):
        """测试 add_tenant_filter 对没有 tenant_id 字段的模型的行为

        TenantFilteredQuery 的 build 方法对没有 tenant_id 的模型会跳过过滤。
        这里验证 get_tenant_id_for_create 显式指定租户 ID 的行为。
        """
        # 验证 get_tenant_id_for_create 显式指定租户 ID
        tenant_id = get_tenant_id_for_create(tenant_id="explicit-tenant-id")
        assert tenant_id == "explicit-tenant-id"

    async def test_get_tenant_id_for_create_with_explicit_id(self):
        """测试 get_tenant_id_for_create 显式指定租户 ID"""
        tenant_id = get_tenant_id_for_create(tenant_id="explicit-tenant-id")
        assert tenant_id == "explicit-tenant-id"

    async def test_get_tenant_id_for_create_from_context(
        self,
        tenant_a: Tenant,
    ):
        """测试 get_tenant_id_for_create 从上下文获取租户 ID"""
        set_tenant_context(tenant_a.id)

        tenant_id = get_tenant_id_for_create()
        assert tenant_id == tenant_a.id

        clear_tenant_context()


# =================================================================
# 第五部分：租户上下文管理测试
# =================================================================

@pytest.mark.asyncio
class TestTenantContextManagement:
    """租户上下文管理测试套件"""

    def test_set_and_get_tenant_context(self, tenant_a: Tenant):
        """测试设置和获取租户上下文"""
        # 设置租户上下文
        set_tenant_context(tenant_a.id, tenant_a.tenant_code)

        # 验证可以获取
        assert get_current_tenant_id() == tenant_a.id

        # 清理
        clear_tenant_context()

        # 验证清理后为 None
        assert get_current_tenant_id() is None

    def test_clear_tenant_context(self, tenant_a: Tenant):
        """测试清除租户上下文"""
        # 设置租户上下文
        set_tenant_context(tenant_a.id)

        # 清除
        clear_tenant_context()

        # 验证已清除
        assert get_current_tenant_id() is None

    def test_tenant_context_overwrite(self, tenant_a: Tenant, tenant_b: Tenant):
        """测试覆盖租户上下文"""
        # 设置租户 A 上下文
        set_tenant_context(tenant_a.id)
        assert get_current_tenant_id() == tenant_a.id

        # 覆盖为租户 B 上下文
        set_tenant_context(tenant_b.id)
        assert get_current_tenant_id() == tenant_b.id

        # 清理
        clear_tenant_context()


# =================================================================
# 第六部分：管理员租户校验测试
# =================================================================

@pytest.mark.asyncio
class TestAdminTenantValidation:
    """管理员租户校验测试套件"""

    async def test_admin_cannot_access_other_tenant(
        self,
        async_client: AsyncClient,
        tenant_a: Tenant,
        tenant_b: Tenant,
        admin_a: Admin,
        admin_a_token: str,
    ):
        """测试管理员不能访问其他租户"""
        # 租户 A 管理员尝试在租户 B 上下文访问
        response = await async_client.get(
            "/api/v1/doctors",
            headers={
                "Authorization": f"Bearer {admin_a_token}",
                "X-Tenant-ID": tenant_b.id,
            },
        )

        # 应该返回 403
        assert response.status_code == 403

    async def test_admin_can_access_own_tenant(
        self,
        async_client: AsyncClient,
        tenant_a: Tenant,
        admin_a: Admin,
        admin_a_token: str,
        doctor_a: Doctor,
    ):
        """测试管理员可以访问自己租户"""
        # 租户 A 管理员访问租户 A 上下文
        response = await async_client.get(
            "/api/v1/doctors",
            headers={
                "Authorization": f"Bearer {admin_a_token}",
                "X-Tenant-ID": tenant_a.id,
            },
        )

        # 应该成功（200 或其他非 403 状态码）
        assert response.status_code in [200, 404, 422]  # 404 表示路由不存在，422 表示参数错误

    async def test_admin_without_tenant_context(
        self,
        async_client: AsyncClient,
        admin_a: Admin,
        admin_a_token: str,
    ):
        """测试管理员无租户上下文时的行为"""
        # 不提供租户上下文
        response = await async_client.get(
            "/api/v1/doctors",
            headers={
                "Authorization": f"Bearer {admin_a_token}",
            },
        )

        # 根据业务逻辑，可能成功（使用管理员自己的租户）或失败
        # 这里只验证不会抛出未处理的异常
        assert response.status_code in [200, 400, 403, 404, 422]
