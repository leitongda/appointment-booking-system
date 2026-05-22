import { useMemo } from 'react';
import type { ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable } from '@ant-design/pro-components';
import { Tag, Image } from 'antd';
import { contentApi } from '@hospital/api';
import { createListRequest } from '@/utils/proTable';
import { useListPage } from '@/hooks/useListPage';
import { useDict } from '@/hooks/useDict';
import { CreateButton, createOperationColumn } from '@/components/ListOperations';
import type { News } from '@hospital/api';

const NewsPage: React.FC = () => {
  const { actionRef, handleDelete } = useListPage({
    deleteFn: contentApi.deleteNews,
  });
  const { options: newsTypeOptions } = useDict('news_type');
  const newsTypeEnum = useMemo(
    () => Object.fromEntries(newsTypeOptions.map((o) => [Number(o.value), { text: o.label }])),
    [newsTypeOptions]
  );

  const columns: ProColumns<News>[] = [
    { title: '封面', dataIndex: 'coverImage', width: 80, search: false, render: (_, r) => r.coverImage ? <Image src={r.coverImage} width={60} /> : '-' },
    { title: '标题', dataIndex: 'title', ellipsis: true },
    { title: '类型', dataIndex: 'type', width: 100, valueEnum: newsTypeEnum },
    { title: '浏览量', dataIndex: 'viewCount', width: 80, search: false },
    { title: '置顶', dataIndex: 'isTop', width: 70, search: false, render: (_, r) => r.isTop ? <Tag color="red">置顶</Tag> : '-' },
    { title: '状态', dataIndex: 'status', width: 80, valueEnum: { 1: { text: '发布', status: 'Success' }, 0: { text: '草稿', status: 'Default' } } },
    { title: '发布时间', dataIndex: 'publishTime', valueType: 'dateTime', width: 160, search: false },
    createOperationColumn<News>({
      width: 120,
      editUrl: (r) => `/content-center/content/news/${r.id}/edit`,
      editPermission: 'content:news:update',
      onDelete: handleDelete,
      deletePermission: 'content:news:delete',
      deleteConfirmText: '确定删除吗？',
    }),
  ];

  return (
    <PageContainer>
      <ProTable<News>
        headerTitle="新闻列表"
        actionRef={actionRef}
        rowKey="id"
        columns={columns}
        request={createListRequest(contentApi.getNewsList)}
        toolBarRender={() => [
          <CreateButton
            key="add"
            permission="content:news:create"
            url="/content-center/content/news/create"
            label="发布新闻"
          />,
        ]}
        pagination={{ defaultPageSize: 10 }}
      />
    </PageContainer>
  );
};

export default NewsPage;
