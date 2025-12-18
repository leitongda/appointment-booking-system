import { PlusOutlined } from '@ant-design/icons';
import type { ActionType, ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable } from '@ant-design/pro-components';
import { Button, App, Popconfirm, Space, Avatar } from 'antd';
import { useRef } from 'react';
import { history, useAccess } from '@umijs/max';
import { storeApi } from '@hospital/api';
import { toProTableResult } from '@/utils/proTable';
import type { Store } from '@hospital/shared';

const StorePage: React.FC = () => {
  const { message } = App.useApp();
  const access = useAccess();
  const actionRef = useRef<ActionType>();

  const handleDelete = async (id: string) => {
    try {
      await storeApi.delete(id);
      message.success('删除成功');
      actionRef.current?.reload();
    } catch (error: any) {
      message.error(error.message || '删除失败');
    }
  };

  const columns: ProColumns<Store>[] = [
    {
      title: 'Logo',
      dataIndex: 'logo',
      width: 60,
      search: false,
      render: (_, record) => record.logo ? <Avatar src={record.logo} size={40} /> : '-',
    },
    { title: '门店名称', dataIndex: 'name', ellipsis: true },
    { title: '门店编码', dataIndex: 'code', width: 100, search: false },
    { title: '城市', dataIndex: 'city', width: 80 },
    { title: '地址', dataIndex: 'address', ellipsis: true, search: false },
    { title: '联系电话', dataIndex: 'phone', width: 120, search: false },
    { title: '风格', dataIndex: 'themeStyle', width: 80, search: false },
    {
      title: '状态',
      dataIndex: 'status',
      width: 80,
      valueEnum: { 1: { text: '营业', status: 'Success' }, 0: { text: '停业', status: 'Default' } },
    },
    {
      title: '操作',
      valueType: 'option',
      width: 120,
      render: (_, record) => (
        <Space>
          {access.hasPermission('store:update') && (
            <a onClick={() => history.push(`/store/${record.id}/edit`)}>编辑</a>
          )}
          {access.hasPermission('store:delete') && (
            <Popconfirm title="确定删除该门店吗？" onConfirm={() => handleDelete(record.id)}>
              <a style={{ color: '#ff4d4f' }}>删除</a>
            </Popconfirm>
          )}
        </Space>
      ),
    },
  ];

  return (
    <PageContainer>
      <ProTable<Store>
        headerTitle="门店列表"
        actionRef={actionRef}
        rowKey="id"
        columns={columns}
        request={async (params) => {
          const { current, pageSize, name, ...rest } = params;
          return toProTableResult(await storeApi.getList({ ...rest, keyword: name, page: current, pageSize }));
        }}
        toolBarRender={() => [
          access.hasPermission('store:create') && (
            <Button
              key="add"
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => history.push('/store/create')}
            >
              新增门店
            </Button>
          ),
        ]}
        pagination={{ defaultPageSize: 10 }}
      />
    </PageContainer>
  );
};

export default StorePage;
