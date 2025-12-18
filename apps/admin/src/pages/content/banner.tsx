import { PlusOutlined } from '@ant-design/icons';
import type { ActionType, ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable } from '@ant-design/pro-components';
import { Button, App, Popconfirm, Space, Image } from 'antd';
import { useRef } from 'react';
import { history, useAccess } from '@umijs/max';
import { contentApi } from '@hospital/api';
import { toProTableResult } from '@/utils/proTable';
import type { Banner } from '@hospital/api';

const BannerPage: React.FC = () => {
  const { message } = App.useApp();
  const access = useAccess();
  const actionRef = useRef<ActionType>();

  const handleDelete = async (id: string) => {
    try {
      await contentApi.deleteBanner(id);
      message.success('删除成功');
      actionRef.current?.reload();
    } catch (error: any) {
      message.error(error.message || '删除失败');
    }
  };

  const columns: ProColumns<Banner>[] = [
    { title: '图片', dataIndex: 'imageUrl', width: 120, search: false, render: (_, r) => <Image src={r.imageUrl} width={100} /> },
    { title: '标题', dataIndex: 'title', ellipsis: true },
    { title: '位置', dataIndex: 'position', width: 100, valueEnum: { home: '首页', mine: '我的' } },
    { title: '链接类型', dataIndex: 'linkType', width: 100, search: false, valueEnum: { 0: '无链接', 1: '内部', 2: '外部' } },
    { title: '排序', dataIndex: 'sortOrder', width: 70, search: false },
    { title: '状态', dataIndex: 'status', width: 80, valueEnum: { 1: { text: '启用', status: 'Success' }, 0: { text: '禁用', status: 'Default' } } },
    {
      title: '操作',
      valueType: 'option',
      width: 120,
      render: (_, record) => (
        <Space>
          {access.hasPermission('content:banner:update') && (
            <a onClick={() => history.push(`/content/banner/${record.id}/edit`)}>编辑</a>
          )}
          {access.hasPermission('content:banner:delete') && (
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
      <ProTable<Banner>
        headerTitle="轮播图列表"
        actionRef={actionRef}
        rowKey="id"
        columns={columns}
        request={async (params) => {
          const { current, pageSize, ...rest } = params;
          return toProTableResult(await contentApi.getBannerList({ ...rest, page: current, pageSize }));
        }}
        toolBarRender={() => [
          access.hasPermission('content:banner:create') && (
            <Button
              key="add"
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => history.push('/content/banner/create')}
            >
              新增轮播图
            </Button>
          ),
        ]}
        pagination={{ defaultPageSize: 10 }}
      />
    </PageContainer>
  );
};

export default BannerPage;
