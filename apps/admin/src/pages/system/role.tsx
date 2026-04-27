import { SafetyCertificateOutlined } from '@ant-design/icons';
import type { ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable } from '@ant-design/pro-components';
import { Tag } from 'antd';
import { history, useAccess } from '@umijs/max';
import { adminApi } from '@hospital/api';
import { createListRequest } from '@/utils/proTable';
import { useListPage } from '@/hooks/useListPage';
import { CreateButton, createOperationColumn } from '@/components/ListOperations';
import type { Role } from '@hospital/api';

const RolePage: React.FC = () => {
  const access = useAccess();
  const { actionRef, handleDelete } = useListPage({
    deleteFn: adminApi.deleteRole,
  });

  const columns: ProColumns<Role>[] = [
    { title: '角色名称', dataIndex: 'name', width: 150 },
    { title: '角色编码', dataIndex: 'code', width: 160 },
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
    createOperationColumn<Role>({
      width: 180,
      editUrl: (r) => `/system/role/${r.id}/edit`,
      editPermission: 'system:role:update',
      onDelete: handleDelete,
      deletePermission: 'system:role:delete',
      deleteConfirmText: '确定删除该角色吗？',
      canDelete: (r) => r.code !== 'SUPER_ADMIN',
      moreActions: (record) => [
        access.hasPermission('system:role:permission') && record.code !== 'SUPER_ADMIN' && {
          key: 'permissions',
          icon: <SafetyCertificateOutlined />,
          label: '分配权限',
          onClick: () => history.push(`/system/role/${record.id}/permissions`),
        },
      ].filter(Boolean) as any,
    }),
  ];

  return (
    <PageContainer>
      <ProTable<Role>
        headerTitle="角色列表"
        actionRef={actionRef}
        rowKey="id"
        columns={columns}
        request={createListRequest(adminApi.getRoles)}
        toolBarRender={() => [
          <CreateButton
            key="add"
            permission="system:role:create"
            url="/system/role/create"
            label="新增角色"
          />,
        ]}
        pagination={{ defaultPageSize: 10 }}
      />
    </PageContainer>
  );
};

export default RolePage;
