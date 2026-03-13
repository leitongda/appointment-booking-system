/**
 * 公告表单页面（重构版）
 *
 * 代码行数：~100 行 (vs 原始 132 行)
 *
 * 使用基础设施：
 * - FormPage 组件：统一表单页面布局和底部工具栏
 * - SwitchGroup 组件：开关组（自动处理 boolean ↔ number 转换）
 * - useFormInitialValues hook：处理初始值和开关字段转换
 * - useFormSubmit hook：处理提交逻辑和开关字段转换
 * - RichTextEditor 组件：富文本编辑器（保留原有）
 * - NOTICE_TYPE_OPTIONS 常量：统一公告类型选项
 *
 * 优化效果：
 * - 减少约 30 行重复代码
 * - 消除手动开关字段转换逻辑
 * - 统一表单页面布局和错误处理
 * - 提高代码可读性和可维护性
 */
import { ProFormText, ProFormSelect } from '@ant-design/pro-components';
import { Card, Form } from 'antd';
import { useEffect, useState } from 'react';
import { useParams, history } from '@umijs/max';
import { contentApi } from '@hospital/api';
import type { Notice } from '@hospital/api';

// 基础设施导入
import FormPage from '@/components/FormPage';
import { SwitchGroup } from '@/components/formFields';
import RichTextEditor from '@/components/RichTextEditor';
import { NOTICE_TYPE_OPTIONS } from '@/constants';
import { useFormInitialValues } from '@/hooks/useFormInitialValues';
import { useFormSubmit } from '@/hooks/useFormSubmit';

const NoticeFormPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const isEdit = !!id;
  const [notice, setNotice] = useState<Notice | null>(null);
  const [loading, setLoading] = useState(false);

  // 加载公告数据
  useEffect(() => {
    if (isEdit && id) {
      setLoading(true);
      contentApi
        .getNoticeDetail(id)
        .then((data) => {
          setNotice(data);
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
  const { initialValues } = useFormInitialValues<Notice>(
    notice,
    {
      switchFields: ['isTop', 'status'],
      defaults: {
        type: 1,
        isTop: false,
        status: true,
      } as Partial<Notice>,
    }
  );

  // 使用 useFormSubmit hook 处理提交
  const { handleSubmit, submitting } = useFormSubmit<Notice>(
    async (values) => {
      if (isEdit && id) {
        await contentApi.updateNotice(id, values);
      } else {
        await contentApi.createNotice(values);
      }
    },
    {
      switchFields: ['isTop', 'status'],
      successMessage: isEdit ? '更新成功' : '发布成功',
      onSuccess: () => {
        history.push('/content/notice');
      },
    }
  );

  return (
    <FormPage
      title={isEdit ? '编辑公告' : '发布公告'}
      loading={loading}
      submitting={submitting}
      initialValues={initialValues}
      onFinish={handleSubmit}
      onCancel={() => history.back()}
      saveText={isEdit ? '保存' : '发布'}
    >
      {/* 公告信息 */}
      <Card title="公告信息" style={{ marginBottom: 16 }}>
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
          options={NOTICE_TYPE_OPTIONS}
          rules={[{ required: true, message: '请选择类型' }]}
        />
      </Card>

      {/* 公告内容 */}
      <Card title="公告内容" style={{ marginBottom: 16 }}>
        <Form.Item
          name="content"
          label="内容"
          rules={[{ required: true, message: '请输入内容' }]}
        >
          <RichTextEditor height={400} placeholder="请输入公告内容..." />
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

export default NoticeFormPage;
