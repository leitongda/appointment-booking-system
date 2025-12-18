import { PageContainer, ProForm, ProFormText, ProFormSelect, ProFormSwitch } from '@ant-design/pro-components';
import { Card, App, Row, Col } from 'antd';
import { useEffect, useState } from 'react';
import { history, useParams } from '@umijs/max';
import { adminApi } from '@hospital/api';
import type { Admin, Role } from '@hospital/api';

const AdminFormPage: React.FC = () => {
  const { message } = App.useApp();
  const { id } = useParams<{ id: string }>();
  const isEdit = !!id;
  const [loading, setLoading] = useState(false);
  const [admin, setAdmin] = useState<Admin | null>(null);
  const [roles, setRoles] = useState<Role[]>([]);

  useEffect(() => {
    loadRoles();
    if (isEdit) {
      loadAdmin();
    }
  }, [id]);

  const loadRoles = async () => {
    try {
      const data = await adminApi.getAllRoles();
      setRoles(data);
    } catch (error) {
      console.error('加载角色失败', error);
    }
  };

  const loadAdmin = async () => {
    if (!id) return;
    setLoading(true);
    try {
      const data = await adminApi.getAdminDetail(id);
      setAdmin(data);
    } catch (error: any) {
      message.error('加载管理员信息失败');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (values: any) => {
    try {
      const data = { ...values, status: values.status ? 1 : 0 };
      if (isEdit && id) {
        await adminApi.updateAdmin(id, data);
        message.success('更新成功');
      } else {
        await adminApi.createAdmin(data);
        message.success('创建成功');
      }
      history.push('/system/admin');
    } catch (error: any) {
      message.error(error.message || '操作失败');
    }
  };

  const initialValues = admin ? {
    ...admin,
    status: admin.status === 1,
  } : {
    status: true,
  };

  return (
    <PageContainer title={isEdit ? '编辑管理员' : '新增管理员'}>
      <ProForm
        onFinish={handleSubmit}
        initialValues={initialValues}
        submitter={{
          searchConfig: { submitText: isEdit ? '保存' : '创建' },
          resetButtonProps: { style: { display: 'none' } },
          render: (_, dom) => (
            <Row>
              <Col span={24} style={{ textAlign: 'center' }}>
                {dom}
              </Col>
            </Row>
          ),
        }}
      >
        <Card title="账号信息" style={{ marginBottom: 16 }} loading={loading}>
          <ProForm.Group>
            <ProFormText
              name="username"
              label="用户名"
              width="md"
              rules={[{ required: true, message: '请输入用户名' }]}
              disabled={isEdit}
            />
            {!isEdit && (
              <ProFormText.Password
                name="password"
                label="密码"
                width="md"
                rules={[{ required: true, message: '请输入密码' }]}
              />
            )}
          </ProForm.Group>
        </Card>

        <Card title="基本信息" style={{ marginBottom: 16 }} loading={loading}>
          <ProForm.Group>
            <ProFormText name="name" label="姓名" width="md" />
            <ProFormText name="phone" label="手机号" width="md" />
          </ProForm.Group>
          <ProFormText name="email" label="邮箱" width="md" />
        </Card>

        <Card title="权限设置" loading={loading}>
          <ProForm.Group>
            <ProFormSelect
              name="roleId"
              label="角色"
              width="md"
              options={roles.map((r) => ({ label: r.name, value: r.id }))}
              placeholder="请选择角色"
            />
            <ProFormSwitch name="status" label="启用状态" />
          </ProForm.Group>
        </Card>
      </ProForm>
    </PageContainer>
  );
};

export default AdminFormPage;

