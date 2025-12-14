import { PlusOutlined } from '@ant-design/icons';
import type { ActionType, ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable } from '@ant-design/pro-components';
import { Button, App, Popconfirm, Space, Tag, Avatar } from 'antd';
import { useRef, useState, useEffect } from 'react';
import { history } from '@umijs/max';
import { doctorApi, departmentApi, storeApi } from '@hospital/api';
import { toProTableResult } from '@/utils/proTable';
import type { Doctor, Department, Store } from '@hospital/shared';

const DoctorListPage: React.FC = () => {
  const { message } = App.useApp();
  const actionRef = useRef<ActionType>();
  const [departments, setDepartments] = useState<Department[]>([]);
  const [stores, setStores] = useState<Store[]>([]);

  useEffect(() => {
    loadDepartments();
    loadStores();
  }, []);

  const loadDepartments = async () => {
    try {
      const res = await departmentApi.getList({ pageSize: 100 });
      setDepartments(res.data ?? []);
    } catch (error) {
      console.error('加载科室失败', error);
    }
  };

  const loadStores = async () => {
    try {
      const res = await storeApi.getList({ pageSize: 100 });
      setStores(res.data ?? []);
    } catch (error) {
      console.error('加载门店失败', error);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await doctorApi.delete(id);
      message.success('删除成功');
      actionRef.current?.reload();
    } catch (error: any) {
      message.error(error.message || '删除失败');
    }
  };

  const columns: ProColumns<Doctor>[] = [
    {
      title: '头像',
      dataIndex: 'avatar',
      width: 60,
      search: false,
      render: (_, record) => (
        <Avatar src={record.avatar} size={40}>
          {record.name?.charAt(0)}
        </Avatar>
      ),
    },
    {
      title: '医生姓名',
      dataIndex: 'name',
      width: 100,
    },
    {
      title: '性别',
      dataIndex: 'gender',
      width: 60,
      search: false,
      render: (_, record) => record.gender === 1 ? '男' : '女',
    },
    {
      title: '所属门店',
      dataIndex: 'storeId',
      width: 120,
      valueType: 'select',
      fieldProps: {
        options: (stores ?? []).map((s) => ({ label: s.name, value: s.id })),
      },
      render: (_, record) => record.storeName || '-',
    },
    {
      title: '所属科室',
      dataIndex: 'departmentId',
      width: 120,
      valueType: 'select',
      fieldProps: {
        options: (departments ?? []).map((d) => ({ label: d.name, value: d.id })),
      },
      render: (_, record) => record.departmentName || '-',
    },
    {
      title: '职称',
      dataIndex: 'title',
      width: 120,
      search: false,
    },
    {
      title: '标签',
      dataIndex: 'tags',
      width: 150,
      search: false,
      ellipsis: true,
      render: (_, record) => {
        if (!record.tags) return '-';
        const tagList = record.tags.split(',').filter(Boolean);
        return (
          <Space size={[0, 4]} wrap>
            {tagList.slice(0, 3).map((tag) => (
              <Tag key={tag} color="blue">{tag}</Tag>
            ))}
            {tagList.length > 3 && <span>+{tagList.length - 3}</span>}
          </Space>
        );
      },
    },
    {
      title: '挂号费',
      dataIndex: 'registrationFee',
      width: 80,
      search: false,
      render: (val) => `¥${val || 0}`,
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
      title: '状态',
      dataIndex: 'status',
      width: 80,
      valueType: 'select',
      valueEnum: {
        1: { text: '在职', status: 'Success' },
        0: { text: '离职', status: 'Default' },
      },
    },
    {
      title: '操作',
      valueType: 'option',
      width: 150,
      fixed: 'right',
      render: (_, record) => (
        <Space>
          <a onClick={() => history.push(`/doctor/${record.id}`)}>详情</a>
          <a onClick={() => history.push(`/doctor/${record.id}/edit`)}>编辑</a>
          <Popconfirm
            title="确定删除该医生吗？"
            onConfirm={() => handleDelete(record.id)}
          >
            <a style={{ color: '#ff4d4f' }}>删除</a>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <PageContainer>
      <ProTable<Doctor>
        headerTitle="医生列表"
        actionRef={actionRef}
        rowKey="id"
        columns={columns}
        scroll={{ x: 1200 }}
        request={async (params) => {
          const { current, pageSize, ...rest } = params;
          return toProTableResult(await doctorApi.getList({
            ...rest,
            page: current,
            pageSize,
          }));
        }}
        toolBarRender={() => [
          <Button
            key="add"
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => history.push('/doctor/create')}
          >
            新增医生
          </Button>,
        ]}
        pagination={{ defaultPageSize: 10 }}
      />
    </PageContainer>
  );
};

export default DoctorListPage;
