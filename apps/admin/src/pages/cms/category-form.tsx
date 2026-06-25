/**
 * 栏目管理 - 新增/编辑表单页
 *
 * 新增模式通过 query 参数 ?siteId=xxx 指定所属站点。
 */
import { ProFormSelect, ProFormText, ProFormDigit } from '@ant-design/pro-components';
import { Card } from 'antd';
import { useEffect, useState } from 'react';
import { useParams, useSearchParams, history } from '@umijs/max';
import { categoryApi, siteApi } from '@hospital/api';
import type { CmsCategory, CmsCategoryTreeNode, CmsSite } from '@hospital/api';

import FormPage from '@/components/FormPage';
import { useFormInitialValues } from '@/hooks/useFormInitialValues';
import { useFormSubmit } from '@/hooks/useFormSubmit';

const CategoryFormPage: React.FC = () => {
  const { id } = useParams();
  const isEdit = !!id;
  const [searchParams] = useSearchParams();
  const querySiteId = searchParams.get('siteId') || undefined;

  const [category, setCategory] = useState<CmsCategory | null>(null);
  const [loading, setLoading] = useState(false);
  const [sites, setSites] = useState<CmsSite[]>([]);
  const [parentOptions, setParentOptions] = useState<{ label: string; value: string }[]>([]);

  // 编辑模式：加载栏目
  useEffect(() => {
    if (isEdit && id) {
      setLoading(true);
      categoryApi
        .getDetail(id)
        .then((data) => setCategory(data))
        .catch(() => {})
        .finally(() => setLoading(false));
    }
  }, [id, isEdit]);

  // 加载站点选项
  useEffect(() => {
    siteApi
      .getList({ page: 1, pageSize: 100 })
      .then((res) => setSites(res.data || []))
      .catch(() => {});
  }, []);

  const currentSiteId = category?.siteId || querySiteId;

  // 当站点确定后，加载同站点的栏目作为父级选项
  useEffect(() => {
    if (!currentSiteId) {
      setParentOptions([]);
      return;
    }
    categoryApi
      .getTree({ siteId: currentSiteId })
      .then((tree) => {
        const options: { label: string; value: string }[] = [];
        const walk = (nodes: CmsCategoryTreeNode[], depth = 0) => {
          nodes.forEach((n) => {
            options.push({ label: `${'　'.repeat(depth)}${n.name}`, value: n.id });
            if (n.children?.length) walk(n.children, depth + 1);
          });
        };
        walk(tree);
        // 编辑时排除自身，避免把自己设为父级
        const filtered = isEdit ? options.filter((o) => o.value !== id) : options;
        setParentOptions(filtered);
      })
      .catch(() => setParentOptions([]));
  }, [currentSiteId, id, isEdit]);

  const { initialValues } = useFormInitialValues<CmsCategory>(category, {
    defaults: {
      siteId: querySiteId,
      status: 1,
      sortOrder: 0,
    } as unknown as Partial<CmsCategory>,
  });

  const { handleSubmit, submitting } = useFormSubmit<CmsCategory>(
    async (values) => {
      if (isEdit && id) {
        await categoryApi.update(id, values as any);
      } else {
        await categoryApi.create(values as any);
      }
    },
    {
      successMessage: isEdit ? '更新成功' : '创建成功',
      onSuccess: () => history.push('/cms/categories'),
    },
  );

  const siteDisabled = isEdit; // 编辑时不可改站点

  return (
    <FormPage
      title={isEdit ? '编辑栏目' : '新增栏目'}
      loading={loading}
      submitting={submitting}
      initialValues={initialValues}
      onFinish={handleSubmit}
      onCancel={() => history.back()}
      saveText={isEdit ? '保存' : '创建'}
    >
      <Card title="基础信息">
        <ProFormSelect
          name="siteId"
          label="所属站点"
          width="md"
          disabled={siteDisabled}
          rules={[{ required: true, message: '请选择所属站点' }]}
          options={sites.map((s) => ({ label: s.name, value: s.id }))}
        />
        <ProFormText
          name="name"
          label="栏目名称"
          width="md"
          rules={[{ required: true, message: '请输入栏目名称' }]}
        />
        <ProFormText
          name="slug"
          label="栏目标识"
          width="md"
          tooltip="站点内唯一，用于 URL 路径，建议英文/数字"
          rules={[
            { required: true, message: '请输入栏目标识' },
            { pattern: /^[a-zA-Z0-9_-]+$/, message: '仅支持英文、数字、下划线和连字符' },
          ]}
        />
        <ProFormSelect
          name="parentId"
          label="父级栏目"
          width="md"
          placeholder="不选则为顶级栏目"
          options={parentOptions}
          allowClear
        />
        <ProFormDigit name="sortOrder" label="排序" width="sm" min={0} fieldProps={{ precision: 0 }} />
        <ProFormText name="icon" label="栏目图标" width="md" placeholder="图标名称或地址" />
        <ProFormText name="description" label="栏目描述" width="lg" />
      </Card>
    </FormPage>
  );
};

export default CategoryFormPage;
