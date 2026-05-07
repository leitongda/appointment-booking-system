"""统一认证函数单元测试

测试新的 AccountInfo 数据类和统一认证函数的基本功能。
"""
import pytest
from app.common.auth_types import (
    AccountInfo,
    RoleType,
    AdminInfo,
    DoctorInfo,
    UserInfo,
)


class TestAccountInfo:
    """测试 AccountInfo 数据类"""

    def test_create_user_account(self):
        """测试创建用户账号"""
        user_info = UserInfo(
            openid="test_openid",
            points=100,
            is_doctor=False,
        )
        account = AccountInfo(
            id="user_123",
            role_type=RoleType.USER,
            tenant_id="tenant_123",
            phone="13800138000",
            name="测试用户",
            status=1,
            user_info=user_info,
        )

        assert account.id == "user_123"
        assert account.is_user is True
        assert account.is_admin is False
        assert account.is_doctor is False
        assert account.user_info is not None
        assert account.user_info.points == 100

    def test_create_admin_account(self):
        """测试创建管理员账号"""
        admin_info = AdminInfo(
            role_code="SUPER_ADMIN",
            permissions=["*"],
            is_super_admin=True,
        )
        account = AccountInfo(
            id="admin_123",
            role_type=RoleType.ADMIN,
            tenant_id="tenant_123",
            phone="13900139000",
            name="管理员",
            status=1,
            admin_info=admin_info,
        )

        assert account.role_type == RoleType.ADMIN
        assert account.is_admin is True
        assert account.is_super_admin is True
        assert account.admin_info is not None

    def test_create_doctor_account(self):
        """测试创建医生账号"""
        doctor_info = DoctorInfo(
            doctor_id="doctor_123",
            name="张医生",
            title="主任医师",
        )
        account = AccountInfo(
            id="doctor_123",
            role_type=RoleType.DOCTOR,
            tenant_id="tenant_123",
            phone="13700137000",
            name="张医生",
            status=1,
            doctor_info=doctor_info,
        )

        assert account.role_type == RoleType.DOCTOR
        assert account.is_doctor is True
        assert account.is_admin is False
        assert account.doctor_info is not None

    def test_to_dict_user(self):
        """测试用户账号转换为字典"""
        user_info = UserInfo(
            openid="test_openid",
            points=100,
        )
        account = AccountInfo(
            id="user_123",
            role_type=RoleType.USER,
            phone="13800138000",
            name="测试用户",
            user_info=user_info,
        )

        result = account.to_dict()
        assert result["id"] == "user_123"
        assert result["role_type"] == "user"
        assert result["phone"] == "13800138000"
        assert result["nickname"] == "测试用户"
        assert result["is_admin"] is False
        assert result["is_doctor"] is False
        assert result["points"] == 100

    def test_to_dict_admin(self):
        """测试管理员账号转换为字典"""
        admin_info = AdminInfo(
            role_code="SUPER_ADMIN",
            role_name="超级管理员",
            permissions=["*"],
            is_super_admin=True,
            can_view_all_stores=True,
        )
        account = AccountInfo(
            id="admin_123",
            role_type=RoleType.ADMIN,
            phone="13900139000",
            name="管理员",
            admin_info=admin_info,
        )

        result = account.to_dict()
        assert result["id"] == "admin_123"
        assert result["role_type"] == "admin"
        assert result["is_admin"] is True
        assert result["is_super_admin"] is True
        assert result["role_code"] == "SUPER_ADMIN"
        assert result["permissions"] == ["*"]

    def test_from_dict_user(self):
        """测试从字典创建用户账号"""
        data = {
            "id": "user_123",
            "role_type": "user",
            "phone": "13800138000",
            "nickname": "测试用户",
            "status": 1,
            "points": 100,
            "is_doctor": False,
        }

        account = AccountInfo.from_dict(data)
        assert account.id == "user_123"
        assert account.role_type == RoleType.USER
        assert account.phone == "13800138000"
        assert account.user_info is not None
        assert account.user_info.points == 100

    def test_from_dict_admin(self):
        """测试从字典创建管理员账号"""
        data = {
            "id": "admin_123",
            "role_type": "admin",
            "phone": "13900139000",
            "name": "管理员",
            "role_code": "SUPER_ADMIN",
            "is_super_admin": True,
            "permissions": ["*"],
        }

        account = AccountInfo.from_dict(data)
        assert account.id == "admin_123"
        assert account.role_type == RoleType.ADMIN
        assert account.is_super_admin is True
        assert account.admin_info is not None


class TestAdminInfo:
    """测试 AdminInfo 数据类"""

    def test_to_dict(self):
        """测试 AdminInfo 转换为字典"""
        admin_info = AdminInfo(
            role_id="role_123",
            role_code="SUPER_ADMIN",
            role_name="超级管理员",
            permissions=["*"],
            current_store_id="store_123",
            store_ids=["store_123", "store_456"],
            is_super_admin=True,
            can_view_all_stores=True,
            tenant_id="tenant_123",
            tenant_name="测试租户",
        )

        result = admin_info.to_dict()
        assert result["role_id"] == "role_123"
        assert result["role_code"] == "SUPER_ADMIN"
        assert result["permissions"] == ["*"]
        assert result["current_store_id"] == "store_123"
        assert result["store_ids"] == ["store_123", "store_456"]
        assert result["is_super_admin"] is True
        assert result["tenant"]["id"] == "tenant_123"
        assert result["tenant"]["name"] == "测试租户"


class TestDoctorInfo:
    """测试 DoctorInfo 数据类"""

    def test_to_dict(self):
        """测试 DoctorInfo 转换为字典"""
        doctor_info = DoctorInfo(
            doctor_id="doctor_123",
            name="张医生",
            department_id="dept_123",
            title="主任医师",
        )

        result = doctor_info.to_dict()
        assert result["id"] == "doctor_123"
        assert result["name"] == "张医生"
        assert result["department_id"] == "dept_123"
        assert result["title"] == "主任医师"


class TestUserInfo:
    """测试 UserInfo 数据类"""

    def test_to_dict(self):
        """测试 UserInfo 转换为字典"""
        user_info = UserInfo(
            openid="test_openid",
            points=100,
            is_doctor=False,
            doctor_id=None,
        )

        result = user_info.to_dict()
        assert result["openid"] == "test_openid"
        assert result["points"] == 100
        assert result["is_doctor"] is False
        assert result["doctor_id"] is None
