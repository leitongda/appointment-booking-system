import { PageContainer, ProForm, ProFormText, ProFormTextArea, ProFormSelect, ProFormSwitch, FooterToolbar } from '@ant-design/pro-components';
import { Card, App, Button, Space, Modal } from 'antd';
import { history } from '@umijs/max';
import { messageApi } from '@hospital/api';
import { useState, useEffect, useCallback } from 'react';
import type { UnifiedTemplate } from '@hospital/shared';

const TYPE_OPTIONS = [
  { label: '系统', value: 'system' },
  { label: '预约', value: 'appointment' },
  { label: '就诊', value: 'consultation' },
  { label: '排班', value: 'schedule' },
  { label: '停诊', value: 'stop_clinic' },
  { label: '反馈', value: 'feedback' },
];

const MessageFormPage: React.FC = () => {
  const { message } = App.useApp();
  const [isBatch, setIsBatch] = useState(false);
  const [templates, setTemplates] = useState<UnifiedTemplate[]>([]);
  const [previewVisible, setPreviewVisible] = useState(false);
  const [previewData, setPreviewData] = useState<{ title: string; content: string }>({ title: '', content: '' });
  const [formRef, setFormRef] = useState<any>(null);

  useEffect(() => {
    messageApi.getUnifiedTemplates({ status: 1, page: 1, pageSize: 100 }).then((res) => {
      setTemplates(res?.items || res?.data || []);
    }).catch(() => {});
  }, []);

  const handleTemplateChange = useCallback((templateId: string) => {
    if (!formRef || !templateId) return;
    const tpl = templates.find((t) => t.id === templateId);
    if (tpl) {
      formRef.setFieldsValue({
        title: tpl.subjectTemplate || '',
        content: tpl.textTemplate || '',
        messageType: tpl.messageType,
      });
    }
  }, [formRef, templates]);

  const handlePreview = useCallback(() => {
    if (!formRef) return;
    const values = formRef.getFieldsValue();
    setPreviewData({ title: values.title || '', content: values.content || '' });
    setPreviewVisible(true);
  }, [formRef]);

  const handleSubmit = async (values: any) => {
    try {
      if (isBatch) {
        const userIds = (values.userId as string).split('\n').map((s: string) => s.trim()).filter(Boolean);
        await messageApi.sendBatch({
          userIds,
          userType: values.userType,
          title: values.title,
          content: values.content,
          messageType: values.messageType,
        });
        message.success(`批量发送成功，共 ${userIds.length} 人`);
      } else {
        await messageApi.send({
          userId: values.userId,
          userType: values.userType,
          title: values.title,
          content: values.content,
          messageType: values.messageType,
        });
        message.success('发送成功');
      }
      history.push('/content-center/message');
    } catch (error: any) {
      message.error(error.message || '发送失败');
    }
  };

  const templateOptions = templates.map((t) => ({
    label: `${t.name} (${t.code})`,
    value: t.id,
  }));

  return (
    <PageContainer title="发送消息">
      <ProForm
        formRef={(ref) => setFormRef(ref)}
        onFinish={handleSubmit}
        initialValues={{ userType: 'patient', messageType: 'system' }}
        submitter={{
          render: (props, _dom) => (
            <FooterToolbar>
              <Space>
                <Button onClick={() => history.back()}>取消</Button>
                <Button onClick={handlePreview}>预览</Button>
                <Button type="primary" onClick={() => props.form?.submit()}>
                  {isBatch ? '批量发送' : '发送'}
                </Button>
              </Space>
            </FooterToolbar>
          ),
        }}
      >
        <Card title="消息信息">
          <ProFormSwitch
            name="isBatch"
            label="批量发送"
            fieldProps={{
              onChange: (checked) => setIsBatch(checked),
            }}
          />
          <ProForm.Group>
            {isBatch ? (
              <ProFormTextArea
                name="userId"
                label="用户ID列表"
                placeholder="每行一个用户ID"
                rules={[{ required: true, message: '请输入用户ID' }]}
                fieldProps={{ rows: 4 }}
                width="xl"
              />
            ) : (
              <ProFormText
                name="userId"
                label="用户ID"
                width="md"
                rules={[{ required: true, message: '请输入用户ID' }]}
              />
            )}
            <ProFormSelect
              name="userType"
              label="用户类型"
              width="md"
              options={[
                { label: '患者', value: 'patient' },
                { label: '医生', value: 'doctor' },
              ]}
              rules={[{ required: true, message: '请选择用户类型' }]}
            />
          </ProForm.Group>
          <ProFormSelect
            name="templateId"
            label="选择模板（可选）"
            width="lg"
            options={templateOptions}
            placeholder="选择模板自动填充标题和内容"
            fieldProps={{
              allowClear: true,
              showSearch: true,
              filterOption: (input, option) =>
                (option?.label as string)?.toLowerCase().includes(input.toLowerCase()),
              onChange: handleTemplateChange,
            }}
          />
          <ProFormSelect
            name="messageType"
            label="消息类型"
            width="md"
            options={TYPE_OPTIONS}
          />
          <ProFormText
            name="title"
            label="标题"
            width="lg"
            rules={[{ required: true, message: '请输入标题' }]}
          />
          <ProFormTextArea
            name="content"
            label="内容"
            placeholder="请输入消息内容"
            fieldProps={{ rows: 6 }}
          />
        </Card>
      </ProForm>

      <Modal
        title="消息预览"
        open={previewVisible}
        onCancel={() => setPreviewVisible(false)}
        footer={<Button onClick={() => setPreviewVisible(false)}>关闭</Button>}
      >
        <p><strong>标题：</strong>{previewData.title || '（空）'}</p>
        <p><strong>内容：</strong></p>
        <div style={{ whiteSpace: 'pre-wrap', background: '#f5f5f5', padding: 12, borderRadius: 4 }}>
          {previewData.content || '（空）'}
        </div>
      </Modal>
    </PageContainer>
  );
};

export default MessageFormPage;
