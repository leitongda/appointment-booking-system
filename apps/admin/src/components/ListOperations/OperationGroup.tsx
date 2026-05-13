import React from 'react';
import { Space, Divider, Dropdown, theme } from 'antd';
import type { MenuProps } from 'antd';
import { MoreOutlined } from '@ant-design/icons';

/**
 * 操作按钮组配置
 */
export interface OperationGroupProps {
  /** 操作按钮（OperationButton 组件） */
  children: React.ReactNode;
  /** 更多操作下拉菜单项 */
  moreItems?: MenuProps['items'];
  /** 按钮间距 */
  size?: number;
  /** 是否显示分隔线 */
  showDivider?: boolean;
}

/**
 * 操作按钮组组件
 * 自动处理 Space + Divider 分隔，以及"更多"下拉菜单
 *
 * @example
 * <OperationGroup>
 *   <OperationButton type="view" url={`/patient/${id}`} />
 *   <OperationButton type="edit" url={`/patient/${id}/edit`} />
 *   <OperationButton type="delete" confirmText="确定删除吗？" onClick={() => handleDelete(id)} />
 * </OperationGroup>
 *
 * @example
 * // 带更多操作
 * <OperationGroup
 *   moreItems={[
 *     { key: 'reset', label: '重置密码', icon: <KeyOutlined /> },
 *     { key: 'blacklist', label: '加黑名单', icon: <StopOutlined /> },
 *   ]}
 * >
 *   <OperationButton type="edit" />
 *   <OperationButton type="delete" />
 * </OperationGroup>
 */
export const OperationGroup: React.FC<OperationGroupProps> = ({
  children,
  moreItems,
  size = 4,
  showDivider = true,
}) => {
  const { token } = theme.useToken();
  // 过滤掉 null/undefined/false 的子元素
  const validChildren = React.Children.toArray(children).filter(Boolean);

  // 有效的更多菜单项
  const validMoreItems = moreItems?.filter(Boolean) ?? [];

  return (
    <Space
      size={size}
      separator={showDivider ? <Divider type="vertical" style={{ margin: 0 }} /> : undefined}
    >
      {validChildren}
      {validMoreItems.length > 0 && (
        <Dropdown menu={{ items: validMoreItems }} trigger={['click']}>
          <a style={{ color: token.colorTextSecondary, fontSize: 13 }}>
            <MoreOutlined /> 更多
          </a>
        </Dropdown>
      )}
    </Space>
  );
};

export default OperationGroup;
