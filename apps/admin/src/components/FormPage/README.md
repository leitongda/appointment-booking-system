# FormPage 组件使用示例

## 完整的表单页面示例

### 使用 FormPage 和其他表单字段组件的完整示例

```tsx
import { PageContainer, ProForm, ProFormText, ProFormSelect, Card, App } from 'antd';
import { history, useParams } from '@umijs/max';
import { useEffect, useState, useRef } from 'react';
import FormPage from '@/components/FormPage';
import { PasswordField, SwitchGroup, ImageUploadCard } from '@/components/formFields';
import { adminApi } from '@hospital/api';
import type { ProFormInstance } from '@ant-design/pro-components';

const UserFormPage: React.FC = () => {
  const { message } = App.useApp();
  const { id } = useParams<{ id: string }>();
  const isEdit = !!id;
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [user, setUser] = useState<any>(null);
  const formRef = useRef<ProFormInstance>();

  useEffect(() => {
    if (isEdit) {
      loadUser();
    }
  }, [id]);

  const loadUser = async () => {
    if (!id) return;
    setLoading(true);
    try {
      const data = await adminApi.getAdminDetail(id);
      setUser(data);
      formRef.current?.setFieldsValue({
        ...data,
        status: data.status === 1,
      });
    } catch (error: any) {
      message.error('加载用户信息失败');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (values: any) => {
    setSubmitting(true);
    try {
      // 使用 SwitchGroup 的辅助函数转换开关值
      const data = {
        ...values,
        status: values.status ? 1 : 0,
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
    } finally {
      setSubmitting(false);
    }
  };

  const initialValues = user ? {
    ...user,
    status: user.status === 1,
  } : {
    status: true,
  };

  return (
    <FormPage
      title={isEdit ? '编辑用户' : '新增用户'}
      loading={loading}
      submitting={submitting}
      formRef={formRef}
      initialValues={initialValues}
      onFinish={handleSubmit}
      onCancel={() => history.back()}
      saveText={isEdit ? '保存' : '创建'}
    >
      <Card title="账号信息" style={{ marginBottom: 16 }}>
        <ProFormText
          name="username"
          label="账号"
          width="md"
          rules={[{ required: true, message: '请输入账号' }]}
          disabled={isEdit}
        />

        {!isEdit && (
          <PasswordField
            strengthLevel="medium"
            showStrengthIndicator={true}
          />
        )}
      </Card>

      <Card title="基本信息" style={{ marginBottom: 16 }}>
        <ImageUploadCard
          title="用户头像"
          name="avatar"
          aspectRatio="1:1"
          width={100}
          height={100}
          folder="avatars"
          placeholder="上传头像"
        />

        <ProFormText
          name="name"
          label="用户名"
          width="md"
          rules={[{ required: true, message: '请输入用户名' }]}
        />

        <ProFormText name="phone" label="手机号" width="md" />
        <ProFormText name="email" label="邮箱" width="md" />
      </Card>

      <Card title="权限设置">
        <ProFormSelect
          name="roleId"
          label="角色"
          width="md"
          options={[
            { label: '管理员', value: '1' },
            { label: '普通用户', value: '2' },
          ]}
          rules={[{ required: true, message: '请选择角色' }]}
        />

        <SwitchGroup
          gutter={16}
          items={[
            {
              name: 'status',
              label: '启用状态',
              span: 12,
              extra: '关闭后用户将无法登录',
            },
            {
              name: 'isRecommended',
              label: '是否推荐',
              span: 12,
            },
          ]}
        />
      </Card>
    </FormPage>
  );
};

export default UserFormPage;
```

## 各组件独立使用示例

### 1. FormPage - 表单页面容器

```tsx
import FormPage from '@/components/FormPage';

<FormPage
  title="新增用户"
  loading={loading}
  submitting={submitting}
  formRef={formRef}
  initialValues={{ status: true }}
  onFinish={handleSubmit}
  onCancel={() => history.back()}
  saveText="创建"
  cancelText="取消"
  formProps={{
    // ProForm 的额外属性
    submitTimeout: 5000,
  }}
  pageContainerProps={{
    // PageContainer 的额外属性
    header: {
      breadcrumb: {},
    },
  }}
>
  {/* 表单内容 */}
  <Card title="基础信息">
    <ProFormText name="username" label="账号" />
  </Card>
</FormPage>
```

### 2. PasswordField - 密码字段

```tsx
import { PasswordField } from '@/components/formFields';

// 基础用法（最小强度）
<PasswordField />

// 中等强度 + 强度指示器
<PasswordField
  strengthLevel="medium"
  showStrengthIndicator={true}
/>

// 强密码模式
<PasswordField
  strengthLevel="strong"
  showStrengthIndicator={true}
/>

// 编辑模式（不填则不修改密码）
<PasswordField
  isEdit={true}
  required={false}
/>

// 自定义名称前缀（用于多个密码字段）
<PasswordField
  namePrefix="doctor"
  label="医生密码"
  confirmLabel="确认医生密码"
/>

// 完整配置
<PasswordField
  namePrefix="user"
  label="用户密码"
  confirmLabel="确认密码"
  required={true}
  strengthLevel="medium"
  showStrengthIndicator={true}
  isEdit={false}
  placeholder="请输入密码"
  confirmPlaceholder="请再次输入密码"
  width="md"
  extra="密码至少需要8个字符、小写字母、数字"
/>
```

