import { PageContainer, ProForm, ProFormText, ProFormTextArea, ProFormSelect, ProFormSwitch } from '@ant-design/pro-components';
import { Card, App, Row, Col, Form } from 'antd';
import { useEffect, useState } from 'react';
import { history, useParams } from '@umijs/max';
import { contentApi } from '@hospital/api';
import type { News } from '@hospital/api';
import ImageUpload from '@/components/ImageUpload';
import RichTextEditor from '@/components/RichTextEditor';

const TYPE_OPTIONS = [
  { label: '医院动态', value: 1 },
  { label: '健康知识', value: 2 },
  { label: '政策法规', value: 3 },
];

const NewsFormPage: React.FC = () => {
  const { message } = App.useApp();
  const { id } = useParams<{ id: string }>();
  const isEdit = !!id;
  const [loading, setLoading] = useState(false);
  const [news, setNews] = useState<News | null>(null);

  useEffect(() => {
    if (isEdit) {
      loadNews();
    }
  }, [id]);

  const loadNews = async () => {
    if (!id) return;
    setLoading(true);
    try {
      const data = await contentApi.getNewsDetail(id);
      setNews(data);
    } catch (error: any) {
      message.error('加载新闻信息失败');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (values: any) => {
    try {
      const data = { ...values, isTop: values.isTop ? 1 : 0, status: values.status ? 1 : 0 };
      if (isEdit && id) {
        await contentApi.updateNews(id, data);
        message.success('更新成功');
      } else {
        await contentApi.createNews(data);
        message.success('创建成功');
      }
      history.push('/content/news');
    } catch (error: any) {
      message.error(error.message || '操作失败');
    }
  };

  const initialValues = news ? {
    ...news,
    isTop: news.isTop === 1,
    status: news.status === 1,
  } : {
    type: 1,
    isTop: false,
    status: true,
  };

  return (
    <PageContainer title={isEdit ? '编辑新闻' : '发布新闻'}>
      <ProForm
        onFinish={handleSubmit}
        initialValues={initialValues}
        submitter={{
          searchConfig: { submitText: isEdit ? '保存' : '发布' },
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
        <Card title="新闻信息" style={{ marginBottom: 16 }} loading={loading}>
          <ProFormText
            name="title"
            label="标题"
            width="lg"
            rules={[{ required: true, message: '请输入标题' }]}
          />
          <ProForm.Group>
            <ProFormSelect
              name="type"
              label="类型"
              width="md"
              options={TYPE_OPTIONS}
              rules={[{ required: true, message: '请选择类型' }]}
            />
          </ProForm.Group>
          <Form.Item name="coverImage" label="封面图">
            <ImageUpload
              aspectRatio="16:9"
              folder="news"
              placeholder="上传封面图"
              width={240}
              height={135}
            />
          </Form.Item>
          <ProFormTextArea
            name="summary"
            label="摘要"
            placeholder="请输入新闻摘要"
          />
        </Card>

        <Card title="新闻内容" style={{ marginBottom: 16 }} loading={loading}>
          <Form.Item
            name="content"
            label="内容"
            rules={[{ required: true, message: '请输入内容' }]}
          >
            <RichTextEditor height={400} placeholder="请输入新闻内容..." />
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

export default NewsFormPage;

