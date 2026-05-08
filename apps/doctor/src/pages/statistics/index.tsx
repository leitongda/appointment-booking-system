import { PageContainer, ProCard, StatisticCard } from '@ant-design/pro-components';
import { Col, Row, DatePicker, Spin, Segmented } from 'antd';
import { Line, Column } from '@ant-design/charts';
import { useState, useEffect } from 'react';
import { statisticsApi } from '@hospital/api';
import type { TrendItem, StatusStatItem } from '@hospital/api';

const { Statistic } = StatisticCard;

const StatisticsPage: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [days, setDays] = useState<number>(7);
  const [trendData, setTrendData] = useState<TrendItem[]>([]);
  const [statusData, setStatusData] = useState<StatusStatItem[]>([]);

  // 汇总统计
  const totalAppointments = trendData.reduce((sum, item) => sum + item.count, 0);
  const completedCount = statusData.find(s => s.status === 5)?.count || 0;
  const cancelledCount = statusData.find(s => s.status === 6)?.count || 0;
  const noShowCount = statusData.find(s => s.status === 8)?.count || 0;  // 8=NO_SHOW(爽约)
  const completionRate = totalAppointments > 0 ? ((completedCount / totalAppointments) * 100).toFixed(1) : '0';
  const noShowRate = totalAppointments > 0 ? ((noShowCount / totalAppointments) * 100).toFixed(1) : '0';

  useEffect(() => {
    loadData();
  }, [days]);

  const loadData = async () => {
    setLoading(true);
    try {
      const [trend, status] = await Promise.all([
        statisticsApi.getMyAppointmentTrend(days),
        statisticsApi.getMyAppointmentStatusStats(),
      ]);
      setTrendData(trend);
      setStatusData(status);
    } catch (error) {
      console.error('加载数据失败', error);
    } finally {
      setLoading(false);
    }
  };

  const trendConfig = {
    data: trendData,
    xField: 'date',
    yField: 'count',
    smooth: true,
    point: { size: 4, shape: 'circle' },
    color: '#1890ff',
    height: 300,
    xAxis: {
      label: {
        formatter: (v: string) => v.substring(5),
      },
    },
    tooltip: {
      formatter: (datum: TrendItem) => ({
        name: '就诊数',
        value: datum.count,
      }),
    },
  };

  const statusColumnConfig = {
    data: statusData.filter(s => s.count > 0),
    xField: 'name',
    yField: 'count',
    color: ({ name }: { name: string }) => {
      const colorMap: Record<string, string> = {
        '待支付': '#FA8C16',
        '已预约': '#1890ff',
        '已签到': '#13c2c2',
        '历史候诊': '#94A3B8',
        '就诊中': '#722ed1',
        '已完成': '#52c41a',
        '已取消': '#d9d9d9',
        '已过期': '#BFBFBF',
        '已爽约': '#ff4d4f',
      };
      return colorMap[name] || '#1890ff';
    },
    height: 300,
    label: {
      position: 'middle' as const,
      style: { fill: '#fff' },
    },
  };

  return (
    <PageContainer 
      extra={
        <Segmented
          options={[
            { label: '近7天', value: 7 },
            { label: '近14天', value: 14 },
            { label: '近30天', value: 30 },
          ]}
          value={days}
          onChange={(value) => setDays(value as number)}
        />
      }
    >
      <Spin spinning={loading}>
        <Row gutter={[16, 16]}>
          <Col xs={24} sm={12} lg={6}>
            <ProCard>
              <Statistic title={`近${days}天就诊`} value={completedCount} suffix="人次" />
            </ProCard>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <ProCard>
              <Statistic title={`近${days}天预约`} value={totalAppointments} suffix="人次" />
            </ProCard>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <ProCard>
              <Statistic 
                title="完成率" 
                value={completionRate} 
                suffix="%" 
                valueStyle={{ color: Number(completionRate) >= 80 ? '#52c41a' : '#faad14' }}
              />
            </ProCard>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <ProCard>
              <Statistic 
                title="爽约率" 
                value={noShowRate} 
                suffix="%" 
                valueStyle={{ color: Number(noShowRate) <= 5 ? '#52c41a' : '#ff4d4f' }}
              />
            </ProCard>
          </Col>
        </Row>

        <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
          <Col xs={24} lg={16}>
            <ProCard title="就诊趋势" headerBordered>
              {trendData.length > 0 ? (
                <Line {...trendConfig} />
              ) : (
                <div style={{ height: 300, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#999' }}>
                  暂无数据
                </div>
              )}
            </ProCard>
          </Col>
          <Col xs={24} lg={8}>
            <ProCard title="预约状态分布" headerBordered>
              {statusData.length > 0 ? (
                <Column {...statusColumnConfig} />
              ) : (
                <div style={{ height: 300, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#999' }}>
                  暂无数据
                </div>
              )}
            </ProCard>
          </Col>
        </Row>
      </Spin>
    </PageContainer>
  );
};

export default StatisticsPage;
