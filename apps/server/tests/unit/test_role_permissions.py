"""统一角色权限配置单元测试

测试 role_permissions.py 中的权限定义、权限匹配逻辑和角色权限映射。
"""
import pytest

from app.common.role_permissions import (
    DOCTOR_PERMISSIONS,
    USER_PERMISSIONS,
    SYSTEM_ROLES,
    check_permission_match,
    get_permissions_for_role_type,
)


# ================================================================
# DOCTOR_PERMISSIONS 验证
# ================================================================


@pytest.mark.unit
class TestDoctorPermissions:
    """测试医生权限集合定义"""

    def test_contains_schedule_view(self):
        assert "doctor:schedule:view" in DOCTOR_PERMISSIONS

    def test_contains_schedule_edit(self):
        assert "doctor:schedule:edit" in DOCTOR_PERMISSIONS

    def test_contains_appointment_view(self):
        assert "doctor:appointment:view" in DOCTOR_PERMISSIONS

    def test_contains_appointment_edit(self):
        assert "doctor:appointment:edit" in DOCTOR_PERMISSIONS

    def test_contains_patient_view(self):
        assert "doctor:patient:view" in DOCTOR_PERMISSIONS

    def test_contains_consultation_wildcard(self):
        assert "doctor:consultation:*" in DOCTOR_PERMISSIONS

    def test_contains_profile_edit(self):
        assert "doctor:profile:edit" in DOCTOR_PERMISSIONS

    def test_contains_message_view(self):
        assert "doctor:message:view" in DOCTOR_PERMISSIONS

    def test_contains_statistics_view(self):
        assert "doctor:statistics:view" in DOCTOR_PERMISSIONS

    def test_is_frozenset_or_set(self):
        assert isinstance(DOCTOR_PERMISSIONS, set)


# ================================================================
# USER_PERMISSIONS 验证
# ================================================================


@pytest.mark.unit
class TestUserPermissions:
    """测试用户权限集合定义"""

    def test_contains_appointment_create(self):
        assert "patient:appointment:create" in USER_PERMISSIONS

    def test_contains_appointment_cancel(self):
        assert "patient:appointment:cancel" in USER_PERMISSIONS

    def test_contains_appointment_view(self):
        assert "patient:appointment:view" in USER_PERMISSIONS

    def test_contains_profile_edit(self):
        assert "patient:profile:edit" in USER_PERMISSIONS

    def test_contains_patient_manage(self):
        assert "patient:patient:manage" in USER_PERMISSIONS

    def test_contains_message_view(self):
        assert "patient:message:view" in USER_PERMISSIONS

    def test_contains_review_create(self):
        assert "patient:review:create" in USER_PERMISSIONS

    def test_contains_review_view(self):
        assert "patient:review:view" in USER_PERMISSIONS

    def test_is_set(self):
        assert isinstance(USER_PERMISSIONS, set)


# ================================================================
# check_permission_match 测试
# ================================================================


@pytest.mark.unit
class TestCheckPermissionMatch:
    """测试权限匹配函数"""

    # --- 精确匹配 ---

    def test_exact_match(self):
        permissions = {"doctor:schedule:view", "doctor:profile:edit"}
        assert check_permission_match("doctor:schedule:view", permissions) is True

    def test_exact_no_match(self):
        permissions = {"doctor:schedule:view", "doctor:profile:edit"}
        assert check_permission_match("doctor:schedule:edit", permissions) is False

    def test_exact_match_empty_permissions(self):
        assert check_permission_match("doctor:schedule:view", set()) is False

    # --- 前缀通配符匹配 ---

    def test_prefix_wildcard_match(self):
        """doctor:consultation:create 匹配 doctor:consultation:*"""
        permissions = {"doctor:consultation:*"}
        assert check_permission_match("doctor:consultation:create", permissions) is True

    def test_prefix_wildcard_match_read(self):
        permissions = {"doctor:consultation:*"}
        assert check_permission_match("doctor:consultation:read", permissions) is True

    def test_prefix_wildcard_no_match_different_prefix(self):
        """doctor:consultation:* 不匹配 doctor:schedule:view"""
        permissions = {"doctor:consultation:*"}
        assert check_permission_match("doctor:schedule:view", permissions) is False

    def test_prefix_wildcard_two_level(self):
        """doctor:* 匹配 doctor:schedule:view（两段前缀）"""
        permissions = {"doctor:*"}
        assert check_permission_match("doctor:schedule:view", permissions) is True

    def test_prefix_wildcard_exact_collision(self):
        """确保 doctor:* 不会误匹配 doctor（权限码本身不一致）"""
        permissions = {"doctor:*"}
        # doctor:* 的前缀拆分: "doctor" -> 检查 "doctor:*" -> 匹配
        assert check_permission_match("doctor:something", permissions) is True

    # --- 全局通配符匹配 ---

    def test_global_wildcard_matches_everything(self):
        permissions = {"*"}
        assert check_permission_match("doctor:schedule:view", permissions) is True

    def test_global_wildcard_matches_any_permission(self):
        permissions = {"*"}
        assert check_permission_match("any:random:permission", permissions) is True

    def test_global_wildcard_among_others(self):
        permissions = {"*", "doctor:schedule:view"}
        assert check_permission_match("patient:review:create", permissions) is True

    # --- 不匹配的情况 ---

    def test_no_match_partial_prefix(self):
        """权限码不完全匹配前缀"""
        permissions = {"doctor:schedule:view"}
        assert check_permission_match("doctor:schedule:edit", permissions) is False

    def test_no_match_completely_different(self):
        permissions = {"patient:appointment:create"}
        assert check_permission_match("doctor:schedule:view", permissions) is False

    def test_no_match_wildcard_not_in_permissions(self):
        """没有通配符权限时，不应匹配"""
        permissions = {"doctor:schedule:view", "doctor:schedule:edit"}
        assert check_permission_match("doctor:schedule:delete", permissions) is False


