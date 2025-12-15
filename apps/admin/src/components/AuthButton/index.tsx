import React from 'react';
import { useAccess } from '@umijs/max';
import { Tooltip } from 'antd';

interface AuthButtonProps {
  /**
   * 需要的权限码
   * 支持单个权限或多个权限（任一满足即可）
   */
  permission: string | string[];
  /**
   * 无权限时的显示模式
   * - hidden: 隐藏（默认）
   * - disabled: 显示但禁用
   * - tooltip: 显示但禁用，并显示提示
   */
  fallback?: 'hidden' | 'disabled' | 'tooltip';
  /**
   * 无权限时的提示文字（fallback 为 tooltip 时有效）
   */
  tooltip?: string;
  /**
   * 子元素
   */
  children: React.ReactElement;
}

/**
 * 权限按钮组件
 * 根据用户权限控制按钮的显示/禁用状态
 * 
 * @example
 * // 基本用法 - 无权限时隐藏
 * <AuthButton permission="doctor:create">
 *   <Button type="primary">新增医生</Button>
 * </AuthButton>
 * 
 * @example
 * // 多个权限（任一满足）
 * <AuthButton permission={['doctor:create', 'doctor:update']}>
 *   <Button>操作</Button>
 * </AuthButton>
 * 
 * @example
 * // 无权限时禁用并显示提示
 * <AuthButton permission="doctor:delete" fallback="tooltip" tooltip="您没有删除权限">
 *   <Button danger>删除</Button>
 * </AuthButton>
 */
const AuthButton: React.FC<AuthButtonProps> = ({
  permission,
  fallback = 'hidden',
  tooltip = '您没有操作权限',
  children,
}) => {
  const access = useAccess();

  // 检查权限
  const hasAuth = React.useMemo(() => {
    const permissions = Array.isArray(permission) ? permission : [permission];
    return access.hasAnyPermission(permissions);
  }, [permission, access]);

  // 有权限直接渲染
  if (hasAuth) {
    return children;
  }

  // 无权限处理
  switch (fallback) {
    case 'hidden':
      return null;
    
    case 'disabled':
      return React.cloneElement(children, { disabled: true });
    
    case 'tooltip':
      return (
        <Tooltip title={tooltip}>
          <span style={{ cursor: 'not-allowed' }}>
            {React.cloneElement(children, { disabled: true })}
          </span>
        </Tooltip>
      );
    
    default:
      return null;
  }
};

/**
 * 权限容器组件
 * 用于包裹一组需要权限控制的内容
 */
export const AuthContainer: React.FC<{
  permission: string | string[];
  children: React.ReactNode;
}> = ({ permission, children }) => {
  const access = useAccess();

  const hasAuth = React.useMemo(() => {
    const permissions = Array.isArray(permission) ? permission : [permission];
    return access.hasAnyPermission(permissions);
  }, [permission, access]);

  if (!hasAuth) {
    return null;
  }

  return <>{children}</>;
};

/**
 * usePermission hook
 * 用于在组件中检查权限
 * 
 * @example
 * const { hasPermission, hasAnyPermission } = usePermission();
 * if (hasPermission('doctor:create')) {
 *   // do something
 * }
 */
export const usePermission = () => {
  const access = useAccess();
  
  return {
    hasPermission: access.hasPermission,
    hasAnyPermission: access.hasAnyPermission,
    hasAllPermissions: access.hasAllPermissions,
    permissions: access.permissions,
    isSuperAdmin: access.canSuperAdmin,
  };
};

export default AuthButton;

