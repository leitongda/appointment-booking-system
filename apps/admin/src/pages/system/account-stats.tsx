import type { ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable } from '@ant-design/pro-components';
import { Card, Row, Col, Statistic, DatePicker, Select, Button, Space, Tag, Spin, App } from 'antd';
import {
  LoginOutlined,
  UserOutlined,
  ClockCircleOutlined,
  FieldTimeOutlined,
  DesktopOutlined,
  MobileOutlined,
  TabletOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import { useState, useEffect, lazy, Suspense, ComponentType, useCallback } from 'react';
import { useRequest } from '@umijs/max';
import { adminApi } from '@hospital/api';
import { createListRequest } from '@/utils/proTable';
import { useListPage } from '@/hooks/useListPage';
import dayjs from 'dayjs';
import type {
  AccountStatsResponse,
  AccountStatsDetail,
  AccountStatsQueryParams,
  DeviceDistribution,
  HourlyDistribution,
} from '@hospital/api';

// ========== 图表懒加载 ==========

const Line = lazy(() =>
  import('@ant-design/charts').then(m => ({ default: m.Line as ComponentType<any> }))
);
const Pie = lazy(() =>
  import('@ant-design/charts').then(m => ({ default: m.Pie as ComponentType<any> }))
);
const Column = lazy(() =>
  import('@ant-design/charts').then(m => ({ default: m.Column as ComponentType<any> }))
);

const ChartLoading = () => (
  <div style={{ height: 300, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
    <Spin />
  </div>
);

// ========== 常量 ==========

const DEVICE_OPTIONS = [
  { label: '全部设备', value: '' },
  { label: '桌面', value: 'desktop' },
  { label: '手机', value: 'mobile' },
  { label: '平板', value: 'tablet' },
];

const DEVICE_MAP: Record<string, { text: string; icon: React.ReactNode; color: string }> = {
  desktop: { text: '桌面', icon: <DesktopOutlined />, color: '#722ed1' },
  mobile: { text: '手机', icon: <MobileOutlined />, color: '#52c41a' },
  tablet: { text: '平板', icon: <TabletOutlined />, color: '#1677ff' },
};

const DEVICE_LABEL_MAP: Record<string, string> = {
  desktop: '桌面',
  mobile: '手机',
  tablet: '平板',
};

// ========== 工具函数 ==========

/**
 * 格式化时长（秒）为可读字符串，复用 online-users.tsx 逻辑
 */
const formatDuration = (seconds: number | undefined | null): string => {
  if (seconds === undefined || seconds === null) return '-';
  if (seconds < 60) return `${seconds}秒`;
  if (seconds < 3600) {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}分${secs > 0 ? secs + '秒' : ''}`;
  }
  const hours = Math.floor(seconds / 3600);
  const mins = Math.floor((seconds % 3600) / 60);
  return `${hours}小时${mins > 0 ? mins + '分' : ''}`;
};

/**
 * 格式化时长（小时）为可读字符串
 */
const formatHours = (hours: number | undefined | null): string => {
  if (hours === undefined || hours === null) return '-';
  if (hours < 1) return `${Math.round(hours * 60)}分钟`;
  if (hours < 24) return `${hours.toFixed(1)}小时`;
  const days = Math.floor(hours / 24);
  const remainHours = Math.round(hours % 24);
  return `${days}天${remainHours > 0 ? remainHours + '小时' : ''}`;
};

// ========== 主页面 ==========

const AccountStatsPage: React.FC = () => {
  const { message } = App.useApp();
  const { actionRef } = useListPage();

  // 筛选状态
  const [dateRange, setDateRange] = useState<[dayjs.Dayjs | null, dayjs.Dayjs | null]>([null, null]);
  const [deviceType, setDeviceType] = useState<string>('');

  // 概览数据请求参数
  const [queryParams, setQueryParams] = useState<AccountStatsQueryParams>({});

  // 概览数据
  const { data: statsData, loading: statsLoading, run: fetchStats } = useRequest(
    () => adminApi.getAccountStats(queryParams),
    {
      refreshDeps: [queryParams],
      onError: () => message.error('加载账号统计数据失败'),
    },
  );

  // 处理查询
  const handleQuery = useCallback(() => {
    const params: AccountStatsQueryParams = {};
    if (dateRange[0]) params.startDate = dateRange[0].format('YYYY-MM-DD');
    if (dateRange[1]) params.endDate = dateRange[1].format('YYYY-MM-DD');
    setQueryParams(params);
    actionRef.current?.reload();
  }, [dateRange]);

  // 处理重置
  const handleReset = useCallback(() => {
    setDateRange([null, null]);
    setDeviceType('');
    setQueryParams({});
    actionRef.current?.reload();
  }, []);

  // 明细表格列定义
  const columns: ProColumns<AccountStatsDetail>[] = [
    {
      title: '账号名',
      dataIndex: 'username',
      width: 120,
      ellipsis: true,
      search: false,
    },
    {
      title: '姓名',
      dataIndex: 'name',
      width: 100,
      ellipsis: true,
      search: false,
    },
    {
      title: '关键词搜索',
      dataIndex: 'keyword',
      hideInTable: true,
      fieldProps: { placeholder: '用户名/姓名' },
      search: {
        transform: (value) => ({ keyword: value }),
      },
    },
    {
      title: '角色',
      dataIndex: 'roleName',
      width: 100,
      search: false,
      render: (_, record) =>
        record.roleName ? <Tag color="blue">{record.roleName}</Tag> : '-',
    },
    {
      title: '登录次数',
      dataIndex: 'loginCount',
      width: 100,
      sorter: true,
      search: false,
      render: (_, record) => (
        <span style={{ fontWeight: 500 }}>{record.loginCount?.toLocaleString() ?? 0}</span>
      ),
    },
    {
      title: '总使用时长',
      dataIndex: 'totalDurationSeconds',
      width: 130,
      search: false,
      render: (_, record) => formatDuration(record.totalDurationSeconds),
    },
    {
      title: '最后登录时间',
      dataIndex: 'lastLoginAt',
      width: 170,
      valueType: 'dateTime',
      search: false,
      sorter: true,
    },
    {
      title: '最后登录IP',
      dataIndex: 'lastLoginIp',
      width: 130,
      search: false,
      render: (_, record) =>
        record.lastLoginIp ? <Tag>{record.lastLoginIp}</Tag> : '-',
    },
    {
      title: '常用设备',
      dataIndex: 'primaryDevice',
      width: 100,
      search: false,
      render: (_, record) => {
        if (!record.primaryDevice) return '-';
        const device = DEVICE_MAP[record.primaryDevice];
        return device ? (
          <Tag icon={device.icon} color={device.color}>
            {device.text}
          </Tag>
        ) : (
          <Tag>{record.primaryDevice}</Tag>
        );
      },
    },
    {
      title: '常用浏览器',
      dataIndex: 'primaryBrowser',
      width: 110,
      search: false,
      ellipsis: true,
      render: (_, record) => record.primaryBrowser || '-',
    },
  ];

  // ========== 图表数据 ==========

  // 登录趋势折线图
  const loginTrendData = (statsData?.dailyTrend || []).map((item: { date: string; count: number }) => ({
    date: item.date,
    登录次数: item.count,
  }));

  const lineConfig = {
    data: loginTrendData,
    xField: 'date',
    yField: '登录次数',
    smooth: true,
    point: { size: 3 },
    xAxis: { tickCount: 7 },
    yAxis: { label: { formatter: (v: string) => parseInt(v).toLocaleString() } },
    tooltip: {
      formatter: (datum: any) => ({ name: '登录次数', value: datum.登录次数.toLocaleString() }),
    },
  };

  // 设备分布饼图
  const deviceData = (statsData?.deviceDistribution || []).map((item: DeviceDistribution) => ({
    type: DEVICE_LABEL_MAP[item.deviceType] || item.deviceType,
    value: item.count,
  }));

  const devicePieConfig = {
    data: deviceData,
    angleField: 'value',
    colorField: 'type',
    radius: 0.8,
    innerRadius: 0.5,
    label: {
      type: 'inner',
      offset: '-30%',
      content: '{percentage}',
      style: { fontSize: 14, textAlign: 'center' as const },
    },
    interactions: [{ type: 'element-active' }],
    legend: { position: 'bottom' as const },
  };

  // 登录时段柱状图
  const hourlyData = (statsData?.hourlyDistribution || []).map((item: HourlyDistribution) => ({
    hour: `${String(item.hour).padStart(2, '0')}:00`,
    次数: item.count,
  }));

  const columnConfig = {
    data: hourlyData,
    xField: 'hour',
    yField: '次数',
    columnWidthRatio: 0.6,
    xAxis: { label: { autoRotate: false } },
    yAxis: { label: { formatter: (v: string) => parseInt(v).toLocaleString() } },
    tooltip: {
      formatter: (datum: any) => ({ name: '登录次数', value: datum.次数.toLocaleString() }),
    },
  };

  // 浏览器分布饼图
  const browserData = (statsData?.browserDistribution || []).map((item: DeviceDistribution) => ({
    type: item.deviceType,
    value: item.count,
  }));

  const browserPieConfig = {
    data: browserData,
    angleField: 'value',
    colorField: 'type',
    radius: 0.8,
    innerRadius: 0.5,
    label: {
      type: 'inner',
      offset: '-30%',
      content: '{percentage}',
      style: { fontSize: 14, textAlign: 'center' as const },
    },
    interactions: [{ type: 'element-active' }],
    legend: { position: 'bottom' as const },
  };

  const summary = statsData?.summary;

  return (
    <PageContainer>
      {/* 过滤区域 */}
      <Card style={{ marginBottom: 16 }}>
        <Space wrap>
          <DatePicker.RangePicker
            value={dateRange}
            onChange={(dates) => setDateRange(dates || [null, null])}
            placeholder={['开始日期', '结束日期']}
            allowClear
            style={{ width: 260 }}
          />
          <Select
            value={deviceType}
            onChange={setDeviceType}
            options={DEVICE_OPTIONS}
            style={{ width: 150 }}
            placeholder="设备类型"
          />
          <Button type="primary" icon={<ReloadOutlined />} onClick={handleQuery}>
            查询
          </Button>
          <Button onClick={handleReset}>重置</Button>
        </Space>
      </Card>

      {/* 顶部统计卡片 */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Card loading={statsLoading}>
            <Statistic
              title="总登录次数"
              value={summary?.totalLogins || 0}
              prefix={<LoginOutlined />}
              styles={{ content: { color: '#1677ff' } }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card loading={statsLoading}>
            <Statistic
              title="活跃账号数"
              value={summary?.activeAccounts || 0}
              prefix={<UserOutlined />}
              styles={{ content: { color: '#52c41a' } }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card loading={statsLoading}>
            <Statistic
              title="平均使用时长"
              value={summary?.avgDurationMinutes || 0}
              suffix="分钟"
              prefix={<ClockCircleOutlined />}
              styles={{ content: { color: '#fa8c16' } }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card loading={statsLoading}>
            <Statistic
              title="总使用时长"
              value={formatHours(summary?.totalDurationHours)}
              prefix={<FieldTimeOutlined />}
              styles={{ content: { color: '#722ed1' } }}
            />
          </Card>
        </Col>
      </Row>

      {/* 第一行图表 */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={12}>
          <Card title="登录趋势">
            <Suspense fallback={<ChartLoading />}>
              <Line {...lineConfig} height={300} />
            </Suspense>
          </Card>
        </Col>
        <Col span={12}>
          <Card title="设备分布">
            <Suspense fallback={<ChartLoading />}>
              <Pie {...devicePieConfig} height={300} />
            </Suspense>
          </Card>
        </Col>
      </Row>

      {/* 第二行图表 */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={12}>
          <Card title="登录时段分布">
            <Suspense fallback={<ChartLoading />}>
              <Column {...columnConfig} height={300} />
            </Suspense>
          </Card>
        </Col>
        <Col span={12}>
          <Card title="浏览器分布">
            <Suspense fallback={<ChartLoading />}>
              <Pie {...browserPieConfig} height={300} />
            </Suspense>
          </Card>
        </Col>
      </Row>

      {/* 底部明细表格 */}
      <ProTable<AccountStatsDetail>
        headerTitle="账号统计明细"
        actionRef={actionRef}
        rowKey="adminId"
        columns={columns}
        request={createListRequest((params) => {
          const queryParams: Record<string, any> = { ...params };
          if (dateRange[0]) queryParams.startDate = dateRange[0].format('YYYY-MM-DD');
          if (dateRange[1]) queryParams.endDate = dateRange[1].format('YYYY-MM-DD');
          if (deviceType) queryParams.deviceType = deviceType;
          return adminApi.getAccountStatsDetails(queryParams);
        })}
        pagination={{ defaultPageSize: 10 }}
        search={{ labelWidth: 'auto', collapsed: false }}
        toolBarRender={() => [
          <Button
            key="refresh"
            icon={<ReloadOutlined />}
            onClick={() => actionRef.current?.reload()}
          >
            刷新
          </Button>,
        ]}
      />
    </PageContainer>
  );
};

export default AccountStatsPage;
