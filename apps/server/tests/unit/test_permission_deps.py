"""统一权限依赖单元测试

测试 permission_deps.py 中 _extract_permissions 和 require_account_permission / require_account_all_permissions。
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException

from app.common.auth_types import AccountInfo, RoleType, AdminInfo, DoctorInfo, UserInfo
from app.common.permission_deps import (
    _extract_permissions,
    require_account_permission,
    require_account_all_permissions,
)


# ================================================================
# _extract_permissions 测试
# ================================================================


@pytest.mark.unit
class TestExtractPermissions:
    """测试从 AccountInfo 提取权限列表"""

    def test_admin_with_admin_info(self):
        """Admin 角色从 admin_info.permissions 获取权限"""
        admin_info = AdminInfo(
            permissions=["admin:user:create", "admin:user:delete"],
        )
        account = AccountInfo(
            id="admin_1",
            role_type=RoleType.ADMIN,
            admin_info=admin_info,
        )
        perms = _extract_permissions(account)
        assert perms == ["admin:user:create", "admin:user:delete"]

    def test_admin_without_admin_info(self):
        """Admin 角色无 admin_info 时返回空列表"""
        account = AccountInfo(
            id="admin_1",
            role_type=RoleType.ADMIN,
        )
        perms = _extract_permissions(account)
        assert perms == []

    def test_admin_with_empty_permissions(self):
        """Admin 角色权限为空列表时返回空列表"""
        admin_info = AdminInfo(permissions=[])
        account = AccountInfo(
            id="admin_1",
            role_type=RoleType.ADMIN,
            admin_info=admin_info,
        )
        perms = _extract_permissions(account)
        assert perms == []

    def test_admin_with_none_permissions(self):
        """Admin 角色权限为 None 时返回空列表"""
        admin_info = AdminInfo(permissions=None)
        # permissions 字段默认为 []，这里手动设置为 None
        admin_info.permissions = None
        account = AccountInfo(
            id="admin_1",
            role_type=RoleType.ADMIN,
            admin_info=admin_info,
        )
        perms = _extract_permissions(account)
        assert perms == []

    def test_doctor_with_doctor_info(self):
        """Doctor 角色从 doctor_info.permissions 获取权限"""
        doctor_info = DoctorInfo(
            doctor_id="d_1",
            permissions=["doctor:schedule:view", "doctor:appointment:view"],
        )
        account = AccountInfo(
            id="doctor_1",
            role_type=RoleType.DOCTOR,
            doctor_info=doctor_info,
        )
        perms = _extract_permissions(account)
        assert perms == ["doctor:schedule:view", "doctor:appointment:view"]

    def test_doctor_without_doctor_info(self):
        """Doctor 角色无 doctor_info 时返回空列表"""
        account = AccountInfo(
            id="doctor_1",
            role_type=RoleType.DOCTOR,
        )
        perms = _extract_permissions(account)
        assert perms == []

    def test_user_with_user_info(self):
        """User 角色从 user_info.permissions 获取权限"""
        user_info = UserInfo(
            openid="wx_123",
            permissions=["patient:appointment:create", "patient:profile:edit"],
        )
        account = AccountInfo(
            id="user_1",
            role_type=RoleType.USER,
            user_info=user_info,
        )
        perms = _extract_permissions(account)
        assert perms == ["patient:appointment:create", "patient:profile:edit"]

    def test_user_without_user_info(self):
        """User 角色无 user_info 时返回空列表"""
        account = AccountInfo(
            id="user_1",
            role_type=RoleType.USER,
        )
        perms = _extract_permissions(account)
        assert perms == []

    def test_user_with_empty_permissions(self):
        """User 角色权限为空列表时返回空列表"""
        user_info = UserInfo(permissions=[])
        account = AccountInfo(
            id="user_1",
            role_type=RoleType.USER,
            user_info=user_info,
        )
        perms = _extract_permissions(account)
        assert perms == []


# ================================================================
# require_account_permission 测试
# ================================================================


@pytest.mark.unit
class TestRequireAccountPermission:
    """测试统一权限检查依赖（任一匹配）"""

    async def _run_check(self, dep_fn, account):
        """执行权限检查依赖的内部函数"""
        check_fn = dep_fn.__wrapped__ if hasattr(dep_fn, "__wrapped__") else dep_fn

        # 拿到 require_account_permission 返回的 check_permission 函数
        # 需要手动调用它，模拟 FastAPI 的 Depends 注入
        import inspect
        closure = inspect.getclosurevars(check_fn)
        # 不需要依赖注入，直接把 account 作为参数传入
        return await check_fn(current_account=account)

    def _get_check_function(self, *permissions):
        """获取 require_account_permission 返回的检查函数"""
        return require_account_permission(*permissions)

    async def test_super_admin_passes(self):
        """超级管理员拥有全部权限"""
        admin_info = AdminInfo(
            permissions=["*"],
            is_super_admin=True,
        )
        account = AccountInfo(
            id="sa_1",
            role_type=RoleType.ADMIN,
            admin_info=admin_info,
        )
        check_fn = self._get_check_function("any:permission")
        result = await check_fn(current_account=account)
        assert result is None

    async def test_wildcard_permission_passes(self):
        """拥有通配符权限时通过"""
        admin_info = AdminInfo(
            permissions=["*"],
            is_super_admin=False,
        )
        account = AccountInfo(
            id="admin_1",
            role_type=RoleType.ADMIN,
            admin_info=admin_info,
        )
        check_fn = self._get_check_function("admin:user:create")
        result = await check_fn(current_account=account)
        assert result is None

    async def test_exact_permission_match_passes(self):
        """精确匹配权限时通过"""
        doctor_info = DoctorInfo(
            doctor_id="d_1",
            permissions=["doctor:schedule:view", "doctor:appointment:view"],
        )
        account = AccountInfo(
            id="doctor_1",
            role_type=RoleType.DOCTOR,
            doctor_info=doctor_info,
        )
        check_fn = self._get_check_function("doctor:schedule:view")
        result = await check_fn(current_account=account)
        assert result is None

    async def test_one_of_permissions_matches(self):
        """多个所需权限中有一个匹配即可通过"""
        user_info = UserInfo(
            permissions=["patient:appointment:create"],
        )
        account = AccountInfo(
            id="user_1",
            role_type=RoleType.USER,
            user_info=user_info,
        )
        check_fn = self._get_check_function(
            "patient:appointment:create", "patient:appointment:cancel"
        )
        result = await check_fn(current_account=account)
        assert result is None

    async def test_no_permission_raises_403(self):
        """无权限时抛出 403"""
        doctor_info = DoctorInfo(
            doctor_id="d_1",
            permissions=["doctor:schedule:view"],
        )
        account = AccountInfo(
            id="doctor_1",
            role_type=RoleType.DOCTOR,
            doctor_info=doctor_info,
        )
        check_fn = self._get_check_function("admin:user:delete")
        with pytest.raises(HTTPException) as exc_info:
            await check_fn(current_account=account)
        assert exc_info.value.status_code == 403

    async def test_empty_permissions_raises_403(self):
        """空权限列表时抛出 403"""
        doctor_info = DoctorInfo(
            doctor_id="d_1",
            permissions=[],
        )
        account = AccountInfo(
            id="doctor_1",
            role_type=RoleType.DOCTOR,
            doctor_info=doctor_info,
        )
        check_fn = self._get_check_function("doctor:schedule:view")
        with pytest.raises(HTTPException) as exc_info:
            await check_fn(current_account=account)
        assert exc_info.value.status_code == 403

    async def test_no_role_info_raises_403(self):
        """无角色信息时抛出 403"""
        account = AccountInfo(
            id="doctor_1",
            role_type=RoleType.DOCTOR,
        )
        check_fn = self._get_check_function("doctor:schedule:view")
        with pytest.raises(HTTPException) as exc_info:
            await check_fn(current_account=account)
        assert exc_info.value.status_code == 403

    async def test_prefix_wildcard_passes(self):
        """前缀通配符权限通过"""
        doctor_info = DoctorInfo(
            doctor_id="d_1",
            permissions=["doctor:consultation:*"],
        )
        account = AccountInfo(
            id="doctor_1",
            role_type=RoleType.DOCTOR,
            doctor_info=doctor_info,
        )
        check_fn = self._get_check_function("doctor:consultation:create")
        result = await check_fn(current_account=account)
        assert result is None

    async def test_error_message_includes_role(self):
        """403 错误信息包含当前角色"""
        doctor_info = DoctorInfo(
            doctor_id="d_1",
            permissions=[],
        )
        account = AccountInfo(
            id="doctor_1",
            role_type=RoleType.DOCTOR,
            doctor_info=doctor_info,
        )
        check_fn = self._get_check_function("admin:user:delete")
        with pytest.raises(HTTPException) as exc_info:
            await check_fn(current_account=account)
        assert "医生" in exc_info.value.detail


# ================================================================
# require_account_all_permissions 测试
# ================================================================


@pytest.mark.unit
class TestRequireAccountAllPermissions:
    """测试统一权限检查依赖（全部匹配）"""

    def _get_check_function(self, *permissions):
        return require_account_all_permissions(*permissions)

    async def test_super_admin_passes(self):
        """超级管理员拥有全部权限"""
        admin_info = AdminInfo(
            permissions=["*"],
            is_super_admin=True,
        )
        account = AccountInfo(
            id="sa_1",
            role_type=RoleType.ADMIN,
            admin_info=admin_info,
        )
        check_fn = self._get_check_function("perm1", "perm2", "perm3")
        result = await check_fn(current_account=account)
        assert result is None

    async def test_all_permissions_present_passes(self):
        """拥有全部所需权限时通过"""
        user_info = UserInfo(
            permissions=["patient:appointment:create", "patient:profile:edit"],
        )
        account = AccountInfo(
            id="user_1",
            role_type=RoleType.USER,
            user_info=user_info,
        )
        check_fn = self._get_check_function(
            "patient:appointment:create", "patient:profile:edit"
        )
        result = await check_fn(current_account=account)
        assert result is None

    async def test_missing_one_permission_raises_403(self):
        """缺少其中一个权限时抛出 403"""
        user_info = UserInfo(
            permissions=["patient:appointment:create"],
        )
        account = AccountInfo(
            id="user_1",
            role_type=RoleType.USER,
            user_info=user_info,
        )
        check_fn = self._get_check_function(
            "patient:appointment:create", "patient:appointment:cancel"
        )
        with pytest.raises(HTTPException) as exc_info:
            await check_fn(current_account=account)
        assert exc_info.value.status_code == 403
        assert "patient:appointment:cancel" in exc_info.value.detail

    async def test_no_permissions_raises_403(self):
        """无任何权限时抛出 403"""
        user_info = UserInfo(permissions=[])
        account = AccountInfo(
            id="user_1",
            role_type=RoleType.USER,
            user_info=user_info,
        )
        check_fn = self._get_check_function("patient:appointment:create")
        with pytest.raises(HTTPException) as exc_info:
            await check_fn(current_account=account)
        assert exc_info.value.status_code == 403

    async def test_wildcard_covers_all(self):
        """通配符覆盖所有权限"""
        admin_info = AdminInfo(
            permissions=["*"],
            is_super_admin=False,
        )
        account = AccountInfo(
            id="admin_1",
            role_type=RoleType.ADMIN,
            admin_info=admin_info,
        )
        check_fn = self._get_check_function("perm1", "perm2", "perm3")
        result = await check_fn(current_account=account)
        assert result is None

    async def test_missing_permissions_listed_in_error(self):
        """403 错误信息列出所有缺少的权限"""
        user_info = UserInfo(
            permissions=[],
        )
        account = AccountInfo(
            id="user_1",
            role_type=RoleType.USER,
            user_info=user_info,
        )
        check_fn = self._get_check_function(
            "patient:appointment:create", "patient:profile:edit"
        )
        with pytest.raises(HTTPException) as exc_info:
            await check_fn(current_account=account)
        detail = exc_info.value.detail
        assert "patient:appointment:create" in detail
        assert "patient:profile:edit" in detail
