import { PageContainer, ProCard, StatisticCard } from '@ant-design/pro-components';
import { Col, Row, Table, Empty, Spin, Tabs } from 'antd';
import {
  CalendarOutlined,
  CheckCircleOutlined,
  TeamOutlined,
  UserOutlined,
  RiseOutlined,
  PayCircleOutlined,
  ReloadOutlined,
  SyncOutlined,
} from '@ant-design/icons';
import { useEffect, useState, useRef, Suspense, lazy, ComponentType } from 'react';
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
  RetentionItem,
  RevisitRateData,
} from '@hospital/api';
import StoreSection from './components/StoreSection';
import './index.less';

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
    <div style={{ color: 'var(--color-text-tertiary)' }}>图表加载中...</div>
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
  const [retentionData, setRetentionData] = useState<RetentionItem[]>([]);
  const [revisitRate, setRevisitRate] = useState<RevisitRateData | null>(null);

  // 并发锁：currentStoreId 抖动(initialState 频繁更新)时避免叠加请求。
  // 上一次全量加载未完成时,跳过本次触发,等待下一次 currentStoreId 变化再加载。
  const loadingRef = useRef(false);

  const loadData = async () => {
    if (loadingRef.current) return;
    loadingRef.current = true;
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
        statisticsApi.getRetentionRate({ cohort: 'month' }), // 8
        statisticsApi.getRevisitRate(),            // 9
      ]);

      if (results[0].status === 'fulfilled') setOverview(results[0].value);
      if (results[1].status === 'fulfilled') setTrendData(results[1].value);
      if (results[2].status === 'fulfilled') setStatusStats(results[2].value);
      if (results[3].status === 'fulfilled') setDeptRanking(results[3].value);
      if (results[4].status === 'fulfilled') setDoctorRanking(results[4].value);
      if (results[5].status === 'fulfilled') setRevenueTrendData(results[5].value);
      if (results[6].status === 'fulfilled') setTimeSlotData(results[6].value);
      if (results[7].status === 'fulfilled') setWeekdayData(results[7].value);
      if (results[8].status === 'fulfilled') setRetentionData(results[8].value);
      if (results[9].status === 'fulfilled') setRevisitRate(results[9].value);
    } catch (error) {
      console.error('加载数据失败', error);
    } finally {
      setLoading(false);
      loadingRef.current = false;
    }
  };

  useEffect(() => {
    loadData();
  }, [currentStoreId]);

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
    color: 'var(--color-primary)',
    height: 280,
  } : null;

  const weekdayConfig = weekdayData.length > 0 ? {
    data: weekdayData.map(item => ({ name: item.name, count: item.count })),
    xField: 'name',
    yField: 'count',
    label: { position: 'top' as const },
    color: 'var(--color-success)',
    height: 280,
  } : null;

  const retentionConfig = retentionData.length > 0 ? {
    data: retentionData.map(item => ({
      cohort: item.cohort,
      留存率: item.retentionRate,
      留存人数: item.retained,
      队列规模: item.cohortSize,
    })),
    xField: 'cohort',
    yField: '留存率',
    label: {
      position: 'top' as const,
      formatter: (d: any) => `${d['留存率']}%`,
    },
    color: 'var(--color-afternoon)',
    height: 280,
    tooltip: {
      formatter: (d: any) => [
        { name: '留存率', value: `${d['留存率']}%` },
        { name: '留存人数', value: d['留存人数'] },
        { name: '队列规模', value: d['队列规模'] },
      ],
    },
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
    <PageContainer className="dashboard-page">
      <Spin spinning={loading}>
        {/* 核心指标 */}
        <ProCard title="核心指标" headerBordered className="dashboard-section">
          <Row gutter={[16, 16]}>
            <Col xs={24} sm={12} lg={4}>
              <ProCard hoverable className="dashboard-kpi-card">
                <Statistic
                  title="今日预约"
                  value={overview?.todayAppointments ?? '-'}
                  icon={<CalendarOutlined style={{ fontSize: 40, color: 'var(--color-primary)' }} />}
                />
              </ProCard>
            </Col>
            <Col xs={24} sm={12} lg={4}>
              <ProCard hoverable className="dashboard-kpi-card">
                <Statistic
                  title="今日就诊"
                  value={overview?.todayVisits ?? '-'}
                  icon={<CheckCircleOutlined style={{ fontSize: 40, color: 'var(--color-success)' }} />}
                />
              </ProCard>
            </Col>
            <Col xs={24} sm={12} lg={4}>
              <ProCard hoverable className="dashboard-kpi-card">
                <Statistic
                  title="总患者数"
                  value={overview?.totalPatients ?? '-'}
                  icon={<TeamOutlined style={{ fontSize: 40, color: 'var(--color-afternoon)' }} />}
                />
              </ProCard>
            </Col>
            <Col xs={24} sm={12} lg={4}>
              <ProCard hoverable className="dashboard-kpi-card">
                <Statistic
                  title="医生数量"
                  value={overview?.totalDoctors ?? '-'}
                  icon={<UserOutlined style={{ fontSize: 40, color: 'var(--color-queue)' }} />}
                />
              </ProCard>
            </Col>
            <Col xs={24} sm={12} lg={4}>
              <ProCard hoverable className="dashboard-kpi-card">
                <Statistic
                  title="本月预约"
                  value={overview?.monthAppointments ?? '-'}
                  icon={<RiseOutlined style={{ fontSize: 40, color: 'var(--color-evening)' }} />}
                />
              </ProCard>
            </Col>
            <Col xs={24} sm={12} lg={4}>
              <ProCard hoverable className="dashboard-kpi-card">
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
        <Row gutter={[16, 16]} className="dashboard-row">
          <Col xs={24} lg={16} className="dashboard-col">
            <ProCard title="趋势分析" headerBordered className="dashboard-chart-card">
              <Tabs
                items={[
                  {
                    key: 'appointment',
                    label: '预约趋势',
                    children: appointmentTrendConfig ? (
                      <div className="dashboard-chart-shell">
                        <Suspense fallback={<ChartLoading />}>
                          <Line {...appointmentTrendConfig} />
                        </Suspense>
                      </div>
                    ) : (
                      <Empty description="暂无数据" className="dashboard-empty" />
                    ),
                  },
                  {
                    key: 'revenue',
                    label: '收入趋势',
                    children: revenueTrendConfig ? (
                      <div className="dashboard-chart-shell">
                        <Suspense fallback={<ChartLoading />}>
                          <Line {...revenueTrendConfig} />
                        </Suspense>
                      </div>
                    ) : (
                      <Empty description="暂无数据" className="dashboard-empty" />
                    ),
                  },
                ]}
              />
            </ProCard>
          </Col>
          <Col xs={24} lg={8} className="dashboard-col">
            <ProCard title="预约状态分布" headerBordered className="dashboard-chart-card">
              {statusPieConfig ? (
                <div className="dashboard-chart-shell">
                  <Suspense fallback={<ChartLoading />}>
                    <Pie {...statusPieConfig} />
                  </Suspense>
                </div>
              ) : (
                <Empty description="暂无数据" className="dashboard-empty" />
              )}
            </ProCard>
          </Col>
        </Row>

        {/* 时段分布 + 星期分布 */}
        <Row gutter={[16, 16]} className="dashboard-row">
          <Col xs={24} lg={12} className="dashboard-col">
            <ProCard title="时段分布" headerBordered className="dashboard-chart-card">
              {timeSlotConfig ? (
                <div className="dashboard-chart-shell">
                  <Suspense fallback={<ChartLoading />}>
                    <Column {...timeSlotConfig} />
                  </Suspense>
                </div>
              ) : (
                <Empty description="暂无数据" className="dashboard-empty" />
              )}
            </ProCard>
          </Col>
          <Col xs={24} lg={12} className="dashboard-col">
            <ProCard title="星期分布" headerBordered className="dashboard-chart-card">
              {weekdayConfig ? (
                <div className="dashboard-chart-shell">
                  <Suspense fallback={<ChartLoading />}>
                    <Column {...weekdayConfig} />
                  </Suspense>
                </div>
              ) : (
                <Empty description="暂无数据" className="dashboard-empty" />
              )}
            </ProCard>
          </Col>
        </Row>

        {/* 留存率 + 复诊率 */}
        <Row gutter={[16, 16]} className="dashboard-row">
          <Col xs={24} lg={14} className="dashboard-col">
            <ProCard title="用户留存率（按月）" headerBordered className="dashboard-chart-card">
              {retentionConfig ? (
                <div className="dashboard-chart-shell">
                  <Suspense fallback={<ChartLoading />}>
                    <Column {...retentionConfig} />
                  </Suspense>
                </div>
              ) : (
                <Empty description="暂无数据" className="dashboard-empty" />
              )}
            </ProCard>
          </Col>
          <Col xs={24} lg={10} className="dashboard-col">
            <ProCard title="复诊率概览" headerBordered className="dashboard-chart-card">
              {revisitRate ? (
                <Row gutter={[12, 12]} className="dashboard-revisit-grid">
                  <Col xs={24} sm={12}>
                    <div className="dashboard-revisit-item">
                      <Statistic
                        title="复诊用户比例"
                        value={revisitRate.overall.revisitRate}
                        precision={1}
                        suffix="%"
                        prefix={<ReloadOutlined style={{ color: 'var(--color-afternoon)' }} />}
                      />
                      <div style={{ color: 'var(--color-text-tertiary)', fontSize: 12, marginTop: 4 }}>
                        {revisitRate.overall.revisitUsers} / {revisitRate.overall.totalUsers} 用户
                      </div>
                    </div>
                  </Col>
                  <Col xs={24} sm={12}>
                    <div className="dashboard-revisit-item">
                      <Statistic
                        title="医生维度复诊率"
                        value={revisitRate.byDoctor.revisitRate}
                        precision={1}
                        suffix="%"
                        prefix={<SyncOutlined style={{ color: 'var(--color-primary)' }} />}
                      />
                      <div style={{ color: 'var(--color-text-tertiary)', fontSize: 12, marginTop: 4 }}>
                        {revisitRate.byDoctor.revisitPairs} / {revisitRate.byDoctor.totalPairs} 医患对
                      </div>
                    </div>
                  </Col>
                  <Col xs={24} sm={12}>
                    <div className="dashboard-revisit-item">
                      <Statistic
                        title="复诊占比"
                        value={revisitRate.visits.revisitRatio}
                        precision={1}
                        suffix="%"
                        prefix={<RiseOutlined style={{ color: 'var(--color-success)' }} />}
                      />
                      <div style={{ color: 'var(--color-text-tertiary)', fontSize: 12, marginTop: 4 }}>
                        复诊 {revisitRate.visits.revisitVisits} / 总计 {revisitRate.visits.totalVisits} 次
                      </div>
                    </div>
                  </Col>
                  <Col xs={24} sm={12}>
                    <div className="dashboard-revisit-item">
                      <Statistic
                        title="统计周期"
                        value={`${revisitRate.params.startDate} ~ ${revisitRate.params.endDate}`}
                        valueStyle={{ fontSize: 14 }}
                      />
                    </div>
                  </Col>
                </Row>
              ) : (
                <Empty description="暂无数据" className="dashboard-empty" />
              )}
            </ProCard>
          </Col>
        </Row>

        {/* 门店专属区域 */}
        <StoreSection />

        {/* 排行榜 */}
        <ProCard title="排行榜" headerBordered>
          <Row gutter={[16, 16]}>
            <Col xs={24} lg={12} className="dashboard-col">
              <ProCard title="科室排行 TOP10" headerBordered collapsible defaultCollapsed={false} className="dashboard-table-card">
                <Table
                  columns={deptColumns}
                  dataSource={deptRanking.map((item) => ({ ...item, key: item.departmentId }))}
                  pagination={false}
                  size="small"
                  scroll={{ x: 360 }}
                  locale={{ emptyText: <Empty description="暂无数据" /> }}
                />
              </ProCard>
            </Col>
            <Col xs={24} lg={12} className="dashboard-col">
              <ProCard title="医生排行 TOP10" headerBordered collapsible defaultCollapsed={false} className="dashboard-table-card">
                <Table
                  columns={doctorColumns}
                  dataSource={doctorRanking.map((item) => ({ ...item, key: item.doctorId }))}
                  pagination={false}
                  size="small"
                  scroll={{ x: 520 }}
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
