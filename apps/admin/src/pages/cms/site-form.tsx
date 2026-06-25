/**
 * 站点管理 - 新增/编辑表单页
 */
import { ProFormText, ProFormTextArea } from '@ant-design/pro-components';
import { Card } from 'antd';
import { useEffect, useState } from 'react';
import { useParams, history } from '@umijs/max';
import { siteApi } from '@hospital/api';
import type { CmsSite } from '@hospital/api';

import FormPage from '@/components/FormPage';
import { SwitchGroup } from '@/components/formFields';
import { useFormInitialValues } from '@/hooks/useFormInitialValues';
import { useFormSubmit } from '@/hooks/useFormSubmit';

const SiteFormPage: React.FC = () => {
  const { id } = useParams();
  const isEdit = !!id;
  const [site, setSite] = useState<CmsSite | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (isEdit && id) {
      setLoading(true);
      siteApi
        .getDetail(id)
        .then((data) => setSite(data))
        .catch(() => {})
        .finally(() => setLoading(false));
    }
  }, [id, isEdit]);

  const { initialValues } = useFormInitialValues<CmsSite>(site, {
    switchFields: ['isDefault', 'status'],
    defaults: {
      status: true,
      isDefault: false,
    } as unknown as Partial<CmsSite>,
  });

  const { handleSubmit, submitting } = useFormSubmit<CmsSite>(
    async (values) => {
      if (isEdit && id) {
        await siteApi.update(id, values as any);
      } else {
        await siteApi.create(values as any);
      }
    },
    {
      switchFields: ['isDefault', 'status'],
      successMessage: isEdit ? '更新成功' : '创建成功',
      onSuccess: () => history.push('/cms/sites'),
    },
  );

  return (
    <FormPage
      title={isEdit ? '编辑站点' : '新增站点'}
      loading={loading}
      submitting={submitting}
      initialValues={initialValues}
      onFinish={handleSubmit}
      onCancel={() => history.back()}
      saveText={isEdit ? '保存' : '创建'}
    >
      <Card title="基础信息" style={{ marginBottom: 16 }}>
        <ProFormText
          name="name"
          label="站点名称"
          width="lg"
          rules={[{ required: true, message: '请输入站点名称' }]}
        />
        <ProFormText
          name="code"
          label="站点编码"
          width="md"
          tooltip="租户内唯一，建议使用英文/数字，如 main、event"
          rules={[
            { required: true, message: '请输入站点编码' },
            { pattern: /^[a-zA-Z0-9_-]+$/, message: '仅支持英文、数字、下划线和连字符' },
          ]}
        />
        <ProFormText name="domain" label="绑定域名" width="lg" placeholder="https://www.example.com" />
        <ProFormTextArea name="description" label="站点描述" width="lg" />
      </Card>

      <Card title="视觉资源" style={{ marginBottom: 16 }}>
        <ProFormText name="logoUrl" label="站点 Logo" width="lg" placeholder="Logo 图片地址" />
        <ProFormText name="faviconUrl" label="站点图标" width="lg" placeholder="Favicon 图片地址" />
      </Card>

      <Card title="状态设置">
        <SwitchGroup
          items={[
            { name: 'status', label: '启用' },
            { name: 'isDefault', label: '设为默认站点' },
          ]}
        />
      </Card>
    </FormPage>
  );
};

export default SiteFormPage;
