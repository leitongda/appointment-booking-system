import { PageContainer, ProCard, StatisticCard } from '@ant-design/pro-components';
import { Col, Row, Table, Empty, Spin, DatePicker } from 'antd';
import { useEffect, useState } from 'react';
import { statisticsApi } from '@hospital/api';
import type { OverviewData, TrendItem, DepartmentRankingItem, DoctorRankingItem, StatusStatItem } from '@hospital/api';

const { Statistic } = StatisticCard;
const { RangePicker } = DatePicker;

const STATUS_MAP: Record<number, string> = {
  0: '待支付', 1: '已预约', 2: '已签到', 3: '候诊中', 4: '就诊中', 5: '已完成', 6: '已取消', 7: '已过期', 8: '已关闭',
};

const StatisticsPage: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [overview, setOverview] = useState<OverviewData | null>(null);
  const [trendData, setTrendData] = useState<TrendItem[]>([]);
  const [statusStats, setStatusStats] = useState<StatusStatItem[]>([]);
  const [deptRanking, setDeptRanking] = useState<DepartmentRankingItem[]>([]);
  const [doctorRanking, setDoctorRanking] = useState<DoctorRankingItem[]>([]);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const [overviewRes, trendRes, statusRes, deptRes, doctorRes] = await Promise.allSettled([
        statisticsApi.getOverview(),
        statisticsApi.getAppointmentTrend(14),
        statisticsApi.getAppointmentStatusStats(),
        statisticsApi.getDepartmentRanking(10),
        statisticsApi.getDoctorRanking(10),
      ]);
      if (overviewRes.status === 'fulfilled') setOverview(overviewRes.value);
      if (trendRes.status === 'fulfilled') setTrendData(trendRes.value);
      if (statusRes.status === 'fulfilled') setStatusStats(statusRes.value);
      if (deptRes.status === 'fulfilled') setDeptRanking(deptRes.value);
      if (doctorRes.status === 'fulfilled') setDoctorRanking(doctorRes.value);
    } catch (error) {
      console.error('加载失败', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <PageContainer>
      <Spin spinning={loading}>
        {/* 概览数据 */}
        <Row gutter={[16, 16]}>
          <Col xs={24} sm={8}><ProCard hoverable><Statistic title="今日预约" value={overview?.todayAppointments ?? '-'} /></ProCard></Col>
          <Col xs={24} sm={8}><ProCard hoverable><Statistic title="本月预约" value={overview?.monthAppointments ?? '-'} /></ProCard></Col>
          <Col xs={24} sm={8}><ProCard hoverable><Statistic title="本月收入" value={overview?.monthRevenue ?? '-'} precision={2} suffix="元" /></ProCard></Col>
        </Row>

        {/* 状态统计 */}
        <ProCard title="预约状态分布" headerBordered style={{ marginTop: 16 }}>
          <Row gutter={[16, 16]}>
            {statusStats.map((item) => (
              <Col key={item.status} xs={12} sm={6} md={4}>
                <Statistic title={item.name || STATUS_MAP[item.status]} value={item.count} />
              </Col>
            ))}
          </Row>
        </ProCard>

        {/* 趋势图 */}
        <ProCard title="近14天预约趋势" headerBordered style={{ marginTop: 16 }}>
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

        {/* 排行榜 */}
        <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
          <Col xs={24} lg={12}>
            <ProCard title="科室排行 TOP10" headerBordered>
              <Table
                columns={[
                  { title: '排名', key: 'rank', width: 60, render: (_, __, i) => i + 1 },
                  { title: '科室', dataIndex: 'departmentName' },
                  { title: '预约数', dataIndex: 'count', width: 80 },
                ]}
                dataSource={deptRanking.map((item) => ({ ...item, key: item.departmentId }))}
                pagination={false}
                size="small"
              />
            </ProCard>
          </Col>
          <Col xs={24} lg={12}>
            <ProCard title="医生排行 TOP10" headerBordered>
              <Table
                columns={[
                  { title: '排名', key: 'rank', width: 60, render: (_, __, i) => i + 1 },
                  { title: '医生', dataIndex: 'doctorName', width: 80 },
                  { title: '科室', dataIndex: 'departmentName' },
                  { title: '预约数', dataIndex: 'count', width: 80 },
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

export default StatisticsPage;
