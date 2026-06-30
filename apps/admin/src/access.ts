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
  // 内容站点 CMS
  const canCmsSite = hasModuleAccess('cms:site', [
    'cms:site:create',
    'cms:site:update',
    'cms:site:delete',
  ]);
  const canCmsCategory = hasModuleAccess('cms:category', [
    'cms:category:create',
    'cms:category:update',
    'cms:category:delete',
  ]);
  const canCmsArticle = hasModuleAccess('cms:article', [
    'cms:article:create',
    'cms:article:update',
    'cms:article:delete',
  ]);
  const canCms = hasPermission('cms') || canCmsSite || canCmsCategory || canCmsArticle;
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
  const canAccountStats = canSystemLogs;
  const canAnalytics = isSuperAdmin || hasAnyPermission(['statistics', 'statistics:view', 'system:log']);
  const canBookingRules = hasPermission('system:settings');
  const canBlacklistSettings = hasAnyPermission(['blacklist:list', 'blacklist:create', 'blacklist:delete']);
  const canBasicSettings = hasPermission('system:settings');
  const canBookingFields = hasPermission('system:settings');
  const canPatientCardConfig = hasPermission('system:settings');
  const canHospitalInfo = hasPermission('system:settings');
  const canEmailConfig = hasAnyPermission(['settings:email', 'settings:edit']);
  const canImageConfig = hasPermission('settings:edit');
  const canSmsSettings = hasAnyPermission(['settings:sms', 'settings:edit']);
  const canSecuritySettings = hasPermission('settings:edit');
  const canSourceReleaseSettings = hasPermission('settings:edit');
  const canWechatSettings = isSuperAdmin || hasAnyPermission(['settings:wechat', 'settings:edit']);
  const canIntegrationSettings =
    isSuperAdmin || hasAnyPermission(['settings:integration', 'settings:edit']);
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
  const canLowcode = isSuperAdmin || hasAnyPermission([
    'lowcode',
    'lowcode:page',
    'lowcode:page:list',
    'lowcode:page:create',
    'lowcode:page:update',
    'lowcode:page:delete',
    'lowcode:page:publish',
  ]);
  const canLowcodeMarketplace = canLowcode || hasAnyPermission([
    'lowcode:marketplace',
    'lowcode:marketplace:view',
    'lowcode:marketplace:publish',
  ]);
  const canTenantUsage = canTenant;
  const canFreelance = hasModuleAccess('freelance', ['freelance:list', 'freelance:create', 'freelance:update', 'freelance:delete', 'freelance:settle']);
  const canAttendance = isSuperAdmin || hasPermission('attendance');
  const canAttendanceShifts = isSuperAdmin || hasPermission('attendance:shift');
  const canAttendanceGroups = isSuperAdmin || hasPermission('attendance:group');
  const canAttendanceRules = isSuperAdmin || hasPermission('attendance:rule');
  const canAttendanceRecords = isSuperAdmin || hasPermission('attendance:record');
  const canAttendanceLeave = isSuperAdmin || hasPermission('attendance:leave');
  const canApproval = hasModuleAccess('approval-flow', ['approval-flow:list', 'approval-flow:create', 'approval-flow:update', 'approval-flow:manage', 'approval-flow:delete', 'approval:read', 'approval:approve', 'approval-instance:manage']);
  const canContacts = hasModuleAccess('contact', ['contact:view', 'contact:create', 'contact:edit', 'contact:delete']);
  const canApprovalFlowManage = hasAnyPermission(['approval-flow:create', 'approval-flow:update', 'approval-flow:manage', 'approval-flow:delete']);

  const canMedicalConfig =
    canShiftTypes ||
    canRuleSets ||
    canBookingRules ||
    canBookingFields ||
    canBookingNotice ||
    canPatientCardConfig;
  const canSystemConfig =
    canHospitalInfo ||
    canWechatSettings ||
    canEmailConfig ||
    canImageConfig ||
    canSmsSettings ||
    canSecuritySettings ||
    canSourceReleaseSettings ||
    canEmailTemplates ||
    canEmailRecipients;
  const canPlatformManagement = canTenant || canTenantPlans || canMiniappPlatform || canLowcode;
  // 平台经营看板：仅超管可见（与后端 require_platform_admin 校验 is_super_admin 对齐）
  const canPlatformMetrics = isSuperAdmin;
  const canOrganizationManagement =
    canStore ||
    canDepartment ||
    canUserManagement ||
    canMedicalConfig;
  const canClinicalOperations =
    canDoctor ||
    canSchedule ||
    canAppointment ||
    canPatient ||
    canMedicalRecord ||
    canLeaveRequest ||
    canConsultationFee;
  const canContentOperations =
    canContent ||
    canMessage ||
    canFeedback ||
    canAnalytics ||
    canFreelance;
  const canSystemManagement =
    canRoleManagement ||
    canSystemConfig ||
    canBlacklistSettings ||
    canSystemLogs ||
    canCheckinAuditLogs ||
    canOnlineUsers ||
    canIntegrationSettings;
  const canSystemMonitoring =
    canSystemLogs ||
    canCheckinAuditLogs ||
    canOnlineUsers;
  const canConfigurationCenter = canMedicalConfig || canSystemConfig || canBlacklistSettings;

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
    canPlatformMetrics,
    canOrganizationManagement,
    canClinicalOperations,
    canContentOperations,
    canSystemManagement,
    canSystemMonitoring,
    canMedicalConfig,
    canSystemConfig,
    canConfigurationCenter,
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
    canCms,
    canCmsSite,
    canCmsCategory,
    canCmsArticle,
    canSystem: canOrganizationManagement || canSystemManagement,
    canManageRoles: canRoleManagement,
    canManageUsers: canUserManagement,
    canRoleManagement,
    canUserManagement,
    canSystemLogs,
    canCheckinAuditLogs,
    canOnlineUsers,
    canAccountStats,
    canAnalytics,
    canBookingRules,
    canBlacklistSettings,
    canBasicSettings,
    canBookingFields,
    canPatientCardConfig,
    canHospitalInfo,
    canEmailConfig,
    canImageConfig,
    canSmsSettings,
    canSecuritySettings,
    canSourceReleaseSettings,
    canWechatSettings,
    canIntegrationSettings,
    canShiftTypes,
    canRuleSets,
    canConsultationFee,
    canEmailTemplates,
    canEmailRecipients,
    canBookingNotice,
    canTenant,
    canTenantPlans,
    canTenantUsage,
    canFreelance,
    canLowcode,
    canLowcodeMarketplace,
    canAttendance,
    canAttendanceShifts,
    canAttendanceGroups,
    canAttendanceRules,
    canAttendanceRecords,
    canAttendanceLeave,
    canApproval,
    canApprovalFlowManage,
    canContacts,
  };
}
