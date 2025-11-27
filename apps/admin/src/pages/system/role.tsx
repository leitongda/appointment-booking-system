import { PageContainer, ProTable } from '@ant-design/pro-components';
import type { ProColumns } from '@ant-design/pro-components';
import { Button, Tag, Space } from 'antd';
import { PlusOutlined } from '@ant-design/icons';

interface RoleRecord {
  id: string;
  name: string;
  code: string;
  description: string;
  status: number;
  createdAt: string;
}

const RolePage: React.FC = () => {
  const columns: ProColumns<RoleRecord>[] = [
    { title: '角色名称', dataIndex: 'name', width: 150 },
    { title: '角色编码', dataIndex: 'code', width: 150 },
    { title: '描述', dataIndex: 'description', width: 250, search: false, ellipsis: true },
    { title: '状态', dataIndex: 'status', width: 80, valueEnum: { 0: { text: '禁用' }, 1: { text: '启用', status: 'Success' } } },
    { title: '创建时间', dataIndex: 'createdAt', width: 180, valueType: 'dateTime', search: false },
    { title: '操作', valueType: 'option', width: 180, render: () => <Space><a>权限配置</a><a>编辑</a><a>删除</a></Space> },
  ];

  return (
    <PageContainer>
      <ProTable<RoleRecord>
        rowKey="id"
        columns={columns}
        toolBarRender={() => [<Button key="add" type="primary" icon={<PlusOutlined />}>新增角色</Button>]}
        request={async () => ({ data: [], success: true, total: 0 })}
      />
    </PageContainer>
  );
};

export default RolePage;