### 3. SwitchGroup - 开关组

```tsx
import { SwitchGroup, transformSwitchValues } from '@/components/formFields';

// 基础用法：垂直排列
<SwitchGroup
  items={[
    { name: 'status', label: '启用状态' },
    { name: 'isRecommended', label: '是否推荐' },
    { name: 'onlineConsultEnabled', label: '在线问诊' },
  ]}
/>

// 响应式布局：每行多个开关
<SwitchGroup
  gutter={16}
  items={[
    { name: 'status', label: '启用状态', span: 8 },
    { name: 'isRecommended', label: '是否推荐', span: 8 },
    { name: 'onlineConsultEnabled', label: '在线问诊', span: 8 },
  ]}
/>

// 带提示和禁用
<SwitchGroup
  items={[
    {
      name: 'status',
      label: '启用状态',
      extra: '关闭后用户将无法看到该内容',
      tooltip: '控制内容的显示状态',
    },
    {
      name: 'isRecommended',
      label: '是否推荐',
      disabled: true,
    },
  ]}
/>

// 全部禁用
<SwitchGroup
  disabledAll={true}
  items={[
    { name: 'status', label: '启用状态' },
    { name: 'isRecommended', label: '是否推荐' },
  ]}
/>

// 使用辅助函数转换表单值
const handleSubmit = async (values: any) => {
  const data = transformSwitchValues(values, ['status', 'isRecommended', 'onlineConsultEnabled']);
  // data.status === 1 或 0（而不是 true/false）
  await api.create(data);
};
```

### 4. ImageUploadCard - 图片上传卡片

```tsx
import { ImageUploadCard } from '@/components/formFields';

// 基础用法：头像上传
<ImageUploadCard
  title="用户头像"
  name="avatar"
  aspectRatio="1:1"
  width={120}
  height={120}
  folder="avatars"
/>

// Banner 上传（16:9）
<ImageUploadCard
  title="医生 Banner"
  name="banner"
  aspectRatio="16:9"
  width={272}
  height={153}
  folder="doctor"
  showCrop={true}
  required={true}
  requiredMessage="请上传医生 Banner 图"
/>

// 高级裁剪配置
<ImageUploadCard
  title="封面图"
  name="cover"
  aspectRatio="16:9"
  cropQuality={0.95}
  cropMaxWidth={1920}
  cropMaxHeight={1080}
  cropShowGrid={true}
  cropShowFlip={true}
  cropShowBrightnessContrast={true}
  cropWatermark={{
    text: '医院水印',
    fontSize: 16,
    color: 'rgba(255,255,255,0.5)',
    opacity: 0.5,
    position: 'bottomRight',
  }}
/>

// 带提示和 tooltip
<ImageUploadCard
  title="执业证书"
  name="licenseImage"
  aspectRatio="free"
  folder="doctor"
  placeholder="上传证书图片"
  tooltip="请上传清晰的执业证书照片"
  extra="支持 JPG、PNG 格式，大小不超过 5MB"
/>

// 禁用状态
<ImageUploadCard
  title="用户头像"
  name="avatar"
  disabled={true}
/>

// 自定义卡片样式
<ImageUploadCard
  title="封面图"
  name="cover"
  cardStyle={{
    background: '#f5f5f5',
    marginBottom: 24,
  }}
  cardClassName="custom-cover-card"
/>
```

## 迁移现有表单页面

### 迁移前（使用 PageContainer + ProForm）

```tsx
// 原始代码
const UserFormPage: React.FC = () => {
  return (
    <PageContainer title="新增用户">
      <ProForm
        onFinish={handleSubmit}
        submitter={{
          render: (props) => (
            <FooterToolbar>
              <Space>
                <Button onClick={() => history.back()}>取消</Button>
                <Button type="primary" onClick={() => props.form?.submit()}>
                  创建
                </Button>
              </Space>
            </FooterToolbar>
          ),
        }}
      >
        <Card title="账号信息">
          {/* 表单字段 */}
        </Card>
      </ProForm>
    </PageContainer>
  );
};
```

### 迁移后（使用 FormPage）

```tsx
// 使用 FormPage 后
const UserFormPage: React.FC = () => {
  return (
    <FormPage
      title="新增用户"
      onFinish={handleSubmit}
      onCancel={() => history.back()}
      saveText="创建"
    >
      <Card title="账号信息">
        {/* 表单字段 */}
      </Card>
    </FormPage>
  );
};
```

代码量减少约 30%，更加简洁清晰。
