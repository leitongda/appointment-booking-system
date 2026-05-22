/**
 * 新闻表单页面
 *
 * 新闻类型通过 useDict('news_type') 从字典 API 获取
 */
import { ProFormText, ProFormTextArea, ProFormSelect } from '@ant-design/pro-components';
import { Card, Form } from 'antd';
import { useEffect, useState, useMemo } from 'react';
import { useParams, history } from '@umijs/max';
import { contentApi } from '@hospital/api';
import type { News } from '@hospital/api';

// 基础设施导入
import FormPage from '@/components/FormPage';
import { ImageUploadCard, SwitchGroup } from '@/components/formFields';
import RichTextEditor from '@/components/RichTextEditor';
import { useDict } from '@/hooks/useDict';
import { useFormInitialValues } from '@/hooks/useFormInitialValues';
import { useFormSubmit } from '@/hooks/useFormSubmit';

const NewsFormPage: React.FC = () => {
  const { id } = useParams();
  const isEdit = !!id;
  const [news, setNews] = useState<News | null>(null);
  const [loading, setLoading] = useState(false);

  // 字典数据
  const { options: newsTypeDict } = useDict('news_type');
  const newsTypeOptions = useMemo(() => newsTypeDict.map(o => ({ label: o.label, value: Number(o.value) })), [newsTypeDict]);

  // 加载新闻数据
  useEffect(() => {
    if (isEdit && id) {
      setLoading(true);
      contentApi
        .getNewsDetail(id)
        .then((data) => {
          setNews(data);
        })
        .catch(() => {
          // 错误在 useFormSubmit 中处理
        })
        .finally(() => {
          setLoading(false);
        });
    }
  }, [id, isEdit]);

  // 使用 useFormInitialValues hook 处理初始值
  const { initialValues } = useFormInitialValues<News>(
    news,
    {
      switchFields: ['isTop', 'status'],
      defaults: {
        type: 1,
        isTop: false,
        status: true,
      } as unknown as Partial<News>,
    }
  );

  // 使用 useFormSubmit hook 处理提交
  const { handleSubmit, submitting } = useFormSubmit<News>(
    async (values) => {
      if (isEdit && id) {
        await contentApi.updateNews(id, values as any);
      } else {
        await contentApi.createNews(values as any);
      }
    },
    {
      switchFields: ['isTop', 'status'],
      successMessage: isEdit ? '更新成功' : '发布成功',
      onSuccess: () => {
        history.push('/content-center/content/news');
      },
    }
  );

  return (
    <FormPage
      title={isEdit ? '编辑新闻' : '发布新闻'}
      loading={loading}
      submitting={submitting}
      initialValues={initialValues}
      onFinish={handleSubmit}
      onCancel={() => history.back()}
      saveText={isEdit ? '保存' : '发布'}
    >
      {/* 新闻信息 */}
      <Card title="新闻信息" style={{ marginBottom: 16 }}>
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
          options={newsTypeOptions}
          rules={[{ required: true, message: '请选择类型' }]}
        />
      </Card>

      {/* 封面图 */}
      <ImageUploadCard
        title="封面图"
        name="coverImage"
        aspectRatio="16:9"
        width={240}
        height={135}
        folder="news"
        placeholder="上传封面图"
      />

      {/* 摘要 */}
      <Card title="摘要" style={{ marginBottom: 16 }}>
        <ProFormTextArea
          name="summary"
          label="摘要"
          placeholder="请输入新闻摘要"
        />
      </Card>

      {/* 新闻内容 */}
      <Card title="新闻内容" style={{ marginBottom: 16 }}>
        <Form.Item
          name="content"
          label="内容"
          rules={[{ required: true, message: '请输入内容' }]}
        >
          <RichTextEditor height={400} placeholder="请输入新闻内容..." />
        </Form.Item>
      </Card>

      {/* 发布设置 */}
      <Card title="发布设置">
        <SwitchGroup
          items={[
            { name: 'isTop', label: '置顶' },
            { name: 'status', label: '立即发布' },
          ]}
        />
      </Card>
    </FormPage>
  );
};

export default NewsFormPage;
