import React from 'react';
import type { ProColumns } from '@ant-design/pro-components';
import type { MenuProps } from 'antd';
import { OperationButton } from './OperationButton';
import { OperationGroup } from './OperationGroup';

/**
 * 创建操作列配置选项
 */
export interface CreateOperationColumnOptions<T extends { id: string }> {
  /** 列宽度，默认 150 */
  width?: number;
  /** 是否固定在右侧，默认 true */
  fixed?: 'right' | false;

  /** 详情页 URL 生成函数 */
  viewUrl?: (record: T) => string;
  /** 详情权限标识 */
  viewPermission?: string;
  /** 详情按钮文字 */
  viewLabel?: string;

  /** 编辑页 URL 生成函数 */
  editUrl?: (record: T) => string;
  /** 编辑权限标识 */
  editPermission?: string;
  /** 编辑按钮文字 */
  editLabel?: string;

  /** 删除回调函数 */
  onDelete?: (id: string, record: T) => void;
  /** 删除权限标识 */
  deletePermission?: string;
  /** 删除确认文案 */
  deleteConfirmText?: string;
  /** 删除确认描述 */
  deleteConfirmDescription?: string;
  /** 删除按钮文字 */
  deleteLabel?: string;
  /** 是否显示删除按钮的条件判断函数 */
  canDelete?: (record: T) => boolean;

  /** 更多操作菜单项生成函数 */
  moreActions?: (record: T) => MenuProps['items'];

  /** 自定义渲染（完全替代默认渲染） */
  customRender?: (record: T) => React.ReactNode;

  /** 额外的操作按钮（在编辑和删除之间） */
  extraButtons?: (record: T) => React.ReactNode;
}

/**
 * 创建操作列配置
 * 快速生成包含详情、编辑、删除等操作的 ProColumns 配置
 *
 * @example
 * // 基础用法
 * const columns: ProColumns<User>[] = [
 *   { title: '用户名', dataIndex: 'name' },
 *   createOperationColumn<User>({
 *     editUrl: (r) => `/user/${r.id}/edit`,
 *     editPermission: 'user:update',
 *     onDelete: handleDelete,
 *     deletePermission: 'user:delete',
 *   }),
 * ];
 *
 * @example
 * // 完整配置
 * createOperationColumn<User>({
 *   width: 200,
 *   viewUrl: (r) => `/user/${r.id}`,
 *   viewPermission: 'user:detail',
 *   editUrl: (r) => `/user/${r.id}/edit`,
 *   editPermission: 'user:update',
 *   onDelete: handleDelete,
 *   deletePermission: 'user:delete',
 *   deleteConfirmText: '确定删除该用户吗？',
 *   canDelete: (r) => r.role !== 'admin',
 *   moreActions: (r) => [
 *     { key: 'reset', label: '重置密码', onClick: () => handleReset(r.id) },
 *   ],
 * })
 */
export function createOperationColumn<T extends { id: string }>(
  options: CreateOperationColumnOptions<T>
): ProColumns<T> {
  const {
    width = 150,
    fixed = 'right',
    viewUrl,
    viewPermission,
    viewLabel,
    editUrl,
    editPermission,
    editLabel,
    onDelete,
    deletePermission,
    deleteConfirmText = '确定删除该记录吗？',
    deleteConfirmDescription,
    deleteLabel,
    canDelete,
    moreActions,
    customRender,
    extraButtons,
  } = options;

  return {
    title: '操作',
    valueType: 'option',
    width,
    fixed: fixed || undefined,
    render: (_, record) => {
      // 自定义渲染
      if (customRender) {
        return customRender(record);
      }

      // 是否可以删除
      const showDelete = onDelete && (canDelete ? canDelete(record) : true);

      return (
        <OperationGroup moreItems={moreActions?.(record)}>
          {/* 详情按钮 */}
          {viewUrl && (
            <OperationButton
              type="view"
              permission={viewPermission}
              url={viewUrl(record)}
              label={viewLabel}
            />
          )}

          {/* 编辑按钮 */}
          {editUrl && (
            <OperationButton
              type="edit"
              permission={editPermission}
              url={editUrl(record)}
              label={editLabel}
            />
          )}

          {/* 额外按钮 */}
          {extraButtons?.(record)}

          {/* 删除按钮 */}
          {showDelete && (
            <OperationButton
              type="delete"
              permission={deletePermission}
              confirmText={deleteConfirmText}
              confirmDescription={deleteConfirmDescription}
              onClick={() => onDelete(record.id, record)}
              label={deleteLabel}
            />
          )}
        </OperationGroup>
      );
    },
  };
}

export default createOperationColumn;
