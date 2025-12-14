import { PlusOutlined } from '@ant-design/icons';
import type { ActionType, ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable, ModalForm, ProFormText, ProFormTextArea, ProFormSelect } from '@ant-design/pro-components';
import { Button, App, Space, Tag, Popconfirm } from 'antd';
import { useRef, useState } from 'react';
import { messageApi } from '@hospital/api';
import { toProTableResult } from '@/utils/proTable';
import type { Message } from '@hospital/shared';

const TYPE_MAP: Record<string, { text: string; color: string }> = {
  system: { text: '系统', color: 'blue' },
  appointment: { text: '预约', color: 'green' },
  reminder: { text: '提醒', color: 'orange' },
  notice: { text: '公告', color: 'purple' },
};

const MessagePage: React.FC = () => {
  const { message } = App.useApp();
  const actionRef = useRef<ActionType>();
  const [modalOpen, setModalOpen] = useState(false);

  const handleSend = async (values: any) => {
    try {
      await messageApi.send({
        userId: values.userId,
        userType: values.userType,
        title: values.title,
        content: values.content,
        messageType: values.messageType,
      });
      message.success('发送成功');
      setModalOpen(false);
      actionRef.current?.reload();
      return true;
    } catch (error: any) {
      message.error(error.message || '发送失败');
      return false;
    }
  };

  const columns: ProColumns<Message>[] = [
    { title: '标题', dataIndex: 'title', ellipsis: true },
    {
      title: '类型',
      dataIndex: 'messageType',
      width: 80,
      valueEnum: Object.fromEntries(Object.entries(TYPE_MAP).map(([k, v]) => [k, { text: v.text }])),
      render: (_, r) => {
        const t = TYPE_MAP[r.messageType || 'system'];
        return <Tag color={t.color}>{t.text}</Tag>;
      },
    },
    {
      title: '用户类型',
      dataIndex: 'userType',
      width: 80,
      valueEnum: { patient: '患者', doctor: '医生' },
    },
    {
      title: '已读',
      dataIndex: 'isRead',
      width: 70,
      search: false,
      render: (_, r) => r.isRead ? <Tag color="green">已读</Tag> : <Tag>未读</Tag>,
    },
    { title: '发送时间', dataIndex: 'createdAt', valueType: 'dateTime', width: 160, search: false },
  ];

  return (
    <PageContainer>
      <ProTable<Message>
        headerTitle="消息列表"
        actionRef={actionRef}
        rowKey="id"
        columns={columns}
        request={async (params) => {
          const { current, pageSize, title, ...rest } = params;
          return toProTableResult(await messageApi.getAllList({ ...rest, keyword: title, page: current, pageSize }));
        }}
        toolBarRender={() => [
          <Button key="add" type="primary" icon={<PlusOutlined />} onClick={() => setModalOpen(true)}>
            发送消息
          </Button>,
        ]}
        pagination={{ defaultPageSize: 10 }}
        search={{ labelWidth: 'auto' }}
      />

      <ModalForm
        title="发送消息"
        open={modalOpen}
        onOpenChange={setModalOpen}
        onFinish={handleSend}
        modalProps={{ destroyOnHidden: true }}
        initialValues={{ userType: 'patient', messageType: 'system' }}
      >
        <ProFormText name="userId" label="用户ID" rules={[{ required: true }]} />
        <ProFormSelect
          name="userType"
          label="用户类型"
          options={[
            { label: '患者', value: 'patient' },
            { label: '医生', value: 'doctor' },
          ]}
          rules={[{ required: true }]}
        />
        <ProFormSelect
          name="messageType"
          label="消息类型"
          options={Object.entries(TYPE_MAP).map(([k, v]) => ({ label: v.text, value: k }))}
        />
        <ProFormText name="title" label="标题" rules={[{ required: true }]} />
        <ProFormTextArea name="content" label="内容" />
      </ModalForm>
    </PageContainer>
  );
};

export default MessagePage;
