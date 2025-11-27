import { PlusOutlined } from '@ant-design/icons';
import { PageContainer, ProTable } from '@ant-design/pro-components';
import type { ProColumns, ActionType } from '@ant-design/pro-components';
import { Avatar, Button, Space, Tag } from 'antd';
import { useRef } from 'react';
import { history } from 'umi';
import type { Doctor } from '@hospital/shared';
import { DOCTOR_TITLES } from '@hospital/shared';

const DoctorListPage: React.FC = () => {
  const actionRef = useRef<ActionType>();

  const columns: ProColumns<Doctor>[] = [
    {
      title: '医生',
      dataIndex: 'name',
      width: 200,
      render: (_, record) => (
        <Space>
          <Avatar src={record.avatar} />
          <span>{record.name}</span>
        </Space>
      ),
    },
    {
      title: '工号',
      dataIndex: 'employeeNo',
      width: 100,
      search: false,
    },
    {
      title: '职称',
      dataIndex: 'title',
      width: 120,
      valueType: 'select',
      valueEnum: DOCTOR_TITLES.reduce((acc, title) => ({ ...acc, [title]: title }), {}),
    },
    {
      title: '所属科室',
      dataIndex: ['department', 'name'],
      width: 150,
    },
    {
      title: '擅长',
      dataIndex: 'specialty',
      width: 200,
      search: false,
      ellipsis: true,
    },
    {
      title: '挂号费',
      dataIndex: 'consultationFee',
      width: 100,
      search: false,
      render: (_, record) => `¥${record.consultationFee}`,
    },
    {
      title: '专家',
      dataIndex: 'isExpert',
      width: 80,
      search: false,
      render: (_, record) => (
        record.isExpert ? <Tag color="gold">是</Tag> : <Tag>否</Tag>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 100,
      valueEnum: {
        0: { text: '禁用', status: 'Default' },
        1: { text: '启用', status: 'Success' },
      },
    },
    {
      title: '操作',
      valueType: 'option',
      width: 180,
      render: (_, record) => (
        <Space>
          <a onClick={() => history.push(`/doctor/${record.id}`)}>详情</a>
          <a onClick={() => history.push(`/doctor/${record.id}/edit`)}>编辑</a>
          <a>删除</a>
        </Space>
      ),
    },
  ];

  return (
    <PageContainer>
      <ProTable<Doctor>
        actionRef={actionRef}
        rowKey="id"
        columns={columns}
        search={{ labelWidth: 'auto' }}
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
        request={async (params) => {
          // TODO: 调用 API 获取数据
          return {
            data: [],
            success: true,
            total: 0,
          };
        }}
      />
    </PageContainer>
  );
};

export default DoctorListPage;

