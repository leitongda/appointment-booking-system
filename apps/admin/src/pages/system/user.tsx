import { KeyOutlined } from '@ant-design/icons';
import type { ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable } from '@ant-design/pro-components';
import { Avatar, Tag, Modal } from 'antd';
import { useMemo } from 'react';
import { useAccess, useModel } from '@umijs/max';
import { adminApi, storeApi, dataApi } from '@hospital/api';
import { createListRequest } from '@/utils/proTable';
import { useListPage } from '@/hooks/useListPage';
import {
  CreateButton,
  OperationButton,
  OperationGroup,
} from '@/components/ListOperations';
import ImportExport from '@/components/ImportExport';
import { DEFAULT_RESET_PASSWORD } from '@/constants';
import type { Admin } from '@hospital/api';

const UserPage: React.FC = () => {
  const access = useAccess();
  const { actionRef, handleDelete, handleAction } = useListPage({
    deleteFn: adminApi.deleteAdmin,
  });
  const { initialState } = useModel('@@initialState');
  const { currentUser } = initialState ?? {};
  const isSuperAdmin = access.canSuperAdmin;
  // 多门店管理员也可以看到门店筛选
  const showStoreFilter = isSuperAdmin || (currentUser?.storeIds?.length ?? 0) > 1;

  const handleResetPassword = (id: string) => {
    Modal.confirm({
      title: `确定重置密码为 ${DEFAULT_RESET_PASSWORD} 吗？`,
      onOk: async () => {
        await handleAction(
          () => adminApi.resetAdminPassword(id, DEFAULT_RESET_PASSWORD),
          { successText: `密码已重置为 ${DEFAULT_RESET_PASSWORD}`, errorText: '重置失败' }
        );
      },
    });
  };

  const columns: ProColumns<Admin>[] = useMemo(() => [
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
      dataIndex: 'stores',
      width: 200,
      search: false,
      render: (_: any, record: Admin) => {
        // 优先使用 stores 数组显示所有门店
        if (record.stores && record.stores.length > 0) {
          return (
            <>
              {record.stores.map((store) => (
                <Tag key={store.id}>{store.name}</Tag>
              ))}
            </>
          );
        }
        // 兼容旧数据：使用 storeName
        if (record.storeName) {
          return <Tag>{record.storeName}</Tag>;
        }
        // 无门店绑定
        return <Tag color="purple">全局</Tag>;
      },
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
      width: 180,
      fixed: 'right',
      render: (_, record) => (
        <OperationGroup
          moreItems={[
            access.hasPermission('system:user:reset-password') && {
              key: 'reset-password',
              icon: <KeyOutlined />,
              label: '重置密码',
              onClick: () => handleResetPassword(record.id),
            },
          ].filter(Boolean) as any}
        >
          <OperationButton
            type="edit"
            permission="system:user:update"
            url={`/organization/staff/${record.id}/edit`}
          />
          {record.roleCode !== 'SUPER_ADMIN' && (
            <OperationButton
              type="delete"
              permission="system:user:delete"
              confirmText="确定删除该用户吗？"
              onClick={() => handleDelete(record.id)}
            />
          )}
        </OperationGroup>
      ),
    },
  ], [showStoreFilter, isSuperAdmin, currentUser?.storeIds, access, handleDelete]);

  return (
    <PageContainer>
      <ProTable<Admin>
        headerTitle="用户列表"
        actionRef={actionRef}
        rowKey="id"
        columns={columns}
        request={createListRequest(adminApi.getAdmins, (params) => {
          const { storeId, ...rest } = params;
          // 处理门店筛选
          if (storeId === 'null') {
            return { ...rest, storeId: '' };
          }
          return storeId ? { ...rest, storeId } : rest;
        })}
        toolBarRender={() => [
          <ImportExport
            key="import-export"
            moduleName="系统用户"
            exportUrl={dataApi.getExportUsersUrl()}
            showImport={false}
          />,
          <CreateButton
            key="add"
            permission="system:user:create"
            url="/organization/staff/create"
            label="新增用户"
          />,
        ]}
        pagination={{ defaultPageSize: 10 }}
      />
    </PageContainer>
  );
};

export default UserPage;
