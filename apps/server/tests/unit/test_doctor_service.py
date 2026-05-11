"""医生服务单元测试

测试医生 CRUD、认证、推荐医生列表等功能。
"""

import pytest
from datetime import date, timedelta
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from app.modules.doctors.service import DoctorService
from app.schemas.doctor import DoctorCreate, DoctorUpdate
from app.models.doctor import Doctor
from app.models.schedule import Schedule
from app.models.appointment import Appointment
from app.core.security import verify_password


@pytest.mark.unit
class TestDoctorQueryMixin:
    """医生查询服务测试"""

    async def test_get_by_id(self, db_session, test_doctor):
        """测试通过ID获取医生"""
        service = DoctorService(db_session)
        doctor = await service.get_by_id(test_doctor.id)

        assert doctor is not None
        assert doctor.id == test_doctor.id
        assert doctor.name == "测试医生"

    async def test_get_by_id_not_found(self, db_session):
        """测试获取不存在的医生"""
        service = DoctorService(db_session)
        doctor = await service.get_by_id(str(uuid4()))
        assert doctor is None

    async def test_get_by_phone(self, db_session, test_doctor):
        """测试通过手机号获取医生"""
        service = DoctorService(db_session)
        # 先设置手机号
        test_doctor.phone = "13800138888"
        test_doctor.password_hash = "$2b$12$test_hash"
        await db_session.commit()

        doctor = await service.get_by_phone("13800138888")

        assert doctor is not None
        assert doctor.phone == "13800138888"

    async def test_get_by_username(self, db_session, test_doctor):
        """测试通过用户名获取医生"""
        service = DoctorService(db_session)
        # 先设置用户名
        test_doctor.username = "doctor_test"
        await db_session.commit()

        doctor = await service.get_by_username("doctor_test")

        assert doctor is not None
        assert doctor.username == "doctor_test"

    async def test_authenticate_success(self, db_session, test_doctor):
        """测试认证成功"""
        from app.core.security import get_password_hash

        service = DoctorService(db_session)
        # 设置密码
        password = "password123"
        test_doctor.phone = "13800138888"
        test_doctor.password_hash = get_password_hash(password)
        await db_session.commit()

        doctor = await service.authenticate("13800138888", password)

        assert doctor is not None
        assert doctor.phone == "13800138888"

    async def test_authenticate_wrong_password(self, db_session, test_doctor):
        """测试认证失败（错误密码）"""
        from app.core.security import get_password_hash

        service = DoctorService(db_session)
        test_doctor.phone = "13800138888"
        test_doctor.password_hash = get_password_hash("password123")
        await db_session.commit()

        doctor = await service.authenticate("13800138888", "wrong_password")

        assert doctor is None

    async def test_authenticate_not_found(self, db_session):
        """测试认证失败（用户不存在）"""
        service = DoctorService(db_session)
        doctor = await service.authenticate("not_exist", "password")
        assert doctor is None

    async def test_update_login_info(self, db_session, test_doctor):
        """测试更新登录信息"""
        service = DoctorService(db_session)
        sync_mock = AsyncMock()
        with patch("app.modules.doctors.service_query.AccountSyncService.sync_doctor_to_account", sync_mock):
            await service.update_login_info(test_doctor.id, "192.168.1.1")

        await db_session.refresh(test_doctor)
        assert test_doctor.last_login_ip == "192.168.1.1"
        assert test_doctor.last_login_at is not None
        sync_mock.assert_awaited_once_with(db_session, test_doctor.id, operator_id=None)

    async def test_get_list(self, db_session, test_tenant, test_doctor):
        """测试获取医生列表"""
        service = DoctorService(db_session)
        doctors, total = await service.get_list(page=1, page_size=10)

        assert total >= 1
        assert len(doctors) >= 1

    async def test_get_list_with_name_filter(self, db_session, test_doctor):
        """测试按名称过滤"""
        service = DoctorService(db_session)
        doctors, total = await service.get_list(name="测试")

        assert total >= 1
        assert any(d.name == "测试医生" for d in doctors)

    async def test_get_list_with_department_filter(self, db_session, test_doctor):
        """测试按科室过滤"""
        service = DoctorService(db_session)
        doctors, total = await service.get_list(department_id=test_doctor.department_id)

        assert total >= 1
        assert all(d.department_id == test_doctor.department_id for d in doctors)

    async def test_get_list_with_store_filter(self, db_session, test_doctor):
        """测试按门店过滤"""
        service = DoctorService(db_session)
        doctors, total = await service.get_list(store_id=test_doctor.store_id)

        assert total >= 1
        assert all(d.store_id == test_doctor.store_id for d in doctors)

    async def test_get_recommended(self, db_session, test_tenant, test_doctor):
        """测试获取推荐医生"""
        # 设置为推荐
        test_doctor.is_recommended = 1
        await db_session.commit()

        service = DoctorService(db_session)
        doctors = await service.get_recommended()

        assert any(d.id == test_doctor.id for d in doctors)
        assert all(d.is_recommended == 1 for d in doctors)

    async def test_get_by_department(self, db_session, test_doctor):
        """测试获取科室的医生列表"""
        service = DoctorService(db_session)
        doctors = await service.get_by_department(test_doctor.department_id)

        assert len(doctors) >= 1
        assert all(d.department_id == test_doctor.department_id for d in doctors)

    async def test_get_all_active(self, db_session, test_doctor):
        """测试获取所有启用的医生"""
        service = DoctorService(db_session)
        doctors = await service.get_all_active()

        assert all(d.status == 1 for d in doctors)
        assert all(d.deleted_at is None for d in doctors)

    async def test_get_doctors_availability(self, db_session, test_tenant, test_doctor, test_store):
        """测试获取医生可用性"""
        # 创建有可用排班的医生
        tomorrow = date.today() + timedelta(days=1)
        schedule = Schedule(
            id=str(uuid4()),
            doctor_id=test_doctor.id,
            store_id=test_store.id,
            tenant_id=test_tenant.id,
            schedule_date=tomorrow,
            time_slot="morning",
            total_slots=10,
            booked_slots=5,
            status=1,
            created_at=test_doctor.created_at,
        )
        db_session.add(schedule)
        await db_session.commit()

        service = DoctorService(db_session)
        availability = await service.get_doctors_availability([test_doctor.id], days=7)

        assert availability.get(test_doctor.id) is True


