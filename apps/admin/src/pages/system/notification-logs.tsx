import type { ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable } from '@ant-design/pro-components';
import { Card, Col, Row, Statistic, Tag, Button, message, Popconfirm, Drawer, Descriptions, Space, Progress } from 'antd';
import { ReloadOutlined } from '@ant-design/icons';
import { notificationLogApi } from '@hospital/api';
import { createListRequest } from '@/utils/proTable';
import { useListPage } from '@/hooks/useListPage';
import { useRequest } from '@umijs/max';
import { useState, useCallback } from 'react';
import type { NotificationLog } from '@hospital/api';
import type { NotificationQuota } from '@hospital/shared';

const CHANNEL_MAP: Record<string, { text: string; color: string }> = {
  sms: { text: '短信', color: 'blue' },
  email: { text: '邮件', color: 'cyan' },
  in_app: { text: '站内信', color: 'green' },
  wechat: { text: '微信', color: 'purple' },
};

const STATUS_MAP: Record<string, { text: string; color: string }> = {
  pending: { text: '待发送', color: 'orange' },
  sent: { text: '已发送', color: 'green' },
  failed: { text: '失败', color: 'red' },
  permanently_failed: { text: '永久失败', color: 'default' },
};

const NotificationLogsPage: React.FC = () => {
  const { actionRef } = useListPage();
  const [selectedRowKeys, setSelectedRowKeys] = useState<string[]>([]);
  const [detailVisible, setDetailVisible] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);
  const [currentLog, setCurrentLog] = useState<NotificationLog | null>(null);

  const { data: stats, loading: statsLoading } = useRequest(
    () => notificationLogApi.getStats(),
    { refreshDeps: [] },
  );

  const { data: quota, loading: quotaLoading } = useRequest(
    () => notificationLogApi.getQuota(),
    { refreshDeps: [] },
  );

  const handleViewDetail = useCallback(async (id: string) => {
    setDetailVisible(true);
    setDetailLoading(true);
    try {
      const detail = await notificationLogApi.getDetail(id);
      setCurrentLog(detail);
    } catch {
      message.error('获取日志详情失败');
    } finally {
      setDetailLoading(false);
    }
  }, []);

  const handleRetry = useCallback(async (id: string) => {
    try {
      await notificationLogApi.retry(id);
      message.success('已加入重试队列');
      actionRef.current?.reload();
    } catch {
      message.error('重试失败');
    }
  }, [actionRef]);

  const handleBatchRetry = useCallback(async () => {
    if (selectedRowKeys.length === 0) return;
    let success = 0;
    let failed = 0;
    for (const id of selectedRowKeys) {
      try {
        await notificationLogApi.retry(id);
        success++;
      } catch {
        failed++;
      }
    }
    message.success(`批量重试完成：成功 ${success}，失败 ${failed}`);
    setSelectedRowKeys([]);
    actionRef.current?.reload();
  }, [selectedRowKeys, actionRef]);

  const columns: ProColumns<NotificationLog>[] = [
    {
      title: '创建时间',
      dataIndex: 'createdAt',
      valueType: 'dateTime',
      width: 160,
      search: false,
    },
    {
      title: '时间范围',
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
      title: '通知通道',
      dataIndex: 'channel',
      width: 100,
      valueEnum: Object.fromEntries(
        Object.entries(CHANNEL_MAP).map(([k, v]) => [k, { text: v.text }])
      ),
      render: (_, r) => {
        const t = CHANNEL_MAP[r.channel || 'in_app'];
        return <Tag color={t.color}>{t.text}</Tag>;
      },
    },
    {
      title: '消息类型',
      dataIndex: 'messageType',
      width: 120,
      valueType: 'text',
    },
    {
      title: '接收人',
      dataIndex: 'recipient',
      width: 150,
      search: false,
      ellipsis: true,
    },
    {
      title: '标题',
      dataIndex: 'title',
      ellipsis: true,
      search: false,
      render: (_, record) => (
        <a onClick={() => handleViewDetail(record.id)}>{record.title || '-'}</a>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 100,
      valueEnum: Object.fromEntries(
        Object.entries(STATUS_MAP).map(([k, v]) => [k, { text: v.text }])
      ),
      render: (_, r) => {
        const t = STATUS_MAP[r.status || 'pending'];
        return <Tag color={t.color}>{t.text}</Tag>;
      },
    },
    {
      title: '错误信息',
      dataIndex: 'errorMessage',
      search: false,
      ellipsis: true,
      render: (_, r) => r.errorMessage || '-',
    },
    {
      title: '操作',
      valueType: 'option',
      width: 120,
      fixed: 'right',
      render: (_, record) => {
        const canRetry = (record.status === 'failed' || record.status === 'permanently_failed') && record.channel !== 'in_app';
        return (
          <Space size={0}>
            <Button type="link" size="small" onClick={() => handleViewDetail(record.id)}>
              查看
            </Button>
            {canRetry && (
              <Popconfirm title="确认重试发送该通知？" onConfirm={() => handleRetry(record.id)}>
                <Button type="link" size="small">重试</Button>
              </Popconfirm>
            )}
          </Space>
        );
      },
    },
  ];

  const quotaData = quota as NotificationQuota | undefined;
  const dailyPercent = quotaData?.dailyLimit ? Math.min(100, Math.round(((quotaData.dailyUsed || 0) / quotaData.dailyLimit) * 100)) : 0;
  const monthlyPercent = quotaData?.monthlyLimit ? Math.min(100, Math.round(((quotaData.monthlyUsed || 0) / quotaData.monthlyLimit) * 100)) : 0;

  return (
    <PageContainer>
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={4}>
          <Card loading={statsLoading}>
            <Statistic title="总发送量" value={stats?.total || 0} />
          </Card>
        </Col>
        <Col span={4}>
          <Card loading={statsLoading}>
            <Statistic title="成功" value={stats?.sent || 0} styles={{ content: { color: '#3f8600' } }} />
          </Card>
        </Col>
        <Col span={4}>
          <Card loading={statsLoading}>
            <Statistic title="失败" value={stats?.failed || 0} styles={{ content: { color: '#cf1322' } }} />
          </Card>
        </Col>
        <Col span={4}>
          <Card loading={statsLoading}>
            <Statistic title="失败率" value={stats?.failureRate || 0} precision={2} suffix="%"
              styles={{ content: { color: (stats?.failureRate || 0) > 5 ? '#cf1322' : '#3f8600' } }}
            />
          </Card>
        </Col>
        <Col span={4}>
          <Card loading={quotaLoading}>
            <Statistic title="今日用量" value={quotaData?.dailyUsed || 0} suffix={quotaData?.dailyLimit ? `/ ${quotaData.dailyLimit}` : ''} />
            {quotaData?.dailyLimit && <Progress percent={dailyPercent} size="small" status={dailyPercent >= 90 ? 'exception' : 'active'} />}
          </Card>
        </Col>
        <Col span={4}>
          <Card loading={quotaLoading}>
            <Statistic title="本月用量" value={quotaData?.monthlyUsed || 0} suffix={quotaData?.monthlyLimit ? `/ ${quotaData.monthlyLimit}` : ''} />
            {quotaData?.monthlyLimit && <Progress percent={monthlyPercent} size="small" status={monthlyPercent >= 90 ? 'exception' : 'active'} />}
          </Card>
        </Col>
      </Row>

      <ProTable<NotificationLog>
        headerTitle="通知日志"
        actionRef={actionRef}
        rowKey="id"
        columns={columns}
        request={createListRequest(notificationLogApi.getList)}
        rowSelection={{
          selectedRowKeys,
          onChange: (keys) => setSelectedRowKeys(keys as string[]),
        }}
        toolBarRender={() => [
          selectedRowKeys.length > 0 && (
            <Popconfirm
              key="batch-retry"
              title={`确认重试 ${selectedRowKeys.length} 条失败通知？`}
              onConfirm={handleBatchRetry}
            >
              <Button icon={<ReloadOutlined />}>批量重试 ({selectedRowKeys.length})</Button>
            </Popconfirm>
          ),
        ]}
        pagination={{ defaultPageSize: 10 }}
        search={{ labelWidth: 'auto' }}
      />

      <Drawer
        title="通知日志详情"
        open={detailVisible}
        onClose={() => {
          setDetailVisible(false);
          setCurrentLog(null);
        }}
        width={560}
        loading={detailLoading}
      >
        {currentLog && (
          <Descriptions column={1} bordered size="small">
            <Descriptions.Item label="ID">{currentLog.id}</Descriptions.Item>
            <Descriptions.Item label="通知通道">
              <Tag color={CHANNEL_MAP[currentLog.channel]?.color}>{CHANNEL_MAP[currentLog.channel]?.text || currentLog.channel}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label="消息类型">{currentLog.messageType || '-'}</Descriptions.Item>
            <Descriptions.Item label="接收人">{currentLog.recipient || '-'}</Descriptions.Item>
            <Descriptions.Item label="标题">{currentLog.title || '-'}</Descriptions.Item>
            <Descriptions.Item label="内容">
              <div style={{ whiteSpace: 'pre-wrap' }}>{currentLog.content || '-'}</div>
            </Descriptions.Item>
            <Descriptions.Item label="状态">
              <Tag color={STATUS_MAP[currentLog.status]?.color}>{STATUS_MAP[currentLog.status]?.text || currentLog.status}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label="错误信息">{currentLog.errorMessage || '-'}</Descriptions.Item>
            <Descriptions.Item label="重试次数">{currentLog.retryCount ?? 0}</Descriptions.Item>
            <Descriptions.Item label="用户ID">{currentLog.userId || '-'}</Descriptions.Item>
            <Descriptions.Item label="用户类型">{currentLog.userType || '-'}</Descriptions.Item>
            <Descriptions.Item label="关联ID">{currentLog.relatedId || '-'}</Descriptions.Item>
            <Descriptions.Item label="发送时间">{currentLog.sentAt || '-'}</Descriptions.Item>
            <Descriptions.Item label="创建时间">{currentLog.createdAt}</Descriptions.Item>
          </Descriptions>
        )}
      </Drawer>
    </PageContainer>
  );
};

export default NotificationLogsPage;
