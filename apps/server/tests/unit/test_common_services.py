"""常见服务模块测试"""
import pytest
from datetime import date, timedelta
from sqlalchemy import select

from app.models.common_service import CommonService, HealthReminder
from app.modules.common_services.service import CommonServiceService, HealthReminderService
from app.models.appointment import Appointment
from app.models.user import Patient
from app.models.department import Department
from app.models.doctor import Doctor


@pytest.mark.asyncio
class TestCommonServiceService:
    async def test_get_list_returns_services_for_tenant(
        self,
        db_session,
        test_tenant,
        test_store,
    ):
        """测试获取租户的常见服务列表"""
        service = CommonServiceService(db_session)

        # 创建测试服务
        test_service = CommonService(
            id="test-service-1",
            tenant_id=test_tenant.id,
            store_id=None,
            name="感冒护理",
            code="cold_care",
            variant="blue",
            link_type=1,
            link_url="/pages/department/index?dept=cold",
            sort_order=1,
            status=1,
        )
        db_session.add(test_service)
        await db_session.commit()

        # 获取列表
        items = await service.get_list()

        assert len(items) >= 1
        service_item = next((s for s in items if s.code == "cold_care"), None)
        assert service_item is not None
        assert service_item.name == "感冒护理"

    async def test_get_list_filters_by_store(
        self,
        db_session,
        test_tenant,
        test_store,
    ):
        """测试按门店过滤服务"""
        service = CommonServiceService(db_session)

        # 创建全局服务
        global_service = CommonService(
            id="global-service-1",
            tenant_id=test_tenant.id,
            store_id=None,
            name="全局服务",
            code="global",
            sort_order=1,
            status=1,
        )
        db_session.add(global_service)

        # 创建门店专属服务
        store_service = CommonService(
            id="store-service-1",
            tenant_id=test_tenant.id,
            store_id=test_store.id,
            name="门店服务",
            code="store",
            sort_order=2,
            status=1,
        )
        db_session.add(store_service)
        await db_session.commit()

        # 查询全局服务
        global_items = await service.get_list(store_id=None)
        global_codes = {s.code for s in global_items}
        assert "global" in global_codes
        assert "store" not in global_codes

        # 查询门店服务（应包含全局+门店）
        store_items = await service.get_list(store_id=test_store.id)
        store_codes = {s.code for s in store_items}
        assert "global" in store_codes
        assert "store" in store_codes

    async def test_get_list_filters_by_status(
        self,
        db_session,
        test_tenant,
    ):
        """测试按状态过滤服务"""
        service = CommonServiceService(db_session)

        # 创建启用的服务
        enabled_service = CommonService(
            id="enabled-service-1",
            tenant_id=test_tenant.id,
            store_id=None,
            name="启用服务",
            code="enabled",
            status=1,
        )
        db_session.add(enabled_service)

        # 创建禁用的服务
        disabled_service = CommonService(
            id="disabled-service-1",
            tenant_id=test_tenant.id,
            store_id=None,
            name="禁用服务",
            code="disabled",
            status=0,
        )
        db_session.add(disabled_service)
        await db_session.commit()

        # 只查询启用的
        items = await service.get_list(status=1)
        codes = {s.code for s in items}
        assert "enabled" in codes
        assert "disabled" not in codes

    async def test_get_service_with_department_mapping(
        self,
        db_session,
        test_tenant,
        test_store,
        test_department,
    ):
        """测试服务-科室映射"""
        service = CommonServiceService(db_session)

        # 创建关联科室的服务
        dept_service = CommonService(
            id="dept-service-1",
            tenant_id=test_tenant.id,
            store_id=None,
            name="科室服务",
            code="dept_service",
            department_id=test_department.id,
            link_type=3,
            sort_order=1,
            status=1,
        )
        db_session.add(dept_service)
        await db_session.commit()

        # 获取列表
        items = await service.get_list()
        service_item = next((s for s in items if s.code == "dept_service"), None)

        assert service_item is not None
        assert service_item.department_id == test_department.id


