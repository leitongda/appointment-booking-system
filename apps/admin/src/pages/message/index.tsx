import { PageContainer, ProTable, ModalForm, ProFormText, ProFormTextArea, ProFormSelect } from '@ant-design/pro-components';
import type { ProColumns, ActionType } from '@ant-design/pro-components';
import { Button, Tag, Space, message, Popconfirm, Tabs, Card, Statistic, Row, Col } from 'antd';
import { PlusOutlined, SendOutlined } from '@ant-design/icons';
import { useRef, useState, useEffect } from 'react';
import { messageApi } from '@hospital/api';
import type { Message, MessageTemplate } from '@hospital/shared';

const MessagePage: React.FC = () => {
  const actionRef = useRef<ActionType>();
  const templateActionRef = useRef<ActionType>();
  const [sendModalVisible, setSendModalVisible] = useState(false);
  const [templateModalVisible, setTemplateModalVisible] = useState(false);
  const [editingTemplate, setEditingTemplate] = useState<MessageTemplate | null>(null);
  const [activeTab, setActiveTab] = useState('messages');

  const handleSendMessage = async (values: any) => {
    try {
      await messageApi.send({
        userId: values.userId,
        userType: values.userType || 'patient',
        title: values.title,
        content: values.content,
        messageType: values.messageType || 'system',
      });
      message.success('发送成功');
      setSendModalVisible(false);
      actionRef.current?.reload();
      return true;
    } catch (error: any) {
      message.error(error.message || '发送失败');
      return false;
    }
  };

  const handleSaveTemplate = async (values: any) => {
    try {
      if (editingTemplate) {
        await messageApi.updateTemplate(editingTemplate.id, values);
        message.success('更新成功');
      } else {
        await messageApi.createTemplate(values);
        message.success('创建成功');
      }
      setTemplateModalVisible(false);
      setEditingTemplate(null);
      templateActionRef.current?.reload();
      return true;
    } catch (error: any) {
      message.error(error.message || '操作失败');
      return false;
    }
  };

  const handleDeleteTemplate = async (id: string) => {
    try {
      await messageApi.deleteTemplate(id);
      message.success('删除成功');
      templateActionRef.current?.reload();
    } catch (error: any) {
      message.error(error.message || '删除失败');
    }
  };

  const getTypeTag = (type: string) => {
    const map: Record<string, { color: string; text: string }> = {
      system: { color: 'blue', text: '系统消息' },
      appointment: { color: 'green', text: '预约通知' },
      consultation: { color: 'orange', text: '就诊通知' },
      stop_clinic: { color: 'red', text: '停诊通知' },
      schedule: { color: 'purple', text: '排班通知' },
    };
    const config = map[type] || { color: 'default', text: type };
    return <Tag color={config.color}>{config.text}</Tag>;
  };

  const messageColumns: ProColumns<Message>[] = [
    { title: '标题', dataIndex: 'title', width: 200, ellipsis: true },
    { title: '内容', dataIndex: 'content', width: 300, ellipsis: true, search: false },
    { 
      title: '类型', 
      dataIndex: 'messageType', 
      width: 100,
      render: (_, r) => getTypeTag(r.messageType),
      valueEnum: {
        system: '系统消息',
        appointment: '预约通知',
        consultation: '就诊通知',
        stop_clinic: '停诊通知',
      }
    },
    { title: '接收用户', dataIndex: 'userId', width: 120, ellipsis: true },
    { 
      title: '状态', 
      dataIndex: 'isRead', 
      width: 80,
      render: (val) => val ? <Tag color="default">已读</Tag> : <Tag color="processing">未读</Tag>,
      valueEnum: { 0: '未读', 1: '已读' }
    },
    { title: '发送时间', dataIndex: 'createdAt', width: 160, valueType: 'dateTime', search: false },
  ];

  const templateColumns: ProColumns<MessageTemplate>[] = [
    { title: '模板编码', dataIndex: 'code', width: 150 },
    { title: '模板名称', dataIndex: 'name', width: 150 },
    { 
      title: '消息类型', 
      dataIndex: 'messageType', 
      width: 100,
      render: (_, r) => getTypeTag(r.messageType),
    },
    { title: '标题模板', dataIndex: 'titleTemplate', width: 200, ellipsis: true, search: false },
    { title: '内容模板', dataIndex: 'contentTemplate', width: 300, ellipsis: true, search: false },
    { 
      title: '状态', 
      dataIndex: 'status', 
      width: 80,
      render: (val) => val === 1 ? <Tag color="success">启用</Tag> : <Tag color="default">禁用</Tag>,
    },
    {
      title: '操作',
      valueType: 'option',
      width: 120,
      render: (_, record) => (
        <Space>
          <a onClick={() => { setEditingTemplate(record); setTemplateModalVisible(true); }}>
            编辑
          </a>
          <Popconfirm title="确定删除吗？" onConfirm={() => handleDeleteTemplate(record.id)}>
            <a style={{ color: 'red' }}>删除</a>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <PageContainer>
      <Tabs 
        activeKey={activeTab} 
        onChange={setActiveTab}
        items={[
          {
            key: 'messages',
            label: '消息列表',
            children: (
              <ProTable<Message>
                actionRef={actionRef}
                rowKey="id"
                columns={messageColumns}
                search={{ labelWidth: 'auto' }}
                toolBarRender={() => [
                  <Button
                    key="send"
                    type="primary"
                    icon={<SendOutlined />}
                    onClick={() => setSendModalVisible(true)}
                  >
                    发送消息
                  </Button>,
                ]}
                request={async (params) => {
                  const { current, pageSize, messageType, isRead, title } = params;
                  const result = await messageApi.getAllList({
                    messageType,
                    isRead: isRead !== undefined ? Number(isRead) : undefined,
                    keyword: title,
                    page: current,
                    pageSize,
                  });
                  return { data: result.data, success: true, total: result.total };
                }}
              />
            ),
          },
          {
            key: 'templates',
            label: '消息模板',
            children: (
              <ProTable<MessageTemplate>
                actionRef={templateActionRef}
                rowKey="id"
                columns={templateColumns}
                search={{ labelWidth: 'auto' }}
                toolBarRender={() => [
                  <Button
                    key="add"
                    type="primary"
                    icon={<PlusOutlined />}
                    onClick={() => { setEditingTemplate(null); setTemplateModalVisible(true); }}
                  >
                    新增模板
                  </Button>,
                ]}
                request={async (params) => {
                  const { current, pageSize } = params;
                  const result = await messageApi.getTemplates({
                    page: current,
                    pageSize,
                  });
                  return { data: result.data, success: true, total: result.total };
                }}
              />
            ),
          },
        ]}
      />

      {/* 发送消息弹窗 */}
      <ModalForm
        title="发送消息"
        open={sendModalVisible}
        onOpenChange={setSendModalVisible}
        onFinish={handleSendMessage}
        modalProps={{ destroyOnClose: true }}
      >
        <ProFormText
          name="userId"
          label="接收用户ID"
          rules={[{ required: true, message: '请输入用户ID' }]}
          placeholder="输入用户ID，留空则发送给所有用户"
        />
        <ProFormSelect
          name="userType"
          label="用户类型"
          options={[
            { label: '患者', value: 'patient' },
            { label: '医生', value: 'doctor' },
          ]}
          initialValue="patient"
        />
        <ProFormSelect
          name="messageType"
          label="消息类型"
          options={[
            { label: '系统消息', value: 'system' },
            { label: '预约通知', value: 'appointment' },
            { label: '就诊通知', value: 'consultation' },
          ]}
          initialValue="system"
          rules={[{ required: true }]}
        />
        <ProFormText
          name="title"
          label="消息标题"
          rules={[{ required: true, message: '请输入消息标题' }]}
        />
        <ProFormTextArea
          name="content"
          label="消息内容"
          rules={[{ required: true, message: '请输入消息内容' }]}
          fieldProps={{ rows: 4 }}
        />
      </ModalForm>

      {/* 模板编辑弹窗 */}
      <ModalForm
        title={editingTemplate ? '编辑模板' : '新增模板'}
        open={templateModalVisible}
        onOpenChange={setTemplateModalVisible}
        onFinish={handleSaveTemplate}
        modalProps={{ destroyOnClose: true }}
        initialValues={editingTemplate || {}}
      >
        <ProFormText
          name="code"
          label="模板编码"
          rules={[{ required: true, message: '请输入模板编码' }]}
          disabled={!!editingTemplate}
        />
        <ProFormText
          name="name"
          label="模板名称"
          rules={[{ required: true, message: '请输入模板名称' }]}
        />
        <ProFormSelect
          name="messageType"
          label="消息类型"
          options={[
            { label: '系统消息', value: 'system' },
            { label: '预约通知', value: 'appointment' },
            { label: '就诊通知', value: 'consultation' },
            { label: '停诊通知', value: 'stop_clinic' },
            { label: '排班通知', value: 'schedule' },
          ]}
          rules={[{ required: true }]}
        />
        <ProFormText
          name="titleTemplate"
          label="标题模板"
          rules={[{ required: true, message: '请输入标题模板' }]}
          tooltip="支持变量：{doctor_name}, {date}, {time_slot} 等"
        />
        <ProFormTextArea
          name="contentTemplate"
          label="内容模板"
          rules={[{ required: true, message: '请输入内容模板' }]}
          fieldProps={{ rows: 4 }}
          tooltip="支持变量：{doctor_name}, {date}, {time_slot}, {queue_number} 等"
        />
        <ProFormText name="description" label="模板说明" />
      </ModalForm>
    </PageContainer>
  );
};

export default MessagePage;
