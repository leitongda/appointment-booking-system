import React from 'react';
import { Popconfirm, theme } from 'antd';
import {
  EyeOutlined,
  EditOutlined,
  DeleteOutlined,
  ExclamationCircleOutlined,
} from '@ant-design/icons';
import { useAccess, history } from '@umijs/max';
import { confirmDelete, type DeleteImpactScope } from '@/components/ConfirmModal';

/**
 * 操作按钮类型
 */
export type OperationButtonType = 'view' | 'edit' | 'delete' | 'custom';

/**
 * 删除操作配置
 */
export interface DeleteOperationConfig {
  /** 实体名称（如：科室、医生） */
  entityName?: string;
  /** 实体标识（如：科室名称） */
  entityIdentifier?: string | ((record?: any) => string);
  /** 影响范围 */
  impactScope?: DeleteImpactScope | ((record?: any) => DeleteImpactScope);
  /** 是否需要强制输入确认（默认 true） */
  requireTyping?: boolean;
  /** 自定义确认标题 */
  confirmTitle?: string;
  /** 自定义确认描述 */
  confirmDescription?: string;
}

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
  /** 删除操作详细配置（仅 type='delete' 时有效） */
  deleteConfig?: DeleteOperationConfig;
  /** 传递给删除回调的记录数据 */
  record?: any;
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
 * // 删除按钮（带影响范围）
 * <OperationButton
 *   type="delete"
 *   permission="doctor:delete"
 *   deleteConfig={{
 *     entityName: '医生',
 *     entityIdentifier: record.name,
 *     impactScope: {
 *       affectedCount: 15,
 *       relatedEntities: ['关联的排班记录', '关联的预约记录'],
 *     },
 *   }}
 *   onClick={() => handleDelete(record.id)}
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
  deleteConfig,
  record,
}) => {
  const { token } = theme.useToken();
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

  // 处理删除操作（带增强确认）
  const handleDeleteClick = () => {
    if (!deleteConfig) {
      // 没有详细配置，使用简单确认
      handleClick();
      return;
    }

    // 解析实体标识
    const entityIdentifier = typeof deleteConfig.entityIdentifier === 'function'
      ? deleteConfig.entityIdentifier(record)
      : deleteConfig.entityIdentifier;

    // 解析影响范围
    const impactScope = typeof deleteConfig.impactScope === 'function'
      ? deleteConfig.impactScope(record)
      : deleteConfig.impactScope;

    // 使用增强的确认删除对话框
    confirmDelete({
      title: deleteConfig.confirmTitle || '确认删除',
      content: deleteConfig.confirmDescription,
      entityName: deleteConfig.entityName || '记录',
      entityIdentifier,
      impactScope,
      requireTyping: deleteConfig.requireTyping ?? true,
      onOk: handleClick,
    });
  };

  // 按钮样式
  const buttonStyle: React.CSSProperties = {
    fontSize: 13,
    color: finalDanger ? token.colorError : undefined,
    ...style,
  };

  // 按钮内容
  const buttonContent = (
    <a
      onClick={confirmText && !deleteConfig ? undefined : (deleteConfig ? handleDeleteClick : handleClick)}
      style={buttonStyle}
      className={disabled ? 'ant-btn-disabled' : undefined}
    >
      {finalIcon} {finalLabel}
    </a>
  );

  // 需要确认的操作（普通确认，非删除或没有 deleteConfig）
  if (confirmText && !disabled && !deleteConfig) {
    return (
      <Popconfirm
        title={confirmText}
        description={confirmDescription}
        onConfirm={handleClick}
        icon={<ExclamationCircleOutlined style={{ color: token.colorWarning }} />}
      >
        {buttonContent}
      </Popconfirm>
    );
  }

  // 删除操作且有 deleteConfig，点击时触发增强确认
  if (type === 'delete' && deleteConfig && !disabled) {
    return buttonContent;
  }

  return buttonContent;
};

export default OperationButton;
