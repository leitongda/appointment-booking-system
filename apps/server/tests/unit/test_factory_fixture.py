"""TestDataFactory 冒烟测试"""
import pytest


@pytest.mark.unit
class TestFactorySmoke:
    """验证 factory fixture 可以正常创建各种测试数据"""

    async def test_create_tenant(self, factory):
        tenant = await factory.create_tenant()
        assert tenant.id is not None
        assert tenant.name == "测试租户"

    async def test_create_doctor(self, factory):
        doctor = await factory.create_doctor(name="张医生")
        assert doctor.name == "张医生"
        assert doctor.tenant_id is not None
        assert doctor.store_id is not None
        assert doctor.department_id is not None

    async def test_create_appointment(self, factory):
        appointment = await factory.create_appointment()
        assert appointment.id is not None
        assert appointment.status == 1
        assert appointment.tenant_id is not None

    async def test_create_full_chain(self, factory):
        data = await factory.create_full_chain()
        assert data.tenant.id is not None
        assert data.store.tenant_id == data.tenant.id
        assert data.department.store_id == data.store.id
        assert data.doctor.department_id == data.department.id
        assert data.schedule.doctor_id == data.doctor.id
        assert data.appointment.doctor_id == data.doctor.id

    async def test_override_fields(self, factory):
        doctor = await factory.create_doctor(name="李主任", title="主任医师")
        assert doctor.name == "李主任"
        assert doctor.title == "主任医师"
