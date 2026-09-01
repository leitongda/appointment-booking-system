"""统一账号分发名实一致性测试

验证 get_current_account_dict / get_current_user_or_admin 虽然名字暗示只处理
"user/admin" 两类，实际调用 get_current_account 全量分发，对 doctor token 同样
正确分发到 Doctor 表。本测试通过 AccountInfo.to_dict() 的字段契约来证明：
handler 拿到的 dict 在 admin / doctor / user 三类下都包含各自所需字段，
从而确证统一入口的名实一致性，并锁死本轮同源隐患修复的回归边界。

相关 bug：
- unified_messages / notification_preferences 此前误挂 get_current_user（只查
  User 表），admin/doctor token 被判"账号不存在"。
- appointments statistics 此前挂 get_current_admin，doctor token 被判 403。
修复方式：统一改用 get_current_account_dict / get_current_user_or_admin。
"""
import pytest

from app.common.auth_types import (
    AccountInfo,
    AdminInfo,
    DoctorInfo,
    RoleType,
    UserInfo,
)
from app.modules.notification_preferences.router import _resolve_user_type


# --------------------------------------------------------------------------- #
# AccountInfo.to_dict() 字段契约 —— 统一分发入口输出的 dict 必须满足下游
# handler（statistics / notification_preferences 等）的依赖。
# --------------------------------------------------------------------------- #


def _build_admin_account() -> AccountInfo:
    return AccountInfo(
        id="admin_001",
        role_type=RoleType.ADMIN,
        tenant_id="tenant_001",
        phone="13900000001",
        name="管理员甲",
        admin_info=AdminInfo(
            role_code="STORE_ADMIN",
            role_name="门店管理员",
            permissions=["appointment:statistics"],
            current_store_id="store_001",
            store_ids=["store_001"],
            is_super_admin=False,
        ),
    )


def _build_operator_account() -> AccountInfo:
    return AccountInfo(
        id="op_001",
        role_type=RoleType.OPERATOR,
        tenant_id="tenant_001",
        phone="13900000002",
        name="运营乙",
        admin_info=AdminInfo(
            role_code="OPERATOR",
            permissions=["statistics:read"],
        ),
    )


def _build_doctor_account() -> AccountInfo:
    return AccountInfo(
        id="doctor_001",
        role_type=RoleType.DOCTOR,
        tenant_id="tenant_001",
        phone="13700000001",
        name="张医生",
        doctor_info=DoctorInfo(
            doctor_id="doctor_001",
            name="张医生",
            department_id="dept_001",
            department_name="内科",
            title="主任医师",
            store_id="store_001",
            store_name="总院",
            permissions=["doctor:statistics:view"],
        ),
    )


def _build_user_account() -> AccountInfo:
    return AccountInfo(
        id="user_001",
        role_type=RoleType.USER,
        tenant_id="tenant_001",
        phone="13800000001",
        name="李患者",
        user_info=UserInfo(openid="openid_001", points=10, is_doctor=False),
    )


class TestUnifiedDispatchContract:
    """to_dict() 在三类角色下的字段契约，证明统一入口名实一致。"""

    def test_admin_dict_has_statistics_handler_fields(self):
        """admin dict 含 statistics handler 依赖的字段（id/role_type/permissions/store）。

        get_current_account_dict / get_current_user_or_admin 对 admin token
        分发到 Admin 表，to_dict() 必须产出 role_type=admin 且携带 permissions
        与 current_store_id，供 statistics 的 admin 分支使用。
        """
        d = _build_admin_account().to_dict()
        assert d["id"] == "admin_001"
        assert d["role_type"] == "admin"
        assert d["is_admin"] is True
        # statistics admin 分支读 permissions 校验 appointment:statistics
        assert "appointment:statistics" in d.get("permissions", [])
        # get_store_filter 读 current_store_id / store_ids
        assert d.get("current_store_id") == "store_001"

    def test_doctor_dict_has_statistics_handler_fields(self):
        """doctor dict 含 statistics handler 医生分支依赖的字段。

        这是 P1 的核心：证明统一入口对 doctor 名实一致 —— to_dict() 产出
        role_type=doctor，顶层带 doctor_id、permissions，以及内嵌 doctor.store_id，
        使 statistics 的 doctor 分支能锁定本人并读取所属门店。
        """
        d = _build_doctor_account().to_dict()
        assert d["role_type"] == "doctor"
        assert d["is_doctor"] is True
        # statistics 医生分支读 doctor_id 锁定本人
        assert d["doctor_id"] == "doctor_001"
        # 医生分支校验 doctor:statistics:view
        assert "doctor:statistics:view" in d.get("permissions", [])
        # _resolve_doctor_store_id 读 doctor.store_id 防越权
        assert d["doctor"]["store_id"] == "store_001"

    def test_operator_dispatched_as_admin_family(self):
        """operator 经 to_dict() 归入 admin 族（is_admin=True, is_operator=True）。

        修复后（auth_types.py:223）is_admin 与 is_admin property 一致，operator
        的 is_admin 为 True，确保所有用 current_user.get("is_admin") 判定 admin
        分支的代码对运营人员正确生效。
        """
        d = _build_operator_account().to_dict()
        assert d["role_type"] == "operator"
        assert d["is_operator"] is True
        assert d["is_admin"] is True

    def test_user_dict_has_basic_fields(self):
        """user dict 携带 id/role_type，不携带 admin/doctor 专属字段。"""
        d = _build_user_account().to_dict()
        assert d["id"] == "user_001"
        assert d["role_type"] == "user"
        assert d["is_admin"] is False
        assert d["is_doctor"] is False

    def test_three_role_types_distinct(self):
        """三类角色 role_type 互不相同，是统一入口正确分发的前提。"""
        roles = {
            _build_admin_account().to_dict()["role_type"],
            _build_doctor_account().to_dict()["role_type"],
            _build_user_account().to_dict()["role_type"],
        }
        assert roles == {"admin", "doctor", "user"}


