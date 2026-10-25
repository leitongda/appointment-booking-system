import {PageContainer, ProCard, StatisticCard} from '@ant-design/pro-components';
import {Row, Col, Table, Empty, Spin, DatePicker, Select, Button, message} from 'antd';
import {DownloadOutlined, ReloadOutlined} from '@ant-design/icons';
import {Suspense, lazy, useEffect, useState, type ComponentType} from 'react';
import dayjs from 'dayjs';
import {platformMetricsApi, type PlatformOverviewData, type TenantCompareItem, type StoreCompareItem, type PlatformTrendPoint} from '@hospital/api';
import {downloadBlob} from '@/utils/download';
import './index.less';

// Statistic 子组件未使用
const { RangePicker } = DatePicker;

// @ant-design/charts v2 体积大，按需懒加载
const Line = lazy(() =>
  import('@ant-design/charts').then((m) => ({ default: m.Line as ComponentType<any> }))
);

type DateRange = [dayjs.Dayjs, dayjs.Dayjs];

const OperationsDashboard: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState(false);
  const [dateRange, setDateRange] = useState<DateRange>([
    dayjs().subtract(29, 'day'),
    dayjs(),
  ]);
  const [tenantFilter, setTenantFilter] = useState<string | undefined>(undefined);
  const [overview, setOverview] = useState<PlatformOverviewData | null>(null);
  const [tenants, setTenants] = useState<TenantCompareItem[]>([]);
  const [stores, setStores] = useState<StoreCompareItem[]>([]);
  const [trend, setTrend] = useState<PlatformTrendPoint[]>([]);

  const dateParams = {
    startDate: dateRange[0].format('YYYY-MM-DD'),
    endDate: dateRange[1].format('YYYY-MM-DD'),
  };

  async function loadData() {
    setLoading(true);
    try {
      const [ov, tc, sc, tr] = await Promise.allSettled([
        platformMetricsApi.getOverview(dateParams),
        platformMetricsApi.getTenantsCompare({ ...dateParams, limit: 50 }),
        platformMetricsApi.getStoresCompare({ ...dateParams, tenantId: tenantFilter, limit: 200 }),
        platformMetricsApi.getTrend(dateParams),
      ]);
      if (ov.status === 'fulfilled') setOverview(ov.value);
      if (tc.status === 'fulfilled') setTenants(tc.value);
      if (sc.status === 'fulfilled') setStores(sc.value);
      if (tr.status === 'fulfilled') setTrend(tr.value);
    } catch (e) {
      console.error('加载平台经营数据失败', e);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dateRange, tenantFilter]);

  async function handleExport() {
    setExporting(true);
    try {
      const blob = await platformMetricsApi.exportStoresCompare({
        ...dateParams,
        tenantId: tenantFilter,
        limit: 1000,
      });
      downloadBlob(blob as any, `门店经营对比_${dayjs().format('YYYYMMDD')}.xlsx`);
      message.success('导出成功');
    } catch (e) {
      console.error('导出失败', e);
      message.error('导出失败');
    } finally {
      setExporting(false);
    }
  }

  // 趋势图配置：把多指标展平为 {date, metric, value}
  const trendChartData = trend.flatMap((p) => [
    { date: p.date, metric: '预约数', value: p.appointmentCount },
    { date: p.date, metric: '已到院', value: p.visitCount },
    { date: p.date, metric: '新患者', value: p.newPatientCount },
  ]);
  const trendConfig = {
    data: trendChartData,
    xField: 'date',
    yField: 'value',
    colorField: 'metric',
    height: 320,
    point: { size: 2 },
  };

  const tenantColumns = [
    { title: '租户', dataIndex: 'tenantName', ellipsis: true },
    { title: '门店数', dataIndex: 'storeCount', width: 80, align: 'center' as const, sorter: (a: TenantCompareItem, b: TenantCompareItem) => a.storeCount - b.storeCount },
    { title: '预约数', dataIndex: 'appointmentCount', width: 90, align: 'right' as const, sorter: (a: TenantCompareItem, b: TenantCompareItem) => a.appointmentCount - b.appointmentCount },
    { title: '已到院', dataIndex: 'visitCount', width: 90, align: 'right' as const },
    { title: '爽约数', dataIndex: 'noShowCount', width: 80, align: 'right' as const },
    {
      title: '爽约率',
      dataIndex: 'noShowRate',
      width: 90,
      align: 'right' as const,
      render: (v: number | null) => (v == null ? '-' : `${v}%`),
    },
    { title: '新患者', dataIndex: 'newPatientCount', width: 80, align: 'right' as const },
    {
      title: '营收',
      dataIndex: 'revenue',
      width: 120,
      align: 'right' as const,
      sorter: (a: TenantCompareItem, b: TenantCompareItem) => a.revenue - b.revenue,
      render: (v: number) => `¥${Number(v || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
    },
  ];

  const storeColumns = [
    { title: '门店', dataIndex: 'storeName', ellipsis: true },
    { title: '所属租户', dataIndex: 'tenantName', ellipsis: true, render: (v: string | null) => v || '-' },
    { title: '预约数', dataIndex: 'appointmentCount', width: 90, align: 'right' as const },
    { title: '已到院', dataIndex: 'visitCount', width: 90, align: 'right' as const },
    { title: '已完成', dataIndex: 'completedCount', width: 90, align: 'right' as const },
    {
      title: '爽约率',
      dataIndex: 'noShowRate',
      width: 90,
      align: 'right' as const,
      render: (v: number | null) => (v == null ? '-' : `${v}%`),
    },
    { title: '新患者', dataIndex: 'newPatientCount', width: 80, align: 'right' as const },
    {
      title: '营收',
      dataIndex: 'revenue',
      width: 120,
      align: 'right' as const,
      render: (v: number) => `¥${Number(v || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
    },
  ];

  const tenantOptions = tenants.map((t) => ({
    label: t.tenantName || '平台级门店',
    value: t.tenantId || '',
  }));

  return (
    <PageContainer
      className="platform-operations-dashboard"
      header={{
        title: '平台经营看板',
        subTitle: '全平台租户/门店经营对比（数据 T+1 预聚合，按就诊日统计）',
      }}
      extra={
        <div className="platform-dashboard-actions">
          <RangePicker
            value={dateRange}
            onChange={(v) => v && v[0] && v[1] && setDateRange([v[0], v[1]])}
          />
          <Button icon={<ReloadOutlined />} onClick={loadData}>
            刷新
          </Button>
          <Button
            type="primary"
            icon={<DownloadOutlined />}
            loading={exporting}
            onClick={handleExport}
          >
            导出门店明细
          </Button>
        </div>
      }
    >
      <Spin spinning={loading}>
        {/* KPI 卡片 */}
        <Row gutter={[16, 16]} className="platform-kpi-section">
          <Col xs={24} sm={12} xl={8} xxl={5}>
            <StatisticCard
              className="platform-kpi-card"
              statistic={{
                title: '涉及租户',
                value: overview?.tenantCount ?? 0,
                description: `有数据门店 ${overview?.activeStoreCount ?? 0} 家`,
              }}
            />
          </Col>
          <Col xs={24} sm={12} xl={8} xxl={5}>
            <StatisticCard
              className="platform-kpi-card"
              statistic={{
                title: '预约总数',
                value: overview?.appointmentCount ?? 0,
                description: `已到院 ${overview?.visitCount ?? 0} · 已完成 ${overview?.completedCount ?? 0}`,
              }}
            />
          </Col>
          <Col xs={24} sm={12} xl={8} xxl={5}>
            <StatisticCard
              className="platform-kpi-card"
              statistic={{
                title: '爽约率',
                value: overview?.noShowRate == null ? '-' : overview.noShowRate,
                suffix: overview?.noShowRate == null ? '' : '%',
                description: `爽约 ${overview?.noShowCount ?? 0} · 取消 ${overview?.cancelledCount ?? 0}`,
              }}
            />
          </Col>
          <Col xs={24} sm={12} xl={8} xxl={4}>
            <StatisticCard
              className="platform-kpi-card"
              statistic={{
                title: '新患者数',
                value: overview?.newPatientCount ?? 0,
                description: '期内首次到店就诊',
              }}
            />
          </Col>
          <Col xs={24} sm={12} xl={8} xxl={5}>
            <StatisticCard
              className="platform-kpi-card"
              statistic={{
                title: '营收（诊费）',
                value: overview?.revenue ?? 0,
                prefix: '¥',
                precision: 2,
                description: '预聚合值，复诊按门诊口径',
              }}
            />
          </Col>
        </Row>

        {/* 趋势图 */}
        <ProCard title="经营趋势" className="platform-chart-section" headerBordered>
          {trend.length > 0 ? (
            <div className="platform-chart-shell">
              <Suspense fallback={<Spin />}>
                <Line {...trendConfig} />
              </Suspense>
            </div>
          ) : (
            <Empty description="暂无数据" style={{ padding: 40 }} />
          )}
        </ProCard>

        {/* 租户对比 */}
        <ProCard
          title="租户经营对比"
          className="platform-table-section"
          headerBordered
        >
          <Table
            rowKey={(r) => r.tenantId || 'platform'}
            size="small"
            columns={tenantColumns}
            dataSource={tenants}
            pagination={false}
            scroll={{ x: 900 }}
            locale={{ emptyText: <Empty description="暂无数据" /> }}
          />
        </ProCard>

        {/* 门店对比 */}
        <ProCard
          title={
            <div className="platform-table-title">
              <span>门店经营对比</span>
              <Select
                allowClear
                placeholder="按租户筛选"
                className="platform-table-filter"
                options={tenantOptions}
                value={tenantFilter}
                onChange={(v) => setTenantFilter(v || undefined)}
              />
            </div>
          }
          className="platform-table-section"
          headerBordered
        >
          <Table
            rowKey={(r) => r.storeId}
            size="small"
            columns={storeColumns}
            dataSource={stores}
            pagination={{ pageSize: 10, showSizeChanger: true }}
            scroll={{ x: 980 }}
            locale={{ emptyText: <Empty description="暂无数据" /> }}
          />
        </ProCard>
      </Spin>
    </PageContainer>
  );
};

export default OperationsDashboard;
