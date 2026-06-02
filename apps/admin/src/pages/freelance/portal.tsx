import { useState, useEffect } from 'react';
import { Card, Col, Row, Statistic, Table, Tag, Spin, Descriptions, Empty } from 'antd';
import { DollarOutlined, FileTextOutlined, ClockCircleOutlined } from '@ant-design/icons';
import { useSearchParams } from '@umijs/max';
import { App } from 'antd';

const STATUS_MAP: Record<string, { text: string; color: string }> = {
  pending: { text: '待发布', color: 'default' },
  published: { text: '已发布', color: 'blue' },
  indexed: { text: '已收录', color: 'green' },
  need_modify: { text: '需修改', color: 'orange' },
  rejected: { text: '已拒绝', color: 'red' },
};

const SETTLE_STATUS_MAP: Record<string, { text: string; color: string }> = {
  pending: { text: '待确认', color: 'gold' },
  confirmed: { text: '已确认', color: 'blue' },
  paid: { text: '已支付', color: 'green' },
  cancelled: { text: '已驳回', color: 'red' },
};

const FreelancePortalPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token') || '';
  const { message } = App.useApp();
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState<any>(null);

  useEffect(() => {
    if (!token) {
      setLoading(false);
      return;
    }
    const fetchData = async () => {
      try {
        const resp = await fetch(`/api/v1/freelance-portal/portal/${token}`);
        if (!resp.ok) throw new Error('访问链接无效');
        const result = await resp.json();
        setData(result);
      } catch (error: any) {
        message.error(error.message || '加载失败');
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [token, message]);

  if (!token) {
    return (
      <div style={{ maxWidth: 600, margin: '100px auto', textAlign: 'center' }}>
        <Empty description="请提供有效的访问链接" />
      </div>
    );
  }

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: 100 }}>
        <Spin size="large" />
      </div>
    );
  }

  if (!data) {
    return (
      <div style={{ maxWidth: 600, margin: '100px auto', textAlign: 'center' }}>
        <Empty description="无法加载数据" />
      </div>
    );
  }

  const taskColumns = [
    { title: '笔记标题', dataIndex: 'title', ellipsis: true },
    {
      title: '状态',
      dataIndex: 'status',
      width: 90,
      render: (v: string) => {
        const s = STATUS_MAP[v] || { text: v, color: 'default' };
        return <Tag color={s.color}>{s.text}</Tag>;
      },
    },
    { title: '点赞', dataIndex: 'likesCount', width: 70 },
    { title: '评论', dataIndex: 'commentsCount', width: 70 },
    { title: '基础', dataIndex: 'baseAmount', width: 80, render: (v: number) => `¥${Number(v).toFixed(2)}` },
    { title: '补贴', dataIndex: 'bonusAmount', width: 80, render: (v: number) => `¥${Number(v).toFixed(2)}` },
    { title: '点赞奖', dataIndex: 'likesBonusAmount', width: 80, render: (v: number) => `¥${Number(v).toFixed(2)}` },
    { title: '发布时间', dataIndex: 'publishedAt', width: 110, render: (v: string) => v ? new Date(v).toLocaleDateString('zh-CN') : '-' },
  ];

  const settlementColumns = [
    { title: '结算单号', dataIndex: 'settlementNo', width: 180, ellipsis: true },
    {
      title: '状态',
      dataIndex: 'status',
      width: 90,
      render: (v: string) => {
        const s = SETTLE_STATUS_MAP[v] || { text: v, color: 'default' };
        return <Tag color={s.color}>{s.text}</Tag>;
      },
    },
    { title: '总金额', dataIndex: 'totalAmount', width: 100, render: (v: number) => `¥${Number(v).toFixed(2)}` },
    { title: '实付', dataIndex: 'actualAmount', width: 100, render: (v: number) => <strong style={{ color: '#52c41a' }}>¥{Number(v).toFixed(2)}</strong> },
    { title: '时间', dataIndex: 'createdAt', width: 110, render: (v: string) => v ? new Date(v).toLocaleDateString('zh-CN') : '-' },
  ];

  return (
    <div style={{ maxWidth: 1000, margin: '0 auto', padding: '24px 16px' }}>
      <h2 style={{ marginBottom: 24 }}>
        {data.freelancer.name} — 我的兼职收入
      </h2>

      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={8}>
          <Card>
            <Statistic title="总任务数" value={data.summary.totalTasks} prefix={<FileTextOutlined />} />
          </Card>
        </Col>
        <Col span={8}>
          <Card>
            <Statistic title="已结算" value={data.summary.totalEarned} precision={2} prefix="¥" valueStyle={{ color: '#3f8600' }} />
          </Card>
        </Col>
        <Col span={8}>
          <Card>
            <Statistic title="待结算" value={data.summary.totalPending} precision={2} prefix="¥" valueStyle={{ color: '#faad14' }} />
          </Card>
        </Col>
      </Row>

      <Card title="我的任务" style={{ marginBottom: 24 }}>
        <Table dataSource={data.tasks} columns={taskColumns} rowKey="id" size="small" pagination={false} />
      </Card>

      <Card title="我的结算">
        <Table dataSource={data.settlements} columns={settlementColumns} rowKey="id" size="small" pagination={false} />
      </Card>
    </div>
  );
};

export default FreelancePortalPage;
