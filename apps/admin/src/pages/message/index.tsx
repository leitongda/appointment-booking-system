import type { ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable } from '@ant-design/pro-components';
import { Tag, Button, Popconfirm, Drawer, Space, Descriptions, Card, Row, Col } from 'antd';
import { MailOutlined, UserOutlined, FileTextOutlined, BarChartOutlined } from '@ant-design/icons';
import { useState, useCallback, useMemo } from 'react';
import { useModel, history } from '@umijs/max';
import { messageApi } from '@hospital/api';
import { useDict } from '@/hooks/useDict';
import { createListRequest } from '@/utils/proTable';
import { useListPage } from '@/hooks/useListPage';
import { CreateButton, OperationGroup, OperationButton } from '@/components/ListOperations';
import type { Message } from '@hospital/shared';

const TYPE_MAP: Record<string, { text: string; color: string }> = {
  appointment: { text: '预约', color: 'green' },
  consultation: { text: '就诊', color: 'cyan' },
  schedule: { text: '排班', color: 'orange' },
  system: { text: '系统', color: 'blue' },
  stop_clinic: { text: '停诊', color: 'red' },
  feedback: { text: '反馈', color: 'purple' },
};

async function batchExecute<T>(items: T[], fn: (item: T) => Promise<any>, batchSize = 10) {
  for (let i = 0; i < items.length; i += batchSize) {
    await Promise.all(items.slice(i, i + batchSize).map(fn));
  }
}

