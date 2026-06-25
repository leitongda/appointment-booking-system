import { PageContainer, ProForm, ProFormText, ProFormTextArea, ProFormSelect, FooterToolbar } from '@ant-design/pro-components';
import type { ProFormInstance } from '@ant-design/pro-components';
import { Card, App, Button, Space, Modal } from 'antd';
import { history } from '@umijs/max';
import { messageApi } from '@hospital/api';
import { useState, useEffect, useCallback, useRef } from 'react';
import type { UnifiedTemplate, RecipientRule } from '@hospital/shared';
import { getStorage, STORAGE_KEYS } from '@hospital/shared';
import { useDict } from '@/hooks/useDict';

const SEND_MODE_OPTIONS = [
  { label: '单发', value: 'single' },
  { label: '批量（用户ID列表）', value: 'batch' },
  { label: '按规则发送', value: 'rule' },
];

async function batchExecute<T>(items: T[], fn: (item: T) => Promise<any>, batchSize = 10) {
  for (let i = 0; i < items.length; i += batchSize) {
    await Promise.all(items.slice(i, i + batchSize).map(fn));
  }
}

const MessageFormPage: React.FC = () => {
  const { message } = App.useApp();
  const { options: messageTypeOptions } = useDict('message_type');
  const [sendMode, setSendMode] = useState<'single' | 'batch' | 'rule'>('single');
  const [templates, setTemplates] = useState<UnifiedTemplate[]>([]);
  const [recipientRules, setRecipientRules] = useState<RecipientRule[]>([]);
  const [previewVisible, setPreviewVisible] = useState(false);
  const [previewData, setPreviewData] = useState<{ title: string; content: string }>({ title: '', content: '' });
  const formRef = useRef<ProFormInstance>(null);

  useEffect(() => {
    messageApi.getUnifiedTemplates({ status: 1, page: 1, pageSize: 100 }).then((res) => {
      setTemplates(Array.isArray(res) ? res : []);
    }).catch(() => {});
    messageApi.getRecipientRules().then((res) => {
      setRecipientRules(Array.isArray(res) ? res : []);
    }).catch(() => {});
  }, []);

  const handleTemplateChange = useCallback((templateId: string) => {
    if (!formRef.current || !templateId) return;
    const tpl = templates.find((t) => t.id === templateId);
    if (tpl) {
      formRef.current.setFieldsValue({
        title: tpl.subjectTemplate || '',
        content: tpl.textTemplate || '',
        messageType: tpl.messageType,
      });
    }
  }, [formRef, templates]);

  const handlePreview = useCallback(() => {
    if (!formRef.current) return;
    const values = formRef.current.getFieldsValue();
    setPreviewData({ title: values.title || '', content: values.content || '' });
    setPreviewVisible(true);
  }, [formRef]);

  const handleSubmit = async (values: any) => {
    try {
      const tenantId = getStorage<string>(STORAGE_KEYS.CURRENT_TENANT_ID) || '';
      const baseParams = {
        tenantId,
        recipientType: values.userType,
        title: values.title,
        content: values.content,
        messageType: values.messageType,
        templateCode: 'manual',
      };

      if (sendMode === 'rule') {
        const result = await messageApi.sendBatchByRule(values.ruleId, {
          ...baseParams,
        });
        message.success(`按规则发送完成，${(result as any)?.message || ''}`);
      } else if (sendMode === 'batch') {
        const userIds = (values.userId as string).split('\n').map((s: string) => s.trim()).filter(Boolean);
        await batchExecute(userIds, (id: string) =>
          messageApi.sendUnified({ ...baseParams, recipientId: id })
        );
        message.success(`批量发送成功，共 ${userIds.length} 人`);
      } else {
        await messageApi.sendUnified({
          ...baseParams,
          recipientId: values.userId,
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
        formRef={formRef}
        onFinish={handleSubmit}
        initialValues={{ userType: 'patient', messageType: 'system' }}
        submitter={{
          render: (props, _dom) => (
            <FooterToolbar>
              <Space>
                <Button onClick={() => history.back()}>取消</Button>
                <Button onClick={handlePreview}>预览</Button>
                <Button type="primary" onClick={() => props.form?.submit()}>
                  {sendMode === 'batch' ? '批量发送' : sendMode === 'rule' ? '按规则发送' : '发送'}
                </Button>
              </Space>
            </FooterToolbar>
          ),
        }}
      >
        <Card title="消息信息">
          <ProFormSelect
            name="sendMode"
            label="发送方式"
            width="md"
            options={SEND_MODE_OPTIONS}
            initialValue="single"
            fieldProps={{
              onChange: (val) => setSendMode(val as 'single' | 'batch' | 'rule'),
            }}
          />
          <ProForm.Group>
            {sendMode === 'single' && (
              <ProFormText
                name="userId"
                label="用户ID"
                width="md"
                rules={[{ required: true, message: '请输入用户ID' }]}
              />
            )}
            {sendMode === 'batch' && (
              <ProFormTextArea
                name="userId"
                label="用户ID列表"
                placeholder="每行一个用户ID"
                rules={[{ required: true, message: '请输入用户ID' }]}
                fieldProps={{ rows: 4 }}
                width="xl"
              />
            )}
            {sendMode === 'rule' && (
              <ProFormSelect
                name="ruleId"
                label="收件人规则"
                width="lg"
                options={recipientRules.map((r: any) => ({
                  label: `${r.name}（${r.eventType || r.event_type || ''}）`,
                  value: r.id,
                }))}
                rules={[{ required: true, message: '请选择收件人规则' }]}
                placeholder="选择规则后将按规则匹配收件人"
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
              hidden={sendMode === 'rule'}
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
            options={messageTypeOptions}
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
