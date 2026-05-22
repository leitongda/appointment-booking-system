/**
 * 轮播图表单页面
 *
 * 链接类型和展示位置通过 useDict 从字典 API 获取
 */
import { ProFormText, ProFormDigit, ProFormSelect } from '@ant-design/pro-components';
import { Card } from 'antd';
import { useEffect, useState, useMemo } from 'react';
import { useParams, history } from '@umijs/max';
import { contentApi } from '@hospital/api';
import type { Banner } from '@hospital/api';

// 基础设施导入
import FormPage from '@/components/FormPage';
import { ImageUploadCard, SwitchGroup } from '@/components/formFields';
import { useDict } from '@/hooks/useDict';
import { useFormInitialValues } from '@/hooks/useFormInitialValues';
import { useFormSubmit } from '@/hooks/useFormSubmit';

const BannerFormPage: React.FC = () => {
  const { id } = useParams();
  const isEdit = !!id;
  const [banner, setBanner] = useState<Banner | null>(null);
  const [loading, setLoading] = useState(false);

  // 字典数据
  const { options: linkTypeDict } = useDict('banner_link_type');
  const { options: positionDict } = useDict('banner_position');
  const linkTypeOptions = useMemo(() => linkTypeDict.map(o => ({ label: o.label, value: Number(o.value) })), [linkTypeDict]);
  const positionOptions = useMemo(() => positionDict.map(o => ({ label: o.label, value: o.value })), [positionDict]);

  // 加载轮播图数据
  useEffect(() => {
    if (isEdit && id) {
      setLoading(true);
      (contentApi as any)
        .getBannerDetail(id)
        .then((data: Banner) => {
          setBanner(data);
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
  const { initialValues } = useFormInitialValues<Banner>(
    banner,
    {
      switchFields: ['status'],
      defaults: {
        linkType: 0,
        position: 'home',
        sortOrder: 0,
        status: true,
      } as unknown as Partial<Banner>,
    }
  );

  // 使用 useFormSubmit hook 处理提交
  const { handleSubmit, submitting } = useFormSubmit<Banner>(
    async (values) => {
      if (isEdit && id) {
        await contentApi.updateBanner(id, values);
      } else {
        await contentApi.createBanner(values);
      }
    },
    {
      switchFields: ['status'],
      successMessage: isEdit ? '更新成功' : '创建成功',
      onSuccess: () => {
        history.push('/content-center/content/banner');
      },
    }
  );

  return (
    <FormPage
      title={isEdit ? '编辑轮播图' : '新增轮播图'}
      loading={loading}
      submitting={submitting}
      initialValues={initialValues}
      onFinish={handleSubmit}
      onCancel={() => history.back()}
      saveText={isEdit ? '保存' : '创建'}
    >
      {/* 轮播图信息 */}
      <ImageUploadCard
        title="轮播图"
        name="imageUrl"
        aspectRatio="16:9"
        width={320}
        height={180}
        folder="banner"
        placeholder="上传轮播图"
        required
        requiredMessage="请上传轮播图片"
      />

      {/* 链接设置 */}
      <Card title="链接设置" style={{ marginBottom: 16 }}>
        <ProFormSelect
          name="linkType"
          label="链接类型"
          width="md"
          options={linkTypeOptions}
        />
        <ProFormSelect
          name="position"
          label="展示位置"
          width="md"
          options={positionOptions}
        />
        <ProFormText
          name="linkUrl"
          label="链接地址"
          width="lg"
          placeholder="请输入链接地址"
        />
      </Card>

      {/* 其他设置 */}
      <Card title="其他设置">
        <ProFormDigit
          name="sortOrder"
          label="排序"
          width="sm"
          min={0}
        />
        <SwitchGroup
          gutter={16}
          items={[
            { name: 'status', label: '启用状态' },
          ]}
        />
      </Card>
    </FormPage>
  );
};

export default BannerFormPage;