const MessagePage: React.FC = () => {
  const { actionRef, message } = useListPage();
  const { initialState } = useModel('@@initialState');
  const { options: messageTypeOptions } = useDict('message_type');
  const messageTypeEnum = useMemo(
    () => Object.fromEntries(messageTypeOptions.map((o) => [o.value, { text: o.label }])),
    [messageTypeOptions],
  );
  const [selectedRowKeys, setSelectedRowKeys] = useState<string[]>([]);
  const [detailVisible, setDetailVisible] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);
  const [currentMessage, setCurrentMessage] = useState<Message | null>(null);

  const currentUser = initialState?.currentUser;

  const handleViewDetail = useCallback(async (id: string) => {
    setDetailVisible(true);
    setDetailLoading(true);
    try {
      const detail = await messageApi.getDetail(id);
      setCurrentMessage(detail);
    } catch {
      message.error('获取消息详情失败');
    } finally {
      setDetailLoading(false);
    }
  }, [message]);

  const handleDelete = useCallback(async (id: string) => {
    try {
      await messageApi.delete(id, currentUser?.id || '');
      message.success('删除成功');
      actionRef.current?.reload();
    } catch {
      message.error('删除失败');
    }
  }, [currentUser?.id, actionRef, message]);

  const handleBatchRead = useCallback(async () => {
    if (selectedRowKeys.length === 0) return;
    try {
      await batchExecute(selectedRowKeys, (id) => messageApi.markAsReadUnified(id));
      message.success(`已标记 ${selectedRowKeys.length} 条为已读`);
      setSelectedRowKeys([]);
      actionRef.current?.reload();
    } catch {
      message.error('批量已读失败');
    }
  }, [selectedRowKeys, actionRef, message]);

  const handleBatchDelete = useCallback(async () => {
    if (!currentUser?.id || selectedRowKeys.length === 0) return;
    try {
      await batchExecute(selectedRowKeys, (id) => messageApi.delete(id, currentUser.id));
      message.success(`已删除 ${selectedRowKeys.length} 条消息`);
      setSelectedRowKeys([]);
      actionRef.current?.reload();
    } catch {
      message.error('批量删除失败');
    }
  }, [currentUser?.id, selectedRowKeys, actionRef, message]);

  const handleClearRead = useCallback(async () => {
    if (!currentUser?.id) return;
    try {
      await messageApi.clearRead(currentUser.id, 'admin');
      message.success('已清空已读消息');
      actionRef.current?.reload();
    } catch {
      message.error('清空已读失败');
    }
  }, [currentUser?.id, actionRef, message]);

  const columns: ProColumns<Message>[] = [
    {
      title: '标题',
      dataIndex: 'title',
      ellipsis: true,
      render: (_, record) => (
        <a onClick={() => handleViewDetail(record.id)}>{record.title}</a>
      ),
    },
    {
      title: '类型',
      dataIndex: 'messageType',
      width: 80,
      valueEnum: messageTypeEnum,
      render: (_, r) => {
        const t = TYPE_MAP[r.messageType || 'system'] || { text: r.messageType || '未知', color: 'default' };
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
    {
      title: '发送时间',
      dataIndex: 'createdAt',
      valueType: 'dateTime',
      width: 160,
      search: false,
    },
    {
      title: '发送时间',
      dataIndex: 'dateRange',
      valueType: 'dateRange',
      width: 200,
      hideInTable: true,
      search: {
        transform: (value) => {
          if (Array.isArray(value) && value.length === 2) {
            return { start_date: value[0], end_date: value[1] };
          }
          return {};
        },
      },
    },
    {
      title: '操作',
      valueType: 'option',
      width: 120,
      render: (_, record) => (
        <OperationGroup>
          <OperationButton
            type="view"
            onClick={() => handleViewDetail(record.id)}
          />
          <OperationButton
            type="delete"
            permission="message:delete"
            confirmText="确认删除此消息？"
            onClick={() => handleDelete(record.id)}
          />
        </OperationGroup>
      ),
    },
  ];

  const detailType = currentMessage?.messageType ? TYPE_MAP[currentMessage.messageType] : undefined;

  const quickLinks = [
    { icon: <MailOutlined />, label: '邮件模板', path: '/system/config/email-templates' },
    { icon: <UserOutlined />, label: '邮件接收人', path: '/system/config/email-recipients' },
    { icon: <FileTextOutlined />, label: '统一模板', path: '/content-center/message/templates' },
    { icon: <BarChartOutlined />, label: '通知日志', path: '/system/monitoring/notification-logs' },
  ];

  return (
    <PageContainer>
      <Card size="small" style={{ marginBottom: 16 }}>
        <Row gutter={16}>
          {quickLinks.map((item) => (
            <Col key={item.path}>
              <Button
                type="link"
                icon={item.icon}
                onClick={() => history.push(item.path)}
                style={{ padding: 0 }}
              >
                {item.label}
              </Button>
            </Col>
          ))}
        </Row>
      </Card>
      <ProTable<Message>
        headerTitle="消息列表"
        actionRef={actionRef}
        rowKey="id"
        columns={columns}
        request={createListRequest(messageApi.getUnifiedList)}
        rowSelection={{
          selectedRowKeys,
          onChange: (keys) => setSelectedRowKeys(keys as string[]),
        }}
        toolBarRender={() => [
          selectedRowKeys.length > 0 && (
            <Space key="batch">
              <Button onClick={handleBatchRead}>批量已读 ({selectedRowKeys.length})</Button>
              <Popconfirm
                title={`确认删除 ${selectedRowKeys.length} 条消息？`}
                onConfirm={handleBatchDelete}
              >
                <Button danger>批量删除 ({selectedRowKeys.length})</Button>
              </Popconfirm>
            </Space>
          ),
          <Popconfirm
            key="clear"
            title="确认清空所有已读消息？"
            onConfirm={handleClearRead}
          >
            <Button>清空已读</Button>
          </Popconfirm>,
          <CreateButton
            key="add"
            permission="message:send"
            url="/content-center/message/create"
            label="发送消息"
          />,
        ]}
        pagination={{ defaultPageSize: 10 }}
        search={{ labelWidth: 'auto' }}
      />

      <Drawer
        title="消息详情"
        open={detailVisible}
        onClose={() => {
          setDetailVisible(false);
          setCurrentMessage(null);
        }}
        width={520}
        loading={detailLoading}
      >
        {currentMessage && (
          <Descriptions column={1} bordered size="small">
            <Descriptions.Item label="标题">{currentMessage.title}</Descriptions.Item>
            <Descriptions.Item label="类型">
              <Tag color={detailType?.color}>{detailType?.text || currentMessage.messageType}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label="用户类型">{currentMessage.userType === 'patient' ? '患者' : '医生'}</Descriptions.Item>
            <Descriptions.Item label="用户ID">{currentMessage.userId}</Descriptions.Item>
            <Descriptions.Item label="状态">
              {currentMessage.isRead ? <Tag color="green">已读</Tag> : <Tag>未读</Tag>}
            </Descriptions.Item>
            <Descriptions.Item label="内容">{currentMessage.content || '-'}</Descriptions.Item>
            <Descriptions.Item label="关联ID">{currentMessage.relatedId || '-'}</Descriptions.Item>
            <Descriptions.Item label="发送时间">{currentMessage.createdAt}</Descriptions.Item>
            {currentMessage.readAt && (
              <Descriptions.Item label="已读时间">{currentMessage.readAt}</Descriptions.Item>
            )}
          </Descriptions>
        )}
      </Drawer>
    </PageContainer>
  );
};

export default MessagePage;
