import type { ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable } from '@ant-design/pro-components';
import { Tag, Button } from 'antd';
import { history, useAccess } from '@umijs/max';
import { tenantApi } from '@hospital/api';
import { createListRequest } from '@/utils/proTable';
import { useListPage } from '@/hooks/useListPage';
import { CreateButton, createOperationColumn } from '@/components/ListOperations';
import type { SubscriptionPlan } from '@hospital/api';

const SubscriptionPlanPage: React.FC = () => {
  const access = useAccess();
  const { actionRef, handleDelete } = useListPage({
    deleteFn: tenantApi.deletePlan,
  });

  const columns: ProColumns<SubscriptionPlan>[] = [
    {
      title: '计划编码',
      dataIndex: 'planCode',
      width: 100,
      copyable: true,
    },
    {
      title: '计划名称',
      dataIndex: 'name',
      width: 120,
    },
    {
      title: '月付价格',
      dataIndex: 'priceMonthly',
      width: 100,
      search: false,
      render: (_, record) => `¥${record.priceMonthly}`,
    },
    {
      title: '年付价格',
      dataIndex: 'priceYearly',
      width: 100,
      search: false,
      render: (_, record) => `¥${record.priceYearly}`,
    },
    {
      title: '门店上限',
      dataIndex: 'maxStores',
      width: 80,
      search: false,
    },
    {
      title: '管理员上限',
      dataIndex: 'maxAdmins',
      width: 100,
      search: false,
    },
    {
      title: '医生上限',
      dataIndex: 'maxDoctors',
      width: 80,
      search: false,
    },
    {
      title: '月预约上限',
      dataIndex: 'maxAppointmentsPerMonth',
      width: 100,
      search: false,
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 80,
      valueEnum: {
        1: { text: '启用', status: 'Success' },
        0: { text: '禁用', status: 'Default' },
      },
    },
    {
      title: '默认',
      dataIndex: 'isDefault',
      width: 80,
      search: false,
      render: (_, record) => record.isDefault ? <Tag color="blue">默认</Tag> : '-',
    },
    {
      title: '排序',
      dataIndex: 'sortOrder',
      width: 60,
      search: false,
    },
    createOperationColumn<SubscriptionPlan>({
      width: 150,
      editUrl: (r) => `/platform/tenant/plans/${r.id}/edit`,
      editPermission: 'tenant:plan:update',
      onDelete: handleDelete,
      deletePermission: 'tenant:plan:delete',
      deleteConfirmText: '确定删除该订阅计划吗？',
      canDelete: (r) => !r.isDefault,
    }),
  ];

  return (
    <PageContainer>
      <ProTable<SubscriptionPlan>
        headerTitle="订阅计划列表"
        actionRef={actionRef}
        rowKey="id"
        columns={columns}
        request={createListRequest(tenantApi.getPlans)}
        toolBarRender={() => [
          <CreateButton
            key="add"
            permission="tenant:plan:create"
            url="/platform/tenant/plans/create"
            label="新增计划"
          />,
          <Button key="back" onClick={() => history.push('/platform/tenant')}>
            返回租户列表
          </Button>,
        ]}
        pagination={false}
      />
    </PageContainer>
  );
};

export default SubscriptionPlanPage;
