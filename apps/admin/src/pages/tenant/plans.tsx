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
        destroyOnClose
      >
        {detailLoading ? (
          <Spin />
        ) : detailData ? (
          <Descriptions column={1} bordered size="small">
            <Descriptions.Item label="计划编码">{detailData.planCode}</Descriptions.Item>
            <Descriptions.Item label="计划名称">{detailData.name}</Descriptions.Item>
            {detailData.description && (
              <Descriptions.Item label="描述">{detailData.description}</Descriptions.Item>
            )}
            <Descriptions.Item label="状态">
              <Tag color={STATUS_MAP[detailData.status]?.color}>
                {STATUS_MAP[detailData.status]?.text}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="是否默认">
              {detailData.isDefault ? <Tag color="blue">默认计划</Tag> : '否'}
            </Descriptions.Item>
            <Descriptions.Item label="月付价格">¥{detailData.priceMonthly}</Descriptions.Item>
            <Descriptions.Item label="年付价格">¥{detailData.priceYearly}</Descriptions.Item>
            <Descriptions.Item label="货币单位">{detailData.currency}</Descriptions.Item>
            <Descriptions.Item label="门店上限">{detailData.maxStores}</Descriptions.Item>
            <Descriptions.Item label="管理员上限">{detailData.maxAdmins}</Descriptions.Item>
            <Descriptions.Item label="医生上限">{detailData.maxDoctors}</Descriptions.Item>
            <Descriptions.Item label="月预约上限">{detailData.maxAppointmentsPerMonth}</Descriptions.Item>
            <Descriptions.Item label="存储空间上限">{detailData.maxStorageMb} MB</Descriptions.Item>
            <Descriptions.Item label="排序">{detailData.sortOrder}</Descriptions.Item>
            <Descriptions.Item label="创建时间">{detailData.createdAt}</Descriptions.Item>
            {detailData.updatedAt && (
              <Descriptions.Item label="更新时间">{detailData.updatedAt}</Descriptions.Item>
            )}
          </Descriptions>
        ) : null}
      </Drawer>
    </PageContainer>
  );
};

export default SubscriptionPlanPage;
