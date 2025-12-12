import { PlusOutlined } from '@ant-design/icons';
import type { ActionType, ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable, ModalForm, ProFormText, ProFormSelect, ProFormSwitch } from '@ant-design/pro-components';
import { Button, App, Popconfirm, Space, Tag, Avatar } from 'antd';
import { useRef, useState, useEffect } from 'react';
import { adminApi } from '@hospital/api';
import type { Admin, Role } from '@hospital/api';

const AdminPage: React.FC = () => {
  const { message } = App.useApp();
  const actionRef = useRef<ActionType>();
  const [modalOpen, setModalOpen] = useState(false);
  const [editingRecord, setEditingRecord] = useState<Admin | null>(null);
  const [roles, setRoles] = useState<Role[]>([]);

  useEffect(() => {
    loadRoles();
  }, []);

  const loadRoles = async () => {
    try {
      const data = await adminApi.getAllRoles();
      setRoles(data);
    } catch (error) {
      console.error('加载角色失败', error);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await adminApi.deleteAdmin(id);
      message.success('删除成功');
      actionRef.current?.reload();
    } catch (error: any) {
      message.error(error.message || '删除失败');
    }
  };

  const handleSubmit = async (values: any) => {
    try {
      const data = { ...values, status: values.status ? 1 : 0 };
      if (editingRecord) {
        await adminApi.updateAdmin(editingRecord.id, data);
        message.success('更新成功');
      } else {
        await adminApi.createAdmin(data);
        message.success('创建成功');
      }
      setModalOpen(false);
      setEditingRecord(null);
      actionRef.current?.reload();
      return true;
    } catch (error: any) {
      message.error(error.message || '操作失败');
      return false;
    }
  };

  const columns: ProColumns<Admin>[] = [
    {
      title: '头像',
      dataIndex: 'avatar',
      width: 60,
      search: false,
      render: (_, record) => <Avatar src={record.avatar} size={36}>{record.name?.charAt(0)}</Avatar>,
    },
    { title: '用户名', dataIndex: 'username', width: 120 },
    { title: '姓名', dataIndex: 'name', width: 100 },
    { title: '手机号', dataIndex: 'phone', width: 120, search: false },
    { title: '角色', dataIndex: 'roleName', width: 100, search: false },
    {
      title: '状态',
      dataIndex: 'status',
      width: 80,
      valueEnum: { 1: { text: '启用', status: 'Success' }, 0: { text: '禁用', status: 'Default' } },
    },
    { title: '最后登录', dataIndex: 'lastLoginAt', valueType: 'dateTime', width: 160, search: false },
    {
      title: '操作',
      valueType: 'option',
      width: 120,
      render: (_, record) => (
        <Space>
          <a onClick={() => { setEditingRecord(record); setModalOpen(true); }}>编辑</a>
          <Popconfirm title="确定删除该管理员吗？" onConfirm={() => handleDelete(record.id)}>
            <a style={{ color: '#ff4d4f' }}>删除</a>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <PageContainer>
      <ProTable<Admin>
        headerTitle="管理员列表"
        actionRef={actionRef}
        rowKey="id"
        columns={columns}
        request={async (params) => {
          const { current, pageSize, ...rest } = params;
          const result = await adminApi.getAdmins({ ...rest, page: current, pageSize });
          return { data: result.data, total: result.total, success: true };
        }}
        toolBarRender={() => [
          <Button key="add" type="primary" icon={<PlusOutlined />} onClick={() => { setEditingRecord(null); setModalOpen(true); }}>
            新增管理员
          </Button>,
        ]}
        pagination={{ defaultPageSize: 10 }}
      />

      <ModalForm
        title={editingRecord ? '编辑管理员' : '新增管理员'}
        open={modalOpen}
        onOpenChange={setModalOpen}
        onFinish={handleSubmit}
        initialValues={editingRecord ? { ...editingRecord, status: editingRecord.status === 1 } : { status: true }}
        modalProps={{ destroyOnClose: true }}
      >
        <ProFormText name="username" label="用户名" rules={[{ required: true }]} disabled={!!editingRecord} />
        {!editingRecord && <ProFormText.Password name="password" label="密码" rules={[{ required: true }]} />}
        <ProFormText name="name" label="姓名" />
        <ProFormText name="phone" label="手机号" />
        <ProFormText name="email" label="邮箱" />
        <ProFormSelect name="roleId" label="角色" options={roles.map((r) => ({ label: r.name, value: r.id }))} />
        <ProFormSwitch name="status" label="启用状态" />
      </ModalForm>
    </PageContainer>
  );
};

export default AdminPage;
