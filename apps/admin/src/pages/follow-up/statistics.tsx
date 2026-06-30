import { PageContainer } from '@ant-design/pro-components';
import { Card, Col, Row, Statistic, Table, DatePicker, Space, Spin, Tag } from 'antd';
import {
  CheckCircleOutlined,
  ClockCircleOutlined,
  CloseCircleOutlined,
  ExclamationCircleOutlined,
} from '@ant-design/icons';
import { useState, useEffect, useCallback } from 'react';
import { followUpApi } from '@hospital/api';
import type { FollowUpStatistics } from '@hospital/api';
import { App } from 'antd';
import dayjs from 'dayjs';

const { RangePicker } = DatePicker;

const FollowUpStatisticsPage: React.FC = () => {
  const { message } = App.useApp();
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<FollowUpStatistics | null>(null);
  const [dateRange, setDateRange] = useState<[string, string] | undefined>(undefined);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const result = await followUpApi.getStatistics({
        startDate: dateRange?.[0],
        endDate: dateRange?.[1],
      });
      setData(result);
    } catch (error: any) {
      message.error(error.message || '加载统计数据失败');
    } finally {
      setLoading(false);
    }
  }, [dateRange, message]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const columns = [
    { title: '排名', key: 'rank', width: 60, render: (_: any, __: any, index: number) => index + 1 },
    { title: '医生', dataIndex: 'doctorName', width: 120 },
    { title: '任务总数', dataIndex: 'total', width: 90 },
    { title: '已完成', dataIndex: 'completed', width: 80 },
    {
      title: '完成率',
      dataIndex: 'rate',
      width: 90,
      render: (rate: number) => (
        <Tag color={rate >= 80 ? 'success' : rate >= 50 ? 'processing' : 'error'}>{rate}%</Tag>
      ),
    },
  ];

  return (
    <PageContainer>
      <Spin spinning={loading}>
        <Space style={{ marginBottom: 16 }}>
          <RangePicker
            onChange={(dates) => {
              if (dates) {
                setDateRange([
                  dates[0]!.format('YYYY-MM-DD'),
                  dates[1]!.format('YYYY-MM-DD'),
                ]);
              } else {
                setDateRange(undefined);
              }
            }}
          />
        </Space>

        <Row gutter={16} style={{ marginBottom: 16 }}>
          <Col span={6}>
            <Card>
              <Statistic
                title="任务总数"
                value={data?.total ?? 0}
                prefix={<ClockCircleOutlined />}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="已完成"
                value={data?.completed ?? 0}
                prefix={<CheckCircleOutlined />}
                valueStyle={{ color: '#3f8600' }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="已逾期"
                value={data?.overdue ?? 0}
                prefix={<ExclamationCircleOutlined />}
                valueStyle={{ color: 'var(--color-error-active)' }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="完成率"
                value={data?.completionRate ?? 0}
                suffix="%"
                prefix={<CheckCircleOutlined />}
                valueStyle={{ color: data && data.completionRate >= 70 ? '#3f8600' : 'var(--color-error-active)' }}
              />
            </Card>
          </Col>
        </Row>

        <Row gutter={16} style={{ marginBottom: 16 }}>
          <Col span={6}>
            <Card>
              <Statistic title="待随访" value={data?.pending ?? 0} />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic title="已跳过" value={data?.skipped ?? 0} />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="逾期率"
                value={data?.overdueRate ?? 0}
                suffix="%"
                prefix={<CloseCircleOutlined />}
                valueStyle={{ color: data && data.overdueRate <= 10 ? '#3f8600' : 'var(--color-error-active)' }}
              />
            </Card>
          </Col>
        </Row>

        <Card title="医生工作量排行">
          <Table
            dataSource={data?.doctorRanking || []}
            columns={columns}
            rowKey="doctorId"
            pagination={false}
            size="small"
          />
        </Card>
      </Spin>
    </PageContainer>
  );
};

export default FollowUpStatisticsPage;
