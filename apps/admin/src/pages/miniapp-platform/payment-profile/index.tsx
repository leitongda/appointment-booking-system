import type { ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable } from '@ant-design/pro-components';
import { Tag, Button, Dropdown } from 'antd';
import { history } from '@umijs/max';
import { miniappPlatformApi } from '@hospital/api';
import { createListRequest } from '@/utils/proTable';
import { useListPage } from '@/hooks/useListPage';
import { CreateButton, createOperationColumn } from '@/components/ListOperations';
import type { PaymentProfile } from '@hospital/api';

const PAYMENT_MODE_MAP: Record<string, { text: string; color: string }> = {
  direct: { text: '直连', color: 'blue' },
  service_provider: { text: '服务商', color: 'green' },
};

const PROFILE_STATUS_MAP: Record<number, { text: string; status: 'Success' | 'Error' }> = {
  0: { text: '已禁用', status: 'Error' },
  1: { text: '已启用', status: 'Success' },
};

const PaymentProfilePage: React.FC = () => {
  const { actionRef, handleDelete, refresh } = useListPage({
    deleteFn: miniappPlatformApi.deletePaymentProfile,
  });

  const handleSetDefault = async (profileId: string) => {
    try {
      await miniappPlatformApi.setDefaultPaymentProfile(profileId);
      refresh();
    } catch (error: any) {
      // Error already handled by API
    }
  };

  const columns: ProColumns<PaymentProfile>[] = [
    {
      title: '配置名称',
      dataIndex: 'name',
      width: 180,
      render: (_, record) => (
        <div>
          <a onClick={() => history.push(`/platform/miniapp-platform/payment-profile/${record.id}`)}>{record.name}</a>
          {record.isDefault && <Tag color="gold" style={{ marginLeft: 8 }}>默认</Tag>}
        </div>
      ),
    },
    {
      title: '编码',
      dataIndex: 'code',
      width: 120,
      search: false,
      copyable: true,
    },
    {
      title: '支付模式',
      dataIndex: 'mode',
      width: 100,
      valueType: 'select',
      valueEnum: {
        direct: { text: '直连', status: 'Success' },
        service_provider: { text: '服务商', status: 'Processing' },
      },
    },
    {
      title: 'AppID',
      dataIndex: 'appId',
      width: 180,
      search: false,
      copyable: true,
      ellipsis: true,
    },
    {
      title: '商户号',
      dataIndex: 'mchId',
      width: 150,
      search: false,
      copyable: true,
      ellipsis: true,
    },
    {
      title: '所属公司',
      dataIndex: ['company', 'name'],
      width: 150,
      search: false,
      render: (_, record) => record.company?.name || '-',
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 80,
      valueEnum: {
        0: { text: '已禁用', status: 'Error' },
        1: { text: '已启用', status: 'Success' },
      },
    },
    {
      title: '创建时间',
      dataIndex: 'createdAt',
      valueType: 'dateTime',
      width: 160,
      search: false,
    },
    createOperationColumn<PaymentProfile>({
      width: 180,
      editUrl: (r) => `/platform/miniapp-platform/payment-profile/${r.id}/edit`,
      onDelete: handleDelete,
      deleteConfirmText: '确定删除该支付配置吗？',
      moreActions: (record) => [
        !record.isDefault && {
          key: 'setDefault',
          label: '设为默认',
          onClick: () => handleSetDefault(record.id),
        },
      ].filter(Boolean) as any,
    }),
  ];

  return (
    <PageContainer>
      <ProTable<PaymentProfile>
        headerTitle="支付配置列表"
        actionRef={actionRef}
        rowKey="id"
        columns={columns}
        request={createListRequest(miniappPlatformApi.getPaymentProfiles)}
        toolBarRender={() => [
          <CreateButton
            key="add"
            url="/platform/miniapp-platform/payment-profile/create"
            label="新增支付配置"
          />,
        ]}
        pagination={{ defaultPageSize: 10 }}
      />
    </PageContainer>
  );
};

export default PaymentProfilePage;
