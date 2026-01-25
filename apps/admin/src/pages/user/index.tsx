import type { ActionType, ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable } from '@ant-design/pro-components';
import { App, Space, Tag, Avatar, Popconfirm, Divider } from 'antd';
import { UserOutlined, DeleteOutlined, EyeOutlined, StopOutlined, CheckCircleOutlined } from '@ant-design/icons';
import { useRef } from 'react';
import { history, useAccess } from '@umijs/max';
import { userManageApi } from '@hospital/api';
import type { UserListItem } from '@hospital/api';
import { toProTableResult } from '@/utils/proTable';

const STATUS_MAP: Record<number, { text: string; status: 'success' | 'error' }> = {
  0: { text: '禁用', status: 'error' },
  1: { text: '正常', status: 'success' },
};

const UserManagePage: React.FC = () => {
  const { message } = App.useApp();
  const access = useAccess();
  const actionRef = useRef<ActionType>();

  const handleUpdateStatus = async (id: string, status: number) => {
    try {
      await userManageApi.updateStatus(id, status);
      message.success(status === 0 ? '已禁用' : '已启用');
      actionRef.current?.reload();
    } catch (error: any) {
      message.error(error.message || '操作失败');
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await userManageApi.deleteUser(id);
      message.success('删除成功');
      actionRef.current?.reload();
    } catch (error: any) {
      message.error(error.message || '删除失败');
    }
  };

  const columns: ProColumns<UserListItem>[] = [
    {
      title: '头像',
      dataIndex: 'avatar',
      width: 60,
      search: false,
      render: (_, record) => (
        <Avatar src={record.avatar} icon={<UserOutlined />} />
      ),
    },
    {
      title: '昵称',
      dataIndex: 'nickname',
      width: 120,
      ellipsis: true,
      render: (_, record) => record.nickname || '微信用户',
    },
    {
      title: '手机号',
      dataIndex: 'phone',
      width: 120,
    },
    {
      title: '就诊卡数量',
      dataIndex: 'cardCount',
      width: 100,
      search: false,
      render: (val) => <Tag color="blue">{val || 0} 张</Tag>,
    },
    {
      title: '预约次数',
      dataIndex: 'appointmentCount',
      width: 100,
      search: false,
    },
    {
      title: '积分',
      dataIndex: 'points',
      width: 80,
      search: false,
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 80,
      valueEnum: {
        0: { text: '禁用', status: 'Error' },
        1: { text: '正常', status: 'Success' },
      },
      render: (_, record) => {
        const s = STATUS_MAP[record.status] || { text: '未知', status: 'default' };
        return <Tag color={s.status === 'success' ? 'green' : 'red'}>{s.text}</Tag>;
      },
    },
    {
      title: '注册时间',
      dataIndex: 'createdAt',
      valueType: 'dateTime',
      width: 160,
      search: false,
    },
    {
      title: '操作',
      valueType: 'option',
      width: 220,
      fixed: 'right',
      render: (_, record) => (
        <Space size={4} split={<Divider type="vertical" style={{ margin: 0 }} />}>
          <a onClick={() => history.push(`/user/${record.id}`)} style={{ fontSize: 13 }}>
            <EyeOutlined /> 详情
          </a>
          {access.hasPermission('user:update') && (
            record.status === 1 ? (
              <Popconfirm
                title="确定禁用该用户吗？禁用后用户将无法预约"
                onConfirm={() => handleUpdateStatus(record.id, 0)}
              >
                <a style={{ color: '#ff4d4f', fontSize: 13 }}>
                  <StopOutlined /> 禁用
                </a>
              </Popconfirm>
            ) : (
              <Popconfirm
                title="确定启用该用户吗？"
                onConfirm={() => handleUpdateStatus(record.id, 1)}
              >
                <a style={{ color: '#52c41a', fontSize: 13 }}>
                  <CheckCircleOutlined /> 启用
                </a>
              </Popconfirm>
            )
          )}
          {access.hasPermission('user:delete') && (
            <Popconfirm
              title="确定删除该用户吗？"
              description="删除后用户的所有就诊卡将被一并删除，此操作不可恢复"
              onConfirm={() => handleDelete(record.id)}
            >
              <a style={{ color: '#ff4d4f', fontSize: 13 }}>
                <DeleteOutlined /> 删除
              </a>
            </Popconfirm>
          )}
        </Space>
      ),
    },
  ];

  return (
    <PageContainer>
      <ProTable<UserListItem>
        headerTitle="患者列表"
        actionRef={actionRef}
        rowKey="id"
        columns={columns}
        scroll={{ x: 1000 }}
        request={async (params) => {
          const { current, pageSize, phone, nickname, status, ...rest } = params;
          const keyword = phone || nickname;
          return toProTableResult(
            await userManageApi.getList({
              ...rest,
              keyword,
              status,
              page: current,
              pageSize,
            })
          );
        }}
        pagination={{ defaultPageSize: 10 }}
        search={{ labelWidth: 'auto' }}
      />
    </PageContainer>
  );
};

export default UserManagePage;

