/**
 * 站点管理 - 列表页
 */
import type { ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable } from '@ant-design/pro-components';
import { Tag } from 'antd';
import { siteApi } from '@hospital/api';
import type { CmsSite } from '@hospital/api';
import { createListRequest } from '@/utils/proTable';
import { useListPage } from '@/hooks/useListPage';
import { CreateButton, createOperationColumn } from '@/components/ListOperations';

const SiteListPage: React.FC = () => {
  const { actionRef, handleDelete } = useListPage({ deleteFn: siteApi.delete });

  const columns: ProColumns<CmsSite>[] = [
    { title: '站点名称', dataIndex: 'name', ellipsis: true },
    { title: '站点编码', dataIndex: 'code', width: 140 },
    { title: '绑定域名', dataIndex: 'domain', width: 220, ellipsis: true },
    {
      title: '状态',
      dataIndex: 'status',
      width: 90,
      valueEnum: {
        1: { text: '正常', status: 'Success' },
        0: { text: '禁用', status: 'Default' },
      },
    },
    {
      title: '默认',
      dataIndex: 'isDefault',
      width: 80,
      render: (_, r) => (r.isDefault ? <Tag color="blue">默认</Tag> : '-'),
    },
    { title: '创建时间', dataIndex: 'createdAt', valueType: 'dateTime', width: 170, search: false },
    createOperationColumn<CmsSite>({
      width: 130,
      editUrl: (r) => `/cms/sites/${r.id}/edit`,
      editPermission: 'cms:site:update',
      onDelete: handleDelete,
      deletePermission: 'cms:site:delete',
      deleteConfirmText: '确定删除该站点吗？',
    }),
  ];

  return (
    <PageContainer>
      <ProTable<CmsSite>
        headerTitle="站点列表"
        actionRef={actionRef}
        rowKey="id"
        columns={columns}
        request={createListRequest(siteApi.getList)}
        toolBarRender={() => [
          <CreateButton
            key="add"
            permission="cms:site:create"
            url="/cms/sites/create"
            label="新增站点"
          />,
        ]}
        pagination={{ defaultPageSize: 10 }}
      />
    </PageContainer>
  );
};

export default SiteListPage;
