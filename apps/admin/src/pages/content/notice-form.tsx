import { PageContainer, ProForm, ProFormText, ProFormSelect, ProFormSwitch, FooterToolbar } from '@ant-design/pro-components';
import type { ProFormInstance } from '@ant-design/pro-components';
import { Card, App, Form, Button, Space, Spin } from 'antd';
import { useEffect, useState, useRef } from 'react';
import { history, useParams } from '@umijs/max';
import { contentApi } from '@hospital/api';
import type { Notice } from '@hospital/api';
import RichTextEditor from '@/components/RichTextEditor';

const TYPE_OPTIONS = [
  { label: '系统公告', value: 1 },
  { label: '停诊通知', value: 2 },
  { label: '活动通知', value: 3 },
];

const NoticeFormPage: React.FC = () => {
  const { message } = App.useApp();
  const { id } = useParams<{ id: string }>();
  const isEdit = !!id;
  const [loading, setLoading] = useState(false);
  const [notice, setNotice] = useState<Notice | null>(null);
  const formRef = useRef<ProFormInstance>();

  useEffect(() => {
    if (isEdit) {
      loadNotice();
    }
  }, [id]);

  const loadNotice = async () => {
    if (!id) return;
    setLoading(true);
    try {
      const data = await contentApi.getNoticeDetail(id);
      setNotice(data);
      // 异步加载完成后，使用 setFieldsValue 更新表单值
      formRef.current?.setFieldsValue({
        ...data,
        isTop: data.isTop === 1,
        status: data.status === 1,
      });
    } catch (error: any) {
      message.error('加载公告信息失败');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (values: any) => {
    try {
      const data = { ...values, isTop: values.isTop ? 1 : 0, status: values.status ? 1 : 0 };
      if (isEdit && id) {
        await contentApi.updateNotice(id, data);
        message.success('更新成功');
      } else {
        await contentApi.createNotice(data);
        message.success('创建成功');
      }
      history.push('/content/notice');
    } catch (error: any) {
      message.error(error.message || '操作失败');
    }
  };

  const initialValues = notice ? {
    ...notice,
    isTop: notice.isTop === 1,
    status: notice.status === 1,
  } : {
    type: 1,
    isTop: false,
    status: true,
  };

  return (
    <PageContainer title={isEdit ? '编辑公告' : '发布公告'}>
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
                  {isEdit ? '保存' : '发布'}
                </Button>
              </Space>
            </FooterToolbar>
          ),
        }}
      >
        <Card title="公告信息" style={{ marginBottom: 16 }} loading={loading}>
          <ProFormText
            name="title"
            label="标题"
            width="lg"
            rules={[{ required: true, message: '请输入标题' }]}
          />
          <ProFormSelect
            name="type"
            label="类型"
            width="md"
            options={TYPE_OPTIONS}
            rules={[{ required: true, message: '请选择类型' }]}
          />
        </Card>

        <Card title="公告内容" style={{ marginBottom: 16 }} loading={loading}>
          <Form.Item
            name="content"
            label="内容"
            rules={[{ required: true, message: '请输入内容' }]}
          >
            <RichTextEditor height={400} placeholder="请输入公告内容..." />
          </Form.Item>
        </Card>

        <Card title="发布设置" loading={loading}>
          <ProForm.Group>
            <ProFormSwitch name="isTop" label="置顶" />
            <ProFormSwitch name="status" label="立即发布" />
          </ProForm.Group>
        </Card>
      </ProForm>
    </PageContainer>
  );
};

export default NoticeFormPage;

