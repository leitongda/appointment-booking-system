import { SearchOutlined } from '@ant-design/icons';
import { PageContainer } from '@ant-design/pro-components';
import { Button, Card, Form, Select, DatePicker, Table, Tag, Empty, Row, Col, Statistic, message, Tabs } from 'antd';
import { useState, Suspense, lazy, ComponentType } from 'react';
import { useAccess } from '@umijs/max';
import { scheduleApi } from '@hospital/api';
import { useStoreWithPermission } from '@/hooks/useStoreWithPermission';
import type { ScheduleStatisticsItem, ScheduleStatisticsResponse, UtilizationTrendResponse, DoctorWorkloadResponse, PeakHourHeatmapResponse } from '@hospital/api';
import dayjs from 'dayjs';

// 图表组件动态加载，减少首屏体积
const Line = lazy(() =>
  import('@ant-design/charts').then(m => ({ default: m.Line as ComponentType<any> }))
);
const Column = lazy(() =>
  import('@ant-design/charts').then(m => ({ default: m.Column as ComponentType<any> }))
);
const Heatmap = lazy(() =>
  import('@ant-design/charts').then(m => ({ default: m.Heatmap as ComponentType<any> }))
);

// 图表加载占位组件
const ChartLoading = ({ height = 300 }: { height?: number }) => (
  <div style={{ height, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
    <div>图表加载中...</div>
  </div>
);

const ScheduleStatisticsPage: React.FC = () => {
  const [form] = Form.useForm();
  const access = useAccess();
  const { stores } = useStoreWithPermission({ enabledOnly: true });
  const [loading, setLoading] = useState(false);
  const [statistics, setStatistics] = useState<ScheduleStatisticsResponse | null>(null);

  // 增强统计状态
  const [trendData, setTrendData] = useState<UtilizationTrendResponse | null>(null);
  const [workloadData, setWorkloadData] = useState<DoctorWorkloadResponse | null>(null);
  const [heatmapData, setHeatmapData] = useState<PeakHourHeatmapResponse | null>(null);
  const [chartLoading, setChartLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('detail');

  const handleQuery = async () => {
    const values = form.getFieldsValue();
    if (!values.storeId || !values.month) {
      return;
    }

    setLoading(true);
    try {
      const result = await scheduleApi.getStatistics({
        storeId: values.storeId,
        year: values.month.year(),
        month: values.month.month() + 1,
      });
      setStatistics(result);
    } catch (error: any) {
      console.error('查询失败', error);
      message.error('查询统计数据失败');
    } finally {
      setLoading(false);
    }
  };

  const fetchEnhancedStats = async () => {
    const values = form.getFieldsValue();
    if (!values.storeId || !values.dateRange || values.dateRange.length !== 2) {
      message.warning('请选择门店和日期范围');
      return;
    }

    setChartLoading(true);
    const storeId = values.storeId;
    const startDate = values.dateRange[0].format('YYYY-MM-DD');
    const endDate = values.dateRange[1].format('YYYY-MM-DD');

    try {
      const [trend, workload, heatmap] = await Promise.all([
        scheduleApi.getUtilizationTrend({
          storeId,
          startDate,
          endDate,
          granularity: values.granularity || 'week',
        }),
        scheduleApi.getDoctorWorkload({ storeId, startDate, endDate }),
        scheduleApi.getPeakHours({ storeId, startDate, endDate }),
      ]);
      setTrendData(trend);
      setWorkloadData(workload);
      setHeatmapData(heatmap);
    } catch (error: any) {
      console.error('查询增强统计失败', error);
      message.error('查询增强统计数据失败');
    } finally {
      setChartLoading(false);
    }
  };

  const handleExportCSV = () => {
    if (!statistics || !statistics.items || statistics.items.length === 0) {
      message.warning('暂无数据可导出');
      return;
    }

    const headers = ['日期', '医生', '上午号源', '上午已预约', '下午号源', '下午已预约', '晚间号源', '晚间已预约'];
    const rows = statistics.items.map(item =>
      [item.scheduleDate, item.doctorName, item.morningSlots, item.morningBooked, item.afternoonSlots, item.afternoonBooked, item.eveningSlots, item.eveningBooked].join(',')
    );
    const csvContent = '﻿' + [headers.join(','), ...rows].join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    const monthStr = `${statistics.year}${String(statistics.month).padStart(2, '0')}`;
    link.href = url;
    link.download = `排班统计_${statistics.storeName}_${monthStr}.csv`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  // 按日期分组数据
  const groupByDate = (items: ScheduleStatisticsItem[]) => {
    const grouped: Record<string, ScheduleStatisticsItem[]> = {};
    items.forEach(item => {
      if (!grouped[item.scheduleDate]) {
        grouped[item.scheduleDate] = [];
      }
      grouped[item.scheduleDate].push(item);
    });
    return grouped;
  };

  // 计算汇总数据
  const calculateSummary = (items: ScheduleStatisticsItem[]) => {
    let totalMorningSlots = 0;
    let totalAfternoonSlots = 0;
    let totalEveningSlots = 0;
    let totalMorningBooked = 0;
    let totalAfternoonBooked = 0;
    let totalEveningBooked = 0;

    items.forEach(item => {
      totalMorningSlots += item.morningSlots;
      totalAfternoonSlots += item.afternoonSlots;
      totalEveningSlots += item.eveningSlots;
      totalMorningBooked += item.morningBooked;
      totalAfternoonBooked += item.afternoonBooked;
      totalEveningBooked += item.eveningBooked;
    });

    return {
      totalSlots: totalMorningSlots + totalAfternoonSlots + totalEveningSlots,
      totalBooked: totalMorningBooked + totalAfternoonBooked + totalEveningBooked,
      morningSlots: totalMorningSlots,
      afternoonSlots: totalAfternoonSlots,
      eveningSlots: totalEveningSlots,
      morningBooked: totalMorningBooked,
      afternoonBooked: totalAfternoonBooked,
      eveningBooked: totalEveningBooked,
    };
  };

  const columns = [
    {
      title: '日期',
      dataIndex: 'scheduleDate',
      width: 120,
      render: (text: string) => {
        const date = dayjs(text);
        const weekday = ['日', '一', '二', '三', '四', '五', '六'][date.day()];
        return `${text} 周${weekday}`;
      },
    },
    {
      title: '医生',
      dataIndex: 'doctorName',
      width: 100,
    },
    {
      title: '上午',
      children: [
        {
          title: '号源',
          dataIndex: 'morningSlots',
          width: 80,
          render: (val: number) => val || '-',
        },
        {
          title: '已预约',
          dataIndex: 'morningBooked',
          width: 80,
          render: (val: number, record: ScheduleStatisticsItem) => {
            if (!record.morningSlots) return '-';
            const rate = record.morningSlots > 0 ? (val / record.morningSlots * 100).toFixed(0) : 0;
            return (
              <span>
                {val}
                <Tag color={Number(rate) > 80 ? 'red' : Number(rate) > 50 ? 'orange' : 'green'} style={{ marginLeft: 4 }}>
                  {rate}%
                </Tag>
              </span>
            );
          },
        },
      ],
    },
    {
      title: '下午',
      children: [
        {
          title: '号源',
          dataIndex: 'afternoonSlots',
          width: 80,
          render: (val: number) => val || '-',
        },
        {
          title: '已预约',
          dataIndex: 'afternoonBooked',
          width: 80,
          render: (val: number, record: ScheduleStatisticsItem) => {
            if (!record.afternoonSlots) return '-';
            const rate = record.afternoonSlots > 0 ? (val / record.afternoonSlots * 100).toFixed(0) : 0;
            return (
              <span>
                {val}
                <Tag color={Number(rate) > 80 ? 'red' : Number(rate) > 50 ? 'orange' : 'green'} style={{ marginLeft: 4 }}>
                  {rate}%
                </Tag>
              </span>
            );
          },
        },
      ],
    },
    {
      title: '晚间',
      children: [
        {
          title: '号源',
          dataIndex: 'eveningSlots',
          width: 80,
          render: (val: number) => val || '-',
        },
        {
          title: '已预约',
          dataIndex: 'eveningBooked',
          width: 80,
          render: (val: number, record: ScheduleStatisticsItem) => {
            if (!record.eveningSlots) return '-';
            const rate = record.eveningSlots > 0 ? (val / record.eveningSlots * 100).toFixed(0) : 0;
            return (
              <span>
                {val}
                <Tag color={Number(rate) > 80 ? 'red' : Number(rate) > 50 ? 'orange' : 'green'} style={{ marginLeft: 4 }}>
                  {rate}%
                </Tag>
              </span>
            );
          },
        },
      ],
    },
  ];

  const summary = statistics ? calculateSummary(statistics.items) : null;

  // 利用率趋势图配置
  const trendConfig = trendData && trendData.items.length > 0 ? {
    data: trendData.items.map(item => ({
      period: item.period,
      value: item.utilizationRate,
      type: '利用率(%)',
    })),
    xField: 'period',
    yField: 'value',
    seriesField: 'type',
    smooth: true,
    yAxis: {
      min: 0,
      max: 100,
      label: { formatter: (v: string) => `${v}%` },
    },
    tooltip: {
      formatter: (data: any) => {
        return { name: '利用率', value: `${data.value}%` };
      },
    },
    height: 300,
  } : null;

  // 医生工作量对比图配置
  const workloadConfig = workloadData && workloadData.items.length > 0 ? {
    data: workloadData.items.map(item => ({
      doctor: item.doctorName,
      value: item.utilizationRate,
      type: '利用率(%)',
    })),
    xField: 'doctor',
    yField: 'value',
    seriesField: 'type',
    label: {
      position: 'top',
      formatter: (data: any) => `${data.value}%`,
    },
    yAxis: {
      min: 0,
      max: 100,
      label: { formatter: (v: string) => `${v}%` },
    },
    height: 300,
  } : null;

  // 高峰时段热力图配置
  const heatmapConfig = heatmapData && heatmapData.cells.length > 0 ? {
    data: heatmapData.cells
      .filter((cell: any) => cell.totalSlots > 0)
      .map((cell: any) => ({
        day: ['周一', '周二', '周三', '周四', '周五', '周六', '周日'][cell.dayOfWeek - 1],
        hour: `${String(cell.hour).padStart(2, '0')}:00`,
        value: cell.bookingRate,
      })),
    xField: 'day',
    yField: 'hour',
    colorField: 'value',
    height: 400,
    color: ['#e6f7ff', '#1890ff', '#096dd9', '#0050b3'],
    tooltip: {
      formatter: (data: any) => {
        return { name: '预约率', value: `${data.value}%` };
      },
    },
  } : null;

  const workloadColumns = [
    { title: '医生', dataIndex: 'doctorName', width: 120 },
    { title: '科室', dataIndex: 'departmentName', width: 120 },
    { title: '总号源', dataIndex: 'totalSlots', width: 100 },
    { title: '已预约', dataIndex: 'bookedSlots', width: 100 },
    { title: '已完成', dataIndex: 'completedAppointments', width: 100 },
    {
      title: '利用率',
      dataIndex: 'utilizationRate',
      width: 120,
      render: (val: number) => (
        <span>
          {val}%
          <Tag color={val > 80 ? 'red' : val > 50 ? 'orange' : 'green'} style={{ marginLeft: 4 }}>
            {val > 80 ? '高' : val > 50 ? '中' : '低'}
          </Tag>
        </span>
      ),
    },
    { title: '排班天数', dataIndex: 'scheduleDays', width: 100 },
  ];

  return (
    <PageContainer>
      <Card title="查询条件" style={{ marginBottom: 16 }}>
        <Form form={form} layout="inline">
          <Form.Item name="storeId" label="选择门店" rules={[{ required: true }]}>
            <Select
              style={{ width: 200 }}
              placeholder="请选择门店"
              options={stores.map(s => ({ label: s.name, value: s.id }))}
            />
          </Form.Item>
          <Form.Item name="month" label="选择月份" rules={[{ required: true }]}>
            <DatePicker.MonthPicker placeholder="选择月份" />
          </Form.Item>
          <Form.Item>
            <Button
              type="primary"
              icon={<SearchOutlined />}
              onClick={handleQuery}
              loading={loading}
            >
              查询
            </Button>
          </Form.Item>
          <Form.Item>
            <Button
              onClick={handleExportCSV}
              disabled={!statistics || !statistics.items || statistics.items.length === 0}
            >
              导出 CSV
            </Button>
          </Form.Item>
        </Form>
        <div style={{ marginTop: 8, fontSize: 12, color: '#999' }}>
          查询流程：选择门店 &gt; 选择月份
        </div>
      </Card>

      {statistics && summary && (
        <>
          <Card title="统计汇总" style={{ marginBottom: 16 }}>
            <Row gutter={16}>
              <Col span={4}>
                <Statistic title="门店" value={statistics.storeName} />
              </Col>
              <Col span={4}>
                <Statistic title="月份" value={`${statistics.year}年${statistics.month}月`} />
              </Col>
              <Col span={4}>
                <Statistic title="总号源" value={summary.totalSlots} />
              </Col>
              <Col span={4}>
                <Statistic title="总预约" value={summary.totalBooked} />
              </Col>
              <Col span={4}>
                <Statistic
                  title="预约率"
                  value={summary.totalSlots > 0 ? (summary.totalBooked / summary.totalSlots * 100).toFixed(1) : 0}
                  suffix="%"
                />
              </Col>
              <Col span={4}>
                <Statistic title="排班天数" value={Object.keys(groupByDate(statistics.items)).length} suffix="天" />
              </Col>
            </Row>
          </Card>

          <Card title="时段统计" style={{ marginBottom: 16 }}>
            <Row gutter={16}>
              <Col span={8}>
                <Statistic title="上午号源" value={summary.morningSlots} />
                <div style={{ fontSize: 12, color: '#999', marginTop: 4 }}>
                  已预约: {summary.morningBooked} ({summary.morningSlots > 0 ? (summary.morningBooked / summary.morningSlots * 100).toFixed(1) : 0}%)
                </div>
              </Col>
              <Col span={8}>
                <Statistic title="下午号源" value={summary.afternoonSlots} />
                <div style={{ fontSize: 12, color: '#999', marginTop: 4 }}>
                  已预约: {summary.afternoonBooked} ({summary.afternoonSlots > 0 ? (summary.afternoonBooked / summary.afternoonSlots * 100).toFixed(1) : 0}%)
                </div>
              </Col>
              <Col span={8}>
                <Statistic title="晚间号源" value={summary.eveningSlots} />
                <div style={{ fontSize: 12, color: '#999', marginTop: 4 }}>
                  已预约: {summary.eveningBooked} ({summary.eveningSlots > 0 ? (summary.eveningBooked / summary.eveningSlots * 100).toFixed(1) : 0}%)
                </div>
              </Col>
            </Row>
          </Card>
        </>
      )}

      <Card title="排班明细">
        {statistics && statistics.items.length > 0 ? (
          <Table
            columns={columns}
            dataSource={statistics.items}
            rowKey={(record) => `${record.scheduleDate}-${record.doctorId}`}
            pagination={{ pageSize: 20 }}
            bordered
            size="small"
            scroll={{ x: 1000 }}
          />
        ) : (
          <Empty description="暂无数据" />
        )}
      </Card>

      {/* 增强统计区域 */}
      <Card title="统计增强分析" style={{ marginTop: 16 }}>
        <Form layout="inline" style={{ marginBottom: 16 }}>
          <Form.Item name="dateRange" label="日期范围" rules={[{ required: true }]}>
            <DatePicker.RangePicker placeholder={['开始日期', '结束日期']} />
          </Form.Item>
          <Form.Item name="granularity" label="粒度" initialValue="week">
            <Select style={{ width: 120 }} options={[
              { label: '按周', value: 'week' },
              { label: '按月', value: 'month' },
            ]} />
          </Form.Item>
          <Form.Item>
            <Button type="primary" icon={<SearchOutlined />} onClick={fetchEnhancedStats} loading={chartLoading}>
              查询增强统计
            </Button>
          </Form.Item>
        </Form>

        <Tabs activeKey={activeTab} onChange={setActiveTab}>
          <Tabs.TabPane tab="利用率趋势" key="trend">
            {trendData && trendData.items.length > 0 && trendConfig ? (
              <Suspense fallback={<ChartLoading />}>
                <Line {...trendConfig} />
              </Suspense>
            ) : (
              <Empty description="暂无数据，请先查询" />
            )}
          </Tabs.TabPane>
          <Tabs.TabPane tab="医生工作量对比" key="workload">
            {workloadData && workloadData.items.length > 0 && workloadConfig ? (
              <>
                <Suspense fallback={<ChartLoading />}>
                  <Column {...workloadConfig} />
                </Suspense>
                <Table
                  columns={workloadColumns}
                  dataSource={workloadData.items}
                  rowKey="doctorId"
                  pagination={{ pageSize: 10 }}
                  size="small"
                  style={{ marginTop: 16 }}
                />
              </>
            ) : (
              <Empty description="暂无数据，请先查询" />
            )}
          </Tabs.TabPane>
          <Tabs.TabPane tab="高峰时段热力图" key="heatmap">
            {heatmapData && heatmapData.cells.length > 0 && heatmapConfig ? (
              <Suspense fallback={<ChartLoading />}>
                <Heatmap {...heatmapConfig} />
              </Suspense>
            ) : (
              <Empty description="暂无数据，请先查询" />
            )}
          </Tabs.TabPane>
        </Tabs>
      </Card>
    </PageContainer>
  );
};

export default ScheduleStatisticsPage;
