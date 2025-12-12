/**
 * 权限配置
 * @see https://umijs.org/docs/max/access
 */
export default function access(initialState: { currentUser?: API.CurrentUser } | undefined) {
  const { currentUser } = initialState ?? {};

  return {
    // 超级管理员权限
    canSuperAdmin: currentUser?.role === 'SUPER_ADMIN',
    // 普通管理员权限
    canAdmin: currentUser?.role === 'ADMIN' || currentUser?.role === 'SUPER_ADMIN',
    // 已登录
    isLogin: !!currentUser,
  };
}
