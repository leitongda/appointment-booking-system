import {
  PageContainer,
  ProForm,
  ProFormText,
  ProFormTextArea,
  ProFormSelect,
  ProFormSwitch,
} from '@ant-design/pro-components';
import { Card, App, Row, Col, Form, Spin } from 'antd';
import { useEffect, useState } from 'react';
import { history, useParams } from '@umijs/max';
import { emailTemplateApi, EMAIL_TEMPLATE_TYPE_OPTIONS } from '@hospital/api';
import type { EmailTemplate } from '@hospital/api';
import RichTextEditor, { EMAIL_TEMPLATE_VARIABLES } from '@/components/RichTextEditor';

const EmailTemplateFormPage: React.FC = () => {
  const { message } = App.useApp();
  const { id } = useParams<{ id: string }>();
  const isEdit = !!id;
  const [loading, setLoading] = useState(false);
  const [template, setTemplate] = useState<EmailTemplate | null>(null);

  useEffect(() => {
    if (isEdit) {
      loadTemplate();
    }
  }, [id]);

  const loadTemplate = async () => {
    if (!id) return;
    setLoading(true);
    try {
      const data = await emailTemplateApi.getById(id);
      setTemplate(data);
    } catch (error: any) {
      message.error('加载邮件模板失败');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (values: any) => {
    try {
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
        message.success('更新成功');
      } else {
        await emailTemplateApi.create(data);
        message.success('创建成功');
      }
      history.push('/system/email-templates');
    } catch (error: any) {
      message.error(error.message || '操作失败');
    }
  };

  const initialValues = template
    ? {
        ...template,
        status: template.status === 1,
      }
    : {
        templateType: 'custom',
        status: true,
      };

  return (
    <PageContainer title={isEdit ? '编辑邮件模板' : '新增邮件模板'}>
      <Spin spinning={loading}>
        <ProForm
          onFinish={handleSubmit}
          initialValues={initialValues}
          submitter={{
            searchConfig: { submitText: isEdit ? '保存' : '创建' },
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
          <Card title="基本信息" style={{ marginBottom: 16 }}>
            <Row gutter={24}>
              <Col span={12}>
                <ProFormText
                  name="code"
                  label="模板编码"
                  placeholder="请输入模板编码（唯一标识）"
                  rules={[
                    { required: true, message: '请输入模板编码' },
                    { pattern: /^[a-zA-Z0-9_]+$/, message: '只能包含字母、数字和下划线' },
                  ]}
                  disabled={isEdit}
                  extra="模板编码创建后不可修改，用于程序调用"
                />
              </Col>
              <Col span={12}>
                <ProFormText
                  name="name"
                  label="模板名称"
                  placeholder="请输入模板名称"
                  rules={[{ required: true, message: '请输入模板名称' }]}
                />
              </Col>
            </Row>
            <Row gutter={24}>
              <Col span={12}>
                <ProFormSelect
                  name="templateType"
                  label="模板类型"
                  options={EMAIL_TEMPLATE_TYPE_OPTIONS}
                  rules={[{ required: true, message: '请选择模板类型' }]}
                />
              </Col>
              <Col span={12}>
                <ProFormSwitch name="status" label="启用状态" />
              </Col>
            </Row>
            <ProFormTextArea
              name="description"
              label="模板说明"
              placeholder="请输入模板说明（可选）"
              fieldProps={{ rows: 2 }}
            />
          </Card>

          <Card title="邮件内容" style={{ marginBottom: 16 }}>
            <ProFormText
              name="subjectTemplate"
              label="邮件主题"
              placeholder="请输入邮件主题，可使用变量如 {{patient_name}}"
              rules={[{ required: true, message: '请输入邮件主题' }]}
              extra="支持使用模板变量，如 {{patient_name}}、{{doctor_name}} 等"
            />

            <Form.Item
              name="contentTemplate"
              label="邮件正文"
              rules={[{ required: true, message: '请输入邮件正文内容' }]}
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
        </ProForm>
      </Spin>
    </PageContainer>
  );
};

export default EmailTemplateFormPage;

