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


@pytest.mark.unit
class TestMultiTenantFixtures:
    """T-1：多租户测试基建（multi_tenant_env / admin_token_factory）"""

    async def test_env_tenants_are_isolated(self, multi_tenant_env):
        env = multi_tenant_env
        assert env.tenant_a.id != env.tenant_b.id
        assert env.tenant_a.tenant_code != env.tenant_b.tenant_code
        assert env.store_a.tenant_id == env.tenant_a.id
        assert env.store_b.tenant_id == env.tenant_b.id
        assert env.admin_a.tenant_id == env.tenant_a.id
        assert env.admin_b.tenant_id == env.tenant_b.id
        # 租户管理员角色必须归属本租户（非平台角色）
        assert env.role_a.tenant_id == env.tenant_a.id
        assert env.role_b.tenant_id == env.tenant_b.id

    async def test_admin_token_factory_roundtrip(self, admin_token_factory, multi_tenant_env):
        from app.core.security import decode_token

        token = admin_token_factory(multi_tenant_env.admin_a)
        payload = decode_token(token)
        assert payload is not None
        assert payload["sub"] == multi_tenant_env.admin_a.id
        assert payload["type"] == "admin"

    async def test_platform_admin_fixture_is_platform_scoped(self, multi_tenant_env):
        admin = multi_tenant_env.platform_admin
        assert admin.tenant_id is None
        assert admin.role is not None
        assert admin.role.tenant_id is None
        assert admin.role.code == "SUPER_ADMIN"

    async def test_tenant_admin_filter_anchors_to_own_tenant(self, multi_tenant_env):
        """非超管的租户过滤必须收敛到本租户，不得退化为 None（全平台）"""
        from app.common.tenant_deps import get_tenant_filter

        env = multi_tenant_env
        current_admin = {
            "id": env.admin_a.id,
            "tenant_id": env.tenant_a.id,
            "is_super_admin": False,
            "is_platform_admin": False,
        }
        assert get_tenant_filter(current_admin) == env.tenant_a.id
        # 平台管理员的跨租户视图是唯一例外
        platform = {"id": env.platform_admin.id, "tenant_id": None, "is_super_admin": True}
        assert get_tenant_filter(platform) is None

