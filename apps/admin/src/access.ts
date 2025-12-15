/**
 * 权限配置
 * @see https://umijs.org/docs/max/access
 */
export default function access(initialState: { currentUser?: API.CurrentUser } | undefined) {
  const { currentUser } = initialState ?? {};
  const permissions = currentUser?.permissions || [];
  // 支持大小写不敏感的角色码检查
  const isSuperAdmin = currentUser?.roleCode?.toUpperCase() === 'SUPER_ADMIN';
  // 检查是否有通配符权限
  const hasWildcard = permissions.includes('*');

  /**
   * 检查是否拥有指定权限
   * @param permission 权限码，如 'doctor:create'
   * @returns boolean
   */
  const hasPermission = (permission: string): boolean => {
    // 超级管理员或拥有通配符权限
    if (isSuperAdmin || hasWildcard) return true;
    // 检查权限列表
    return permissions.includes(permission);
  };

  /**
   * 检查是否拥有指定权限中的任意一个
   * @param permissionList 权限码列表
   * @returns boolean
   */
  const hasAnyPermission = (permissionList: string[]): boolean => {
    if (isSuperAdmin || hasWildcard) return true;
    return permissionList.some((p) => permissions.includes(p));
  };

  /**
   * 检查是否拥有所有指定权限
   * @param permissionList 权限码列表
   * @returns boolean
   */
  const hasAllPermissions = (permissionList: string[]): boolean => {
    if (isSuperAdmin || hasWildcard) return true;
    return permissionList.every((p) => permissions.includes(p));
  };

  return {
    // 超级管理员权限
    canSuperAdmin: isSuperAdmin,
    // 已登录
    isLogin: !!currentUser,
    // 权限检查函数
    hasPermission,
    hasAnyPermission,
    hasAllPermissions,
    // 当前用户的权限列表
    permissions,
    
    // ========== 菜单权限（用于路由 access 配置）==========
    // 仪表盘
    canDashboard: hasPermission('dashboard') || hasPermission('dashboard:view'),
    // 门店管理
    canStore: hasPermission('store') || hasPermission('store:list'),
    // 科室管理
    canDepartment: hasPermission('department') || hasPermission('department:list'),
    // 医生管理
    canDoctor: hasPermission('doctor') || hasPermission('doctor:list'),
    // 排班管理
    canSchedule: hasPermission('schedule') || hasPermission('schedule:list'),
    // 预约管理
    canAppointment: hasPermission('appointment') || hasPermission('appointment:list'),
    // 患者管理
    canPatient: hasPermission('patient') || hasPermission('patient:list'),
    // 停诊审核
    canLeaveRequest: hasPermission('leave-request') || hasPermission('leave-request:list'),
    // 用户反馈
    canFeedback: hasPermission('feedback') || hasPermission('feedback:list'),
    // 消息管理
    canMessage: hasPermission('message') || hasPermission('message:list'),
    // 内容管理
    canContent: hasPermission('content') || hasAnyPermission(['content:news', 'content:notice', 'content:banner']),
    // 统计分析
    canStatistics: hasPermission('statistics') || hasPermission('statistics:view'),
    // 系统设置
    canSystem: hasPermission('system') || hasAnyPermission(['system:role', 'system:admin', 'system:settings', 'system:log']),
  };
}
