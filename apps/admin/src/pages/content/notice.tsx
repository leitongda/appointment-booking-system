import type { ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable } from '@ant-design/pro-components';
import { Tag } from 'antd';
import { contentApi } from '@hospital/api';
import { createListRequest } from '@/utils/proTable';
import { useListPage } from '@/hooks/useListPage';
import { CreateButton, createOperationColumn } from '@/components/ListOperations';
import type { Notice } from '@hospital/api';

const NoticePage: React.FC = () => {
  const { actionRef, handleDelete } = useListPage({
    deleteFn: contentApi.deleteNotice,
  });

  const columns: ProColumns<Notice>[] = [
    { title: '标题', dataIndex: 'title', ellipsis: true },
    { title: '类型', dataIndex: 'type', width: 100, valueEnum: { 1: '系统公告', 2: '停诊通知', 3: '活动通知' } },
    { title: '置顶', dataIndex: 'isTop', width: 70, search: false, render: (_, r) => r.isTop ? <Tag color="red">置顶</Tag> : '-' },
    { title: '状态', dataIndex: 'status', width: 80, valueEnum: { 1: { text: '发布', status: 'Success' }, 0: { text: '草稿', status: 'Default' } } },
    { title: '发布时间', dataIndex: 'publishTime', valueType: 'dateTime', width: 160, search: false },
    createOperationColumn<Notice>({
      width: 120,
      editUrl: (r) => `/content-center/content/notice/${r.id}/edit`,
      editPermission: 'content:notice:update',
      onDelete: handleDelete,
      deletePermission: 'content:notice:delete',
      deleteConfirmText: '确定删除吗？',
    }),
  ];

  return (
    <PageContainer>
      <ProTable<Notice>
        headerTitle="公告列表"
        actionRef={actionRef}
        rowKey="id"
        columns={columns}
        request={createListRequest(contentApi.getNoticeList)}
        toolBarRender={() => [
          <CreateButton
            key="add"
            permission="content:notice:create"
            url="/content-center/content/notice/create"
            label="发布公告"
          />,
        ]}
        pagination={{ defaultPageSize: 10 }}
      />
    </PageContainer>
  );
};

export default NoticePage;
