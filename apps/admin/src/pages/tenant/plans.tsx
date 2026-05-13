import type { ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable } from '@ant-design/pro-components';
import { Tag, Button, Drawer, Descriptions, Spin } from 'antd';
import { history, useAccess } from '@umijs/max';
import { tenantApi } from '@hospital/api';
import { createListRequest } from '@/utils/proTable';
import { useListPage } from '@/hooks/useListPage';
import { CreateButton, createOperationColumn } from '@/components/ListOperations';
import type { SubscriptionPlan } from '@hospital/api';
import { useState, useCallback } from 'react';

const STATUS_MAP: Record<number, { text: string; color: string }> = {
  0: { text: '禁用', color: 'default' },
  1: { text: '启用', color: 'success' },
};

const SubscriptionPlanPage: React.FC = () => {
  const access = useAccess();
  const { actionRef, handleDelete } = useListPage({
    deleteFn: tenantApi.deletePlan,
  });

  // Drawer 详情状态
  const [detailData, setDetailData] = useState<SubscriptionPlan | null>(null);
  const [detailOpen, setDetailOpen] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);

  const handleView = useCallback(async (planId: string) => {
    setDetailOpen(true);
    setDetailLoading(true);
    try {
      const data = await tenantApi.getPlan(planId);
      setDetailData(data);
    } finally {
      setDetailLoading(false);
    }
  }, []);

  const handleDetailClose = useCallback(() => {
    setDetailOpen(false);
    setDetailData(null);
  }, []);

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
      width: 180,
      editUrl: (r) => `/platform/tenant/plans/${r.id}/edit`,
      editPermission: 'tenant:plan:update',
      onDelete: handleDelete,
      deletePermission: 'tenant:plan:delete',
      deleteConfirmText: '确定删除该订阅计划吗？',
      canDelete: (r) => !r.isDefault,
      moreActions: (record) => [
        access.hasPermission('tenant:plan:view') && {
          key: 'view',
          label: '查看详情',
          onClick: () => handleView(record.id),
        },
      ].filter(Boolean) as any,
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

      <Drawer
        title="订阅计划详情"
        width={520}
        open={detailOpen}
        onClose={handleDetailClose}
        destroyOnHidden
      >
        {detailLoading ? (
          <Spin />
        ) : detailData ? (
          <Descriptions column={1} bordered size="small" items={[
            { key: '0', label: '计划编码', children: detailData.planCode },
            { key: '1', label: '计划名称', children: detailData.name },
            ...(detailData.description ? [{ key: '2', label: '描述', children: detailData.description }] : []),
            { key: '3', label: '状态', children: (
              <Tag color={STATUS_MAP[detailData.status]?.color}>
                {STATUS_MAP[detailData.status]?.text}
              </Tag>
            ) },
            { key: '4', label: '是否默认', children: detailData.isDefault ? <Tag color="blue">默认计划</Tag> : '否' },
            { key: '5', label: '月付价格', children: `¥${detailData.priceMonthly}` },
            { key: '6', label: '年付价格', children: `¥${detailData.priceYearly}` },
            { key: '7', label: '货币单位', children: detailData.currency },
            { key: '8', label: '门店上限', children: detailData.maxStores },
            { key: '9', label: '管理员上限', children: detailData.maxAdmins },
            { key: '10', label: '医生上限', children: detailData.maxDoctors },
            { key: '11', label: '月预约上限', children: detailData.maxAppointmentsPerMonth },
            { key: '12', label: '存储空间上限', children: `${detailData.maxStorageMb} MB` },
            { key: '13', label: '排序', children: detailData.sortOrder },
            { key: '14', label: '创建时间', children: detailData.createdAt },
            ...(detailData.updatedAt ? [{ key: '15', label: '更新时间', children: detailData.updatedAt }] : []),
          ]} />
        ) : null}
      </Drawer>
    </PageContainer>
  );
};

export default SubscriptionPlanPage;
