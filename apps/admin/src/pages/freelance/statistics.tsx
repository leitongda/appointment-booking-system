import { PageContainer } from '@ant-design/pro-components';
import { Card, Col, Row, Statistic, Table, Spin } from 'antd';
import {
  TeamOutlined,
  DollarOutlined,
  ClockCircleOutlined,
  FileTextOutlined,
  MessageOutlined,
} from '@ant-design/icons';
import { useState, useEffect, useCallback } from 'react';
import { freelanceSettlementApi } from '@hospital/api';
import { App } from 'antd';

const FreelanceStatisticsPage: React.FC = () => {
  const { message } = App.useApp();
  const [loading, setLoading] = useState(false);
  const [overview, setOverview] = useState<any>(null);
  const [byFreelancer, setByFreelancer] = useState<any[]>([]);
  const [byMonth, setByMonth] = useState<any[]>([]);
  const [taskStats, setTaskStats] = useState<any>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [overviewData, freelancerData, monthData, taskData] = await Promise.all([
        freelanceSettlementApi.getStatistics(),
        freelanceSettlementApi.getStatisticsByFreelancer(),
        freelanceSettlementApi.getStatisticsByMonth(),
        freelanceSettlementApi.getTaskStatistics(),
      ]);
      setOverview(overviewData);
      setByFreelancer(freelancerData);
      setByMonth(monthData);
      setTaskStats(taskData);
    } catch (error: any) {
      message.error(error.message || '加载统计数据失败');
    } finally {
      setLoading(false);
    }
  }, [message]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const freelancerColumns = [
    { title: '排名', key: 'rank', width: 60, render: (_: any, __: any, index: number) => index + 1 },
    { title: '兼职人员', dataIndex: 'freelancerName', width: 120 },
    { title: '结算次数', dataIndex: 'settlementCount', width: 90 },
    {
      title: '总结算金额',
      dataIndex: 'totalAmount',
      width: 120,
      render: (v: number) => `¥${Number(v).toFixed(2)}`,
    },
    {
      title: '实际支付',
      dataIndex: 'actualAmount',
      width: 120,
      render: (v: number) => <strong style={{ color: 'var(--color-success)' }}>¥{Number(v).toFixed(2)}</strong>,
    },
  ];

  const monthColumns = [
    { title: '月份', dataIndex: 'month', width: 100 },
    { title: '结算次数', dataIndex: 'settlementCount', width: 90 },
    {
      title: '总结算金额',
      dataIndex: 'totalAmount',
      width: 120,
      render: (v: number) => `¥${Number(v).toFixed(2)}`,
    },
    {
      title: '实际支付',
      dataIndex: 'actualAmount',
      width: 120,
      render: (v: number) => <strong style={{ color: 'var(--color-success)' }}>¥{Number(v).toFixed(2)}</strong>,
    },
  ];

  return (
    <PageContainer>
      <Spin spinning={loading}>
        <Row gutter={16} style={{ marginBottom: 16 }}>
          <Col span={6}>
            <Card>
              <Statistic
                title="兼职人员数"
                value={overview?.totalFreelancers ?? 0}
                prefix={<TeamOutlined />}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="已结算金额"
                value={overview?.totalSettledAmount ?? 0}
                precision={2}
                prefix={<DollarOutlined />}
                suffix="元"
                valueStyle={{ color: '#3f8600' }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="待结算金额"
                value={overview?.totalPendingAmount ?? 0}
                precision={2}
                prefix={<ClockCircleOutlined />}
                suffix="元"
                valueStyle={{ color: 'var(--color-warning)' }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="总任务数"
                value={taskStats?.totalTasks ?? 0}
                prefix={<FileTextOutlined />}
              />
            </Card>
          </Col>
        </Row>

        <Row gutter={16} style={{ marginBottom: 16 }}>
          <Col span={6}>
            <Card>
              <Statistic title="总互动数" value={taskStats?.totalInteractions ?? 0} prefix={<MessageOutlined />} />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic title="已发布任务" value={taskStats?.taskCounts?.published ?? 0} />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic title="已收录任务" value={taskStats?.taskCounts?.indexed ?? 0} valueStyle={{ color: '#3f8600' }} />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic title="待发布任务" value={taskStats?.taskCounts?.pending ?? 0} />
            </Card>
          </Col>
        </Row>

        <Row gutter={16}>
          <Col span={12}>
            <Card title="兼职人员结算排行">
              <Table
                dataSource={byFreelancer}
                columns={freelancerColumns}
                rowKey="freelancerId"
                pagination={false}
                size="small"
              />
            </Card>
          </Col>
          <Col span={12}>
            <Card title="月度结算趋势">
              <Table
                dataSource={byMonth}
                columns={monthColumns}
                rowKey="month"
                pagination={false}
                size="small"
              />
            </Card>
          </Col>
        </Row>
      </Spin>
    </PageContainer>
  );
};

export default FreelanceStatisticsPage;