# ================================================================
# get_permissions_for_role_type 测试
# ================================================================


@pytest.mark.unit
class TestGetPermissionsForRoleType:
    """测试根据角色类型获取权限集合"""

    def test_doctor_returns_doctor_permissions(self):
        perms = get_permissions_for_role_type("doctor")
        assert perms == DOCTOR_PERMISSIONS

    def test_user_returns_user_permissions(self):
        perms = get_permissions_for_role_type("user")
        assert perms == USER_PERMISSIONS

    def test_admin_returns_empty_set(self):
        perms = get_permissions_for_role_type("admin")
        assert perms == set()

    def test_unknown_returns_empty_set(self):
        perms = get_permissions_for_role_type("unknown_role")
        assert perms == set()

    def test_returns_copy_not_reference(self):
        """确保返回的是副本，而非原始集合的引用"""
        perms1 = get_permissions_for_role_type("doctor")
        perms1.add("test:permission")
        perms2 = get_permissions_for_role_type("doctor")
        assert "test:permission" not in perms2


# ================================================================
# SYSTEM_ROLES 字典验证
# ================================================================


@pytest.mark.unit
class TestSystemRoles:
    """测试系统预定义角色配置"""

    def test_has_super_admin(self):
        assert "SUPER_ADMIN" in SYSTEM_ROLES
        assert SYSTEM_ROLES["SUPER_ADMIN"]["role_type"] == "admin"
        assert SYSTEM_ROLES["SUPER_ADMIN"]["permissions"] == ["*"]

    def test_has_platform_admin(self):
        assert "PLATFORM_ADMIN" in SYSTEM_ROLES
        assert SYSTEM_ROLES["PLATFORM_ADMIN"]["role_type"] == "admin"

    def test_has_tenant_admin(self):
        assert "TENANT_ADMIN" in SYSTEM_ROLES
        assert SYSTEM_ROLES["TENANT_ADMIN"]["role_type"] == "admin"

    def test_has_store_admin(self):
        assert "STORE_ADMIN" in SYSTEM_ROLES
        assert SYSTEM_ROLES["STORE_ADMIN"]["role_type"] == "admin"

    def test_has_doctor_role(self):
        assert "DOCTOR" in SYSTEM_ROLES
        doctor = SYSTEM_ROLES["DOCTOR"]
        assert doctor["role_type"] == "doctor"
        assert doctor["is_default"] is True
        assert set(doctor["permissions"]) == DOCTOR_PERMISSIONS

    def test_has_patient_role(self):
        assert "PATIENT" in SYSTEM_ROLES
        patient = SYSTEM_ROLES["PATIENT"]
        assert patient["role_type"] == "user"
        assert patient["is_default"] is True
        assert set(patient["permissions"]) == USER_PERMISSIONS

    def test_all_roles_have_name(self):
        for key, role in SYSTEM_ROLES.items():
            assert "name" in role, f"角色 {key} 缺少 name 字段"
            assert isinstance(role["name"], str)
            assert len(role["name"]) > 0

    def test_all_roles_have_role_type(self):
        valid_types = {"admin", "doctor", "user", "operator"}
        for key, role in SYSTEM_ROLES.items():
            assert "role_type" in role, f"角色 {key} 缺少 role_type 字段"
            assert role["role_type"] in valid_types

    def test_all_roles_have_is_default(self):
        for key, role in SYSTEM_ROLES.items():
            assert "is_default" in role, f"角色 {key} 缺少 is_default 字段"
