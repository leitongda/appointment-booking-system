import { PlusOutlined } from '@ant-design/icons';
import type { ActionType, ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable } from '@ant-design/pro-components';
import { Button, App, Popconfirm, Space, Tag } from 'antd';
import { useRef } from 'react';
import { history, useAccess } from '@umijs/max';
import { contentApi } from '@hospital/api';
import { toProTableResult } from '@/utils/proTable';
import type { Notice } from '@hospital/api';

const NoticePage: React.FC = () => {
  const { message } = App.useApp();
  const access = useAccess();
  const actionRef = useRef<ActionType>();

  const handleDelete = async (id: string) => {
    try {
      await contentApi.deleteNotice(id);
      message.success('删除成功');
      actionRef.current?.reload();
    } catch (error: any) {
      message.error(error.message || '删除失败');
    }
  };

  const columns: ProColumns<Notice>[] = [
    { title: '标题', dataIndex: 'title', ellipsis: true },
    { title: '类型', dataIndex: 'type', width: 100, valueEnum: { 1: '系统公告', 2: '停诊通知', 3: '活动通知' } },
    { title: '置顶', dataIndex: 'isTop', width: 70, search: false, render: (_, r) => r.isTop ? <Tag color="red">置顶</Tag> : '-' },
    { title: '状态', dataIndex: 'status', width: 80, valueEnum: { 1: { text: '发布', status: 'Success' }, 0: { text: '草稿', status: 'Default' } } },
    { title: '发布时间', dataIndex: 'publishTime', valueType: 'dateTime', width: 160, search: false },
    {
      title: '操作',
      valueType: 'option',
      width: 120,
      render: (_, record) => (
        <Space>
          {access.hasPermission('content:notice:update') && (
            <a onClick={() => history.push(`/content/notice/${record.id}/edit`)}>编辑</a>
          )}
          {access.hasPermission('content:notice:delete') && (
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
      <ProTable<Notice>
        headerTitle="公告列表"
        actionRef={actionRef}
        rowKey="id"
        columns={columns}
        request={async (params) => {
          const { current, pageSize, ...rest } = params;
          return toProTableResult(await contentApi.getNoticeList({ ...rest, page: current, pageSize }));
        }}
        toolBarRender={() => [
          access.hasPermission('content:notice:create') && (
            <Button
              key="add"
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => history.push('/content/notice/create')}
            >
              发布公告
            </Button>
          ),
        ]}
        pagination={{ defaultPageSize: 10 }}
      />
    </PageContainer>
  );
};

export default NoticePage;
