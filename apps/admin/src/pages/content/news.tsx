import { PlusOutlined } from '@ant-design/icons';
import type { ActionType, ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable } from '@ant-design/pro-components';
import { Button, App, Popconfirm, Space, Tag, Image } from 'antd';
import { useRef } from 'react';
import { history, useAccess } from '@umijs/max';
import { contentApi } from '@hospital/api';
import { toProTableResult } from '@/utils/proTable';
import type { News } from '@hospital/api';

const NewsPage: React.FC = () => {
  const { message } = App.useApp();
  const access = useAccess();
  const actionRef = useRef<ActionType>();

  const handleDelete = async (id: string) => {
    try {
      await contentApi.deleteNews(id);
      message.success('删除成功');
      actionRef.current?.reload();
    } catch (error: any) {
      message.error(error.message || '删除失败');
    }
  };

  const columns: ProColumns<News>[] = [
    { title: '封面', dataIndex: 'coverImage', width: 80, search: false, render: (_, r) => r.coverImage ? <Image src={r.coverImage} width={60} /> : '-' },
    { title: '标题', dataIndex: 'title', ellipsis: true },
    { title: '类型', dataIndex: 'type', width: 100, valueEnum: { 1: '医院动态', 2: '健康知识', 3: '政策法规' } },
    { title: '浏览量', dataIndex: 'viewCount', width: 80, search: false },
    { title: '置顶', dataIndex: 'isTop', width: 70, search: false, render: (_, r) => r.isTop ? <Tag color="red">置顶</Tag> : '-' },
    { title: '状态', dataIndex: 'status', width: 80, valueEnum: { 1: { text: '发布', status: 'Success' }, 0: { text: '草稿', status: 'Default' } } },
    { title: '发布时间', dataIndex: 'publishTime', valueType: 'dateTime', width: 160, search: false },
    {
      title: '操作',
      valueType: 'option',
      width: 120,
      render: (_, record) => (
        <Space>
          {access.hasPermission('content:news:update') && (
            <a onClick={() => history.push(`/content/news/${record.id}/edit`)}>编辑</a>
          )}
          {access.hasPermission('content:news:delete') && (
            <Popconfirm title="确定删除吗？" onConfirm={() => handleDelete(record.id)}>
              <a style={{ color: '#ff4d4f' }}>删除</a>
            </Popconfirm>
          )}
        </Space>
      ),
    },
  ];

  return (
    <PageContainer>
      <ProTable<News>
        headerTitle="新闻列表"
        actionRef={actionRef}
        rowKey="id"
        columns={columns}
        request={async (params) => {
          const { current, pageSize, ...rest } = params;
          return toProTableResult(await contentApi.getNewsList({ ...rest, page: current, pageSize }));
        }}
        toolBarRender={() => [
          access.hasPermission('content:news:create') && (
            <Button
              key="add"
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => history.push('/content/news/create')}
            >
              发布新闻
            </Button>
          ),
        ]}
        pagination={{ defaultPageSize: 10 }}
      />
    </PageContainer>
  );
};

export default NewsPage;
