"""认证依赖

本模块重新导出认证、租户、权限、数据库相关依赖，保持向后兼容。
拆分后的模块：
- auth_deps.py: 用户/医生/管理员认证
- tenant_deps.py: 租户校验、上下文、状态检查
- permission_deps.py: 权限检查、门店访问控制
"""

# 数据库相关
from app.db.session import get_db

# 认证相关
from app.common.auth_deps import (
    security,
    get_current_user,
    get_current_doctor,
    get_current_doctor_by_token,
    get_current_admin,
    get_current_super_admin,
    get_optional_user,
    get_current_user_or_admin,
)

# 租户相关
from app.common.tenant_deps import (
    get_current_tenant,
    get_current_tenant_or_404,
    get_platform_admin,
    get_tenant_filter,
    check_tenant_access,
    get_tenant_from_admin,
    require_tenant_admin,
    require_platform_admin,
    check_tenant_role_access,
    validate_tenant_consistency,
    require_tenant_context,
    require_tenant_active_for_write,
)

# 权限相关
from app.common.permission_deps import (
    get_store_filter,
    check_store_access,
    get_effective_store_id,
    require_permission,
    require_all_permissions,
)

__all__ = [
    # 数据库相关
    "get_db",
    # 认证相关
    "security",
    "get_current_user",
    "get_current_doctor",
    "get_current_doctor_by_token",
    "get_current_admin",
    "get_current_super_admin",
    "get_optional_user",
    "get_current_user_or_admin",
    # 租户相关
    "get_current_tenant",
    "get_current_tenant_or_404",
    "get_platform_admin",
    "get_tenant_filter",
    "check_tenant_access",
    "get_tenant_from_admin",
    "require_tenant_admin",
    "require_platform_admin",
    "check_tenant_role_access",
    "validate_tenant_consistency",
    "require_tenant_context",
    "require_tenant_active_for_write",
    # 权限相关
    "get_store_filter",
    "check_store_access",
    "get_effective_store_id",
    "require_permission",
    "require_all_permissions",
]
