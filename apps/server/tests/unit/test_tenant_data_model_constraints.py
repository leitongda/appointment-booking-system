"""P3 数据模型租户约束测试（SQLite create_all 语义验证）

覆盖：
- admins.username / roles.code 租户内唯一 + 平台行唯一；
- 业务单号（appointment_no）与配置编码（shift_types.code）租户内唯一；
- TenantUsageLog 每日唯一；
- content 四表 tenant_id 列存在。
"""
import uuid
from datetime import date, datetime

import bcrypt
import pytest
from sqlalchemy.exc import IntegrityError

from app.models.admin import Admin, Role
from app.models.appointment import Appointment
from app.models.content import Banner, News, Notice
from app.models.content_version import ContentVersion
from app.models.shift_type import ShiftType
from app.models.tenant import TenantUsageLog

pytestmark = [pytest.mark.unit]


def _hash() -> str:
    return bcrypt.hashpw(uuid.uuid4().hex.encode(), bcrypt.gensalt()).decode()


async def _role(db, tenant_id, code):
    role = Role(
        id=str(uuid.uuid4()),
        name=f"角色{code}",
        code=code,
        tenant_id=tenant_id,
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db.add(role)
    await db.commit()
    await db.refresh(role)
    return role


async def _admin(db, tenant_id, username):
    admin = Admin(
        id=str(uuid.uuid4()),
        username=username,
        password_hash=_hash(),
        tenant_id=tenant_id,
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db.add(admin)
    await db.commit()
    await db.refresh(admin)
    return admin


class TestAdminUsernameTenantUnique:
    async def test_same_username_allowed_across_tenants(self, db_session, multi_tenant_env):
        env = multi_tenant_env
        await _admin(db_session, env.tenant_a.id, "shared_admin")
        await _admin(db_session, env.tenant_b.id, "shared_admin")
        # 平台行（tenant_id=None）同名也允许
        await _admin(db_session, None, "shared_admin")

    async def test_duplicate_within_tenant_rejected(self, db_session, multi_tenant_env):
        env = multi_tenant_env
        await _admin(db_session, env.tenant_a.id, "dup_admin")
        with pytest.raises(IntegrityError):
            await _admin(db_session, env.tenant_a.id, "dup_admin")

    async def test_duplicate_platform_username_rejected(self, db_session):
        await _admin(db_session, None, "platform_dup")
        with pytest.raises(IntegrityError):
            await _admin(db_session, None, "platform_dup")


class TestRoleCodeTenantUnique:
    async def test_same_code_allowed_across_tenants(self, db_session, multi_tenant_env):
        env = multi_tenant_env
        await _role(db_session, env.tenant_a.id, "SAME_CODE")
        await _role(db_session, env.tenant_b.id, "SAME_CODE")
        await _role(db_session, None, "SAME_CODE")

    async def test_duplicate_within_tenant_rejected(self, db_session, multi_tenant_env):
        env = multi_tenant_env
        await _role(db_session, env.tenant_a.id, "DUP_CODE")
        with pytest.raises(IntegrityError):
            await _role(db_session, env.tenant_a.id, "DUP_CODE")

    async def test_duplicate_platform_code_rejected(self, db_session):
        await _role(db_session, None, "PLATFORM_DUP")
        with pytest.raises(IntegrityError):
            await _role(db_session, None, "PLATFORM_DUP")


class TestBusinessNumberTenantUnique:
    async def test_appointment_no_tenant_scoped(self, db_session, factory, multi_tenant_env):
        env = multi_tenant_env
        user_a, patient_a = await factory.create_patient(env.tenant_a.id)
        user_b, patient_b = await factory.create_patient(env.tenant_b.id)
        schedule_a = await factory.create_schedule(env.tenant_a.id)
        schedule_b = await factory.create_schedule(env.tenant_b.id)

        common_no = "YY-TENANT-SHARED-001"
        appt_a = await factory.create_appointment(
            env.tenant_a.id, schedule_a.doctor_id, schedule_a.id,
            patient_a.id, user_a.id, appointment_no=common_no,
        )
        appt_b = await factory.create_appointment(
            env.tenant_b.id, schedule_b.doctor_id, schedule_b.id,
            patient_b.id, user_b.id, appointment_no=common_no,
        )
        assert appt_a.appointment_no == appt_b.appointment_no == common_no

        with pytest.raises(IntegrityError):
            await factory.create_appointment(
                env.tenant_a.id, schedule_a.doctor_id, schedule_a.id,
                patient_a.id, user_a.id, appointment_no=common_no,
            )


class TestShiftTypeCodeTenantUnique:
    async def test_code_tenant_scoped(self, db_session, multi_tenant_env):
        env = multi_tenant_env
        for tenant_id in (env.tenant_a.id, env.tenant_b.id, None):
            db_session.add(
                ShiftType(
                    id=str(uuid.uuid4()),
                    code="OPD",
                    name="门诊",
                    enabled=True,
                    tenant_id=tenant_id,
                    created_at=datetime.now(),
                    updated_at=datetime.now(),
                )
            )
        await db_session.commit()

        db_session.add(
            ShiftType(
                id=str(uuid.uuid4()),
                code="OPD",
                name="门诊重复",
                enabled=True,
                tenant_id=env.tenant_a.id,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
        )
        with pytest.raises(IntegrityError):
            await db_session.commit()


class TestTenantUsageDailyUnique:
    async def test_same_tenant_same_day_rejected(self, db_session, multi_tenant_env):
        env = multi_tenant_env
        day = date.today()
        db_session.add(
            TenantUsageLog(
                id=str(uuid.uuid4()),
                tenant_id=env.tenant_a.id,
                usage_date=day,
                created_at=datetime.now(),
            )
        )
        await db_session.commit()

        db_session.add(
            TenantUsageLog(
                id=str(uuid.uuid4()),
                tenant_id=env.tenant_a.id,
                usage_date=day,
                created_at=datetime.now(),
            )
        )
        with pytest.raises(IntegrityError):
            await db_session.commit()


class TestContentTenantColumns:
    async def test_content_tables_have_tenant_column(self, db_session, multi_tenant_env):
        env = multi_tenant_env
        rows = [
            News(id=str(uuid.uuid4()), tenant_id=env.tenant_a.id, title="新闻", is_deleted=False),
            Notice(id=str(uuid.uuid4()), tenant_id=env.tenant_a.id, title="公告", is_deleted=False),
            Banner(id=str(uuid.uuid4()), tenant_id=env.tenant_a.id, image_url="http://x", is_deleted=False),
            ContentVersion(
                id=str(uuid.uuid4()),
                tenant_id=env.tenant_a.id,
                content_type="news",
                content_id="x",
                snapshot="{}",
            ),
        ]
        db_session.add_all(rows)
        await db_session.commit()
        assert all(row.tenant_id == env.tenant_a.id for row in rows)
