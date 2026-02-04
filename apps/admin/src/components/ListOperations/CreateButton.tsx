import React from 'react';
import { Button } from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import { useAccess, history } from '@umijs/max';

/**
 * 新增按钮配置
 */
export interface CreateButtonProps {
  /** 权限标识，如 'patient:create'，不传则不进行权限检查 */
  permission?: string;
  /** 跳转链接 */
  url?: string;
  /** 自定义点击回调（与 url 互斥，优先使用 url） */
  onClick?: () => void;
  /** 按钮文字，默认 "新增" */
  label?: string;
  /** 自定义图标 */
  icon?: React.ReactNode;
  /** 按钮类型 */
  type?: 'primary' | 'default' | 'dashed' | 'link' | 'text';
  /** 是否禁用 */
  disabled?: boolean;
  /** 额外的 key（用于 toolBarRender 数组） */
  buttonKey?: string;
}

/**
 * 新增按钮组件
 * 封装权限检查和统一样式
 *
 * @example
 * // 基础用法
 * <CreateButton permission="patient:create" url="/medical-card/create" label="新增就诊卡" />
 *
 * @example
 * // 自定义点击
 * <CreateButton
 *   permission="patient:create"
 *   label="新增就诊卡"
 *   onClick={() => setModalVisible(true)}
 * />
 *
 * @example
 * // 在 toolBarRender 中使用
 * toolBarRender={() => [
 *   <CreateButton key="add" permission="patient:create" url="/patient/create" />,
 * ]}
 */
export const CreateButton: React.FC<CreateButtonProps> = ({
  permission,
  url,
  onClick,
  label = '新增',
  icon = <PlusOutlined />,
  type = 'primary',
  disabled,
  buttonKey,
}) => {
  const access = useAccess();

  // 权限检查（如果提供了 permission 参数）
  if (permission && !access.hasPermission(permission)) {
    return null;
  }

  // 点击处理
  const handleClick = () => {
    if (url) {
      history.push(url);
    } else {
      onClick?.();
    }
  };

  return (
    <Button
      key={buttonKey}
      type={type}
      icon={icon}
      onClick={handleClick}
      disabled={disabled}
    >
      {label}
    </Button>
  );
};

export default CreateButton;
