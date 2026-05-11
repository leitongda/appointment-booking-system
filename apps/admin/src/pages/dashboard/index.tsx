import { PageContainer, ProCard, StatisticCard } from '@ant-design/pro-components';
import { Col, Row, Table, Empty, Spin, Tabs } from 'antd';
import {
  CalendarOutlined,
  CheckCircleOutlined,
  TeamOutlined,
  UserOutlined,
  RiseOutlined,
  PayCircleOutlined,
} from '@ant-design/icons';
import { useEffect, useState, Suspense, lazy, ComponentType } from 'react';
import { useModel } from '@umijs/max';
import { statisticsApi } from '@hospital/api';
import type {
  OverviewData,
  TrendItem,
  RevenueTrendItem,
  StatusStatItem,
  DepartmentRankingItem,
  DoctorRankingItem,
  TimeSlotItem,
  WeekdayItem,
} from '@hospital/api';
import StoreSection from './components/StoreSection';

const { Statistic } = StatisticCard;

// 懒加载图表组件
const Line = lazy(() =>
  import('@ant-design/charts').then(m => ({ default: m.Line as ComponentType<any> }))
);
const Column = lazy(() =>
  import('@ant-design/charts').then(m => ({ default: m.Column as ComponentType<any> }))
);
const Pie = lazy(() =>
  import('@ant-design/charts').then(m => ({ default: m.Pie as ComponentType<any> }))
);

