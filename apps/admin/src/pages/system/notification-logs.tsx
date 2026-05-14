import type { ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable } from '@ant-design/pro-components';
import { Card, Col, Row, Statistic, Tag, Button, message, Popconfirm } from 'antd';
import { notificationLogApi } from '@hospital/api';
import { createListRequest } from '@/utils/proTable';
import { useListPage } from '@/hooks/useListPage';
import { useRequest } from '@umijs/max';
import type { NotificationLog } from '@hospital/api';

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

  const { data: stats, loading: statsLoading } = useRequest(
    () => notificationLogApi.getStats(),
    {
      refreshDeps: [],
    }
  );

  const columns: ProColumns<NotificationLog>[] = [
    {
      title: '创建时间',
      dataIndex: 'createdAt',
      valueType: 'dateTime',
      width: 160,
      search: false,
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
      width: 80,
      fixed: 'right',
      render: (_, record) => {
        const canRetry = (record.status === 'failed' || record.status === 'permanently_failed') && record.channel !== 'in_app';
        if (!canRetry) return null;
        return (
          <Popconfirm
            title="确认重试发送该通知？"
            onConfirm={async () => {
              try {
                await notificationLogApi.retry(record.id);
                message.success('已加入重试队列');
                actionRef.current?.reload();
              } catch {
                message.error('重试失败');
              }
            }}
          >
            <Button type="link" size="small">重试</Button>
          </Popconfirm>
        );
      },
    },
  ];

  return (
    <PageContainer>
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Card loading={statsLoading}>
            <Statistic title="总发送量" value={stats?.total || 0} />
          </Card>
        </Col>
        <Col span={6}>
          <Card loading={statsLoading}>
            <Statistic
              title="成功"
              value={stats?.sent || 0}
              styles={{ content: { color: '#3f8600' } }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card loading={statsLoading}>
            <Statistic
              title="失败"
              value={stats?.failed || 0}
              styles={{ content: { color: '#cf1322' } }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card loading={statsLoading}>
            <Statistic
              title="失败率"
              value={stats?.failureRate || 0}
              precision={2}
              suffix="%"
              styles={{ content: { color: (stats?.failureRate || 0) > 5 ? '#cf1322' : '#3f8600' } }}
            />
          </Card>
        </Col>
      </Row>

      <ProTable<NotificationLog>
        headerTitle="通知日志"
        actionRef={actionRef}
        rowKey="id"
        columns={columns}
        request={createListRequest(notificationLogApi.getList)}
        pagination={{ defaultPageSize: 10 }}
        search={{ labelWidth: 'auto' }}
        form={{
          onValuesChange: (_, values) => {
            if (values.startDate || values.endDate) {
              actionRef.current?.reload();
            }
          },
        }}
      />
    </PageContainer>
  );
};

export default NotificationLogsPage;
