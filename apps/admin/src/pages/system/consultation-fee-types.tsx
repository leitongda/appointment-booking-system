import type { ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable } from '@ant-design/pro-components';
import { consultationFeeTypeApi } from '@hospital/api';
import type { ConsultationFeeType } from '@hospital/shared';
import { useListPage } from '@/hooks/useListPage';
import { CreateButton, createOperationColumn } from '@/components/ListOperations';

const ConsultationFeeTypesPage: React.FC = () => {
  const { actionRef, handleDelete } = useListPage({
    deleteFn: consultationFeeTypeApi.delete,
  });

  const columns: ProColumns<ConsultationFeeType>[] = [
    {
      title: '类型名称',
      dataIndex: 'name',
      ellipsis: true,
    },
    {
      title: '类型编码',
      dataIndex: 'code',
      ellipsis: true,
      search: false,
    },
    {
      title: '描述',
      dataIndex: 'description',
      ellipsis: true,
      search: false,
    },
    {
      title: '排序',
      dataIndex: 'sortOrder',
      width: 80,
      search: false,
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 80,
      valueType: 'select',
      valueEnum: {
        1: { text: '启用', status: 'Success' },
        0: { text: '禁用', status: 'Default' },
      },
    },
    {
      title: '创建时间',
      dataIndex: 'createdAt',
      valueType: 'dateTime',
      width: 160,
      search: false,
    },
    createOperationColumn<ConsultationFeeType>({
      width: 120,
      editUrl: (r) => `/system/consultation-fee-types/${r.id}/edit`,
      editPermission: 'system:consultation-fee',
      onDelete: handleDelete,
      deletePermission: 'system:consultation-fee',
      deleteConfirmText: '确定删除该诊费类型吗？',
      deleteConfirmDescription: '删除后相关诊费配置也会受影响',
    }),
  ];

  return (
    <PageContainer>
      <ProTable<ConsultationFeeType>
        headerTitle="诊费类型列表"
        actionRef={actionRef}
        rowKey="id"
        columns={columns}
        search={false}
        request={async (params) => {
          const list = await consultationFeeTypeApi.getList({ status: params.status });
          return {
            data: list,
            success: true,
            total: list.length,
          };
        }}
        toolBarRender={() => [
          <CreateButton
            key="add"
            permission="system:consultation-fee"
            url="/system/consultation-fee-types/create"
            label="新增诊费类型"
          />,
        ]}
        pagination={false}
      />
    </PageContainer>
  );
};

export default ConsultationFeeTypesPage;
