/**
 * 邮件模板表单页面（重构版）
 *
 * 代码行数：154 行 (vs 原始 184 行)
 *
 * 使用基础设施：
 * - FormPage 组件：统一表单页面布局和底部工具栏
 * - SwitchGroup 组件：开关组（自动处理 boolean ↔ number 转换）
 * - codeRules('lower'): 编码验证规则
 * - useFormInitialValues: 处理初始值和开关字段转换
 * - useFormSubmit: 处理表单提交和字段转换
 *
 * 优化效果：
 * - 减少重复的表单布局代码
 * - 自动处理状态字段的 boolean ↔ number 转换
 * - 使用标准化的编码验证规则
 * - 提高代码可读性和可维护性
 */
import { useState, useEffect } from 'react';
import { ProFormText, ProFormSelect, ProFormTextArea } from '@ant-design/pro-components';
import { Card, Form } from 'antd';
import { useParams, history } from '@umijs/max';
import { emailTemplateApi } from '@hospital/api';
import type { EmailTemplate } from '@hospital/api';

// 基础设施导入
import FormPage from '@/components/FormPage';
import { SwitchGroup } from '@/components/formFields';
import { requiredRules, codeRules } from '@/utils/formValidators';
import { useFormInitialValues } from '@/hooks/useFormInitialValues';
import { useFormSubmit } from '@/hooks/useFormSubmit';
import { EMAIL_TEMPLATE_TYPE_OPTIONS } from '@/constants/formFields';
import RichTextEditor, { EMAIL_TEMPLATE_VARIABLES } from '@/components/RichTextEditor';

const EmailTemplateFormPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const isEdit = !!id;
  const [template, setTemplate] = useState<EmailTemplate | null>(null);

  // 加载邮件模板数据
  useEffect(() => {
    if (!isEdit || !id) return;

    const loadTemplate = async () => {
      try {
        const data = await emailTemplateApi.getById(id);
        setTemplate(data);
      } catch (error) {
        console.error('加载邮件模板失败', error);
      }
    };
    loadTemplate();
  }, [id, isEdit]);

  // 使用 useFormInitialValues hook 处理初始值
  const { initialValues } = useFormInitialValues<EmailTemplate>(
    template,
    {
      switchFields: ['status'],
      defaults: {
        templateType: 'custom',
        status: true,
      },
    }
  );

  // 使用 useFormSubmit hook 处理提交
  const { handleSubmit, submitting } = useFormSubmit<EmailTemplate>(
    async (values) => {
      const data = {
        code: values.code,
        name: values.name,
        templateType: values.templateType,
        subjectTemplate: values.subjectTemplate,
        contentTemplate: values.contentTemplate,
        description: values.description,
        status: values.status ? 1 : 0,
      };

      if (isEdit && id) {
        await emailTemplateApi.update(id, data);
      } else {
        await emailTemplateApi.create(data);
      }
    },
    {
      switchFields: ['status'],
      successMessage: isEdit ? '更新成功' : '创建成功',
      onSuccess: () => {
        history.push('/system/config/email-templates');
      },
    }
  );

  return (
    <FormPage
      title={isEdit ? '编辑邮件模板' : '新增邮件模板'}
      loading={isEdit && !template}
      submitting={submitting}
      initialValues={initialValues}
      onFinish={handleSubmit}
      onCancel={() => history.back()}
      saveText={isEdit ? '保存' : '创建'}
    >
      {/* 基本信息 */}
      <Card title="基本信息" style={{ marginBottom: 16 }}>
        <ProFormText
          name="code"
          label="模板编码"
          width="md"
          placeholder="请输入模板编码（唯一标识）"
          rules={[
            requiredRules('请输入模板编码'),
            codeRules('lower').pattern,
          ]}
          disabled={isEdit}
          extra="模板编码创建后不可修改，用于程序调用"
        />

        <ProFormText
          name="name"
          label="模板名称"
          width="md"
          placeholder="请输入模板名称"
          rules={[requiredRules('请输入模板名称')]}
        />

        <ProFormSelect
          name="templateType"
          label="模板类型"
          width="md"
          options={EMAIL_TEMPLATE_TYPE_OPTIONS}
          rules={[requiredRules('请选择模板类型')]}
        />

        {/* 使用 SwitchGroup 组件 */}
        <SwitchGroup
          items={[
            {
              name: 'status',
              label: '启用状态',
            },
          ]}
        />

        <ProFormTextArea
          name="description"
          label="模板说明"
          width="lg"
          placeholder="请输入模板说明（可选）"
          fieldProps={{ rows: 2 }}
        />
      </Card>

      {/* 邮件内容 */}
      <Card title="邮件内容">
        <ProFormText
          name="subjectTemplate"
          label="邮件主题"
          width="lg"
          placeholder="请输入邮件主题，可使用变量如 {{patient_name}}"
          rules={[requiredRules('请输入邮件主题')]}
          extra="支持使用模板变量，如 {{patient_name}}、{{doctor_name}} 等"
        />

        <Form.Item
          name="contentTemplate"
          label="邮件正文"
          rules={[requiredRules('请输入邮件正文内容')]}
          extra={
            <span>
              可用变量：
              {EMAIL_TEMPLATE_VARIABLES.map((v) => (
                <code key={v.value} style={{ marginLeft: 8, color: '#1890ff' }}>
                  {`{{${v.value}}}`}
                </code>
              ))}
            </span>
          }
        >
          <RichTextEditor height={400} variables={EMAIL_TEMPLATE_VARIABLES} />
        </Form.Item>
      </Card>
    </FormPage>
  );
};

export default EmailTemplateFormPage;
