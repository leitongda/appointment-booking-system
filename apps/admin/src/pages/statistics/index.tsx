import { useState, useEffect } from 'react';
import { PageContainer } from '@ant-design/pro-components';
import { Card, Row, Col, Statistic, DatePicker, Segmented, Table, Spin } from 'antd';
import {
  CalendarOutlined,
  TeamOutlined,
  UserOutlined,
  PayCircleOutlined,
} from '@ant-design/icons';
import { Line, Pie, Column, Bar } from '@ant-design/charts';
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
import './index.less';

const StatisticsPage = () => {
  const [loading, setLoading] = useState(true);
  const [trendDays, setTrendDays] = useState<number>(7);
  const [overview, setOverview] = useState<OverviewData | null>(null);
  const [appointmentTrend, setAppointmentTrend] = useState<TrendItem[]>([]);
  const [revenueTrend, setRevenueTrend] = useState<RevenueTrendItem[]>([]);
  const [statusStats, setStatusStats] = useState<StatusStatItem[]>([]);
  const [deptRanking, setDeptRanking] = useState<DepartmentRankingItem[]>([]);
  const [doctorRanking, setDoctorRanking] = useState<DoctorRankingItem[]>([]);
  const [timeSlotDist, setTimeSlotDist] = useState<TimeSlotItem[]>([]);
  const [weekdayDist, setWeekdayDist] = useState<WeekdayItem[]>([]);

  useEffect(() => {
    loadData();
  }, []);

  useEffect(() => {
    loadTrendData();
  }, [trendDays]);

  const loadData = async () => {
    setLoading(true);
    try {
      const [
        overviewData,
        statusData,
        deptData,
        doctorData,
        timeSlotData,
        weekdayData,
      ] = await Promise.all([
        statisticsApi.getOverview(),
        statisticsApi.getAppointmentStatusStats(),
        statisticsApi.getDepartmentRanking(),
        statisticsApi.getDoctorRanking(),
        statisticsApi.getTimeSlotDistribution(),
        statisticsApi.getWeekdayDistribution(),
      ]);

      setOverview(overviewData);
      setStatusStats(statusData);
      setDeptRanking(deptData);
      setDoctorRanking(doctorData);
      setTimeSlotDist(timeSlotData);
      setWeekdayDist(weekdayData);
    } catch (error) {
      console.error('加载统计数据失败', error);
    } finally {
      setLoading(false);
    }
  };

  const loadTrendData = async () => {
    try {
      const [trendData, revenueData] = await Promise.all([
        statisticsApi.getAppointmentTrend(trendDays),
        statisticsApi.getRevenueTrend(trendDays),
      ]);
      setAppointmentTrend(trendData);
      setRevenueTrend(revenueData);
    } catch (error) {
      console.error('加载趋势数据失败', error);
    }
  };

  const appointmentTrendConfig = {
    data: appointmentTrend,
    xField: 'date',
    yField: 'count',
    smooth: true,
    point: { size: 4, shape: 'circle' },
    color: '#1890ff',
    height: 300,
  };

  const revenueTrendConfig = {
    data: revenueTrend,
    xField: 'date',
    yField: 'revenue',
    smooth: true,
    point: { size: 4, shape: 'circle' },
    color: '#52c41a',
    height: 300,
  };

  const statusPieConfig = {
    data: statusStats,
    angleField: 'count',
    colorField: 'name',
    radius: 0.8,
    label: {
      type: 'outer',
      content: '{name} {percentage}',
    },
    height: 300,
  };

  const timeSlotPieConfig = {
    data: timeSlotDist,
    angleField: 'count',
    colorField: 'name',
    radius: 0.8,
    innerRadius: 0.6,
    label: {
      type: 'inner',
      offset: '-50%',
      content: '{value}',
      style: { textAlign: 'center', fontSize: 14 },
    },
    height: 300,
  };

  const weekdayColumnConfig = {
    data: weekdayDist,
    xField: 'name',
    yField: 'count',
    color: '#1890ff',
    height: 300,
    label: {
      position: 'middle' as const,
      style: { fill: '#fff' },
    },
  };

  const deptColumns = [
    { title: '排名', dataIndex: 'rank', width: 60 },
    { title: '科室', dataIndex: 'departmentName' },
    { title: '预约数', dataIndex: 'count', width: 100 },
  ];

  const doctorColumns = [
    { title: '排名', dataIndex: 'rank', width: 60 },
    { title: '医生', dataIndex: 'doctorName', width: 100 },
    { title: '职称', dataIndex: 'title', width: 80 },
    { title: '科室', dataIndex: 'departmentName' },
    { title: '预约数', dataIndex: 'count', width: 80 },
  ];

  return (
    <PageContainer title="数据统计">
      <Spin spinning={loading}>
        {/* 概览卡片 */}
        <Row gutter={[16, 16]} className="overview-cards">
          <Col xs={24} sm={12} lg={6}>
            <Card>
              <Statistic
                title="今日预约"
                value={overview?.todayAppointments || 0}
                prefix={<CalendarOutlined />}
                valueStyle={{ color: '#1890ff' }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <Card>
              <Statistic
                title="今日就诊"
                value={overview?.todayVisits || 0}
                prefix={<TeamOutlined />}
                valueStyle={{ color: '#52c41a' }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <Card>
              <Statistic
                title="总患者数"
                value={overview?.totalPatients || 0}
                prefix={<UserOutlined />}
                valueStyle={{ color: '#722ed1' }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <Card>
              <Statistic
                title="本月收入"
                value={overview?.monthRevenue || 0}
                prefix={<PayCircleOutlined />}
                precision={2}
                suffix="元"
                valueStyle={{ color: '#fa8c16' }}
              />
            </Card>
          </Col>
        </Row>

        {/* 趋势图表 */}
        <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
          <Col span={24}>
            <Card
              title="预约趋势"
              extra={
                <Segmented
                  options={[
                    { label: '近7天', value: 7 },
                    { label: '近14天', value: 14 },
                    { label: '近30天', value: 30 },
                  ]}
                  value={trendDays}
                  onChange={(value) => setTrendDays(value as number)}
                />
              }
            >
              <Line {...appointmentTrendConfig} />
            </Card>
          </Col>
        </Row>

        <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
          <Col span={24}>
            <Card title="收入趋势">
              <Line {...revenueTrendConfig} />
            </Card>
          </Col>
        </Row>

        {/* 分布图表 */}
        <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
          <Col xs={24} lg={8}>
            <Card title="预约状态分布">
              <Pie {...statusPieConfig} />
            </Card>
          </Col>
          <Col xs={24} lg={8}>
            <Card title="时段分布">
              <Pie {...timeSlotPieConfig} />
            </Card>
          </Col>
          <Col xs={24} lg={8}>
            <Card title="星期分布">
              <Column {...weekdayColumnConfig} />
            </Card>
          </Col>
        </Row>

        {/* 排行榜 */}
        <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
          <Col xs={24} lg={12}>
            <Card title="科室预约排行">
              <Table
                columns={deptColumns}
                dataSource={deptRanking.map((item, index) => ({
                  ...item,
                  rank: index + 1,
                  key: item.departmentId,
                }))}
                pagination={false}
                size="small"
              />
            </Card>
          </Col>
          <Col xs={24} lg={12}>
            <Card title="医生预约排行">
              <Table
                columns={doctorColumns}
                dataSource={doctorRanking.map((item, index) => ({
                  ...item,
                  rank: index + 1,
                  key: item.doctorId,
                }))}
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

export default StatisticsPage;

