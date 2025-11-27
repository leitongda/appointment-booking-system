import { PageContainer, ProTable } from '@ant-design/pro-components';
import type { ProColumns } from '@ant-design/pro-components';
import { Button, Tag, Space, Avatar } from 'antd';
import { PlusOutlined } from '@ant-design/icons';

interface AdminRecord {
  id: string;
  name: string;
  phone: string;
  avatar: string;
  roleName: string;
  status: number;
  lastLoginTime: string;
  createdAt: string;
}

const AdminPage: React.FC = () => {
  const columns: ProColumns<AdminRecord>[] = [
    { title: '管理员', dataIndex: 'name', width: 150, render: (_, r) => <Space><Avatar src={r.avatar} />{r.name}</Space> },
    { title: '手机号', dataIndex: 'phone', width: 130 },
    { title: '角色', dataIndex: 'roleName', width: 120 },
    { title: '状态', dataIndex: 'status', width: 80, valueEnum: { 0: { text: '禁用' }, 1: { text: '启用', status: 'Success' } } },
    { title: '最后登录', dataIndex: 'lastLoginTime', width: 180, valueType: 'dateTime', search: false },
    { title: '创建时间', dataIndex: 'createdAt', width: 180, valueType: 'dateTime', search: false },
    { title: '操作', valueType: 'option', width: 180, render: () => <Space><a>编辑</a><a>重置密码</a><a>删除</a></Space> },
  ];

  return (
    <PageContainer>
      <ProTable<AdminRecord>
        rowKey="id"
        columns={columns}
        toolBarRender={() => [<Button key="add" type="primary" icon={<PlusOutlined />}>新增管理员</Button>]}
        request={async () => ({ data: [], success: true, total: 0 })}
      />
    </PageContainer>
  );
};

export default AdminPage;

