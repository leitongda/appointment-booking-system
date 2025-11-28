import { PageContainer, ProTable, ModalForm, ProFormText, ProFormSelect, ProFormSwitch } from '@ant-design/pro-components';
import type { ProColumns, ActionType } from '@ant-design/pro-components';
import { Button, Tag, Space, message, Popconfirm, Avatar, Modal, Form, Input, Switch } from 'antd';
import { PlusOutlined, UserOutlined, KeyOutlined } from '@ant-design/icons';
import { useRef, useState, useEffect } from 'react';
import { adminApi } from '@hospital/api';
import type { Admin, Role } from '@hospital/api';

const AdminPage: React.FC = () => {
  const actionRef = useRef<ActionType>();
  const [modalVisible, setModalVisible] = useState(false);
  const [passwordVisible, setPasswordVisible] = useState(false);
  const [editingAdmin, setEditingAdmin] = useState<Admin | null>(null);
  const [passwordForm] = Form.useForm();
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

  const handleAdd = () => {
    setEditingAdmin(null);
    setModalVisible(true);
  };

  const handleEdit = (record: Admin) => {
    setEditingAdmin(record);
    setModalVisible(true);
  };

  const handleResetPassword = (record: Admin) => {
    setEditingAdmin(record);
    passwordForm.resetFields();
    setPasswordVisible(true);
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
      const submitData = {
        username: values.username,
        name: values.name,
        phone: values.phone,
        email: values.email,
        roleId: values.roleId,
        status: values.status ? 1 : 0,
        password: values.password,
      };

      if (editingAdmin) {
        await adminApi.updateAdmin(editingAdmin.id, submitData);
        message.success('更新成功');
      } else {
        await adminApi.createAdmin(submitData);
        message.success('创建成功');
      }
      setModalVisible(false);
      actionRef.current?.reload();
      return true;
    } catch (error: any) {
      message.error(error.message || '操作失败');
      return false;
    }
  };

  const handlePasswordSubmit = async () => {
    if (!editingAdmin) return;
    
    try {
      const values = await passwordForm.validateFields();
      await adminApi.resetAdminPassword(editingAdmin.id, values.newPassword);
      message.success('密码重置成功');
      setPasswordVisible(false);
    } catch (error: any) {
      if (error.message) {
        message.error(error.message);
      }
    }
  };

  const handleStatusChange = async (id: string, status: number) => {
    try {
      await adminApi.updateAdmin(id, { status });
      message.success(status === 1 ? '已启用' : '已禁用');
      actionRef.current?.reload();
    } catch (error: any) {
      message.error(error.message || '操作失败');
    }
  };

  const columns: ProColumns<Admin>[] = [
    { 
      title: '管理员', 
      dataIndex: 'name', 
      width: 180, 
      render: (_, r) => (
        <Space>
          <Avatar src={r.avatar} icon={<UserOutlined />} />
          <div>
            <div>{r.name || r.username}</div>
            <div style={{ fontSize: 12, color: '#999' }}>{r.username}</div>
          </div>
        </Space>
      )
    },
    { title: '手机号', dataIndex: 'phone', width: 130 },
    { title: '邮箱', dataIndex: 'email', width: 180, search: false, ellipsis: true },
    { 
      title: '角色', 
      dataIndex: 'roleName', 
      width: 120,
      render: (_, r) => r.roleName ? <Tag color="blue">{r.roleName}</Tag> : '-'
    },
    { 
      title: '状态', 
      dataIndex: 'status', 
      width: 100, 
      valueEnum: { 0: { text: '禁用' }, 1: { text: '启用', status: 'Success' } },
      render: (_, r) => (
        <Switch 
          checked={r.status === 1} 
          onChange={(checked) => handleStatusChange(r.id, checked ? 1 : 0)}
          checkedChildren="启用" 
          unCheckedChildren="禁用"
        />
      )
    },
    { title: '最后登录', dataIndex: 'lastLoginAt', width: 180, valueType: 'dateTime', search: false },
    { title: '创建时间', dataIndex: 'createdAt', width: 180, valueType: 'dateTime', search: false },
    { 
      title: '操作', 
      valueType: 'option', 
      width: 200, 
      render: (_, record) => (
        <Space>
          <a onClick={() => handleEdit(record)}>编辑</a>
          <a onClick={() => handleResetPassword(record)}><KeyOutlined /> 重置密码</a>
          <Popconfirm title="确定删除吗？" onConfirm={() => handleDelete(record.id)}>
            <a style={{ color: 'red' }}>删除</a>
          </Popconfirm>
        </Space>
      )
    },
  ];

  return (
    <PageContainer>
      <ProTable<Admin>
        actionRef={actionRef}
        rowKey="id"
        columns={columns}
        toolBarRender={() => [
          <Button key="add" type="primary" icon={<PlusOutlined />} onClick={handleAdd}>
            新增管理员
          </Button>
        ]}
        request={async (params) => {
          try {
            const { current, pageSize, status, name } = params;
            const result = await adminApi.getAdmins({
              status,
              keyword: name,
              page: current || 1,
              pageSize: pageSize || 10,
            });
            return { 
              data: result.data || [], 
              success: true, 
              total: result.total || 0 
            };
          } catch (error: any) {
            message.error(error.message || '获取数据失败');
            return { data: [], success: false, total: 0 };
          }
        }}
      />

      <ModalForm
        title={editingAdmin ? '编辑管理员' : '新增管理员'}
        open={modalVisible}
        onOpenChange={setModalVisible}
        onFinish={handleSubmit}
        initialValues={editingAdmin ? {
          ...editingAdmin,
          status: editingAdmin.status === 1,
        } : { status: true }}
        modalProps={{ destroyOnClose: true }}
      >
        <ProFormText 
          name="username" 
          label="用户名" 
          rules={[{ required: true }, { min: 3, message: '用户名至少3位' }]} 
          disabled={!!editingAdmin}
          tooltip={editingAdmin ? '用户名不可修改' : undefined}
        />
        <ProFormText name="name" label="姓名" />
        <ProFormText 
          name="phone" 
          label="手机号" 
          rules={[{ pattern: /^1\d{10}$/, message: '请输入正确的手机号' }]} 
        />
        <ProFormText name="email" label="邮箱" rules={[{ type: 'email', message: '请输入正确的邮箱' }]} />
        <ProFormSelect 
          name="roleId" 
          label="角色" 
          options={roles.map(r => ({ label: r.name, value: r.id }))} 
          rules={[{ required: true }]} 
        />
        {!editingAdmin && (
          <ProFormText.Password name="password" label="密码" rules={[{ required: true, min: 6 }]} />
        )}
        <ProFormSwitch name="status" label="状态" checkedChildren="启用" unCheckedChildren="禁用" initialValue={true} />
      </ModalForm>

      <Modal
        title={`重置密码 - ${editingAdmin?.name || editingAdmin?.username}`}
        open={passwordVisible}
        onCancel={() => setPasswordVisible(false)}
        onOk={handlePasswordSubmit}
      >
        <Form form={passwordForm} layout="vertical">
          <Form.Item 
            name="newPassword" 
            label="新密码" 
            rules={[
              { required: true, message: '请输入新密码' },
              { min: 6, message: '密码至少6位' }
            ]}
          >
            <Input.Password placeholder="请输入新密码" />
          </Form.Item>
          <Form.Item 
            name="confirmPassword" 
            label="确认密码"
            dependencies={['newPassword']}
            rules={[
              { required: true, message: '请确认密码' },
              ({ getFieldValue }) => ({
                validator(_, value) {
                  if (!value || getFieldValue('newPassword') === value) {
                    return Promise.resolve();
                  }
                  return Promise.reject(new Error('两次输入的密码不一致'));
                },
              }),
            ]}
          >
            <Input.Password placeholder="请再次输入密码" />
          </Form.Item>
        </Form>
      </Modal>
    </PageContainer>
  );
};

export default AdminPage;
