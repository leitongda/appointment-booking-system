"""Admin service compatibility exports."""

from app.modules.admin.service_admins import AdminService
from app.modules.admin.service_logs import OperationLogService
from app.modules.admin.service_permissions import PermissionService
from app.modules.admin.service_roles import RoleService

__all__ = ["AdminService", "RoleService", "OperationLogService", "PermissionService"]
