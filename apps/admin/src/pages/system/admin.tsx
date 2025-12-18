import { PlusOutlined } from '@ant-design/icons';
import type { ActionType, ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable } from '@ant-design/pro-components';
import { Button, App, Popconfirm, Space, Avatar } from 'antd';
import { useRef } from 'react';
import { history, useAccess } from '@umijs/max';
import { adminApi } from '@hospital/api';
import { toProTableResult } from '@/utils/proTable';
import type { Admin } from '@hospital/api';

const AdminPage: React.FC = () => {
  const { message } = App.useApp();
  const access = useAccess();
  const actionRef = useRef<ActionType>();

  const handleDelete = async (id: string) => {
    try {
      await adminApi.deleteAdmin(id);
      message.success('删除成功');
      actionRef.current?.reload();
    } catch (error: any) {
      message.error(error.message || '删除失败');
    }
  };

  const handleResetPassword = async (id: string) => {
    try {
      await adminApi.resetAdminPassword(id, '123456');
      message.success('密码已重置为 123456');
    } catch (error: any) {
      message.error(error.message || '重置失败');
    }
  };

  const columns: ProColumns<Admin>[] = [
    {
      title: '头像',
      dataIndex: 'avatar',
      width: 60,
      search: false,
      render: (_, record) => <Avatar src={record.avatar} size={36}>{record.name?.charAt(0)}</Avatar>,
    },
    { title: '用户名', dataIndex: 'username', width: 120 },
    { title: '姓名', dataIndex: 'name', width: 100 },
    { title: '手机号', dataIndex: 'phone', width: 120, search: false },
    { title: '角色', dataIndex: 'roleName', width: 100, search: false },
    {
      title: '状态',
      dataIndex: 'status',
      width: 80,
      valueEnum: { 1: { text: '启用', status: 'Success' }, 0: { text: '禁用', status: 'Default' } },
    },
    { title: '最后登录', dataIndex: 'lastLoginAt', valueType: 'dateTime', width: 160, search: false },
    {
      title: '操作',
      valueType: 'option',
      width: 180,
      render: (_, record) => (
        <Space>
          {access.hasPermission('system:admin:update') && (
            <a onClick={() => history.push(`/system/admin/${record.id}/edit`)}>编辑</a>
          )}
          {access.hasPermission('system:admin:reset-password') && (
            <Popconfirm title="确定重置密码为 123456 吗？" onConfirm={() => handleResetPassword(record.id)}>
              <a>重置密码</a>
            </Popconfirm>
          )}
          {access.hasPermission('system:admin:delete') && record.roleCode !== 'SUPER_ADMIN' && (
            <Popconfirm title="确定删除该管理员吗？" onConfirm={() => handleDelete(record.id)}>
              <a style={{ color: '#ff4d4f' }}>删除</a>
            </Popconfirm>
          )}
        </Space>
      ),
    },
  ];

  return (
    <PageContainer>
      <ProTable<Admin>
        headerTitle="管理员列表"
        actionRef={actionRef}
        rowKey="id"
        columns={columns}
        request={async (params) => {
          const { current, pageSize, ...rest } = params;
          return toProTableResult(await adminApi.getAdmins({ ...rest, page: current, pageSize }));
        }}
        toolBarRender={() => [
          access.hasPermission('system:admin:create') && (
            <Button
              key="add"
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => history.push('/system/admin/create')}
            >
              新增管理员
            </Button>
          ),
        ]}
        pagination={{ defaultPageSize: 10 }}
      />
    </PageContainer>
  );
};

export default AdminPage;
