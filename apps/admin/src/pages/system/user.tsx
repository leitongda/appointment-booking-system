import { PlusOutlined } from '@ant-design/icons';
import type { ActionType, ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable } from '@ant-design/pro-components';
import { Button, App, Popconfirm, Space, Avatar, Tag } from 'antd';
import { useRef } from 'react';
import { history, useAccess, useModel } from '@umijs/max';
import { adminApi, storeApi, dataApi } from '@hospital/api';
import { toProTableResult } from '@/utils/proTable';
import type { Admin } from '@hospital/api';
import ImportExport from '@/components/ImportExport';

const UserPage: React.FC = () => {
  const { message } = App.useApp();
  const access = useAccess();
  const actionRef = useRef<ActionType>();
  const { initialState } = useModel('@@initialState');
  const { currentUser, currentStore } = initialState ?? {};
  const isSuperAdmin = access.canSuperAdmin;
  // 多门店管理员也可以看到门店筛选
  const showStoreFilter = isSuperAdmin || (currentUser?.storeIds?.length ?? 0) > 1;

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
    { title: '账号', dataIndex: 'username', width: 120 },
    { title: '用户名', dataIndex: 'name', width: 100 },
    { title: '手机号', dataIndex: 'phone', width: 120, search: false },
    { title: '角色', dataIndex: 'roleName', width: 100, search: false },
    // 超级管理员或多门店管理员可以看到门店列
    ...(showStoreFilter ? [{
      title: '所属门店',
      dataIndex: 'storeName',
      width: 120,
      search: false,
      render: (_: any, record: Admin) => record.storeName || <Tag color="purple">全局</Tag>,
    } as ProColumns<Admin>] : []),
    // 超级管理员或多门店管理员可以按门店筛选
    ...(showStoreFilter ? [{
      title: '门店',
      dataIndex: 'storeId',
      hideInTable: true,
      valueType: 'select',
      request: async () => {
        try {
          const stores = await storeApi.getAll();
          let storeList = stores ?? [];
          // 非超管只显示其关联的门店
          if (!isSuperAdmin && currentUser?.storeIds?.length) {
            storeList = storeList.filter((s: any) => currentUser.storeIds?.includes(s.id));
          }
          const options = [
            { label: '全部', value: '' },
            ...storeList.map((s: any) => ({ label: s.name, value: s.id })),
          ];
          // 只有超管可以看到"全局用户"选项
          if (isSuperAdmin) {
            options.splice(1, 0, { label: '全局用户', value: 'null' });
          }
          return options;
        } catch {
          return [];
        }
      },
    } as ProColumns<Admin>] : []),
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
      width: 100,
      render: (_, record) => (
        <Space>
          {access.hasPermission('system:user:update') && (
            <a onClick={() => history.push(`/system/user/${record.id}/edit`)}>编辑</a>
          )}
          {access.hasPermission('system:user:reset-password') && (
            <Popconfirm title="确定重置密码为 123456 吗？" onConfirm={() => handleResetPassword(record.id)}>
              <a>重置密码</a>
            </Popconfirm>
          )}
          {access.hasPermission('system:user:delete') && record.roleCode !== 'SUPER_ADMIN' && (
            <Popconfirm title="确定删除该用户吗？" onConfirm={() => handleDelete(record.id)}>
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
        headerTitle="用户列表"
        actionRef={actionRef}
        rowKey="id"
        columns={columns}
        request={async (params) => {
          const { current, pageSize, storeId, ...rest } = params;
          const queryParams: any = { ...rest, page: current, pageSize };
          // 处理门店筛选
          if (storeId === 'null') {
            // 查询全局用户（store_id 为空）
            queryParams.storeId = '';
          } else if (storeId) {
            queryParams.storeId = storeId;
          }
          return toProTableResult(await adminApi.getAdmins(queryParams));
        }}
        toolBarRender={() => [
          <ImportExport
            key="import-export"
            moduleName="系统用户"
            exportUrl={dataApi.getExportUsersUrl()}
            showImport={false}
          />,
          access.hasPermission('system:user:create') && (
            <Button
              key="add"
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => history.push('/system/user/create')}
            >
              新增用户
            </Button>
          ),
        ]}
        pagination={{ defaultPageSize: 10 }}
      />
    </PageContainer>
  );
};

export default UserPage;

