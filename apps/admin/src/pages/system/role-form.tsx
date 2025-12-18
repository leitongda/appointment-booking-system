import { PageContainer, ProForm, ProFormText, ProFormTextArea, ProFormSwitch } from '@ant-design/pro-components';
import { Card, App, Row, Col } from 'antd';
import { useEffect, useState } from 'react';
import { history, useParams } from '@umijs/max';
import { adminApi } from '@hospital/api';
import type { Role } from '@hospital/api';

const RoleFormPage: React.FC = () => {
  const { message } = App.useApp();
  const { id } = useParams<{ id: string }>();
  const isEdit = !!id;
  const [loading, setLoading] = useState(false);
  const [role, setRole] = useState<Role | null>(null);

  useEffect(() => {
    if (isEdit) {
      loadRole();
    }
  }, [id]);

  const loadRole = async () => {
    if (!id) return;
    setLoading(true);
    try {
      const data = await adminApi.getRoleDetail(id);
      setRole(data);
    } catch (error: any) {
      message.error('加载角色信息失败');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (values: any) => {
    try {
      const data = { ...values, status: values.status ? 1 : 0 };
      if (isEdit && id) {
        await adminApi.updateRole(id, data);
        message.success('更新成功');
      } else {
        await adminApi.createRole(data);
        message.success('创建成功');
      }
      history.push('/system/role');
    } catch (error: any) {
      message.error(error.message || '操作失败');
    }
  };

  const initialValues = role ? {
    ...role,
    status: role.status === 1,
  } : {
    status: true,
  };

  return (
    <PageContainer title={isEdit ? '编辑角色' : '新增角色'}>
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
        <Card title="角色信息" loading={loading}>
          <ProForm.Group>
            <ProFormText
              name="name"
              label="角色名称"
              width="md"
              rules={[{ required: true, message: '请输入角色名称' }]}
            />
            <ProFormText
              name="code"
              label="角色编码"
              width="md"
              rules={[{ required: true, message: '请输入角色编码' }]}
              disabled={isEdit}
            />
          </ProForm.Group>
          <ProFormTextArea
            name="description"
            label="描述"
            placeholder="请输入角色描述"
          />
          <ProFormSwitch name="status" label="启用状态" />
        </Card>
      </ProForm>
    </PageContainer>
  );
};

export default RoleFormPage;

