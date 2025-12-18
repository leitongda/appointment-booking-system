import { PlusOutlined } from '@ant-design/icons';
import type { ActionType, ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable } from '@ant-design/pro-components';
import { Button, App, Popconfirm, Space, Tag } from 'antd';
import { useRef, useState, useEffect } from 'react';
import { history, useAccess } from '@umijs/max';
import { departmentApi, storeApi } from '@hospital/api';
import { toProTableResult } from '@/utils/proTable';
import type { Department, Store } from '@hospital/shared';

const DepartmentPage: React.FC = () => {
  const { message } = App.useApp();
  const access = useAccess();
  const actionRef = useRef<ActionType>();
  const [stores, setStores] = useState<Store[]>([]);

  useEffect(() => {
    loadStores();
  }, []);

  const loadStores = async () => {
    try {
      const res = await storeApi.getList({ pageSize: 100, status: 1 });
      setStores(res.data ?? []);
    } catch (error) {
      console.error('加载门店失败', error);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await departmentApi.delete(id);
      message.success('删除成功');
      actionRef.current?.reload();
    } catch (error: any) {
      message.error(error.message || '删除失败');
    }
  };

  const columns: ProColumns<Department>[] = [
    {
      title: '科室名称',
      dataIndex: 'name',
      ellipsis: true,
      width: 150,
    },
    {
      title: '所属门店',
      dataIndex: 'storeName',
      ellipsis: true,
      width: 120,
      search: false,
      render: (_, record) => record.storeName || '-',
    },
    {
      title: '门店筛选',
      dataIndex: 'storeId',
      hideInTable: true,
      valueType: 'select',
      fieldProps: {
        options: stores.map((s) => ({ label: s.name, value: s.id })),
        allowClear: true,
        placeholder: '请选择门店',
      },
    },
    {
      title: '科室标签',
      dataIndex: 'tag',
      ellipsis: true,
      width: 100,
      search: false,
      render: (_, record) => record.tag ? <Tag color="blue">{record.tag}</Tag> : '-',
    },
    {
      title: '排序',
      dataIndex: 'sortOrder',
      width: 70,
      search: false,
    },
    {
      title: '终极科室',
      dataIndex: 'isFinal',
      width: 90,
      search: false,
      render: (_, record) => (
        record.isFinal === 1 ? <Tag color="green">是</Tag> : <Tag>否</Tag>
      ),
    },
    {
      title: '推荐',
      dataIndex: 'isRecommended',
      width: 70,
      search: false,
      render: (_, record) => (
        record.isRecommended === 1 ? <Tag color="orange">推荐</Tag> : '-'
      ),
    },
    {
      title: '热门',
      dataIndex: 'isHot',
      width: 70,
      search: false,
      render: (_, record) => (
        record.isHot === 1 ? <Tag color="red">热门</Tag> : '-'
      ),
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
    {
      title: '操作',
      valueType: 'option',
      width: 120,
      fixed: 'right',
      render: (_, record) => (
        <Space>
          {access.hasPermission('department:update') && (
            <a onClick={() => history.push(`/department/${record.id}/edit`)}>编辑</a>
          )}
          {access.hasPermission('department:delete') && (
            <Popconfirm
              title="确定删除该科室吗？"
              onConfirm={() => handleDelete(record.id)}
            >
              <a style={{ color: '#ff4d4f' }}>删除</a>
            </Popconfirm>
          )}
        </Space>
      ),
    },
  ];

  return (
    <PageContainer>
      <ProTable<Department>
        headerTitle="科室列表"
        actionRef={actionRef}
        rowKey="id"
        columns={columns}
        scroll={{ x: 1200 }}
        request={async (params) => {
          const { current, pageSize, ...rest } = params;
          return toProTableResult(await departmentApi.getList({
            ...rest,
            page: current,
            pageSize,
          }));
        }}
        toolBarRender={() => [
          access.hasPermission('department:create') && (
            <Button
              key="add"
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => history.push('/department/create')}
            >
              新增科室
            </Button>
          ),
        ]}
        pagination={{ defaultPageSize: 10 }}
      />
    </PageContainer>
  );
};

export default DepartmentPage;
