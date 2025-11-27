import { PageContainer, ProTable, ModalForm, ProFormText, ProFormSelect, ProFormSwitch } from '@ant-design/pro-components';
import type { ProColumns, ActionType } from '@ant-design/pro-components';
import { Button, Tag, Space, message, Popconfirm, Avatar, Modal, Form, Input } from 'antd';
import { PlusOutlined, UserOutlined, KeyOutlined } from '@ant-design/icons';
import { useRef, useState } from 'react';

interface AdminRecord {
  id: string;
  name: string;
  phone: string;
  avatar: string;
  roleId: string;
  roleName: string;
  status: number;
  lastLoginTime: string;
  createdAt: string;
}

const AdminPage: React.FC = () => {
  const actionRef = useRef<ActionType>();
  const [modalVisible, setModalVisible] = useState(false);
  const [passwordVisible, setPasswordVisible] = useState(false);
  const [editingAdmin, setEditingAdmin] = useState<AdminRecord | null>(null);
  const [passwordForm] = Form.useForm();

  const handleAdd = () => {
    setEditingAdmin(null);
    setModalVisible(true);
  };

  const handleEdit = (record: AdminRecord) => {
    setEditingAdmin(record);
    setModalVisible(true);
  };

  const handleResetPassword = (record: AdminRecord) => {
    setEditingAdmin(record);
    passwordForm.resetFields();
    setPasswordVisible(true);
  };

  const handleDelete = async (id: string) => {
    message.success('删除成功');
    actionRef.current?.reload();
  };

  const handleSubmit = async (values: any) => {
    try {
      if (editingAdmin) {
        message.success('更新成功');
      } else {
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
    try {
      const values = await passwordForm.validateFields();
      console.log('重置密码:', editingAdmin?.id, values);
      message.success('密码重置成功');
      setPasswordVisible(false);
    } catch (error) {
      // 校验失败
    }
  };

  const columns: ProColumns<AdminRecord>[] = [
    { 
      title: '管理员', 
      dataIndex: 'name', 
      width: 150, 
      render: (_, r) => (
        <Space>
          <Avatar src={r.avatar} icon={<UserOutlined />} />
          {r.name}
        </Space>
      )
    },
    { title: '手机号', dataIndex: 'phone', width: 130 },
    { 
      title: '角色', 
      dataIndex: 'roleName', 
      width: 120,
      render: (_, r) => <Tag color="blue">{r.roleName}</Tag>
    },
    { 
      title: '状态', 
      dataIndex: 'status', 
      width: 100, 
      valueEnum: { 0: { text: '禁用' }, 1: { text: '启用', status: 'Success' } } 
    },
    { title: '最后登录', dataIndex: 'lastLoginTime', width: 180, valueType: 'dateTime', search: false },
    { title: '创建时间', dataIndex: 'createdAt', width: 180, valueType: 'dateTime', search: false },
    { 
      title: '操作', 
      valueType: 'option', 
      width: 200, 
      render: (_, record) => (
        <Space>
          <a onClick={() => handleEdit(record)}>编辑</a>
          <a onClick={() => handleResetPassword(record)}><KeyOutlined /> 重置密码</a>
          {record.id !== '1' && (
            <Popconfirm title="确定删除吗？" onConfirm={() => handleDelete(record.id)}>
              <a style={{ color: 'red' }}>删除</a>
            </Popconfirm>
          )}
        </Space>
      )
    },
  ];

  const mockData: AdminRecord[] = [
    { id: '1', name: '系统管理员', phone: '13800138000', avatar: '', roleId: '1', roleName: '超级管理员', status: 1, lastLoginTime: '2024-11-27 09:30:00', createdAt: '2024-01-01 00:00:00' },
    { id: '2', name: '张三', phone: '13800138001', avatar: '', roleId: '2', roleName: '科室管理员', status: 1, lastLoginTime: '2024-11-26 15:20:00', createdAt: '2024-11-01 10:00:00' },
  ];

  const roleOptions = [
    { label: '超级管理员', value: '1' },
    { label: '科室管理员', value: '2' },
    { label: '内容管理员', value: '3' },
  ];

  return (
    <PageContainer>
      <ProTable<AdminRecord>
        actionRef={actionRef}
        rowKey="id"
        columns={columns}
        toolBarRender={() => [
          <Button key="add" type="primary" icon={<PlusOutlined />} onClick={handleAdd}>
            新增管理员
          </Button>
        ]}
        request={async () => ({ data: mockData, success: true, total: mockData.length })}
      />

      <ModalForm
        title={editingAdmin ? '编辑管理员' : '新增管理员'}
        open={modalVisible}
        onOpenChange={setModalVisible}
        onFinish={handleSubmit}
        initialValues={editingAdmin || { status: true }}
        modalProps={{ destroyOnClose: true }}
      >
        <ProFormText name="name" label="姓名" rules={[{ required: true }]} />
        <ProFormText 
          name="phone" 
          label="手机号" 
          rules={[
            { required: true },
            { pattern: /^1\d{10}$/, message: '请输入正确的手机号' }
          ]} 
        />
        <ProFormSelect name="roleId" label="角色" options={roleOptions} rules={[{ required: true }]} />
        {!editingAdmin && (
          <ProFormText.Password name="password" label="密码" rules={[{ required: true, min: 6 }]} />
        )}
        <ProFormSwitch name="status" label="状态" checkedChildren="启用" unCheckedChildren="禁用" initialValue={true} />
      </ModalForm>

      <Modal
        title={`重置密码 - ${editingAdmin?.name}`}
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