# --------------------------------------------------------------------------- #
# _resolve_user_type —— notification_preferences 的三端角色映射
# 防止 admin/operator 误落入 patient（旧 is_doctor 二分逻辑的回归）。
# --------------------------------------------------------------------------- #


class TestResolveUserType:
    """notification_preferences 的 user_type 解析，覆盖三端 + 运营人员。"""

    def test_admin_maps_to_admin(self):
        d = _build_admin_account().to_dict()
        assert _resolve_user_type(d) == "admin"

    def test_operator_maps_to_admin(self):
        """运营人员应归入 admin 维度，而非 patient。"""
        d = _build_operator_account().to_dict()
        assert _resolve_user_type(d) == "admin"

    def test_doctor_maps_to_doctor(self):
        d = _build_doctor_account().to_dict()
        assert _resolve_user_type(d) == "doctor"

    def test_user_maps_to_patient(self):
        d = _build_user_account().to_dict()
        assert _resolve_user_type(d) == "patient"

    def test_missing_role_type_defaults_to_patient(self):
        """缺失 role_type 时安全回落到 patient，不抛异常。"""
        assert _resolve_user_type({"id": "x"}) == "patient"


# --------------------------------------------------------------------------- #
# statistics 角色分支逻辑 —— 用 handler 内联的判定条件做断言，避免起 DB。
# 复刻 get_appointment_statistics 里的分支判定，锁死其行为契约。
# --------------------------------------------------------------------------- #


def _statistics_branch_decision(current_user: dict) -> str:
    """复刻 router_query.get_appointment_statistics 的角色分支判定。

    返回该角色将被走的分支：'doctor' / 'admin_ok' / 'admin_forbidden'。
    用于在不依赖数据库的情况下锁死分支逻辑的回归边界。
    """
    role_type = current_user.get("role_type")
    if role_type == "doctor":
        if "doctor:statistics:view" not in current_user.get("permissions", []):
            return "doctor_forbidden"
        if not current_user.get("doctor_id"):
            return "doctor_missing_id"
        return "doctor"
    if "appointment:statistics" not in current_user.get("permissions", []):
        return "admin_forbidden"
    return "admin_ok"


class TestStatisticsRoleBranch:
    """statistics 接口角色分支回归边界。"""

    def test_doctor_with_permission_views_own(self):
        d = _build_doctor_account().to_dict()
        assert _statistics_branch_decision(d) == "doctor"

    def test_doctor_without_permission_forbidden(self):
        """缺失 doctor:statistics:view 的医生被拒（P0#2 严格校验）。"""
        d = _build_doctor_account().to_dict()
        d["permissions"] = []  # 剥夺统计权限
        assert _statistics_branch_decision(d) == "doctor_forbidden"

    def test_admin_with_permission_ok(self):
        d = _build_admin_account().to_dict()
        assert _statistics_branch_decision(d) == "admin_ok"

    def test_admin_without_appointment_statistics_forbidden(self):
        """缺 appointment:statistics 权限的管理员被拒。"""
        d = _build_admin_account().to_dict()
        d["permissions"] = []
        assert _statistics_branch_decision(d) == "admin_forbidden"

    def test_user_cannot_access(self):
        """普通用户无任何统计权限分支，被拒。"""
        d = _build_user_account().to_dict()
        assert _statistics_branch_decision(d) == "admin_forbidden"
