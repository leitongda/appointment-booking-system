import React from 'react';
import { Popconfirm } from 'antd';
import {
  EyeOutlined,
  EditOutlined,
  DeleteOutlined,
} from '@ant-design/icons';
import { useAccess, history } from '@umijs/max';

/**
 * 操作按钮类型
 */
export type OperationButtonType = 'view' | 'edit' | 'delete' | 'custom';

/**
 * 操作按钮配置
 */
export interface OperationButtonProps {
  /** 按钮类型 */
  type?: OperationButtonType;
  /** 权限标识，如 'patient:update' */
  permission?: string;
  /** 点击回调 */
  onClick?: () => void;
  /** 跳转链接（与 onClick 互斥，优先使用 url） */
  url?: string;
  /** 需要确认的操作文案（如删除确认） */
  confirmText?: string;
  /** 确认弹窗描述 */
  confirmDescription?: string;
  /** 自定义图标 */
  icon?: React.ReactNode;
  /** 按钮文字 */
  label?: string;
  /** 是否为危险操作（红色） */
  danger?: boolean;
  /** 是否禁用 */
  disabled?: boolean;
  /** 自定义样式 */
  style?: React.CSSProperties;
}

/**
 * 默认按钮配置
 */
const defaultConfig: Record<Exclude<OperationButtonType, 'custom'>, { icon: React.ReactNode; label: string; danger?: boolean }> = {
  view: { icon: <EyeOutlined />, label: '详情' },
  edit: { icon: <EditOutlined />, label: '编辑' },
  delete: { icon: <DeleteOutlined />, label: '删除', danger: true },
};

/**
 * 操作按钮组件
 * 封装权限检查、确认弹窗、跳转等通用逻辑
 *
 * @example
 * // 查看按钮
 * <OperationButton type="view" permission="patient:detail" url={`/patient/${id}`} />
 *
 * @example
 * // 删除按钮（带确认）
 * <OperationButton
 *   type="delete"
 *   permission="patient:delete"
 *   confirmText="确定删除该记录吗？"
 *   onClick={() => handleDelete(id)}
 * />
 *
 * @example
 * // 自定义按钮
 * <OperationButton
 *   type="custom"
 *   permission="patient:blacklist"
 *   icon={<StopOutlined />}
 *   label="加黑名单"
 *   onClick={handleBlacklist}
 * />
 */
export const OperationButton: React.FC<OperationButtonProps> = ({
  type = 'custom',
  permission,
  onClick,
  url,
  confirmText,
  confirmDescription,
  icon,
  label,
  danger,
  disabled,
  style,
}) => {
  const access = useAccess();

  // 权限检查
  if (permission && !access.hasPermission(permission)) {
    return null;
  }

  // 获取默认配置
  const config = type !== 'custom' ? defaultConfig[type] : undefined;
  const finalIcon = icon ?? config?.icon;
  const finalLabel = label ?? config?.label ?? '';
  const finalDanger = danger ?? config?.danger;

  // 点击处理
  const handleClick = () => {
    if (url) {
      history.push(url);
    } else {
      onClick?.();
    }
  };

  // 按钮样式
  const buttonStyle: React.CSSProperties = {
    fontSize: 13,
    color: finalDanger ? '#ff4d4f' : undefined,
    ...style,
  };

  // 按钮内容
  const buttonContent = (
    <a
      onClick={confirmText ? undefined : handleClick}
      style={buttonStyle}
      className={disabled ? 'ant-btn-disabled' : undefined}
    >
      {finalIcon} {finalLabel}
    </a>
  );

  // 需要确认的操作
  if (confirmText && !disabled) {
    return (
      <Popconfirm
        title={confirmText}
        description={confirmDescription}
        onConfirm={handleClick}
      >
        {buttonContent}
      </Popconfirm>
    );
  }

  return buttonContent;
};

export default OperationButton;
