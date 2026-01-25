import { PlusOutlined, SafetyCertificateOutlined, EditOutlined, DeleteOutlined, MoreOutlined } from '@ant-design/icons';
import type { ActionType, ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable } from '@ant-design/pro-components';
import { Button, App, Popconfirm, Space, Tag, Divider, Dropdown } from 'antd';
import type { MenuProps } from 'antd';
import { useRef } from 'react';
import { history, useAccess } from '@umijs/max';
import { adminApi } from '@hospital/api';
import { toProTableResult } from '@/utils/proTable';
import type { Role } from '@hospital/api';

const RolePage: React.FC = () => {
  const { message } = App.useApp();
  const access = useAccess();
  const actionRef = useRef<ActionType>();

  const handleDelete = async (id: string) => {
    try {
      await adminApi.deleteRole(id);
      message.success('删除成功');
      actionRef.current?.reload();
    } catch (error: any) {
      message.error(error.message || '删除失败');
    }
  };

  const columns: ProColumns<Role>[] = [
    { title: '角色名称', dataIndex: 'name', width: 150 },
    { title: '角色编码', dataIndex: 'code', width: 120 },
    { title: '描述', dataIndex: 'description', ellipsis: true, search: false },
    {
      title: '权限数量',
      dataIndex: 'permissions',
      width: 100,
      search: false,
      render: (_, record) => (
        <Tag color="blue">{record.permissions?.length || 0} 个权限</Tag>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 80,
      valueEnum: { 1: { text: '启用', status: 'Success' }, 0: { text: '禁用', status: 'Default' } },
    },
    { title: '创建时间', dataIndex: 'createdAt', valueType: 'dateTime', width: 160, search: false },
    {
      title: '操作',
      valueType: 'option',
      width: 180,
      fixed: 'right',
      render: (_, record) => {
        // 更多操作菜单项
        const moreMenuItems: MenuProps['items'] = [
          access.hasPermission('system:role:permission') && record.code !== 'SUPER_ADMIN' && {
            key: 'permissions',
            icon: <SafetyCertificateOutlined />,
            label: '分配权限',
            onClick: () => history.push(`/system/role/${record.id}/permissions`),
          },
        ].filter(Boolean);

        return (
          <Space size={4} split={<Divider type="vertical" style={{ margin: 0 }} />}>
            {access.hasPermission('system:role:update') && (
              <a onClick={() => history.push(`/system/role/${record.id}/edit`)} style={{ fontSize: 13 }}>
                <EditOutlined /> 编辑
              </a>
            )}
            {access.hasPermission('system:role:delete') && record.code !== 'SUPER_ADMIN' && (
              <Popconfirm title="确定删除该角色吗？" onConfirm={() => handleDelete(record.id)}>
                <a style={{ color: '#ff4d4f', fontSize: 13 }}>
                  <DeleteOutlined /> 删除
                </a>
              </Popconfirm>
            )}
            {moreMenuItems.length > 0 && (
              <Dropdown menu={{ items: moreMenuItems }} trigger={['click']}>
                <a style={{ color: '#666', fontSize: 13 }}>
                  <MoreOutlined /> 更多
                </a>
              </Dropdown>
            )}
          </Space>
        );
      },
    },
  ];

  return (
    <PageContainer>
      <ProTable<Role>
        headerTitle="角色列表"
        actionRef={actionRef}
        rowKey="id"
        columns={columns}
        request={async (params) => {
          const { current, pageSize, ...rest } = params;
          return toProTableResult(await adminApi.getRoles({ ...rest, page: current, pageSize }));
        }}
        toolBarRender={() => [
          access.hasPermission('system:role:create') && (
            <Button
              key="add"
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => history.push('/system/role/create')}
            >
              新增角色
            </Button>
          ),
        ]}
        pagination={{ defaultPageSize: 10 }}
      />
    </PageContainer>
  );
};

export default RolePage;
