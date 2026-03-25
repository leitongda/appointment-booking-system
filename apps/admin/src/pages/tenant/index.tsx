import type { ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable } from '@ant-design/pro-components';
import { Tag, Button, Space, Popconfirm } from 'antd';
import { history, useAccess } from '@umijs/max';
import { tenantApi } from '@hospital/api';
import { createListRequest } from '@/utils/proTable';
import { useListPage } from '@/hooks/useListPage';
import { CreateButton, createOperationColumn } from '@/components/ListOperations';
import type { Tenant } from '@hospital/api';

const TENANT_STATUS_MAP: Record<number, { text: string; status: 'Success' | 'Error' | 'Warning' | 'Default' }> = {
  0: { text: '已禁用', status: 'Default' },
  1: { text: '正常', status: 'Success' },
  2: { text: '已欠费', status: 'Error' },
  3: { text: '试用中', status: 'Warning' },
};

const TenantPage: React.FC = () => {
  const access = useAccess();
  const { actionRef, handleDelete, refresh } = useListPage({
    deleteFn: tenantApi.deleteTenant,
  });

  const handleActivate = async (tenantId: string) => {
    await tenantApi.activateTenant(tenantId);
    refresh();
  };

  const handleSuspend = async (tenantId: string) => {
    await tenantApi.suspendTenant(tenantId);
    refresh();
  };

  const columns: ProColumns<Tenant>[] = [
    {
      title: '租户标识',
      dataIndex: 'tenantCode',
      width: 120,
      copyable: true,
    },
    {
      title: '租户名称',
      dataIndex: 'name',
      width: 150,
      render: (_, record) => (
        <a onClick={() => history.push(`/tenant/${record.id}`)}>{record.name}</a>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 80,
      valueEnum: {
        0: { text: '已禁用', status: 'Default' },
        1: { text: '正常', status: 'Success' },
        2: { text: '已欠费', status: 'Error' },
        3: { text: '试用中', status: 'Warning' },
      },
    },
    {
      title: '订阅计划',
      dataIndex: 'subscriptionPlanId',
      width: 100,
      search: false,
      render: (_, record) => (
        record.subscriptionPlanName ? (
          <Tag color="blue">{record.subscriptionPlanName}</Tag>
        ) : (
          <Tag>未订阅</Tag>
        )
      ),
    },
    {
      title: '订阅到期',
      dataIndex: 'subscriptionEndAt',
      width: 120,
      valueType: 'date',
      search: false,
    },
    {
      title: '门店/管理员',
      dataIndex: 'storeCount',
      width: 100,
      search: false,
      render: (_, record) => (
        <span>
          {record.storeCount || 0} / {record.adminCount || 0}
        </span>
      ),
    },
    {
      title: '联系人',
      dataIndex: 'contactName',
      width: 100,
      search: false,
    },
    {
      title: '联系电话',
      dataIndex: 'contactPhone',
      width: 120,
      search: false,
    },
    {
      title: '创建时间',
      dataIndex: 'createdAt',
      valueType: 'dateTime',
      width: 160,
      search: false,
    },
    createOperationColumn<Tenant>({
      width: 200,
      editUrl: (r) => `/tenant/${r.id}/edit`,
      editPermission: 'tenant:update',
      onDelete: handleDelete,
      deletePermission: 'tenant:delete',
      deleteConfirmText: '确定删除该租户吗？删除后数据将无法恢复！',
      canDelete: (r) => r.status === 0,
      moreActions: (record) => [
        access.hasPermission('tenant:update') && record.status === 0 && {
          key: 'activate',
          label: '激活',
          onClick: () => handleActivate(record.id),
        },
        access.hasPermission('tenant:update') && record.status === 1 && {
          key: 'suspend',
          label: (
            <Popconfirm
              title="确定暂停该租户吗？暂停后租户将无法使用系统。"
              onConfirm={() => handleSuspend(record.id)}
            >
              <span>暂停</span>
            </Popconfirm>
          ),
        },
      ].filter(Boolean) as any,
    }),
  ];

  return (
    <PageContainer>
      <ProTable<Tenant>
        headerTitle="租户列表"
        actionRef={actionRef}
        rowKey="id"
        columns={columns}
        request={createListRequest(tenantApi.getTenants)}
        toolBarRender={() => [
          <CreateButton
            key="add"
            permission="tenant:create"
            url="/tenant/create"
            label="新增租户"
          />,
          access.hasPermission('tenant:plan:view') && (
            <Button key="plans" onClick={() => history.push('/tenant/plans')}>
              订阅计划
            </Button>
          ),
        ].filter(Boolean)}
        pagination={{ defaultPageSize: 10 }}
      />
    </PageContainer>
  );
};

export default TenantPage;
