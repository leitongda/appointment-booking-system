import { PageContainer, ProCard, StatisticCard } from '@ant-design/pro-components';
import { Col, Row, Table, Empty, Spin, DatePicker, Select, Form, Button, Card, Progress } from 'antd';
import { SearchOutlined } from '@ant-design/icons';
import { useEffect, useState } from 'react';
import { statisticsApi, storeApi } from '@hospital/api';
import type {
  AppointmentSummary,
  TrendItem,
  StatusStatItem,
  DepartmentRankingItem,
  DoctorRankingItem,
  StoreRankingItem,
  TimeSlotItem,
} from '@hospital/api';
import dayjs from 'dayjs';

const { Statistic } = StatisticCard;
const { RangePicker } = DatePicker;

const AppointmentStatisticsPage: React.FC = () => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(true);
  const [stores, setStores] = useState<any[]>([]);
  const [summary, setSummary] = useState<AppointmentSummary | null>(null);
  const [trendData, setTrendData] = useState<TrendItem[]>([]);
  const [statusStats, setStatusStats] = useState<StatusStatItem[]>([]);
  const [storeRanking, setStoreRanking] = useState<StoreRankingItem[]>([]);
  const [deptRanking, setDeptRanking] = useState<DepartmentRankingItem[]>([]);
  const [doctorRanking, setDoctorRanking] = useState<DoctorRankingItem[]>([]);
  const [timeSlotStats, setTimeSlotStats] = useState<TimeSlotItem[]>([]);

  useEffect(() => {
    loadStores();
    loadData();
  }, []);

  const loadStores = async () => {
    try {
      const res = await storeApi.getList({ pageSize: 100, status: 1 });
      setStores(res.data ?? []);
    } catch (error) {
      console.error('加载门店失败', error);
    }
  };

  const loadData = async (params?: { startDate?: string; endDate?: string; storeId?: string }) => {
    setLoading(true);
    try {
      const [summaryRes, trendRes, statusRes, storeRes, deptRes, doctorRes, timeRes] = await Promise.allSettled([
        statisticsApi.getAppointmentSummary(params),
        statisticsApi.getAppointmentTrend(14),
        statisticsApi.getAppointmentStatusStats(params),
        statisticsApi.getStoreRanking({ limit: 10, ...params }),
        statisticsApi.getDepartmentRanking(10),
        statisticsApi.getDoctorRanking(10),
        statisticsApi.getTimeSlotDistribution(),
      ]);
      
      if (summaryRes.status === 'fulfilled') setSummary(summaryRes.value);
      if (trendRes.status === 'fulfilled') setTrendData(trendRes.value);
      if (statusRes.status === 'fulfilled') setStatusStats(statusRes.value);
      if (storeRes.status === 'fulfilled') setStoreRanking(storeRes.value);
      if (deptRes.status === 'fulfilled') setDeptRanking(deptRes.value);
      if (doctorRes.status === 'fulfilled') setDoctorRanking(doctorRes.value);
      if (timeRes.status === 'fulfilled') setTimeSlotStats(timeRes.value);
    } catch (error) {
      console.error('加载失败', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = () => {
    const values = form.getFieldsValue();
    const params: any = {};
    
    if (values.dateRange && values.dateRange.length === 2) {
      params.startDate = values.dateRange[0].format('YYYY-MM-DD');
      params.endDate = values.dateRange[1].format('YYYY-MM-DD');
    }
    
    if (values.storeId) {
      params.storeId = values.storeId;
    }
    
    loadData(params);
  };

  return (
    <PageContainer>
      <Spin spinning={loading}>
        {/* 筛选条件 */}
        <Card style={{ marginBottom: 16 }}>
          <Form form={form} layout="inline">
            <Form.Item name="dateRange" label="日期范围">
              <RangePicker />
            </Form.Item>
            <Form.Item name="storeId" label="门店">
              <Select
                style={{ width: 180 }}
                placeholder="全部门店"
                allowClear
                options={stores.map(s => ({ label: s.name, value: s.id }))}
              />
            </Form.Item>
            <Form.Item>
              <Button type="primary" icon={<SearchOutlined />} onClick={handleSearch}>
                查询
              </Button>
            </Form.Item>
          </Form>
        </Card>

        {/* 汇总数据 */}
        {summary && (
          <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
            <Col xs={24} sm={12} md={6}>
              <ProCard hoverable>
                <Statistic title="总预约数" value={summary.total} />
              </ProCard>
            </Col>
            <Col xs={24} sm={12} md={6}>
              <ProCard hoverable>
                <Statistic
                  title="完成率"
                  value={summary.completedRate}
                  suffix="%"
                  description={
                    <Progress
                      percent={summary.completedRate}
                      showInfo={false}
                      strokeColor="#52c41a"
                      size="small"
                    />
                  }
                />
              </ProCard>
            </Col>
            <Col xs={24} sm={12} md={6}>
              <ProCard hoverable>
                <Statistic
                  title="爽约率"
                  value={summary.noShowRate}
                  suffix="%"
                  description={
                    <Progress
                      percent={summary.noShowRate}
                      showInfo={false}
                      strokeColor="#ff4d4f"
                      size="small"
                    />
                  }
                />
              </ProCard>
            </Col>
            <Col xs={24} sm={12} md={6}>
              <ProCard hoverable>
                <Statistic
                  title="取消率"
                  value={summary.cancelledRate}
                  suffix="%"
                  description={
                    <Progress
                      percent={summary.cancelledRate}
                      showInfo={false}
                      strokeColor="#faad14"
                      size="small"
                    />
                  }
                />
              </ProCard>
            </Col>
          </Row>
        )}

        {/* 状态分布 */}
        <ProCard title="预约状态分布" headerBordered style={{ marginBottom: 16 }}>
          <Row gutter={[16, 16]}>
            {statusStats.map((item) => (
              <Col key={item.status} xs={12} sm={6} md={4} lg={3}>
                <Statistic title={item.name} value={item.count} />
              </Col>
            ))}
          </Row>
        </ProCard>

        {/* 趋势图 */}
        <ProCard title="近14天预约趋势" headerBordered style={{ marginBottom: 16 }}>
          {trendData.length > 0 ? (
            <div style={{ display: 'flex', alignItems: 'flex-end', height: 200, gap: 8, padding: '0 16px', overflowX: 'auto' }}>
              {trendData.map((item, index) => {
                const max = Math.max(...trendData.map((d) => d.count), 1);
                const height = (item.count / max) * 160;
                return (
                  <div key={index} style={{ minWidth: 40, textAlign: 'center' }}>
                    <div style={{ height: height || 4, background: 'linear-gradient(180deg, #1890ff 0%, #69c0ff 100%)', borderRadius: '4px 4px 0 0', marginBottom: 4 }} />
                    <div style={{ fontSize: 11, color: '#666' }}>{item.count}</div>
                    <div style={{ fontSize: 10, color: '#999' }}>{item.date.slice(5)}</div>
                  </div>
                );
              })}
            </div>
          ) : (
            <Empty description="暂无数据" />
          )}
        </ProCard>

        {/* 时段分布 */}
        <ProCard title="预约时段分布" headerBordered style={{ marginBottom: 16 }}>
          <Row gutter={[16, 16]}>
            {timeSlotStats.map((item) => (
              <Col key={item.timeSlot} xs={8} sm={8} md={8}>
                <Card>
                  <Statistic title={item.name} value={item.count} suffix="人次" />
                </Card>
              </Col>
            ))}
          </Row>
        </ProCard>

        {/* 排行榜 */}
        <Row gutter={[16, 16]}>
          <Col xs={24} lg={8}>
            <ProCard title="门店排行 TOP10" headerBordered>
              <Table
                columns={[
                  { title: '排名', key: 'rank', width: 50, render: (_, __, i) => i + 1 },
                  { title: '门店', dataIndex: 'storeName' },
                  { title: '预约数', dataIndex: 'count', width: 70 },
                ]}
                dataSource={storeRanking.map((item) => ({ ...item, key: item.storeId }))}
                pagination={false}
                size="small"
              />
            </ProCard>
          </Col>
          <Col xs={24} lg={8}>
            <ProCard title="科室排行 TOP10" headerBordered>
              <Table
                columns={[
                  { title: '排名', key: 'rank', width: 50, render: (_, __, i) => i + 1 },
                  { title: '科室', dataIndex: 'departmentName' },
                  { title: '预约数', dataIndex: 'count', width: 70 },
                ]}
                dataSource={deptRanking.map((item) => ({ ...item, key: item.departmentId }))}
                pagination={false}
                size="small"
              />
            </ProCard>
          </Col>
          <Col xs={24} lg={8}>
            <ProCard title="医生排行 TOP10" headerBordered>
              <Table
                columns={[
                  { title: '排名', key: 'rank', width: 50, render: (_, __, i) => i + 1 },
                  { title: '医生', dataIndex: 'doctorName', width: 70 },
                  { title: '科室', dataIndex: 'departmentName' },
                  { title: '预约数', dataIndex: 'count', width: 70 },
                ]}
                dataSource={doctorRanking.map((item) => ({ ...item, key: item.doctorId }))}
                pagination={false}
                size="small"
              />
            </ProCard>
          </Col>
        </Row>
      </Spin>
    </PageContainer>
  );
};

export default AppointmentStatisticsPage;
