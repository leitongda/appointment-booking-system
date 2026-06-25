/**
 * 文章管理 - 列表页
 */
import type { ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable } from '@ant-design/pro-components';
import { Tag } from 'antd';
import { useEffect, useMemo, useState } from 'react';
import { articleApi, categoryApi, siteApi } from '@hospital/api';
import type { CmsArticle, CmsCategory, CmsSite } from '@hospital/api';
import { createListRequest } from '@/utils/proTable';
import { useListPage } from '@/hooks/useListPage';
import { CreateButton, createOperationColumn } from '@/components/ListOperations';

const ArticleListPage: React.FC = () => {
  const { actionRef, handleDelete } = useListPage({ deleteFn: articleApi.delete });
  const [sites, setSites] = useState<CmsSite[]>([]);
  const [categories, setCategories] = useState<CmsCategory[]>([]);

  useEffect(() => {
    siteApi
      .getList({ page: 1, pageSize: 100 })
      .then((res) => setSites(res.data || []))
      .catch(() => {});
    categoryApi
      .getList()
      .then(setCategories)
      .catch(() => setCategories([]));
  }, []);

  const siteOptions = useMemo(
    () => sites.map((s) => ({ label: s.name, value: s.id })),
    [sites],
  );
  const categoryOptions = useMemo(
    () => categories.map((c) => ({ label: c.name, value: c.id })),
    [categories],
  );

  const columns: ProColumns<CmsArticle>[] = [
    {
      title: '文章标题',
      dataIndex: 'title',
      ellipsis: true,
      render: (_, r) => (
        <span>
          {r.title}
          {r.isTop ? <Tag color="red" style={{ marginLeft: 6 }}>置顶</Tag> : null}
        </span>
      ),
    },
    {
      title: '所属站点',
      dataIndex: 'siteId',
      width: 130,
      hideInTable: !siteOptions.length,
      valueType: 'select',
      fieldProps: { options: siteOptions, allowClear: true, showSearch: true },
      render: (_, r) => sites.find((s) => s.id === r.siteId)?.name || r.siteId,
    },
    {
      title: '栏目',
      dataIndex: 'categoryId',
      width: 130,
      valueType: 'select',
      fieldProps: { options: categoryOptions, allowClear: true, showSearch: true },
      render: (_, r) => categories.find((c) => c.id === r.categoryId)?.name || '-',
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 100,
      valueType: 'select',
      valueEnum: {
        0: { text: '草稿', status: 'Default' },
        1: { text: '已发布', status: 'Success' },
        2: { text: '已下线', status: 'Warning' },
      },
    },
    { title: '浏览量', dataIndex: 'viewCount', width: 90, search: false },
    { title: '发布时间', dataIndex: 'publishTime', valueType: 'dateTime', width: 170, search: false },
    createOperationColumn<CmsArticle>({
      width: 170,
      viewUrl: (r) => `/cms/articles/${r.id}/detail`,
      viewPermission: 'cms:article',
      editUrl: (r) => `/cms/articles/${r.id}/edit`,
      editPermission: 'cms:article:update',
      onDelete: handleDelete,
      deletePermission: 'cms:article:delete',
      deleteConfirmText: '确定删除该文章吗？',
    }),
  ];

  return (
    <PageContainer>
      <ProTable<CmsArticle>
        headerTitle="文章列表"
        actionRef={actionRef}
        rowKey="id"
        columns={columns}
        request={createListRequest(articleApi.getList)}
        toolBarRender={() => [
          <CreateButton
            key="add"
            permission="cms:article:create"
            url="/cms/articles/create"
            label="发布文章"
          />,
        ]}
        pagination={{ defaultPageSize: 10 }}
      />
    </PageContainer>
  );
};

export default ArticleListPage;
