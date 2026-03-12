from app.modules.admin.service_admins import AdminService as modular_admin_service
from app.modules.admin.service_logs import OperationLogService as modular_operation_log_service
from app.modules.admin.service_permissions import PermissionService as modular_permission_service
from app.modules.admin.service_roles import RoleService as modular_role_service
from app.services.admin_service import (
    AdminService as legacy_admin_service,
    OperationLogService as legacy_operation_log_service,
    PermissionService as legacy_permission_service,
    RoleService as legacy_role_service,
)


def test_role_service_wrapper_reuses_modular_service():
    assert legacy_role_service is modular_role_service


def test_admin_service_wrapper_reuses_modular_service():
    assert legacy_admin_service is modular_admin_service


def test_operation_log_service_wrapper_reuses_modular_service():
    assert legacy_operation_log_service is modular_operation_log_service


def test_permission_service_wrapper_reuses_modular_service():
    assert legacy_permission_service is modular_permission_service
