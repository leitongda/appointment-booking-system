import { ProFormText, ProFormSelect, ProFormTextArea, ProFormDateTimePicker } from '@ant-design/pro-components';
import { Card, App } from 'antd';
import { useEffect, useState } from 'react';
import { useParams, history } from '@umijs/max';
import { platformAnnouncementApi, tenantApi } from '@hospital/api';
import type { PlatformAnnouncement } from '@hospital/api';
import FormPage from '@/components/FormPage';
import { fetchAllData } from '@/utils/fetchAllData';

const TARGET_TYPE_OPTIONS = [
  { label: '全部租户', value: 'all' },
  { label: '指定租户', value: 'specific' },
];

const PRIORITY_OPTIONS = [
  { label: '普通', value: 0 },
  { label: '重要', value: 1 },
  { label: '紧急', value: 2 },
];

const PlatformAnnouncementFormPage: React.FC = () => {
  const { message } = App.useApp();
  const { id } = useParams();
  const isEdit = !!id;
  const [announcement, setAnnouncement] = useState<PlatformAnnouncement | null>(null);
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [tenants, setTenants] = useState<{ label: string; value: string }[]>([]);

  useEffect(() => {
    if (isEdit && id) {
      setLoading(true);
      platformAnnouncementApi
        .getDetail(id)
        .then(setAnnouncement)
        .catch(() => { message.error('加载公告详情失败'); })
        .finally(() => setLoading(false));
    }
  }, [id, isEdit]);

  // 加载租户列表（用于指定租户选择）
  useEffect(() => {
    fetchAllData((page, pageSize) =>
      tenantApi.getTenants({ page, pageSize }).then((res: any) => ({
        data: res.data ?? [],
        total: res.total ?? 0,
        page: res.page ?? 1,
        pageSize: res.pageSize ?? 100,
      }))
    ).then((allTenants: any[]) => {
      setTenants(allTenants.map((t: any) => ({ label: t.name, value: t.id })));
    });
  }, []);

  const isDisabled = !!(isEdit && announcement && announcement.status !== 'draft');

  const handleSubmit = async (values: any) => {
    setSubmitting(true);
    try {
      if (isEdit && id) {
        await platformAnnouncementApi.update(id, values);
      } else {
        await platformAnnouncementApi.create(values);
      }
      history.push('/platform/announcement/list');
    } finally {
      setSubmitting(false);
    }
  };

  const initialValues = isEdit && announcement
    ? {
        title: announcement.title,
        content: announcement.content,
        targetType: announcement.targetType,
        targetTenantIds: announcement.targetTenantIds,
        priority: announcement.priority,
        publishAt: announcement.publishAt,
        expireAt: announcement.expireAt,
      }
    : {
        targetType: 'all',
        priority: 0,
      };

  return (
    <FormPage
      title={isEdit ? '编辑公告' : '发布公告'}
      loading={loading}
      submitting={submitting}
      initialValues={initialValues}
      onFinish={handleSubmit}
      onCancel={() => history.back()}
      saveText={isEdit ? '保存' : '创建'}
      formProps={{ disabled: isDisabled }}
    >
      <Card title="基本信息" style={{ marginBottom: 16 }}>
        <ProFormText
          name="title"
          label="标题"
          width="lg"
          rules={[{ required: true, message: '请输入标题' }]}
        />
        <ProFormSelect
          name="targetType"
          label="发布目标"
          width="md"
          options={TARGET_TYPE_OPTIONS}
          rules={[{ required: true, message: '请选择发布目标' }]}
        />
        <ProFormSelect
          name="targetTenantIds"
          label="指定租户"
          width="lg"
          options={tenants}
          mode="multiple"
          placeholder="请选择目标租户"
          dependencies={['targetType']}
          rules={[
            ({ getFieldValue }) => ({
              validator(_, value) {
                if (getFieldValue('targetType') === 'specific' && (!value || value.length === 0)) {
                  return Promise.reject(new Error('请选择至少一个租户'));
                }
                return Promise.resolve();
              },
            }),
          ]}
          fieldProps={{ showSearch: true, optionFilterProp: 'label' }}
        />
        <ProFormSelect
          name="priority"
          label="优先级"
          width="md"
          options={PRIORITY_OPTIONS}
          rules={[{ required: true, message: '请选择优先级' }]}
        />
      </Card>

      <Card title="公告内容" style={{ marginBottom: 16 }}>
        <ProFormTextArea
          name="content"
          label="内容"
          rules={[{ required: true, message: '请输入公告内容' }]}
          fieldProps={{ rows: 10, placeholder: '请输入公告内容...' }}
        />
      </Card>

      <Card title="定时设置">
        <ProFormDateTimePicker
          name="publishAt"
          label="定时发布"
          width="md"
          extra="留空则创建后手动发布"
        />
        <ProFormDateTimePicker
          name="expireAt"
          label="过期时间"
          width="md"
          extra="留空则永不过期"
        />
      </Card>
    </FormPage>
  );
};

export default PlatformAnnouncementFormPage;
