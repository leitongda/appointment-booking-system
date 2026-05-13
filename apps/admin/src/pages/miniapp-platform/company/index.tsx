import type { ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable } from '@ant-design/pro-components';
import { history } from '@umijs/max';
import { miniappPlatformApi } from '@hospital/api';
import { createListRequest } from '@/utils/proTable';
import { useListPage } from '@/hooks/useListPage';
import { CreateButton, createOperationColumn } from '@/components/ListOperations';
import type { Company } from '@hospital/api';

const CompanyPage: React.FC = () => {
  const { actionRef, handleDelete } = useListPage({
    deleteFn: miniappPlatformApi.deleteCompany,
  });

  const columns: ProColumns<Company>[] = [
    {
      title: '公司名称',
      dataIndex: 'name',
      width: 200,
      render: (_, record) => (
        <a onClick={() => history.push(`/platform/miniapp-platform/company/${record.id}`)}>{record.name}</a>
      ),
    },
    {
      title: '编码',
      dataIndex: 'code',
      width: 120,
      copyable: true,
    },
    {
      title: '统一社会信用代码',
      dataIndex: 'unifiedSocialCreditCode',
      width: 180,
      search: false,
      ellipsis: true,
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
    createOperationColumn<Company>({
      width: 150,
      editUrl: (r) => `/platform/miniapp-platform/company/${r.id}/edit`,
      onDelete: handleDelete,
      deleteConfirmText: '确定删除该公司吗？',
    }),
  ];

  return (
    <PageContainer>
      <ProTable<Company>
        headerTitle="公司列表"
        actionRef={actionRef}
        rowKey="id"
        columns={columns}
        request={createListRequest(miniappPlatformApi.getCompanies)}
        toolBarRender={() => [
          <CreateButton
            key="add"
            url="/platform/miniapp-platform/company/create"
            label="新增公司"
          />,
        ]}
        pagination={{ defaultPageSize: 10 }}
      />
    </PageContainer>
  );
};

export default CompanyPage;
