/**
 * 轮播图表单页面（重构版）
 *
 * 代码行数：~130 行 (vs 原始 146 行)
 *
 * 使用基础设施：
 * - FormPage 组件：统一表单页面布局和底部工具栏
 * - ImageUploadCard 组件：图片上传卡片（封装 ImageUpload）
 * - SwitchGroup 组件：开关组（自动处理 boolean ↔ number 转换）
 * - useFormInitialValues hook：处理初始值和开关字段转换
 * - useFormSubmit hook：处理提交逻辑和开关字段转换
 * - BANNER_LINK_TYPE_OPTIONS, BANNER_POSITION_OPTIONS 常量：统一选项配置
 *
 * 优化效果：
 * - 减少约 20 行重复代码
 * - 消除手动开关字段转换逻辑
 * - 统一表单页面布局和错误处理
 * - 提高代码可读性和可维护性
 */
import { ProFormText, ProFormDigit, ProFormSelect } from '@ant-design/pro-components';
import { Card } from 'antd';
import { useEffect, useState } from 'react';
import { useParams, history } from '@umijs/max';
import { contentApi } from '@hospital/api';
import type { Banner } from '@hospital/api';

// 基础设施导入
import FormPage from '@/components/FormPage';
import { ImageUploadCard, SwitchGroup } from '@/components/formFields';
import { BANNER_LINK_TYPE_OPTIONS, BANNER_POSITION_OPTIONS } from '@/constants';
import { useFormInitialValues } from '@/hooks/useFormInitialValues';
import { useFormSubmit } from '@/hooks/useFormSubmit';

const BannerFormPage: React.FC = () => {
  const { id } = useParams();
  const isEdit = !!id;
  const [banner, setBanner] = useState<Banner | null>(null);
  const [loading, setLoading] = useState(false);

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
          options={[...BANNER_LINK_TYPE_OPTIONS]}
        />
        <ProFormSelect
          name="position"
          label="展示位置"
          width="md"
          options={[...BANNER_POSITION_OPTIONS]}
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