@pytest.mark.asyncio
class TestHealthReminderService:
    async def test_get_config_returns_tenant_reminders(
        self,
        db_session,
        test_tenant,
    ):
        """测试获取租户的健康提醒配置"""
        service = HealthReminderService(db_session)

        # 创建提醒配置
        reminder = HealthReminder(
            id="reminder-1",
            tenant_id=test_tenant.id,
            store_id=None,
            reminder_type="checkup",
            name="年度体检",
            title="体检提醒",
            content="建议每年进行一次体检",
            tips='["注意体检前空腹", "携带身份证件"]',
            recommended_interval=365,
            status=1,
        )
        db_session.add(reminder)
        await db_session.commit()

        # 获取配置
        items = await service.get_config()

        assert len(items) >= 1
        reminder_item = next((r for r in items if r.reminder_type == "checkup"), None)
        assert reminder_item is not None
        assert reminder_item.name == "年度体检"
        assert reminder_item.tips is not None

    async def test_get_config_filters_by_type(
        self,
        db_session,
        test_tenant,
    ):
        """测试按类型过滤提醒"""
        service = HealthReminderService(db_session)

        # 创建不同类型的提醒
        checkup_reminder = HealthReminder(
            id="checkup-1",
            tenant_id=test_tenant.id,
            reminder_type="checkup",
            name="体检提醒",
            status=1,
        )
        db_session.add(checkup_reminder)

        vaccine_reminder = HealthReminder(
            id="vaccine-1",
            tenant_id=test_tenant.id,
            reminder_type="vaccine",
            name="疫苗提醒",
            status=1,
        )
        db_session.add(vaccine_reminder)
        await db_session.commit()

        # 只查询体检提醒
        items = await service.get_config(reminder_type="checkup")

        assert all(r.reminder_type == "checkup" for r in items)

    async def test_get_user_reminder_returns_next_check_date(
        self,
        db_session,
        test_tenant,
        test_user,
        test_patient,
        test_doctor,
        test_store,
    ):
        """测试获取用户下次检查日期"""
        service = HealthReminderService(db_session)

        # 创建提醒配置
        reminder = HealthReminder(
            id="reminder-1",
            tenant_id=test_tenant.id,
            reminder_type="checkup",
            name="年度体检",
            recommended_interval=365,
            status=1,
        )
        db_session.add(reminder)

        # 创建历史预约
        past_appointment = Appointment(
            id="apt-1",
            user_id=test_user.id,
            patient_id=test_patient.id,
            doctor_id=test_doctor.id,
            tenant_id=test_tenant.id,
            store_id=test_store.id,
            appointment_no="TEST001",
            queue_number=1,
            status=4,  # 已完成
            patient_name=test_patient.name,
            patient_phone=test_patient.phone,
            doctor_name=test_doctor.name,
            department_name="测试科室",
            appointment_time=date.today() - timedelta(days=30),
        )
        db_session.add(past_appointment)
        await db_session.commit()

        # 获取用户提醒
        result = await service.get_user_reminder(test_user.id)

        assert result["has_data"] is True
        assert result["last_check_date"] is not None
        assert result["next_check_date"] is not None
        # 下次检查日期应该是上次检查日期 + 365天
        from datetime import datetime
        last_check = datetime.fromisoformat(result["last_check_date"]).date()
        next_check = datetime.fromisoformat(result["next_check_date"]).date()
        expected_next = last_check + timedelta(days=365)
        assert next_check == expected_next

    async def test_get_user_reminder_with_no_appointments(
        self,
        db_session,
        test_tenant,
        test_user,
        test_patient,
    ):
        """测试无预约历史时的用户提醒"""
        service = HealthReminderService(db_session)

        # 创建提醒配置
        reminder = HealthReminder(
            id="reminder-1",
            tenant_id=test_tenant.id,
            reminder_type="checkup",
            name="年度体检",
            recommended_interval=180,
            status=1,
        )
        db_session.add(reminder)
        await db_session.commit()

        # 获取用户提醒（无预约历史）
        result = await service.get_user_reminder(test_user.id)

        assert result["has_data"] is True
        assert result["last_check_date"] is None
        assert result["next_check_date"] is not None
        # 应该是今天 + 180天
        from datetime import datetime
        next_check = datetime.fromisoformat(result["next_check_date"]).date()
        expected_next = date.today() + timedelta(days=180)
        assert next_check == expected_next

    async def test_get_user_reminder_with_no_patient(
        self,
        db_session,
        test_tenant,
        test_user,
    ):
        """测试无就诊人时的用户提醒"""
        service = HealthReminderService(db_session)

        # 创建提醒配置
        reminder = HealthReminder(
            id="reminder-1",
            tenant_id=test_tenant.id,
            reminder_type="checkup",
            name="年度体检",
            status=1,
        )
        db_session.add(reminder)
        await db_session.commit()

        # 获取用户提醒（无就诊人）
        result = await service.get_user_reminder(test_user.id)

        assert result["has_data"] is False
        assert "暂无提醒" in result["reminder_content"]
