/**
 * 文章管理 - 新增/编辑表单页
 */
import { ProFormSelect, ProFormText, ProFormTextArea, ProFormDigit } from '@ant-design/pro-components';
import { Card, Form } from 'antd';
import { useEffect, useState } from 'react';
import { useParams, history } from '@umijs/max';
import { articleApi, categoryApi, siteApi } from '@hospital/api';
import type { CmsArticle, CmsCategory, CmsSite } from '@hospital/api';

import FormPage from '@/components/FormPage';
import { ImageUploadCard, SwitchGroup } from '@/components/formFields';
import RichTextEditor from '@/components/RichTextEditor';
import { useFormInitialValues } from '@/hooks/useFormInitialValues';
import { useFormSubmit } from '@/hooks/useFormSubmit';

const ArticleFormPage: React.FC = () => {
  const { id } = useParams();
  const isEdit = !!id;
  const [article, setArticle] = useState<CmsArticle | null>(null);
  const [loading, setLoading] = useState(false);
  const [sites, setSites] = useState<CmsSite[]>([]);
  const [categories, setCategories] = useState<CmsCategory[]>([]);
  const [siteId, setSiteId] = useState<string | undefined>();

  // 编辑模式加载数据
  useEffect(() => {
    if (isEdit && id) {
      setLoading(true);
      articleApi
        .getDetail(id)
        .then((data) => {
          setArticle(data);
          setSiteId(data.siteId);
        })
        .catch(() => {})
        .finally(() => setLoading(false));
    }
  }, [id, isEdit]);

  // 加载站点
  useEffect(() => {
    siteApi
      .getList({ page: 1, pageSize: 100 })
      .then((res) => setSites(res.data || []))
      .catch(() => {});
  }, []);

  // 加载栏目（按当前站点过滤）
  useEffect(() => {
    if (!siteId) {
      setCategories([]);
      return;
    }
    categoryApi
      .getList({ siteId })
      .then(setCategories)
      .catch(() => setCategories([]));
  }, [siteId]);

  const { initialValues } = useFormInitialValues<CmsArticle>(article, {
    switchFields: ['isTop', 'status'],
    defaults: {
      status: false,
      isTop: false,
      sortOrder: 0,
    } as unknown as Partial<CmsArticle>,
  });

  const { handleSubmit, submitting } = useFormSubmit<CmsArticle>(
    async (values) => {
      if (isEdit && id) {
        await articleApi.update(id, values as any);
      } else {
        await articleApi.create(values as any);
      }
    },
    {
      switchFields: ['isTop', 'status'],
      successMessage: isEdit ? '更新成功' : '发布成功',
      onSuccess: () => history.push('/cms/articles'),
    },
  );

  const categoryOptions = categories.map((c) => ({ label: c.name, value: c.id }));
  const siteDisabled = isEdit;

  return (
    <FormPage
      title={isEdit ? '编辑文章' : '发布文章'}
      loading={loading}
      submitting={submitting}
      initialValues={initialValues}
      onFinish={handleSubmit}
      onCancel={() => history.back()}
      saveText={isEdit ? '保存' : '发布'}
    >
      <Card title="基础信息" style={{ marginBottom: 16 }}>
        <ProFormText
          name="title"
          label="标题"
          width="lg"
          rules={[{ required: true, message: '请输入文章标题' }]}
        />
        <ProFormText name="subtitle" label="副标题" width="lg" />
        <ProFormSelect
          name="siteId"
          label="所属站点"
          width="md"
          disabled={siteDisabled}
          rules={[{ required: true, message: '请选择所属站点' }]}
          options={sites.map((s) => ({ label: s.name, value: s.id }))}
          fieldProps={{
            onChange: (val: string) => setSiteId(val),
          }}
        />
        <ProFormSelect
          name="categoryId"
          label="栏目"
          width="md"
          options={categoryOptions}
          allowClear
          placeholder={siteId ? '请选择栏目' : '请先选择站点'}
          disabled={!siteId}
        />
        <ProFormText name="author" label="作者" width="md" />
        <ProFormText name="source" label="来源" width="md" />
      </Card>

      <ImageUploadCard
        title="封面图"
        name="coverImage"
        aspectRatio="16:9"
        width={240}
        height={135}
        folder="cms/article"
        placeholder="上传文章封面图"
      />

      <Card title="摘要" style={{ marginBottom: 16 }}>
        <ProFormTextArea name="summary" label="摘要" placeholder="请输入文章摘要（选填）" />
      </Card>

      <Card title="正文内容" style={{ marginBottom: 16 }}>
        <Form.Item
          name="content"
          label="正文"
          rules={[{ required: true, message: '请输入正文内容' }]}
        >
          <RichTextEditor height={450} placeholder="请输入文章正文..." />
        </Form.Item>
      </Card>

      <Card title="SEO 设置" style={{ marginBottom: 16 }}>
        <ProFormText name="seoTitle" label="SEO 标题" width="lg" />
        <ProFormText name="seoKeywords" label="SEO 关键词" width="lg" placeholder="多个关键词用英文逗号分隔" />
        <ProFormTextArea name="seoDescription" label="SEO 描述" width="lg" />
      </Card>

      <Card title="发布设置">
        <ProFormDigit
          name="sortOrder"
          label="排序"
          width="sm"
          min={0}
          fieldProps={{ precision: 0 }}
        />
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

export default ArticleFormPage;
