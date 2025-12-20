import { PageContainer, ProForm, ProFormText, ProFormSelect, ProFormSwitch, ProFormDependency } from '@ant-design/pro-components';
import { Card, App, Row, Col, Alert } from 'antd';
import { useEffect, useState } from 'react';
import { history, useParams, useModel } from '@umijs/max';
import { adminApi, storeApi } from '@hospital/api';
import type { Admin, Role } from '@hospital/api';

interface Store {
  id: string;
  name: string;
}

const UserFormPage: React.FC = () => {
  const { message } = App.useApp();
  const { id } = useParams<{ id: string }>();
  const isEdit = !!id;
  const [loading, setLoading] = useState(false);
  const [admin, setAdmin] = useState<Admin | null>(null);
  const [roles, setRoles] = useState<Role[]>([]);
  const [stores, setStores] = useState<Store[]>([]);
  
  const { initialState } = useModel('@@initialState');
  const currentStore = initialState?.currentStore;
  const isSuperAdmin = !currentStore; // 超级管理员没有关联门店

  useEffect(() => {
    loadRoles();
    if (isSuperAdmin) {
      loadStores();
    }
    if (isEdit) {
      loadAdmin();
    }
  }, [id]);

  const loadRoles = async () => {
    try {
      const data = await adminApi.getAllRoles();
      // 门店管理员不能分配超级管理员角色
      if (!isSuperAdmin) {
        setRoles(data.filter((r: Role) => r.code !== 'SUPER_ADMIN'));
      } else {
        setRoles(data);
      }
    } catch (error) {
      console.error('加载角色失败', error);
    }
  };

  const loadStores = async () => {
    try {
      const data = await storeApi.getAll();
      setStores(data);
    } catch (error) {
      console.error('加载门店失败', error);
    }
  };

  const loadAdmin = async () => {
    if (!id) return;
    setLoading(true);
    try {
      const data = await adminApi.getAdminDetail(id);
      setAdmin(data);
    } catch (error: any) {
      message.error('加载用户信息失败');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (values: any) => {
    try {
      // 排除确认密码字段
      const { confirmPassword, ...restValues } = values;
      const data = { 
        ...restValues, 
        status: values.status ? 1 : 0,
        // 门店管理员创建的用户自动继承其门店
        storeId: isSuperAdmin ? values.storeId : currentStore?.id,
      };
      if (isEdit && id) {
        await adminApi.updateAdmin(id, data);
        message.success('更新成功');
      } else {
        await adminApi.createAdmin(data);
        message.success('创建成功');
      }
      history.push('/system/user');
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

  // 获取选中的角色编码
  const getSelectedRoleCode = (roleId: string) => {
    const role = roles.find(r => r.id === roleId);
    return role?.code;
  };

  return (
    <PageContainer title={isEdit ? '编辑用户' : '新增用户'}>
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
              fieldProps={{ autoComplete: 'off' }}
            />
            {!isEdit && (
              <>
                <ProFormText.Password
                  name="password"
                  label="密码"
                  width="md"
                  placeholder="不填则默认为 123456"
                  extra="不填写则使用默认密码：123456"
                  fieldProps={{ autoComplete: 'new-password' }}
                />
                <ProFormText.Password
                  name="confirmPassword"
                  label="确认密码"
                  width="md"
                  placeholder="请再次输入密码"
                  dependencies={['password']}
                  rules={[
                    ({ getFieldValue }) => ({
                      validator(_, value) {
                        const password = getFieldValue('password');
                        if (!password && !value) {
                          return Promise.resolve();
                        }
                        if (password && !value) {
                          return Promise.reject(new Error('请再次输入密码'));
                        }
                        if (password !== value) {
                          return Promise.reject(new Error('两次输入的密码不一致'));
                        }
                        return Promise.resolve();
                      },
                    }),
                  ]}
                  fieldProps={{ autoComplete: 'new-password' }}
                />
              </>
            )}
          </ProForm.Group>
        </Card>

        <Card title="基本信息" style={{ marginBottom: 16 }} loading={loading}>
          <ProForm.Group>
            <ProFormText name="name" label="姓名" width="md" fieldProps={{ autoComplete: 'off' }} />
            <ProFormText name="phone" label="手机号" width="md" fieldProps={{ autoComplete: 'off' }} />
          </ProForm.Group>
          <ProFormText name="email" label="邮箱" width="md" fieldProps={{ autoComplete: 'off' }} />
        </Card>

        <Card title="权限设置" loading={loading}>
          <ProForm.Group>
            <ProFormSelect
              name="roleId"
              label="角色"
              width="md"
              options={roles.map((r) => ({ label: r.name, value: r.id }))}
              placeholder="请选择角色"
              rules={[{ required: true, message: '请选择角色' }]}
            />
            <ProFormSwitch name="status" label="启用状态" />
          </ProForm.Group>

          {/* 超级管理员可以选择门店 */}
          {isSuperAdmin && (
            <ProFormDependency name={['roleId']}>
              {({ roleId }) => {
                const roleCode = getSelectedRoleCode(roleId);
                const isSuperAdminRole = roleCode === 'SUPER_ADMIN';
                
                if (isSuperAdminRole) {
                  return (
                    <Alert
                      message="超级管理员不需要绑定门店，可管理所有门店数据"
                      type="info"
                      showIcon
                      style={{ marginBottom: 16 }}
                    />
                  );
                }
                
                return (
                  <ProFormSelect
                    name="storeId"
                    label="所属门店"
                    width="md"
                    options={stores.map((s) => ({ label: s.name, value: s.id }))}
                    placeholder="请选择门店（门店管理员必选）"
                    rules={[
                      {
                        required: roleCode === 'STORE_ADMIN',
                        message: '门店管理员必须选择所属门店',
                      },
                    ]}
                    extra="门店管理员需要绑定门店，选择后只能管理该门店数据"
                  />
                );
              }}
            </ProFormDependency>
          )}

          {/* 门店管理员创建用户时显示提示 */}
          {!isSuperAdmin && currentStore && (
            <Alert
              message={`用户将自动归属到门店：${currentStore.name}`}
              type="info"
              showIcon
              style={{ marginTop: 16 }}
            />
          )}
        </Card>
      </ProForm>
    </PageContainer>
  );
};

export default UserFormPage;

