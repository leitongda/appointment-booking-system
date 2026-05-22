import { useState, useEffect, Suspense, lazy, ComponentType, useCallback } from 'react';
import { PageContainer } from '@ant-design/pro-components';
import { Card, Row, Col, Statistic, Table, Select, Typography, Space, Spin, Tabs, Tag, App, DatePicker } from 'antd';
import dayjs from 'dayjs';
import {
  EyeOutlined,
  UserOutlined,
  AimOutlined,
  SearchOutlined,
  ClockCircleOutlined,
  TeamOutlined,
} from '@ant-design/icons';
import { request } from '@hospital/api';
import type { ColumnsType } from 'antd/es/table';

// 图表组件动态加载，减少首屏体积约 1.5MB
const Line = lazy(() =>
  import('@ant-design/charts').then(m => ({ default: m.Line as ComponentType<any> }))
);
const Column = lazy(() =>
  import('@ant-design/charts').then(m => ({ default: m.Column as ComponentType<any> }))
);
const WordCloud = lazy(() =>
  import('@ant-design/charts').then(m => ({ default: m.WordCloud as ComponentType<any> }))
);

// 图表加载占位组件
const ChartLoading = ({ height = 300 }: { height?: number }) => (
  <div style={{ height, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
    <Spin tip="图表加载中..." />
  </div>
);

const { Text, Title } = Typography;

// 平台选项
const PLATFORM_OPTIONS = [
  { label: '全部平台', value: '' },
  { label: 'Admin 后台', value: 'admin' },
  { label: 'H5 患者端', value: 'h5' },
  { label: '小程序', value: 'miniapp' },
];

const EVENT_TYPE_OPTIONS = [
  { label: '全部事件', value: '' },
  { label: '页面访问', value: 'page_view' },
  { label: '页面离开', value: 'page_leave' },
  { label: '点击', value: 'click' },
  { label: '搜索', value: 'search' },
  { label: '自定义', value: 'custom' },
];

const EVENT_TYPE_MAP: Record<string, { text: string; color: string }> = {
  page_view: { text: '页面访问', color: 'blue' },
  page_leave: { text: '页面离开', color: 'default' },
  click: { text: '点击', color: 'orange' },
  search: { text: '搜索', color: 'purple' },
  custom: { text: '自定义', color: 'cyan' },
};

interface BehaviorOverview {
  total_page_views: number;
  total_unique_users: number;
  total_clicks: number;
  total_searches: number;
  avg_duration?: number;
  top_pages: { page_path: string; page_title?: string; view_count: number; unique_users: number }[];
  top_clicks: { element_id?: string; element_text?: string; page_path?: string; click_count: number }[];
  top_keywords: { keyword: string; search_count: number }[];
  daily_stats: { date: string; page_views: number; unique_users: number; clicks: number; searches: number }[];
}

interface BehaviorLog {
  id: string;
  platform: string;
  sessionId: string;
  eventType: string;
  pagePath?: string;
  elementId?: string;
  elementText?: string;
  searchKeyword?: string;
  duration?: number;
  deviceType?: string;
  browser?: string;
  os?: string;
  createdAt: string;
}

interface TenantActivity {
  currentDau: number;
  currentWau: number;
  currentMau: number;
  dailyBreakdown: { date: string; dau: number; totalSessions: number; newUsers: number }[];
}

// ========== 行为概览 Tab ==========

const BehaviorOverviewTab: React.FC = () => {
  const { message } = App.useApp();
  const [loading, setLoading] = useState(false);
  const [platform, setPlatform] = useState('');
  const [days, setDays] = useState(7);
  const [data, setData] = useState<BehaviorOverview | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const params: Record<string, any> = { days };
      if (platform) params.platform = platform;
      const result = await request.get<BehaviorOverview>('/analytics/overview', { params });
      setData(result);
    } catch {
      message.error('加载行为概览数据失败');
    } finally {
      setLoading(false);
    }
  }, [platform, days]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const trendConfig = {
    data: data?.daily_stats?.map(item => [
      { date: item.date, type: '页面访问', value: item.page_views },
      { date: item.date, type: '独立用户', value: item.unique_users },
      { date: item.date, type: '点击次数', value: item.clicks },
    ]).flat() || [],
    xField: 'date',
    yField: 'value',
    seriesField: 'type',
    smooth: true,
    legend: { position: 'top' as const },
    xAxis: { tickCount: 7 },
    yAxis: { label: { formatter: (v: string) => parseInt(v).toLocaleString() } },
    tooltip: { formatter: (datum: any) => ({ name: datum.type, value: datum.value.toLocaleString() }) },
  };

  const pageRankConfig = {
    data: data?.top_pages?.slice(0, 10) || [],
    xField: 'view_count',
    yField: 'page_path',
    seriesField: 'page_path',
    legend: false,
    label: { position: 'right' as const, formatter: (item: any) => item.view_count.toLocaleString() },
    xAxis: { label: { formatter: (v: string) => parseInt(v).toLocaleString() } },
  };

  const wordCloudConfig = {
    data: data?.top_keywords?.map(item => ({ word: item.keyword, weight: item.search_count })) || [],
    wordField: 'word',
    weightField: 'weight',
    colorField: 'word',
    wordStyle: { fontFamily: 'Verdana', fontSize: [14, 48] as [number, number], rotation: 0 },
    random: () => 0.5,
  };

  const formatDuration = (ms?: number) => {
    if (!ms) return '-';
    const seconds = Math.floor(ms / 1000);
    if (seconds < 60) return `${seconds}秒`;
    const minutes = Math.floor(seconds / 60);
    return `${minutes}分${seconds % 60}秒`;
  };

  return (
    <Spin spinning={loading}>
      <Card style={{ marginBottom: 16 }}>
        <Space size="large">
          <Space>
            <Text>平台：</Text>
            <Select value={platform} onChange={setPlatform} options={PLATFORM_OPTIONS} style={{ width: 150 }} />
          </Space>
          <Space>
            <Text>时间范围：</Text>
            <Select
              value={days}
              onChange={setDays}
              options={[
                { label: '最近 7 天', value: 7 },
                { label: '最近 14 天', value: 14 },
                { label: '最近 30 天', value: 30 },
                { label: '最近 90 天', value: 90 },
              ]}
              style={{ width: 150 }}
            />
          </Space>
        </Space>
      </Card>

      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic title="页面访问量 (PV)" value={data?.total_page_views || 0} prefix={<EyeOutlined />} styles={{ content: { color: '#1890ff' } }} />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic title="独立访客数 (UV)" value={data?.total_unique_users || 0} prefix={<UserOutlined />} styles={{ content: { color: '#52c41a' } }} />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic title="点击次数" value={data?.total_clicks || 0} prefix={<AimOutlined />} styles={{ content: { color: '#faad14' } }} />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic title="搜索次数" value={data?.total_searches || 0} prefix={<SearchOutlined />} styles={{ content: { color: '#722ed1' } }} />
          </Card>
        </Col>
      </Row>

      {data?.avg_duration && (
        <Card style={{ marginBottom: 16 }}>
          <Space>
            <ClockCircleOutlined style={{ fontSize: 24, color: '#1890ff' }} />
            <div>
              <Text type="secondary">平均页面停留时长</Text>
              <Title level={4} style={{ margin: 0 }}>{formatDuration(data.avg_duration)}</Title>
            </div>
          </Space>
        </Card>
      )}

      <Card title="访问趋势" style={{ marginBottom: 16 }}>
        <Suspense fallback={<ChartLoading />}>
          <Line {...trendConfig} height={300} />
        </Suspense>
      </Card>

      <Row gutter={[16, 16]}>
        <Col xs={24} lg={12}>
          <Card title="页面访问排行 Top 10">
            <Suspense fallback={<ChartLoading />}>
              <Column {...pageRankConfig} height={300} />
            </Suspense>
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card title="搜索关键词词云">
            {data?.top_keywords && data.top_keywords.length > 0 ? (
              <Suspense fallback={<ChartLoading />}>
                <WordCloud {...wordCloudConfig} height={300} />
              </Suspense>
            ) : (
              <div style={{ height: 300, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <Text type="secondary">暂无搜索数据</Text>
              </div>
            )}
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} lg={12}>
          <Card title="热门页面">
            <Table
              dataSource={data?.top_pages || []}
              columns={[
                { title: '页面路径', dataIndex: 'page_path', ellipsis: true,
                  render: (path, record) => (
                    <div>
                      <div>{path}</div>
                      {record.page_title && <Text type="secondary" style={{ fontSize: 12 }}>{record.page_title}</Text>}
                    </div>
                  ),
                },
                { title: 'PV', dataIndex: 'view_count', width: 80, render: (v) => v.toLocaleString() },
                { title: 'UV', dataIndex: 'unique_users', width: 80, render: (v) => v.toLocaleString() },
              ]}
              rowKey="page_path"
              pagination={false}
              size="small"
            />
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card title="热门点击">
            <Table
              dataSource={data?.top_clicks || []}
              columns={[
                { title: '元素', render: (_, record) => (
                  <div>
                    <div>{record.element_text || record.element_id || '-'}</div>
                    {record.page_path && <Text type="secondary" style={{ fontSize: 12 }}>{record.page_path}</Text>}
                  </div>
                )},
                { title: '点击次数', dataIndex: 'click_count', width: 100, render: (v) => v.toLocaleString() },
              ]}
              rowKey={(record) => `${record.element_id}-${record.page_path}`}
              pagination={false}
              size="small"
            />
          </Card>
        </Col>
      </Row>
    </Spin>
  );
};

// ========== 租户活跃度 Tab ==========

const TenantActivityTab: React.FC = () => {
  const { message } = App.useApp();
  const [loading, setLoading] = useState(false);
  const [days, setDays] = useState(30);
  const [data, setData] = useState<TenantActivity | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const result = await request.get<TenantActivity>('/analytics/tenant-activity', { params: { days } });
      setData(result);
    } catch {
      message.error('加载租户活跃度数据失败');
    } finally {
      setLoading(false);
    }
  }, [days]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const trendConfig = {
    data: data?.dailyBreakdown?.map(item => [
      { date: item.date, type: 'DAU', value: item.dau },
      { date: item.date, type: '新增用户', value: item.newUsers },
    ]).flat() || [],
    xField: 'date',
    yField: 'value',
    seriesField: 'type',
    smooth: true,
    legend: { position: 'top' as const },
    xAxis: { tickCount: 10 },
  };

  return (
    <Spin spinning={loading}>
      <Card style={{ marginBottom: 16 }}>
        <Space>
          <Text>时间范围：</Text>
          <Select
            value={days}
            onChange={setDays}
            options={[
              { label: '最近 7 天', value: 7 },
              { label: '最近 14 天', value: 14 },
              { label: '最近 30 天', value: 30 },
              { label: '最近 90 天', value: 90 },
            ]}
            style={{ width: 150 }}
          />
        </Space>
      </Card>

      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={24} sm={8}>
          <Card>
            <Statistic
              title="今日活跃用户 (DAU)"
              value={data?.currentDau || 0}
              prefix={<UserOutlined />}
              styles={{ content: { color: '#1890ff' } }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card>
            <Statistic
              title="本周活跃用户 (WAU)"
              value={data?.currentWau || 0}
              prefix={<TeamOutlined />}
              styles={{ content: { color: '#52c41a' } }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card>
            <Statistic
              title="本月活跃用户 (MAU)"
              value={data?.currentMau || 0}
              prefix={<TeamOutlined />}
              styles={{ content: { color: '#722ed1' } }}
            />
          </Card>
        </Col>
      </Row>

      <Card title="活跃趋势" style={{ marginBottom: 16 }}>
        <Suspense fallback={<ChartLoading />}>
          <Line {...trendConfig} height={300} />
        </Suspense>
      </Card>

      <Card title="每日活跃明细">
        <Table
          dataSource={data?.dailyBreakdown || []}
          rowKey="date"
          size="small"
          pagination={false}
          columns={[
            { title: '日期', dataIndex: 'date', width: 120 },
            { title: 'DAU', dataIndex: 'dau', width: 100 },
            { title: '会话数', dataIndex: 'totalSessions', width: 100 },
            { title: '新增用户', dataIndex: 'newUsers', width: 100 },
          ]}
        />
      </Card>
    </Spin>
  );
};

// ========== 行为日志 Tab ==========

const BehaviorLogTab: React.FC = () => {
  const { message } = App.useApp();
  const [loading, setLoading] = useState(false);
  const [logs, setLogs] = useState<BehaviorLog[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [platform, setPlatform] = useState('');
  const [eventType, setEventType] = useState('');
  const [dateRange, setDateRange] = useState<[dayjs.Dayjs | null, dayjs.Dayjs | null]>([null, null]);

  const fetchLogs = useCallback(async () => {
    setLoading(true);
    try {
      const params: Record<string, any> = { page, page_size: pageSize };
      if (platform) params.platform = platform;
      if (eventType) params.event_type = eventType;
      if (dateRange[0]) params.start_time = dateRange[0].startOf('day').toISOString();
      if (dateRange[1]) params.end_time = dateRange[1].endOf('day').toISOString();
      const result = await request.get<{ data: BehaviorLog[]; total: number }>('/analytics/logs', { params });
      setLogs(result.data || []);
      setTotal(result.total || 0);
    } catch {
      message.error('加载行为日志失败');
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, platform, eventType, dateRange]);

  useEffect(() => { fetchLogs(); }, [fetchLogs]);

  const columns: ColumnsType<BehaviorLog> = [
    { title: '时间', dataIndex: 'createdAt', width: 170, render: (v) => v?.slice(0, 19)?.replace('T', ' ') || '-' },
    { title: '平台', dataIndex: 'platform', width: 80, render: (v) => <Tag>{v || '-'}</Tag> },
    {
      title: '事件类型', dataIndex: 'eventType', width: 100,
      render: (v) => {
        const item = EVENT_TYPE_MAP[v];
        return <Tag color={item?.color || 'default'}>{item?.text || v}</Tag>;
      },
    },
    { title: '页面路径', dataIndex: 'pagePath', ellipsis: true },
    { title: '元素', ellipsis: true, render: (_, r) => r.elementText || r.elementId || '-' },
    { title: '搜索词', dataIndex: 'searchKeyword', width: 120, ellipsis: true },
    { title: '停留(ms)', dataIndex: 'duration', width: 90, render: (v) => v ? v.toLocaleString() : '-' },
    { title: '设备', width: 80, render: (_, r) => r.deviceType || '-' },
    { title: '浏览器', width: 90, render: (_, r) => r.browser || '-' },
  ];

  return (
    <Spin spinning={loading}>
      <Card style={{ marginBottom: 16 }}>
        <Space size="large" wrap>
          <Space>
            <Text>平台：</Text>
            <Select
              value={platform}
              onChange={(v) => { setPlatform(v); setPage(1); }}
              options={PLATFORM_OPTIONS}
              style={{ width: 150 }}
            />
          </Space>
          <Space>
            <Text>事件类型：</Text>
            <Select
              value={eventType}
              onChange={(v) => { setEventType(v); setPage(1); }}
              options={EVENT_TYPE_OPTIONS}
              style={{ width: 150 }}
            />
          </Space>
          <Space>
            <Text>日期范围：</Text>
            <DatePicker.RangePicker
              value={dateRange}
              onChange={(dates) => { setDateRange(dates || [null, null]); setPage(1); }}
              placeholder={['开始日期', '结束日期']}
              allowClear
              style={{ width: 260 }}
            />
          </Space>
        </Space>
      </Card>

      <Card>
        <Table
          dataSource={logs}
          columns={columns}
          rowKey="id"
          size="small"
          scroll={{ x: 1000 }}
          pagination={{
            current: page,
            pageSize,
            total,
            showSizeChanger: true,
            showTotal: (t) => `共 ${t} 条`,
            onChange: (p, ps) => { setPage(p); setPageSize(ps); },
          }}
        />
      </Card>
    </Spin>
  );
};

// ========== 主页面 ==========

const AnalyticsPage: React.FC = () => {
  return (
    <PageContainer>
      <Tabs
        defaultActiveKey="overview"
        items={[
          { key: 'overview', label: '行为概览', children: <BehaviorOverviewTab /> },
          { key: 'activity', label: '租户活跃度', children: <TenantActivityTab /> },
          { key: 'logs', label: '行为日志', children: <BehaviorLogTab /> },
        ]}
      />
    </PageContainer>
  );
};

export default AnalyticsPage;
