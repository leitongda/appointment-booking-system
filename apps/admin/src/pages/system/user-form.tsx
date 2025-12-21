import { PageContainer, ProForm, ProFormText, ProFormSelect, ProFormSwitch, ProFormDependency, FooterToolbar } from '@ant-design/pro-components';
import type { ProFormInstance } from '@ant-design/pro-components';
import { Card, App, Alert, Button, Space, Form } from 'antd';
import { useEffect, useState, useRef } from 'react';
import { history, useParams, useModel, useAccess } from '@umijs/max';
import { adminApi, storeApi } from '@hospital/api';
import type { Admin, Role } from '@hospital/api';
import ImageUpload from '@/components/ImageUpload';

interface Store {
  id: string;
  name: string;
}

const UserFormPage: React.FC = () => {
  const { message } = App.useApp();
  const { id } = useParams<{ id: string }>();
  const access = useAccess();
  const isEdit = !!id;
  const [loading, setLoading] = useState(false);
  const [admin, setAdmin] = useState<Admin | null>(null);
  const [roles, setRoles] = useState<Role[]>([]);
  const [stores, setStores] = useState<Store[]>([]);
  const formRef = useRef<ProFormInstance>();
  
  const { initialState } = useModel('@@initialState');
  const { currentUser, currentStore } = initialState ?? {};
  const isSuperAdmin = access.canSuperAdmin;

  useEffect(() => {
    loadRoles();
    // 超管或多门店管理员需要加载门店列表
    if (isSuperAdmin || (currentUser?.storeIds?.length ?? 0) > 1) {
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
      let storeList = data ?? [];
      // 非超管只显示其关联的门店
      if (!isSuperAdmin && currentUser?.storeIds?.length) {
        storeList = storeList.filter((s: Store) => currentUser.storeIds?.includes(s.id));
      }
      setStores(storeList);
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
      // 异步加载完成后，使用 setFieldsValue 更新表单值
      formRef.current?.setFieldsValue({
        ...data,
        status: data.status === 1,
        // 使用 storeIds 数组
        storeIds: data.storeIds || (data.storeId ? [data.storeId] : []),
      });
    } catch (error: any) {
      message.error('加载用户信息失败');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (values: any) => {
    try {
      // 排除确认密码字段
      const { confirmPassword, storeIds, ...restValues } = values;
      const data = { 
        ...restValues, 
        status: values.status ? 1 : 0,
        // 多门店绑定
        storeIds: isSuperAdmin ? storeIds : (currentStore?.id ? [currentStore.id] : []),
        // 兼容旧字段：使用第一个门店作为 storeId
        storeId: isSuperAdmin ? (storeIds?.[0] || null) : currentStore?.id,
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
    storeIds: admin.storeIds || (admin.storeId ? [admin.storeId] : []),
  } : {
    status: true,
    storeIds: [],
  };

  // 获取选中的角色编码
  const getSelectedRoleCode = (roleId: string) => {
    const role = roles.find(r => r.id === roleId);
    return role?.code;
  };

  return (
    <PageContainer title={isEdit ? '编辑用户' : '新增用户'}>
      <ProForm
        formRef={formRef}
        onFinish={handleSubmit}
        initialValues={initialValues}
        submitter={{
          render: (props, dom) => (
            <FooterToolbar>
              <Space>
                <Button onClick={() => history.back()}>取消</Button>
                <Button type="primary" onClick={() => props.form?.submit()}>
                  {isEdit ? '保存' : '创建'}
                </Button>
              </Space>
            </FooterToolbar>
          ),
        }}
      >
        <Card title="账号信息" style={{ marginBottom: 16 }} loading={loading}>
          <ProForm.Group>
            <ProFormText
              name="username"
              label="账号"
              width="md"
              rules={[{ required: true, message: '请输入账号' }]}
              disabled={isEdit}
              placeholder="用于登录的唯一标识"
              extra={isEdit ? '账号创建后不可修改' : '账号用于登录，创建后不可修改'}
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
          <Form.Item 
            name="avatar" 
            label="头像"
            valuePropName="value"
          >
            <ImageUpload
              aspectRatio="1:1"
              width={100}
              height={100}
              folder="avatars"
              placeholder="上传头像"
              allowUrlTransfer={false}
              showCrop={true}
            />
          </Form.Item>
          <ProForm.Group>
            <ProFormText 
              name="name" 
              label="用户名" 
              width="md" 
              placeholder="用户的显示名称"
              fieldProps={{ autoComplete: 'off' }} 
            />
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
                
                // 门店管理员可以绑定多个门店
                const isStoreAdminRole = roleCode === 'STORE_ADMIN';
                
                return (
                  <ProFormSelect
                    name="storeIds"
                    label="绑定门店"
                    width="lg"
                    mode="multiple"
                    options={stores.map((s) => ({ label: s.name, value: s.id }))}
                    placeholder={isStoreAdminRole ? "请选择要管理的门店（可多选）" : "请选择门店"}
                    rules={[
                      {
                        required: isStoreAdminRole,
                        message: '门店管理员必须至少绑定一个门店',
                      },
                    ]}
                    extra={
                      isStoreAdminRole 
                        ? "门店管理员可以绑定多个门店，并在后台切换查看不同门店的数据" 
                        : "普通用户绑定门店后，只能操作该门店的数据"
                    }
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

