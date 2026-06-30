/**
 * 操作指引管理 - 创建/编辑表单
 */
import { PageContainer, ProCard } from '@ant-design/pro-components';
import { App, Button, Form, Input, InputNumber, Space, Spin } from 'antd';
import { history, useParams } from '@umijs/max';
import { useEffect, useState, useCallback } from 'react';
import { adminGuideToursApi } from '@hospital/api';
import type { GuideTourFormData, TourStep } from '@hospital/api';
import StepEditor from './components/StepEditor';

export default function GuideTourFormPage() {
  const { id } = useParams() as { id?: string };
  const isEdit = !!id;
  const { message } = App.useApp();
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [steps, setSteps] = useState<TourStep[]>([]);

  // 加载已有数据
  useEffect(() => {
    if (!isEdit || !id) return;

    const fetchDetail = async () => {
      try {
        setLoading(true);
        const detail = await adminGuideToursApi.getById(id);
        form.setFieldsValue({
          code: detail.code,
          titleZh: detail.title?.zh || '',
          titleEn: detail.title?.en || '',
          descriptionZh: detail.description?.zh || '',
          descriptionEn: detail.description?.en || '',
          sortOrder: detail.sortOrder || 0,
        });
        setSteps(detail.steps || []);
      } catch (error: any) {
        message.error(error.message || '加载失败');
        history.push('/system/guide-tours');
      } finally {
        setLoading(false);
      }
    };

    fetchDetail();
  }, [id, isEdit, form, message]);

  const handleSubmit = useCallback(async () => {
    try {
      const values = await form.validateFields();
      setSubmitting(true);

      const data: GuideTourFormData = {
        code: values.code,
        title: { zh: values.titleZh, en: values.titleEn },
        description: { zh: values.descriptionZh, en: values.descriptionEn },
        steps: steps,
        sortOrder: values.sortOrder || 0,
      };

      if (isEdit && id) {
        await adminGuideToursApi.update(id, data);
        message.success('更新成功');
      } else {
        await adminGuideToursApi.create(data);
        message.success('创建成功');
      }

      history.push('/system/guide-tours');
    } catch (error: any) {
      if (error.message) {
        message.error(error.message || '操作失败');
      }
    } finally {
      setSubmitting(false);
    }
  }, [form, isEdit, id, steps, message]);

  if (loading) {
    return (
      <PageContainer title={isEdit ? '编辑指引' : '新建指引'}>
        <ProCard><Spin style={{ display: 'block', margin: '100px auto' }} /></ProCard>
      </PageContainer>
    );
  }

  return (
    <PageContainer
      title={isEdit ? '编辑指引' : '新建指引'}
      extra={
        <Space>
          <Button onClick={() => history.push('/system/guide-tours')}>取消</Button>
          <Button type="primary" loading={submitting} onClick={handleSubmit}>
            {isEdit ? '保存' : '创建'}
          </Button>
        </Space>
      }
    >
      <ProCard title="基本信息" style={{ marginBottom: 16 }}>
        <Form form={form} layout="vertical">
          <Space style={{ width: '100%' }} wrap>
            <Form.Item
              name="code"
              label="标识码"
              rules={[{ required: true, message: '请输入标识码' }]}
              style={{ width: 240 }}
            >
              <Input placeholder="dashboard_overview" disabled={isEdit} />
            </Form.Item>
            <Form.Item name="sortOrder" label="排序" initialValue={0} style={{ width: 120 }}>
              <InputNumber placeholder="0" style={{ width: '100%' }} />
            </Form.Item>
          </Space>

          <Space style={{ width: '100%' }} wrap>
            <Form.Item
              name="titleZh"
              label="标题 (中文)"
              rules={[{ required: true, message: '请输入中文标题' }]}
              style={{ flex: 1, minWidth: 240 }}
            >
              <Input placeholder="仪表盘操作指引" />
            </Form.Item>
            <Form.Item
              name="titleEn"
              label="Title (English)"
              style={{ flex: 1, minWidth: 240 }}
            >
              <Input placeholder="Dashboard Guide" />
            </Form.Item>
          </Space>

          <Space style={{ width: '100%' }} wrap>
            <Form.Item name="descriptionZh" label="描述 (中文)" style={{ flex: 1, minWidth: 240 }}>
              <Input.TextArea placeholder="指引描述（可选）" rows={2} />
            </Form.Item>
            <Form.Item name="descriptionEn" label="Description (English)" style={{ flex: 1, minWidth: 240 }}>
              <Input.TextArea placeholder="Guide description (optional)" rows={2} />
            </Form.Item>
          </Space>
        </Form>
      </ProCard>

      <ProCard title="引导步骤">
        <StepEditor value={steps} onChange={setSteps} />
      </ProCard>
    </PageContainer>
  );
}
