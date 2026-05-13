import type { ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable } from '@ant-design/pro-components';
import { history } from '@umijs/max';
import { miniappPlatformApi } from '@hospital/api';
import { createListRequest } from '@/utils/proTable';
import { useListPage } from '@/hooks/useListPage';
import { CreateButton, createOperationColumn } from '@/components/ListOperations';
import type { MiniappInstance } from '@hospital/api';

const MiniappInstancePage: React.FC = () => {
  const { actionRef, handleDelete, refresh } = useListPage({
    deleteFn: miniappPlatformApi.deleteMiniappInstance,
  });

  const handleActivate = async (instanceId: string) => {
    try {
      await miniappPlatformApi.activateMiniappInstance(instanceId);
      refresh();
    } catch (error: any) {
      // Error already handled by API
    }
  };

  const handleArchive = async (instanceId: string) => {
    try {
      await miniappPlatformApi.archiveMiniappInstance(instanceId);
      refresh();
    } catch (error: any) {
      // Error already handled by API
    }
  };

  const columns: ProColumns<MiniappInstance>[] = [
    {
      title: '实例名称',
      dataIndex: 'name',
      width: 180,
      render: (_, record) => (
        <a onClick={() => history.push(`/platform/miniapp-platform/instance/${record.id}`)}>{record.name}</a>
      ),
    },
    {
      title: '编码',
      dataIndex: 'code',
      width: 100,
      search: false,
      copyable: true,
    },
    {
      title: 'AppID',
      dataIndex: 'appId',
      width: 180,
      copyable: true,
      ellipsis: true,
    },
    {
      title: '模板',
      dataIndex: 'templateName',
      width: 120,
      search: false,
      render: (_, record) => record.templateName || '-',
    },
    {
      title: '模板版本',
      dataIndex: 'templateVersion',
      width: 100,
      search: false,
      render: (_, record) => record.templateVersion || '-',
    },
    {
      title: '默认门店',
      dataIndex: 'storeName',
      width: 120,
      search: false,
      render: (_, record) => record.storeName || '-',
    },
    {
      title: '支付配置',
      dataIndex: 'paymentProfileName',
      width: 120,
      search: false,
      render: (_, record) => record.paymentProfileName || '-',
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 80,
      valueEnum: {
        0: { text: '已禁用', status: 'Error' },
        1: { text: '已启用', status: 'Success' },
        2: { text: '已归档', status: 'Default' },
      },
    },
    {
      title: '创建时间',
      dataIndex: 'createdAt',
      valueType: 'dateTime',
      width: 160,
      search: false,
    },
    createOperationColumn<MiniappInstance>({
      width: 200,
      editUrl: (r) => `/platform/miniapp-platform/instance/${r.id}/edit`,
      onDelete: handleDelete,
      deleteConfirmText: '确定删除该实例吗？删除后数据将无法恢复！',
      canDelete: (r) => r.status === 0,
      moreActions: (record) => [
        record.status === 0 && {
          key: 'activate',
          label: '激活',
          onClick: () => handleActivate(record.id),
        },
        record.status === 1 && {
          key: 'archive',
          label: '归档',
          onClick: () => handleArchive(record.id),
        },
      ].filter(Boolean) as any,
    }),
  ];

  return (
    <PageContainer>
      <ProTable<MiniappInstance>
        headerTitle="小程序实例列表"
        actionRef={actionRef}
        rowKey="id"
        columns={columns}
        request={createListRequest(miniappPlatformApi.getMiniappInstances)}
        toolBarRender={() => [
          <CreateButton
            key="add"
            url="/platform/miniapp-platform/instance/create"
            label="新增实例"
          />,
        ]}
        pagination={{ defaultPageSize: 10 }}
      />
    </PageContainer>
  );
};

export default MiniappInstancePage;