const ChartLoading = ({ height = 300 }: { height?: number }) => (
  <div style={{ height, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
    <div style={{ color: '#999' }}>图表加载中...</div>
  </div>
);

const Dashboard: React.FC = () => {
  const { initialState } = useModel('@@initialState');
  const currentStoreId = initialState?.currentStore?.id;

  const [loading, setLoading] = useState(true);
  const [overview, setOverview] = useState<OverviewData | null>(null);
  const [statusStats, setStatusStats] = useState<StatusStatItem[]>([]);
  const [trendData, setTrendData] = useState<TrendItem[]>([]);
  const [revenueTrendData, setRevenueTrendData] = useState<RevenueTrendItem[]>([]);
  const [timeSlotData, setTimeSlotData] = useState<TimeSlotItem[]>([]);
  const [weekdayData, setWeekdayData] = useState<WeekdayItem[]>([]);
  const [deptRanking, setDeptRanking] = useState<DepartmentRankingItem[]>([]);
  const [doctorRanking, setDoctorRanking] = useState<DoctorRankingItem[]>([]);

  useEffect(() => {
    loadData();
  }, [currentStoreId]);

  const loadData = async () => {
    setLoading(true);
    try {
      const results = await Promise.allSettled([
        statisticsApi.getOverview(),               // 0
        statisticsApi.getAppointmentTrend(14),     // 1
        statisticsApi.getAppointmentStatusStats(), // 2
        statisticsApi.getDepartmentRanking(10),    // 3
        statisticsApi.getDoctorRanking(10),        // 4
        statisticsApi.getRevenueTrend(14),         // 5
        statisticsApi.getTimeSlotDistribution(),   // 6
        statisticsApi.getWeekdayDistribution(),    // 7
      ]);

      if (results[0].status === 'fulfilled') setOverview(results[0].value);
      if (results[1].status === 'fulfilled') setTrendData(results[1].value);
      if (results[2].status === 'fulfilled') setStatusStats(results[2].value);
      if (results[3].status === 'fulfilled') setDeptRanking(results[3].value);
      if (results[4].status === 'fulfilled') setDoctorRanking(results[4].value);
      if (results[5].status === 'fulfilled') setRevenueTrendData(results[5].value);
      if (results[6].status === 'fulfilled') setTimeSlotData(results[6].value);
      if (results[7].status === 'fulfilled') setWeekdayData(results[7].value);
    } catch (error) {
      console.error('加载数据失败', error);
    } finally {
      setLoading(false);
    }
  };

  // 图表配置
  const appointmentTrendConfig = trendData.length > 0 ? {
    data: trendData.map(item => ({ date: item.date.slice(5), count: item.count })),
    xField: 'date',
    yField: 'count',
    smooth: true,
    area: { style: { fillOpacity: 0.15 } },
    point: { size: 3 },
    yAxis: { min: 0 },
    tooltip: { formatter: (d: any) => ({ name: '预约数', value: d.count }) },
    height: 280,
  } : null;

  const revenueTrendConfig = revenueTrendData.length > 0 ? {
    data: revenueTrendData.map(item => ({ date: item.date.slice(5), revenue: item.revenue })),
    xField: 'date',
    yField: 'revenue',
    smooth: true,
    area: { style: { fillOpacity: 0.15 } },
    point: { size: 3 },
    yAxis: { min: 0, label: { formatter: (v: string) => `${Number(v).toLocaleString()}` } },
    tooltip: { formatter: (d: any) => ({ name: '收入', value: `${d.revenue.toLocaleString()} 元` }) },
    height: 280,
  } : null;

  const statusPieConfig = statusStats.length > 0 ? {
    data: statusStats.map(item => ({ name: item.name, count: item.count })),
    angleField: 'count',
    colorField: 'name',
    innerRadius: 0.6,
    label: { text: 'name', position: 'outside' as const },
    legend: { position: 'right' as const },
    tooltip: { formatter: (d: any) => ({ name: d.name, value: d.count }) },
    statistic: {
      title: { style: { fontSize: '14px' }, content: '总计' },
      content: { style: { fontSize: '20px', fontWeight: 'bold' }, content: statusStats.reduce((s, i) => s + i.count, 0).toString() },
    },
    height: 280,
  } : null;

  const timeSlotConfig = timeSlotData.length > 0 ? {
    data: timeSlotData.map(item => ({ name: item.name, count: item.count })),
    xField: 'name',
    yField: 'count',
    label: { position: 'top' as const },
    color: '#1890ff',
    height: 280,
  } : null;

  const weekdayConfig = weekdayData.length > 0 ? {
    data: weekdayData.map(item => ({ name: item.name, count: item.count })),
    xField: 'name',
    yField: 'count',
    label: { position: 'top' as const },
    color: '#52c41a',
    height: 280,
  } : null;

  const deptColumns = [
    { title: '排名', dataIndex: 'rank', width: 60, render: (_: any, __: any, index: number) => index + 1 },
    { title: '科室', dataIndex: 'departmentName', ellipsis: true },
    { title: '预约数', dataIndex: 'count', width: 80 },
  ];

  const doctorColumns = [
    { title: '排名', dataIndex: 'rank', width: 60, render: (_: any, __: any, index: number) => index + 1 },
    { title: '医生', dataIndex: 'doctorName', width: 80 },
    { title: '职称', dataIndex: 'title', width: 80 },
    { title: '科室', dataIndex: 'departmentName', ellipsis: true },
    { title: '预约数', dataIndex: 'count', width: 70 },
  ];

  return (
    <PageContainer>
      <Spin spinning={loading}>
        {/* 核心指标 */}
        <ProCard title="核心指标" headerBordered style={{ marginBottom: 16 }}>
          <Row gutter={[16, 16]}>
            <Col xs={24} sm={12} lg={4}>
              <ProCard hoverable>
                <Statistic
                  title="今日预约"
                  value={overview?.todayAppointments ?? '-'}
                  icon={<CalendarOutlined style={{ fontSize: 40, color: '#1890ff' }} />}
                />
              </ProCard>
            </Col>
            <Col xs={24} sm={12} lg={4}>
              <ProCard hoverable>
                <Statistic
                  title="今日就诊"
                  value={overview?.todayVisits ?? '-'}
                  icon={<CheckCircleOutlined style={{ fontSize: 40, color: '#52c41a' }} />}
                />
              </ProCard>
            </Col>
            <Col xs={24} sm={12} lg={4}>
              <ProCard hoverable>
                <Statistic
                  title="总患者数"
                  value={overview?.totalPatients ?? '-'}
                  icon={<TeamOutlined style={{ fontSize: 40, color: '#722ed1' }} />}
                />
              </ProCard>
            </Col>
            <Col xs={24} sm={12} lg={4}>
              <ProCard hoverable>
                <Statistic
                  title="医生数量"
                  value={overview?.totalDoctors ?? '-'}
                  icon={<UserOutlined style={{ fontSize: 40, color: '#13c2c2' }} />}
                />
              </ProCard>
            </Col>
            <Col xs={24} sm={12} lg={4}>
              <ProCard hoverable>
                <Statistic
                  title="本月预约"
                  value={overview?.monthAppointments ?? '-'}
                  icon={<RiseOutlined style={{ fontSize: 40, color: '#fa8c16' }} />}
                />
              </ProCard>
            </Col>
            <Col xs={24} sm={12} lg={4}>
              <ProCard hoverable>
                <Statistic
                  title="本月收入"
                  value={overview?.monthRevenue ?? '-'}
                  precision={2}
                  suffix="元"
                  icon={<PayCircleOutlined style={{ fontSize: 40, color: '#eb2f96' }} />}
                />
              </ProCard>
            </Col>
          </Row>
        </ProCard>

        {/* 趋势 + 状态分布 */}
        <Row gutter={16} style={{ marginBottom: 16 }}>
          <Col xs={24} lg={16}>
            <ProCard title="趋势分析" headerBordered>
              <Tabs
                items={[
                  {
                    key: 'appointment',
                    label: '预约趋势',
                    children: appointmentTrendConfig ? (
                      <Suspense fallback={<ChartLoading />}>
                        <Line {...appointmentTrendConfig} />
                      </Suspense>
                    ) : (
                      <Empty description="暂无数据" style={{ padding: 40 }} />
                    ),
                  },
                  {
                    key: 'revenue',
                    label: '收入趋势',
                    children: revenueTrendConfig ? (
                      <Suspense fallback={<ChartLoading />}>
                        <Line {...revenueTrendConfig} />
                      </Suspense>
                    ) : (
                      <Empty description="暂无数据" style={{ padding: 40 }} />
                    ),
                  },
                ]}
              />
            </ProCard>
          </Col>
          <Col xs={24} lg={8}>
            <ProCard title="预约状态分布" headerBordered style={{ height: '100%' }}>
              {statusPieConfig ? (
                <Suspense fallback={<ChartLoading />}>
                  <Pie {...statusPieConfig} />
                </Suspense>
              ) : (
                <Empty description="暂无数据" style={{ padding: 40 }} />
              )}
            </ProCard>
          </Col>
        </Row>

        {/* 时段分布 + 星期分布 */}
        <Row gutter={16} style={{ marginBottom: 16 }}>
          <Col xs={24} lg={12}>
            <ProCard title="时段分布" headerBordered>
              {timeSlotConfig ? (
                <Suspense fallback={<ChartLoading />}>
                  <Column {...timeSlotConfig} />
                </Suspense>
              ) : (
                <Empty description="暂无数据" style={{ padding: 40 }} />
              )}
            </ProCard>
          </Col>
          <Col xs={24} lg={12}>
            <ProCard title="星期分布" headerBordered>
              {weekdayConfig ? (
                <Suspense fallback={<ChartLoading />}>
                  <Column {...weekdayConfig} />
                </Suspense>
              ) : (
                <Empty description="暂无数据" style={{ padding: 40 }} />
              )}
            </ProCard>
          </Col>
        </Row>

        {/* 门店专属区域 */}
        <StoreSection />

        {/* 排行榜 */}
        <ProCard title="排行榜" headerBordered>
          <Row gutter={[16, 16]}>
            <Col xs={24} lg={12}>
              <ProCard title="科室排行 TOP10" headerBordered collapsible defaultCollapsed={false}>
                <Table
                  columns={deptColumns}
                  dataSource={deptRanking.map((item) => ({ ...item, key: item.departmentId }))}
                  pagination={false}
                  size="small"
                  locale={{ emptyText: <Empty description="暂无数据" /> }}
                />
              </ProCard>
            </Col>
            <Col xs={24} lg={12}>
              <ProCard title="医生排行 TOP10" headerBordered collapsible defaultCollapsed={false}>
                <Table
                  columns={doctorColumns}
                  dataSource={doctorRanking.map((item) => ({ ...item, key: item.doctorId }))}
                  pagination={false}
                  size="small"
                  locale={{ emptyText: <Empty description="暂无数据" /> }}
                />
              </ProCard>
            </Col>
          </Row>
        </ProCard>
      </Spin>
    </PageContainer>
  );
};

export default Dashboard;
