import type { ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable } from '@ant-design/pro-components';
import { Tag, Avatar } from 'antd';
import { UserOutlined, StopOutlined, CheckCircleOutlined } from '@ant-design/icons';
import { userManageApi } from '@hospital/api';
import type { UserListItem } from '@hospital/api';
import { createListRequest } from '@/utils/proTable';
import { useListPage } from '@/hooks/useListPage';
import { OperationButton, OperationGroup } from '@/components/ListOperations';

const STATUS_MAP: Record<number, { text: string; status: 'success' | 'error' }> = {
  0: { text: '禁用', status: 'error' },
  1: { text: '正常', status: 'success' },
};

const UserManagePage: React.FC = () => {
  const { actionRef, handleAction, handleDelete } = useListPage({
    deleteFn: userManageApi.deleteUser,
  });

  const handleUpdateStatus = async (id: string, status: number) => {
    await handleAction(
      () => userManageApi.updateStatus(id, status),
      { successText: status === 0 ? '已禁用' : '已启用', errorText: '操作失败', reloadOnSuccess: true }
    );
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
        <OperationGroup>
          <OperationButton
            type="view"
            url={`/medical-services/user/${record.id}`}
          />
          {record.status === 1 ? (
            <OperationButton
              type="custom"
              permission="user:update"
              icon={<StopOutlined />}
              label="禁用"
              danger
              confirmText="确定禁用该用户吗？禁用后用户将无法预约"
              onClick={() => handleUpdateStatus(record.id, 0)}
            />
          ) : (
            <OperationButton
              type="custom"
              permission="user:update"
              icon={<CheckCircleOutlined />}
              label="启用"
              style={{ color: '#52c41a' }}
              confirmText="确定启用该用户吗？"
              onClick={() => handleUpdateStatus(record.id, 1)}
            />
          )}
          <OperationButton
            type="delete"
            permission="user:delete"
            confirmText="确定删除该用户吗？"
            confirmDescription="删除后用户的所有就诊卡将被一并删除，此操作不可恢复"
            onClick={() => handleDelete(record.id)}
          />
        </OperationGroup>
      ),
    },
  ];

  return (
    <PageContainer>
      <ProTable<UserListItem>
        headerTitle="用户列表"
        actionRef={actionRef}
        rowKey="id"
        columns={columns}
        scroll={{ x: 1000 }}
        request={createListRequest(userManageApi.getList, (params) => {
          const { phone, nickname, ...rest } = params;
          return { ...rest, keyword: phone || nickname };
        })}
        pagination={{ defaultPageSize: 10 }}
        search={{ labelWidth: 'auto' }}
      />
    </PageContainer>
  );
};

export default UserManagePage;
