import type { Admin } from '@hospital/api';

export function createPermissions(admin: Admin | null) {
  if (!admin) {
    return {
      hasPermission: () => false,
      hasAnyPermission: () => false,
      hasAllPermissions: () => false,
      isSuperAdmin: false,
      isStoreAdmin: false,
      canSwitchStores: false,
      canDashboard: false,
      canPlatformManagement: false,
      canOrganizationManagement: false,
      canMedicalServices: false,
      canOperationsConfig: false,
      canContentOperations: false,
    };
  }

  const permissions = admin.permissions || [];
  const roleCode = admin.roleCode?.toUpperCase();
  const isSuperAdmin = roleCode === 'SUPER_ADMIN' || admin.isSuperAdmin;
  const isStoreAdmin = roleCode === 'STORE_ADMIN' || admin.isStoreAdmin;
  const canSwitchStores = admin.canSwitchStores || isSuperAdmin;
  const hasWildcard = permissions.includes('*');

  const hasPermission = (permission: string): boolean => {
    if (isSuperAdmin || hasWildcard) return true;
    return permissions.includes(permission);
  };

  const hasAnyPermission = (list: string[]): boolean => {
    if (isSuperAdmin || hasWildcard) return true;
    return list.some(p => permissions.includes(p));
  };

  const hasAllPermissions = (list: string[]): boolean => {
    if (isSuperAdmin || hasWildcard) return true;
    return list.every(p => permissions.includes(p));
  };

  const hasModuleAccess = (menuPerm: string, childPerms: string[] = []): boolean => {
    return hasPermission(menuPerm) || hasAnyPermission(childPerms);
  };

  const canDashboard = hasPermission('dashboard') || hasPermission('dashboard:view');
  const canTenant = hasModuleAccess('tenant', ['tenant:list', 'tenant:create', 'tenant:update', 'tenant:delete']);
  const canTenantPlans = hasAnyPermission(['tenant:plan:view', 'tenant:plan:create', 'tenant:plan:update', 'tenant:plan:delete']);
  const canMiniappPlatform = hasAnyPermission(['miniapp-platform', 'miniapp-platform:company', 'miniapp-platform:payment-profile', 'miniapp-platform:instance']);
  const canPlatformManagement = canTenant || canTenantPlans || canMiniappPlatform;

  const canStore = hasModuleAccess('store', ['store:list', 'store:create', 'store:update', 'store:delete']);
  const canDepartment = hasModuleAccess('department', ['department:list', 'department:create', 'department:update', 'department:delete']);
  const canRoleManagement = isSuperAdmin && hasAnyPermission(['system:role', 'system:role:create', 'system:role:update', 'system:role:delete', 'system:role:permission']);
  const canUserManagement = hasAnyPermission(['system:user', 'system:user:create', 'system:user:update', 'system:user:delete', 'system:user:reset-password']);
  const canSystemLogs = isSuperAdmin || hasPermission('system:log');
  const canOrganizationManagement = canStore || canDepartment || canRoleManagement || canUserManagement || canSystemLogs;

  const canDoctor = hasModuleAccess('doctor', ['doctor:list', 'doctor:detail', 'doctor:create', 'doctor:update', 'doctor:delete', 'doctor:booking-setting']);
  const canSchedule = hasModuleAccess('schedule', ['schedule:list', 'schedule:create', 'schedule:update', 'schedule:delete', 'schedule:template', 'schedule:custom', 'schedule:rest-day', 'schedule:suspension', 'schedule:statistics']);
  const canAppointment = hasModuleAccess('appointment', ['appointment:list', 'appointment:detail', 'appointment:update', 'appointment:cancel', 'appointment:statistics']);
  const canPatient = hasModuleAccess('patient', ['patient:list', 'patient:detail', 'patient:create', 'patient:update', 'patient:delete']);
  const canMedicalServices = canDoctor || canSchedule || canAppointment || canPatient;

  const canBookingRules = hasPermission('system:settings');
  const canBasicSettings = hasPermission('system:settings');
  const canRuleSets = isSuperAdmin;
  const canConsultationFee = isSuperAdmin || hasPermission('system:consultation-fee');
  const canOperationsConfig = canBookingRules || canBasicSettings || canRuleSets || canConsultationFee;

  const canContent = hasPermission('content') || hasAnyPermission(['content:news', 'content:notice', 'content:banner', 'content:news:create', 'content:notice:create', 'content:banner:create']);
  const canMessage = hasModuleAccess('message', ['message:list', 'message:send', 'message:delete']);
  const canFeedback = hasModuleAccess('feedback', ['feedback:list', 'feedback:reply', 'feedback:delete']);
  const canContentOperations = canContent || canMessage || canFeedback;

  return {
    hasPermission,
    hasAnyPermission,
    hasAllPermissions,
    isSuperAdmin,
    isStoreAdmin,
    canSwitchStores,
    canDashboard,
    canPlatformManagement,
    canOrganizationManagement,
    canMedicalServices,
    canOperationsConfig,
    canContentOperations,
  };
}
