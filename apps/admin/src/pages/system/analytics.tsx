import { useState, useEffect, Suspense, lazy, ComponentType } from 'react';
import { PageContainer } from '@ant-design/pro-components';
import { Card, Row, Col, Statistic, Table, Select, Typography, Space, Tag, Spin } from 'antd';
import {
  EyeOutlined,
  UserOutlined,
  AimOutlined,
  SearchOutlined,
  ClockCircleOutlined,
} from '@ant-design/icons';
import { request } from '@hospital/api';

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

const { Title, Text } = Typography;

// 平台选项
const PLATFORM_OPTIONS = [
  { label: '全部平台', value: '' },
  { label: 'Admin 后台', value: 'admin' },
  { label: 'H5 患者端', value: 'h5' },
  { label: '小程序', value: 'miniapp' },
];

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

const AnalyticsPage: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [platform, setPlatform] = useState('');
  const [days, setDays] = useState(7);
  const [data, setData] = useState<BehaviorOverview | null>(null);

  const fetchData = async () => {
    setLoading(true);
    try {
      const params: Record<string, any> = { days };
      if (platform) {
        params.platform = platform;
      }
      const result = await request.get<BehaviorOverview>('/analytics/overview', { params });
      setData(result);
    } catch (error) {
      console.error('获取数据失败:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [platform, days]);

  // 趋势图配置
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
    xAxis: {
      tickCount: 7,
    },
    yAxis: {
      label: {
        formatter: (v: string) => `${parseInt(v).toLocaleString()}`,
      },
    },
    tooltip: {
      formatter: (datum: any) => ({
        name: datum.type,
        value: datum.value.toLocaleString(),
      }),
    },
  };

  // 页面访问排行配置
  const pageRankConfig = {
    data: data?.top_pages?.slice(0, 10) || [],
    xField: 'view_count',
    yField: 'page_path',
    seriesField: 'page_path',
    legend: false,
    label: {
      position: 'right' as const,
      formatter: (item: any) => item.view_count.toLocaleString(),
    },
    xAxis: {
      label: {
        formatter: (v: string) => parseInt(v).toLocaleString(),
      },
    },
  };

  // 搜索关键词词云配置
  const wordCloudConfig = {
    data: data?.top_keywords?.map(item => ({
      word: item.keyword,
      weight: item.search_count,
    })) || [],
    wordField: 'word',
    weightField: 'weight',
    colorField: 'word',
    wordStyle: {
      fontFamily: 'Verdana',
      fontSize: [14, 48] as [number, number],
      rotation: 0,
    },
    random: () => 0.5,
  };

  // 格式化时长
  const formatDuration = (ms?: number) => {
    if (!ms) return '-';
    const seconds = Math.floor(ms / 1000);
    if (seconds < 60) return `${seconds}秒`;
    const minutes = Math.floor(seconds / 60);
    const remainSeconds = seconds % 60;
    return `${minutes}分${remainSeconds}秒`;
  };

  return (
    <PageContainer>
      <Spin spinning={loading}>
        {/* 筛选区域 */}
        <Card style={{ marginBottom: 16 }}>
          <Space size="large">
            <Space>
              <Text>平台：</Text>
              <Select
                value={platform}
                onChange={setPlatform}
                options={PLATFORM_OPTIONS}
                style={{ width: 150 }}
              />
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

        {/* 核心指标 */}
        <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
          <Col xs={24} sm={12} lg={6}>
            <Card>
              <Statistic
                title="页面访问量 (PV)"
                value={data?.total_page_views || 0}
                prefix={<EyeOutlined />}
                styles={{ content: { color: '#1890ff' } }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <Card>
              <Statistic
                title="独立访客数 (UV)"
                value={data?.total_unique_users || 0}
                prefix={<UserOutlined />}
                styles={{ content: { color: '#52c41a' } }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <Card>
              <Statistic
                title="点击次数"
                value={data?.total_clicks || 0}
                prefix={<AimOutlined />}
                styles={{ content: { color: '#faad14' } }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <Card>
              <Statistic
                title="搜索次数"
                value={data?.total_searches || 0}
                prefix={<SearchOutlined />}
                styles={{ content: { color: '#722ed1' } }}
              />
            </Card>
          </Col>
        </Row>

        {/* 平均停留时长 */}
        {data?.avg_duration && (
          <Card style={{ marginBottom: 16 }}>
            <Space>
              <ClockCircleOutlined style={{ fontSize: 24, color: '#1890ff' }} />
              <div>
                <Text type="secondary">平均页面停留时长</Text>
                <Title level={4} style={{ margin: 0 }}>
                  {formatDuration(data.avg_duration)}
                </Title>
              </div>
            </Space>
          </Card>
        )}

        {/* 趋势图 */}
        <Card title="访问趋势" style={{ marginBottom: 16 }}>
          <Suspense fallback={<ChartLoading />}>
            <Line {...trendConfig} height={300} />
          </Suspense>
        </Card>

        <Row gutter={[16, 16]}>
          {/* 页面访问排行 */}
          <Col xs={24} lg={12}>
            <Card title="页面访问排行 Top 10">
              <Suspense fallback={<ChartLoading />}>
                <Column {...pageRankConfig} height={300} />
              </Suspense>
            </Card>
          </Col>

          {/* 搜索关键词词云 */}
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
          {/* 热门页面详情 */}
          <Col xs={24} lg={12}>
            <Card title="热门页面">
              <Table
                dataSource={data?.top_pages || []}
                columns={[
                  {
                    title: '页面路径',
                    dataIndex: 'page_path',
                    ellipsis: true,
                    render: (path, record) => (
                      <div>
                        <div>{path}</div>
                        {record.page_title && (
                          <Text type="secondary" style={{ fontSize: 12 }}>{record.page_title}</Text>
                        )}
                      </div>
                    ),
                  },
                  {
                    title: 'PV',
                    dataIndex: 'view_count',
                    width: 80,
                    render: (v) => v.toLocaleString(),
                  },
                  {
                    title: 'UV',
                    dataIndex: 'unique_users',
                    width: 80,
                    render: (v) => v.toLocaleString(),
                  },
                ]}
                rowKey="page_path"
                pagination={false}
                size="small"
              />
            </Card>
          </Col>

          {/* 热门点击 */}
          <Col xs={24} lg={12}>
            <Card title="热门点击">
              <Table
                dataSource={data?.top_clicks || []}
                columns={[
                  {
                    title: '元素',
                    render: (_, record) => (
                      <div>
                        <div>{record.element_text || record.element_id || '-'}</div>
                        {record.page_path && (
                          <Text type="secondary" style={{ fontSize: 12 }}>{record.page_path}</Text>
                        )}
                      </div>
                    ),
                  },
                  {
                    title: '点击次数',
                    dataIndex: 'click_count',
                    width: 100,
                    render: (v) => v.toLocaleString(),
                  },
                ]}
                rowKey={(record) => `${record.element_id}-${record.page_path}`}
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

export default AnalyticsPage;

