/**
 * 权限配置
 * @see https://umijs.org/docs/max/access
 */
export default function access(initialState: { currentUser?: API.CurrentUser } | undefined) {
  const { currentUser } = initialState ?? {};
  const permissions = currentUser?.permissions || [];
  const roleCode = currentUser?.roleCode?.toUpperCase();
  const isSuperAdmin = roleCode === 'SUPER_ADMIN' || currentUser?.isSuperAdmin;
  const isStoreAdmin = roleCode === 'STORE_ADMIN' || currentUser?.isStoreAdmin;
  const isStoreUser = roleCode === 'STORE_USER';
  const canSwitchStores = currentUser?.canSwitchStores || isSuperAdmin;
  const hasWildcard = permissions.includes('*');

  const hasPermission = (permission: string): boolean => {
    if (isSuperAdmin || hasWildcard) return true;
    return permissions.includes(permission);
  };

  const hasAnyPermission = (permissionList: string[]): boolean => {
    if (isSuperAdmin || hasWildcard) return true;
    return permissionList.some((permission) => permissions.includes(permission));
  };

  const hasAllPermissions = (permissionList: string[]): boolean => {
    if (isSuperAdmin || hasWildcard) return true;
    return permissionList.every((permission) => permissions.includes(permission));
  };

  const hasModuleAccess = (menuPermission: string, childPermissions: string[] = []): boolean => {
    return hasPermission(menuPermission) || hasAnyPermission(childPermissions);
  };

  const canDashboard = hasPermission('dashboard') || hasPermission('dashboard:view');
  const canStore = hasModuleAccess('store', ['store:list', 'store:create', 'store:update', 'store:delete']);
  const canDepartment = hasModuleAccess('department', ['department:list', 'department:create', 'department:update', 'department:delete']);
  const canDoctor = hasModuleAccess('doctor', [
    'doctor:list',
    'doctor:detail',
    'doctor:create',
    'doctor:update',
    'doctor:delete',
    'doctor:booking-setting',
  ]);
  const canSchedule = hasModuleAccess('schedule', [
    'schedule:list',
    'schedule:create',
    'schedule:update',
    'schedule:delete',
    'schedule:template',
    'schedule:custom',
    'schedule:rest-day',
    'schedule:suspension',
    'schedule:statistics',
  ]);
  const canAppointment = hasModuleAccess('appointment', [
    'appointment:list',
    'appointment:detail',
    'appointment:update',
    'appointment:cancel',
    'appointment:statistics',
  ]);
  const canPatient = hasModuleAccess('patient', [
    'patient:list',
    'patient:detail',
    'patient:create',
    'patient:update',
    'patient:delete',
  ]);
  const canMedicalRecord = canPatient;
  const canLeaveRequest = hasModuleAccess('leave-request', ['leave-request:list', 'leave-request:approve']);
  const canFeedback = hasModuleAccess('feedback', ['feedback:list', 'feedback:reply', 'feedback:delete']);
  const canMessage = hasModuleAccess('message', ['message:list', 'message:send', 'message:delete']);
  const canContent = hasPermission('content') || hasAnyPermission([
    'content:news',
    'content:notice',
    'content:banner',
    'content:news:create',
    'content:notice:create',
    'content:banner:create',
  ]);
  const canRoleManagement =
    isSuperAdmin &&
    hasAnyPermission([
      'system:role',
      'system:role:create',
      'system:role:update',
      'system:role:delete',
      'system:role:permission',
    ]);
  const canUserManagement = hasAnyPermission([
    'system:user',
    'system:user:create',
    'system:user:update',
    'system:user:delete',
    'system:user:reset-password',
  ]);
  const canSystemLogs = isSuperAdmin || hasPermission('system:log');
  const canCheckinAuditLogs = canSystemLogs;
  const canOnlineUsers = canSystemLogs;
  const canAnalytics = isSuperAdmin || hasAnyPermission(['statistics', 'statistics:view', 'system:log']);
  const canBookingRules = hasPermission('system:settings');
  const canBlacklistSettings = hasPermission('system:settings');
  const canBasicSettings = hasPermission('system:settings');
  const canWechatSettings = isSuperAdmin || hasAnyPermission(['system:settings', 'settings:wechat', 'settings:edit']);
  const canShiftTypes = isSuperAdmin || hasPermission('system:settings');
  const canRuleSets = isSuperAdmin;
  const canConsultationFee = isSuperAdmin || hasPermission('system:consultation-fee');
  const canEmailTemplates =
    isSuperAdmin ||
    hasAnyPermission([
      'system:settings',
      'system:email-template:create',
      'system:email-template:update',
      'system:email-template:delete',
    ]);
  const canEmailRecipients = isSuperAdmin || hasPermission('system:settings');
  const canBookingNotice = isSuperAdmin || hasPermission('system:settings');
  const canTenant = isSuperAdmin || hasAnyPermission(['tenant', 'tenant:list', 'tenant:create', 'tenant:update', 'tenant:delete']);
  const canTenantPlans = isSuperAdmin || hasAnyPermission(['tenant:plan:view', 'tenant:plan:create', 'tenant:plan:update', 'tenant:plan:delete']);
  const canMiniappPlatform = isSuperAdmin || hasAnyPermission([
    'miniapp-platform',
    'miniapp-platform:company',
    'miniapp-platform:payment-profile',
    'miniapp-platform:instance',
  ]);

  const canPlatformManagement = canTenant || canTenantPlans || canMiniappPlatform;
  const canOrganizationManagement =
    canStore ||
    canDepartment ||
    canRoleManagement ||
    canUserManagement ||
    canSystemLogs ||
    canCheckinAuditLogs ||
    canOnlineUsers ||
    canAnalytics;
  const canMedicalServices =
    canDoctor ||
    canSchedule ||
    canAppointment ||
    canPatient ||
    canMedicalRecord ||
    canLeaveRequest;
  const canOperationsConfig =
    canBookingRules ||
    canBlacklistSettings ||
    canBasicSettings ||
    canWechatSettings ||
    canShiftTypes ||
    canRuleSets ||
    canConsultationFee ||
    canEmailTemplates ||
    canEmailRecipients ||
    canBookingNotice;
  const canContentOperations = canContent || canMessage || canFeedback;

  return {
    canSuperAdmin: isSuperAdmin,
    canStoreAdmin: isStoreAdmin,
    canStoreUser: isStoreUser,
    canSwitchStores,

    isLogin: !!currentUser,
    hasPermission,
    hasAnyPermission,
    hasAllPermissions,
    permissions,

    canDashboard,
    canPlatformManagement,
    canOrganizationManagement,
    canMedicalServices,
    canOperationsConfig,
    canContentOperations,
    canStoreCreate: isSuperAdmin,
    canStoreDelete: isSuperAdmin,
    canStore,
    canDepartment,
    canDoctor,
    canSchedule,
    canAppointment,
    canPatient,
    canMedicalRecord,
    canLeaveRequest,
    canFeedback,
    canMessage,
    canContent,
    canSystem: canOrganizationManagement || canOperationsConfig,
    canManageRoles: canRoleManagement,
    canManageUsers: canUserManagement,
    canRoleManagement,
    canUserManagement,
    canSystemLogs,
    canCheckinAuditLogs,
    canOnlineUsers,
    canAnalytics,
    canBookingRules,
    canBlacklistSettings,
    canBasicSettings,
    canWechatSettings,
    canShiftTypes,
    canRuleSets,
    canConsultationFee,
    canEmailTemplates,
    canEmailRecipients,
    canBookingNotice,
    canTenant,
    canTenantPlans,
  };
}
