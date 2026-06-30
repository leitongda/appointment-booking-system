import { CopyOutlined, EyeOutlined, SendOutlined } from '@ant-design/icons';
import type { ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable, ModalForm, ProFormText, ProFormTextArea, ProFormSelect } from '@ant-design/pro-components';
import { Tag, Switch, Button, Modal, Descriptions, Input } from 'antd';
import { useState, useMemo } from 'react';
import { messageApi } from '@hospital/api';
import { createListRequest } from '@/utils/proTable';
import { useListPage } from '@/hooks/useListPage';
import { OperationGroup, OperationButton, CreateButton } from '@/components/ListOperations';
import { useDict } from '@/hooks/useDict';
import type { MessageType, UnifiedTemplate } from '@hospital/shared';

const MESSAGE_TYPES: readonly MessageType[] = [
  'appointment',
  'consultation',
  'schedule',
  'system',
  'stop_clinic',
  'feedback',
];

const toMessageType = (value?: string): MessageType => (
  value && MESSAGE_TYPES.includes(value as MessageType) ? value as MessageType : 'system'
);

const UnifiedTemplatesPage: React.FC = () => {
  const { actionRef, message, access } = useListPage();
  const { options: messageTypeOptions } = useDict('message_type');
  const messageTypeEnum = useMemo(
    () => Object.fromEntries(messageTypeOptions.map((o) => [o.value, { text: o.label }])),
    [messageTypeOptions],
  );
  const [modalVisible, setModalVisible] = useState(false);
  const [currentTemplate, setCurrentTemplate] = useState<UnifiedTemplate | null>(null);
  const [previewVisible, setPreviewVisible] = useState(false);
  const [previewTemplate, setPreviewTemplate] = useState<UnifiedTemplate | null>(null);
  const [testSendVisible, setTestSendVisible] = useState(false);
  const [testSendTemplateId, setTestSendTemplateId] = useState<string | null>(null);
  const [testUserId, setTestUserId] = useState('');
  const [testSending, setTestSending] = useState(false);

  const handleDelete = async (id: string) => {
    try {
      await messageApi.deleteUnifiedTemplate(id);
      message.success('删除成功');
      actionRef.current?.reload();
    } catch (error: any) {
      message.error(error.message || '删除失败');
    }
  };

  const handleStatusChange = async (id: string, status: boolean) => {
    try {
      await messageApi.updateUnifiedTemplate(id, { status: status ? 1 : 0 });
      message.success('状态更新成功');
      actionRef.current?.reload();
    } catch (error: any) {
      message.error(error.message || '状态更新失败');
    }
  };

  const handleSubmit = async (values: any) => {
    try {
      if (currentTemplate) {
        await messageApi.updateUnifiedTemplate(currentTemplate.id, values);
        message.success('更新成功');
      } else {
        await messageApi.createUnifiedTemplate(values);
        message.success('创建成功');
      }
      setModalVisible(false);
      setCurrentTemplate(null);
      actionRef.current?.reload();
      return true;
    } catch (error: any) {
      message.error(error.message || '操作失败');
      return false;
    }
  };

  const handleClone = (record: UnifiedTemplate) => {
    setCurrentTemplate({ ...record, id: '', code: `${record.code}_copy`, name: `${record.name} (副本)` } as any);
    setModalVisible(true);
  };

  const handleTestSend = async () => {
    if (!testSendTemplateId || !testUserId) {
      message.warning('请输入测试用户ID');
      return;
    }
    setTestSending(true);
    try {
      const tpl = previewTemplate;
      await messageApi.send({
        userId: testUserId,
        userType: 'patient',
        title: tpl?.subjectTemplate || `测试: ${tpl?.name}`,
        content: tpl?.textTemplate || '',
        messageType: toMessageType(tpl?.messageType),
      });
      message.success('测试发送成功');
      setTestSendVisible(false);
      setTestUserId('');
    } catch (error: any) {
      message.error(error.message || '测试发送失败');
    } finally {
      setTestSending(false);
    }
  };

  const columns: ProColumns<UnifiedTemplate>[] = [
    {
      title: '模板编码',
      dataIndex: 'code',
      width: 150,
      ellipsis: true,
    },
    {
      title: '模板名称',
      dataIndex: 'name',
      width: 150,
      ellipsis: true,
    },
    {
      title: '消息类型',
      dataIndex: 'messageType',
      width: 100,
      valueEnum: messageTypeEnum,
      render: (_, record) => {
        const option = messageTypeOptions.find(o => o.value === record.messageType);
        return <Tag color="blue">{option?.label || record.messageType}</Tag>;
      },
    },
    {
      title: '主题模板',
      dataIndex: 'subjectTemplate',
      width: 200,
      ellipsis: true,
      search: false,
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 100,
      valueEnum: {
        1: { text: '启用', status: 'Success' },
        0: { text: '禁用', status: 'Default' },
      },
      render: (_, record) => (
        <Switch
          checked={record.status === 1}
          checkedChildren="启用"
          unCheckedChildren="禁用"
          onChange={(checked) => handleStatusChange(record.id, checked)}
          disabled={!access.hasPermission('message:send')}
        />
      ),
    },
    {
      title: '创建时间',
      dataIndex: 'createdAt',
      valueType: 'dateTime',
      width: 180,
      search: false,
    },
    {
      title: '操作',
      valueType: 'option',
      width: 220,
      render: (_, record) => (
        <OperationGroup>
          <OperationButton
            type="custom"
            icon={<EyeOutlined />}
            label="预览"
            onClick={() => {
              setPreviewTemplate(record);
              setPreviewVisible(true);
            }}
          />
          <OperationButton
            type="edit"
            permission="message:send"
            onClick={() => {
              setCurrentTemplate(record);
              setModalVisible(true);
            }}
          />
          <OperationButton
            type="custom"
            icon={<CopyOutlined />}
            permission="message:send"
            label="克隆"
            onClick={() => handleClone(record)}
          />
          <OperationButton
            type="delete"
            permission="message:delete"
            confirmText="确认删除此模板？"
            onClick={() => handleDelete(record.id)}
          />
        </OperationGroup>
      ),
    },
  ];

  return (
    <PageContainer>
      <ProTable<UnifiedTemplate>
        headerTitle="统一模板管理"
        actionRef={actionRef}
        rowKey="id"
        search={{
          labelWidth: 'auto',
        }}
        toolBarRender={() => [
          <CreateButton
            key="create"
            permission="message:send"
            label="新建模板"
            onClick={() => {
              setCurrentTemplate(null);
              setModalVisible(true);
            }}
          />,
        ]}
        request={createListRequest(messageApi.getUnifiedTemplates)}
        columns={columns}
        pagination={{
          defaultPageSize: 10,
          showSizeChanger: true,
        }}
      />

      <ModalForm
        title={currentTemplate?.id ? '编辑模板' : currentTemplate?.code?.endsWith('_copy') ? '克隆模板' : '新建模板'}
        open={modalVisible}
        onOpenChange={(visible) => {
          setModalVisible(visible);
          if (!visible) {
            setCurrentTemplate(null);
          }
        }}
        initialValues={currentTemplate || {}}
        onFinish={handleSubmit}
        modalProps={{
          destroyOnClose: true,
        }}
      >
        <ProFormText
          name="code"
          label="模板编码"
          placeholder="请输入模板编码"
          rules={[{ required: true, message: '请输入模板编码' }]}
          disabled={!!currentTemplate?.id}
        />
        <ProFormText
          name="name"
          label="模板名称"
          placeholder="请输入模板名称"
          rules={[{ required: true, message: '请输入模板名称' }]}
        />
        <ProFormSelect
          name="messageType"
          label="消息类型"
          options={messageTypeOptions}
          rules={[{ required: true, message: '请选择消息类型' }]}
        />
        <ProFormText
          name="eventType"
          label="事件类型"
          placeholder="请输入事件类型（可选）"
        />
        <ProFormText
          name="subjectTemplate"
          label="主题模板"
          placeholder="请输入主题模板"
        />
        <ProFormTextArea
          name="textTemplate"
          label="文本模板"
          placeholder="请输入文本模板内容"
          fieldProps={{ rows: 4 }}
        />
        <ProFormTextArea
          name="htmlTemplate"
          label="HTML模板"
          placeholder="请输入HTML模板内容（可选）"
          fieldProps={{ rows: 4 }}
        />
        <ProFormText
          name="wechatTemplateId"
          label="微信模板ID"
          placeholder="请输入微信模板ID（可选）"
        />
      </ModalForm>

      {/* 模板预览 Modal */}
      <Modal
        title="模板预览"
        open={previewVisible}
        onCancel={() => setPreviewVisible(false)}
        footer={[
          <Button key="close" onClick={() => setPreviewVisible(false)}>关闭</Button>,
          <Button
            key="test"
            type="primary"
            icon={<SendOutlined />}
            onClick={() => {
              setTestSendTemplateId(previewTemplate?.id || null);
              setPreviewVisible(false);
              setTestSendVisible(true);
            }}
            disabled={!access.hasPermission('message:send')}
          >
            测试发送
          </Button>,
        ]}
        width={600}
      >
        {previewTemplate && (
          <Descriptions column={1} bordered size="small">
            <Descriptions.Item label="模板编码">{previewTemplate.code}</Descriptions.Item>
            <Descriptions.Item label="模板名称">{previewTemplate.name}</Descriptions.Item>
            <Descriptions.Item label="消息类型">
              {messageTypeOptions.find(o => o.value === previewTemplate.messageType)?.label || previewTemplate.messageType}
            </Descriptions.Item>
            <Descriptions.Item label="事件类型">{previewTemplate.eventType || '-'}</Descriptions.Item>
            <Descriptions.Item label="主题模板">{previewTemplate.subjectTemplate || '-'}</Descriptions.Item>
            <Descriptions.Item label="文本模板">
              <div style={{ whiteSpace: 'pre-wrap' }}>{previewTemplate.textTemplate || '-'}</div>
            </Descriptions.Item>
            <Descriptions.Item label="HTML模板">
              <div style={{ whiteSpace: 'pre-wrap', maxHeight: 200, overflow: 'auto' }}>{previewTemplate.htmlTemplate || '-'}</div>
            </Descriptions.Item>
            <Descriptions.Item label="微信模板ID">{previewTemplate.wechatTemplateId || '-'}</Descriptions.Item>
          </Descriptions>
        )}
      </Modal>

      {/* 测试发送 Modal */}
      <Modal
        title="测试发送"
        open={testSendVisible}
        onCancel={() => {
          setTestSendVisible(false);
          setTestUserId('');
        }}
        onOk={handleTestSend}
        confirmLoading={testSending}
        okText="发送"
      >
        <div style={{ marginBottom: 12 }}>
          <span>将使用当前模板向指定用户发送一条测试消息</span>
        </div>
        <Input
          placeholder="请输入测试用户ID"
          value={testUserId}
          onChange={(e) => setTestUserId(e.target.value)}
        />
      </Modal>
    </PageContainer>
  );
};

export default UnifiedTemplatesPage;
