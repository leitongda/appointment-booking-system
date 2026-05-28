"""
医生预约设置服务单元测试 (A6 - 租户隔离)

覆盖:
- 租户隔离：不同租户之间的数据不可互相访问
- 创建时自动赋值 tenant_id
- 直接 tenant_id 过滤模式（非 Store JOIN）
"""
from datetime import datetime
from uuid import uuid4

import pytest
from unittest.mock import patch

from app.models.doctor_booking_setting import DoctorBookingSetting
from app.models.tenant import Tenant, SubscriptionPlan
from app.models.store import Store
from app.models.doctor import Doctor
from app.models.department import Department
from app.schemas.doctor_booking_setting import (
    DoctorBookingSettingCreate,
    DoctorBookingSettingQuery,
)
from app.modules.doctor_booking_settings.service import DoctorBookingSettingService


@pytest.mark.unit
class TestDoctorBookingSettingTenantIsolation:
    """测试医生预约设置的租户隔离"""

    async def _create_tenant_with_data(self, db_session, tenant_code, store_name, doctor_name):
        """辅助方法：创建一个完整的租户 + 门店 + 科室 + 医生"""
        plan = SubscriptionPlan(
            id=str(uuid4()),
            plan_code=f"plan_{tenant_code}",
            name=f"{tenant_code}计划",
            status=1,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db_session.add(plan)
        await db_session.flush()

        tenant = Tenant(
            id=str(uuid4()),
            tenant_code=tenant_code,
            name=f"租户{tenant_code}",
            status=1,
            subscription_plan_id=plan.id,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db_session.add(tenant)
        await db_session.flush()

        store = Store(
            id=str(uuid4()),
            name=store_name,
            address=f"{store_name}地址",
            phone="13800000000",
            tenant_id=tenant.id,
            status=1,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db_session.add(store)
        await db_session.flush()

        dept = Department(
            id=str(uuid4()),
            name="测试科室",
            store_id=store.id,
            tenant_id=tenant.id,
            status=1,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db_session.add(dept)
        await db_session.flush()

        doctor = Doctor(
            id=str(uuid4()),
            name=doctor_name,
            title="主治医师",
            department_id=dept.id,
            store_id=store.id,
            tenant_id=tenant.id,
            status=1,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db_session.add(doctor)
        await db_session.commit()

        return tenant, store, doctor

    async def _create_setting(self, db_session, tenant_id, store_id, doctor_id):
        """辅助方法：直接创建一条 DoctorBookingSetting 记录"""
        setting = DoctorBookingSetting(
            id=str(uuid4()),
            tenant_id=tenant_id,
            store_id=store_id,
            doctor_id=doctor_id,
            booking_start_offset=0,
            booking_range_days=14,
            release_time="08:00",
            status=1,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db_session.add(setting)
        await db_session.commit()
        await db_session.refresh(setting)
        return setting

    async def test_get_by_id_tenant_isolation(self, db_session):
        """租户A不能通过 get_by_id 查询到租户B的设置"""
        tenant_a, store_a, doctor_a = await self._create_tenant_with_data(
            db_session, "tenant_a", "门店A", "医生A"
        )
        tenant_b, store_b, doctor_b = await self._create_tenant_with_data(
            db_session, "tenant_b", "门店B", "医生B"
        )

        setting_a = await self._create_setting(db_session, tenant_a.id, store_a.id, doctor_a.id)
        setting_b = await self._create_setting(db_session, tenant_b.id, store_b.id, doctor_b.id)

        service = DoctorBookingSettingService(db_session)

        # 租户A 查自己的设置：能找到
        with patch("app.modules.doctor_booking_settings.service.get_current_tenant_id", return_value=tenant_a.id):
            result = await service.get_by_id(setting_a.id)
            assert result is not None
            assert result.id == setting_a.id

        # 租户A 查租户B的设置：找不到
        with patch("app.modules.doctor_booking_settings.service.get_current_tenant_id", return_value=tenant_a.id):
            result = await service.get_by_id(setting_b.id)
            assert result is None

        # 租户B 查租户A的设置：找不到
        with patch("app.modules.doctor_booking_settings.service.get_current_tenant_id", return_value=tenant_b.id):
            result = await service.get_by_id(setting_a.id)
            assert result is None

    async def test_get_by_store_and_doctor_tenant_isolation(self, db_session):
        """租户A不能通过 get_by_store_and_doctor 查询到租户B的设置"""
        tenant_a, store_a, doctor_a = await self._create_tenant_with_data(
            db_session, "tenant_a", "门店A", "医生A"
        )
        tenant_b, store_b, doctor_b = await self._create_tenant_with_data(
            db_session, "tenant_b", "门店B", "医生B"
        )

        await self._create_setting(db_session, tenant_a.id, store_a.id, doctor_a.id)
        await self._create_setting(db_session, tenant_b.id, store_b.id, doctor_b.id)

        service = DoctorBookingSettingService(db_session)

        # 租户A 查自己门店+医生的设置：能找到
        with patch("app.modules.doctor_booking_settings.service.get_current_tenant_id", return_value=tenant_a.id):
            result = await service.get_by_store_and_doctor(store_a.id, doctor_a.id)
            assert result is not None

        # 租户A 用租户B的 store_id + doctor_id 查：找不到（tenant_id 过滤）
        with patch("app.modules.doctor_booking_settings.service.get_current_tenant_id", return_value=tenant_a.id):
            result = await service.get_by_store_and_doctor(store_b.id, doctor_b.id)
            assert result is None

    async def test_get_effective_for_store_and_doctor_tenant_isolation(self, db_session):
        """租户A不能通过 get_effective_for_store_and_doctor 查询到租户B的设置"""
        tenant_a, store_a, doctor_a = await self._create_tenant_with_data(
            db_session, "tenant_a", "门店A", "医生A"
        )
        tenant_b, store_b, doctor_b = await self._create_tenant_with_data(
            db_session, "tenant_b", "门店B", "医生B"
        )

        setting_a = await self._create_setting(db_session, tenant_a.id, store_a.id, doctor_a.id)
        setting_b = await self._create_setting(db_session, tenant_b.id, store_b.id, doctor_b.id)

        service = DoctorBookingSettingService(db_session)

        # 租户A 查询有效的设置：能找到自己的
        with patch("app.modules.doctor_booking_settings.service.get_current_tenant_id", return_value=tenant_a.id):
            result = await service.get_effective_for_store_and_doctor(store_a.id, doctor_a.id)
            assert result is not None
            assert result.id == setting_a.id

        # 租户A 用租户B的参数查询：找不到
        with patch("app.modules.doctor_booking_settings.service.get_current_tenant_id", return_value=tenant_a.id):
            result = await service.get_effective_for_store_and_doctor(store_b.id, doctor_b.id)
            assert result is None

    async def test_get_list_tenant_isolation(self, db_session):
        """租户A通过 get_list 只能看到自己的设置，看不到租户B的"""
        tenant_a, store_a, doctor_a = await self._create_tenant_with_data(
            db_session, "tenant_a", "门店A", "医生A"
        )
        tenant_b, store_b, doctor_b = await self._create_tenant_with_data(
            db_session, "tenant_b", "门店B", "医生B"
        )

        await self._create_setting(db_session, tenant_a.id, store_a.id, doctor_a.id)
        await self._create_setting(db_session, tenant_b.id, store_b.id, doctor_b.id)

        service = DoctorBookingSettingService(db_session)

        # 租户A 列表：只有 1 条
        with patch("app.modules.doctor_booking_settings.service.get_current_tenant_id", return_value=tenant_a.id):
            query = DoctorBookingSettingQuery(page=1, page_size=10)
            items, total = await service.get_list(query)
            assert total == 1
            assert len(items) == 1
            assert items[0]["store_name"] == "门店A"

        # 租户B 列表：只有 1 条
        with patch("app.modules.doctor_booking_settings.service.get_current_tenant_id", return_value=tenant_b.id):
            query = DoctorBookingSettingQuery(page=1, page_size=10)
            items, total = await service.get_list(query)
            assert total == 1
            assert len(items) == 1
            assert items[0]["store_name"] == "门店B"

    async def test_get_existing_doctor_ids_tenant_isolation(self, db_session):
        """租户A通过 get_existing_doctor_ids 只能看到自己租户下的医生ID"""
        tenant_a, store_a, doctor_a = await self._create_tenant_with_data(
            db_session, "tenant_a", "门店A", "医生A"
        )
        tenant_b, store_b, doctor_b = await self._create_tenant_with_data(
            db_session, "tenant_b", "门店B", "医生B"
        )

        await self._create_setting(db_session, tenant_a.id, store_a.id, doctor_a.id)
        await self._create_setting(db_session, tenant_b.id, store_b.id, doctor_b.id)

        service = DoctorBookingSettingService(db_session)

        # 租户A：只能看到自己的 doctor_id
        with patch("app.modules.doctor_booking_settings.service.get_current_tenant_id", return_value=tenant_a.id):
            # 注意：get_existing_doctor_ids 按 store_id 过滤，这里用 store_a.id
            doctor_ids = await service.get_existing_doctor_ids(store_a.id)
            assert doctor_a.id in doctor_ids
            assert doctor_b.id not in doctor_ids

        # 租户B：只能看到自己的 doctor_id
        with patch("app.modules.doctor_booking_settings.service.get_current_tenant_id", return_value=tenant_b.id):
            doctor_ids = await service.get_existing_doctor_ids(store_b.id)
            assert doctor_b.id in doctor_ids
            assert doctor_a.id not in doctor_ids

    async def test_create_auto_assigns_tenant_id(self, db_session, test_tenant, test_store, test_doctor):
        """创建设置时，tenant_id 自动从上下文获取"""
        service = DoctorBookingSettingService(db_session)

        data = DoctorBookingSettingCreate(
            store_id=test_store.id,
            doctor_id=test_doctor.id,
            booking_start_offset=1,
            booking_range_days=7,
            release_time="09:00",
            status=1,
        )

        with patch("app.modules.doctor_booking_settings.service.get_current_tenant_id", return_value=test_tenant.id):
            setting = await service.create(data)

            assert setting is not None
            assert setting.tenant_id == test_tenant.id
            assert setting.store_id == test_store.id
            assert setting.doctor_id == test_doctor.id

    async def test_direct_tenant_id_filtering_no_store_join(self, db_session):
        """验证直接 tenant_id 过滤模式（非 Store JOIN），get_by_id 不做 JOIN 查询"""
        tenant_a, store_a, doctor_a = await self._create_tenant_with_data(
            db_session, "tenant_a", "门店A", "医生A"
        )

        setting = await self._create_setting(db_session, tenant_a.id, store_a.id, doctor_a.id)

        service = DoctorBookingSettingService(db_session)

        # 使用 None 作为 tenant_id（不过滤）：应该能找到
        with patch("app.modules.doctor_booking_settings.service.get_current_tenant_id", return_value=None):
            result = await service.get_by_id(setting.id)
            assert result is not None

        # 使用正确的 tenant_id：能找到
        with patch("app.modules.doctor_booking_settings.service.get_current_tenant_id", return_value=tenant_a.id):
            result = await service.get_by_id(setting.id)
            assert result is not None

        # 使用错误的 tenant_id：找不到
        with patch("app.modules.doctor_booking_settings.service.get_current_tenant_id", return_value="wrong-tenant"):
            result = await service.get_by_id(setting.id)
            assert result is None