@pytest.mark.unit
class TestDoctorMutationMixin:
    """医生变更服务测试"""

    async def test_create_doctor(self, db_session, test_tenant, test_department, test_store):
        """测试创建医生"""
        from app.middleware.tenant_context import set_tenant_context
        service = DoctorService(db_session)
        data = DoctorCreate(
            name="新医生",
            store_id=test_store.id,
            department_id=test_department.id,
            phone="13900139000",
            password="password123",
            title="主治医师",
            status=1,
        )

        # 设置租户上下文并 Mock quota check
        token = set_tenant_context(test_tenant.id)
        with patch("app.common.quota.check_quota", new_callable=AsyncMock):
            doctor = await service.create(data)
        set_tenant_context(None)  # 清理上下文

        assert doctor.name == "新医生"
        assert doctor.phone == "13900139000"
        assert doctor.department_id == test_department.id

    async def test_create_doctor_with_user(self, db_session, test_tenant, test_department, test_store):
        """测试创建带用户账号的医生"""
        from app.middleware.tenant_context import set_tenant_context
        service = DoctorService(db_session)
        data = DoctorCreate(
            name="带账号医生",
            store_id=test_store.id,
            department_id=test_department.id,
            phone="13900139001",
            password="password123",
            gender=1,
            status=1,
        )

        # 设置租户上下文并 Mock quota check
        token = set_tenant_context(test_tenant.id)
        with patch("app.common.quota.check_quota", new_callable=AsyncMock):
            doctor = await service.create(data)
        set_tenant_context(None)  # 清理上下文

        assert doctor.name == "带账号医生"
        assert doctor.user_id is not None

    async def test_update_doctor(self, db_session, test_doctor):
        """测试更新医生"""
        service = DoctorService(db_session)
        data = DoctorUpdate(name="更新后的医生")

        doctor = await service.update(test_doctor.id, data)

        assert doctor is not None
        assert doctor.name == "更新后的医生"

    async def test_update_doctor_password(self, db_session, test_doctor):
        """测试更新医生密码"""
        service = DoctorService(db_session)
        new_password = "new_password123"
        data = DoctorUpdate(password=new_password)

        doctor = await service.update(test_doctor.id, data)

        assert doctor is not None
        assert doctor.password_hash is not None
        # 验证新密码
        assert verify_password(new_password, doctor.password_hash)

    async def test_update_doctor_not_found(self, db_session):
        """测试更新不存在的医生"""
        service = DoctorService(db_session)
        data = DoctorUpdate(name="新名称")

        doctor = await service.update(str(uuid4()), data)

        assert doctor is None

    async def test_delete_doctor(self, db_session, test_tenant, test_department, test_store):
        """测试删除医生（软删除）"""
        # 创建新医生
        doctor = Doctor(
            id=str(uuid4()),
            name="待删除医生",
            tenant_id=test_tenant.id,
            department_id=test_department.id,
            store_id=test_store.id,
            status=1,
            created_at=test_department.created_at,
        )
        db_session.add(doctor)
        await db_session.commit()

        service = DoctorService(db_session)
        result = await service.delete(doctor.id)

        assert result is True

        # 验证软删除
        await db_session.refresh(doctor)
        assert doctor.deleted_at is not None
        assert doctor.status == 0

    async def test_delete_doctor_with_active_appointments(self, db_session, test_tenant, test_doctor, test_patient, test_user, test_schedule):
        """测试删除有活跃预约的医生"""
        # 创建活跃预约
        appointment = Appointment(
            id=str(uuid4()),
            appointment_no=f"YY{test_doctor.created_at.strftime('%Y%m%d%H%M%S')}1234",
            user_id=test_user.id,
            patient_id=test_patient.id,
            doctor_id=test_doctor.id,
            schedule_id=test_schedule.id,
            tenant_id=test_tenant.id,
            status=1,  # 已预约
            patient_name=test_patient.name,
            doctor_name=test_doctor.name,
            created_at=test_doctor.created_at,
        )
        db_session.add(appointment)
        await db_session.commit()

        service = DoctorService(db_session)

        with pytest.raises(ValueError, match="该医生有.*条进行中的预约"):
            await service.delete(test_doctor.id)

    async def test_check_username_exists(self, db_session, test_doctor):
        """测试检查用户名是否存在"""
        test_doctor.username = "doctor_test"
        await db_session.commit()

        service = DoctorService(db_session)

        assert await service.check_username_exists("doctor_test") is True
        assert await service.check_username_exists("not_exist") is False

    async def test_check_username_exists_exclude_id(self, db_session, test_doctor):
        """测试检查用户名是否存在（排除自身）"""
        test_doctor.username = "doctor_test"
        await db_session.commit()

        service = DoctorService(db_session)

        # 排除自身应该返回 False
        assert await service.check_username_exists("doctor_test", exclude_id=test_doctor.id) is False

    async def test_name_to_pinyin(self, db_session):
        """测试姓名转拼音"""
        service = DoctorService(db_session)

        pinyin = service.name_to_pinyin("张三")
        assert pinyin == "zhangsan"

    async def test_generate_username(self, db_session, test_tenant, test_department, test_store):
        """测试生成用户名"""
        service = DoctorService(db_session)

        username = await service.generate_username("李四")

        assert username is not None
        assert "lisi" in username

    async def test_generate_username_duplicate(self, db_session, test_doctor):
        """测试生成用户名（重复时添加后缀）"""
        # 设置已存在的用户名
        test_doctor.username = "zhangsan"
        await db_session.commit()

        service = DoctorService(db_session)

        username = await service.generate_username("张三")

        # 应该添加数字后缀
        assert "zhangsan" in username
        assert username != "zhangsan"

    async def test_suggest_usernames(self, db_session):
        """测试建议用户名列表"""
        service = DoctorService(db_session)

        suggestions = await service.suggest_usernames("base", count=3)

        assert len(suggestions) > 0
        assert len(suggestions) <= 3
        assert all("base" in s for s in suggestions)

    async def test_batch_update_sort_order(self, db_session, test_tenant, test_department, test_store):
        """测试批量更新排序"""
        # 创建多个医生
        doctor1 = Doctor(
            id=str(uuid4()),
            name="医生1",
            tenant_id=test_tenant.id,
            department_id=test_department.id,
            store_id=test_store.id,
            sort_order=1,
            status=1,
            created_at=test_department.created_at,
        )
        doctor2 = Doctor(
            id=str(uuid4()),
            name="医生2",
            tenant_id=test_tenant.id,
            department_id=test_department.id,
            store_id=test_store.id,
            sort_order=2,
            status=1,
            created_at=test_department.created_at,
        )
        db_session.add_all([doctor1, doctor2])
        await db_session.commit()

        service = DoctorService(db_session)
        items = [
            {"id": doctor1.id, "sort_order": 10},
            {"id": doctor2.id, "sort_order": 20},
        ]
        count = await service.batch_update_sort_order(items)

        assert count == 2

        # 验证排序已更新
        doctor1_updated = await db_session.get(Doctor, doctor1.id)
        doctor2_updated = await db_session.get(Doctor, doctor2.id)
        assert doctor1_updated.sort_order == 10
        assert doctor2_updated.sort_order == 20
