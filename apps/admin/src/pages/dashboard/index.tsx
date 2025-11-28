import { PageContainer, ProCard, StatisticCard } from '@ant-design/pro-components';
import { Col, Row, Spin, Table, Tag } from 'antd';
import { Line, Pie } from '@ant-design/charts';
import {
  UserOutlined,
  CalendarOutlined,
  CheckCircleOutlined,
  PayCircleOutlined,
  TeamOutlined,
  MedicineBoxOutlined,
} from '@ant-design/icons';
import { useState, useEffect } from 'react';
import { statisticsApi } from '@hospital/api';
import type { OverviewData, TrendItem, DepartmentRankingItem, DoctorRankingItem } from '@hospital/api';

const { Statistic } = StatisticCard;

const Dashboard: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [overview, setOverview] = useState<OverviewData | null>(null);
  const [trendData, setTrendData] = useState<TrendItem[]>([]);
  const [deptRanking, setDeptRanking] = useState<DepartmentRankingItem[]>([]);
  const [doctorRanking, setDoctorRanking] = useState<DoctorRankingItem[]>([]);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const [overviewData, trend, deptData, doctorData] = await Promise.all([
        statisticsApi.getOverview(),
        statisticsApi.getAppointmentTrend(7),
        statisticsApi.getDepartmentRanking(5),
        statisticsApi.getDoctorRanking(5),
      ]);
      setOverview(overviewData);
      setTrendData(trend);
      setDeptRanking(deptData);
      setDoctorRanking(doctorData);
    } catch (error) {
      console.error('加载数据失败', error);
    } finally {
      setLoading(false);
    }
  };

  const trendConfig = {
    data: trendData,
    xField: 'date',
    yField: 'count',
    smooth: true,
    point: { size: 4, shape: 'circle' },
    color: '#1890ff',
    height: 280,
    xAxis: {
      label: {
        formatter: (v: string) => v.substring(5), // 只显示月-日
      },
    },
    tooltip: {
      formatter: (datum: TrendItem) => ({
        name: '预约数',
        value: datum.count,
      }),
    },
  };

  const pieConfig = {
    data: deptRanking.map(item => ({
      name: item.departmentName,
      value: item.count,
    })),
    angleField: 'value',
    colorField: 'name',
    radius: 0.8,
    innerRadius: 0.6,
    height: 280,
    label: {
      type: 'inner',
      offset: '-50%',
      content: '{value}',
      style: { textAlign: 'center', fontSize: 12 },
    },
    legend: {
      position: 'bottom' as const,
    },
    interactions: [{ type: 'element-active' }],
  };

  const deptColumns = [
    { title: '排名', dataIndex: 'rank', width: 60 },
    { title: '科室', dataIndex: 'departmentName' },
    { title: '预约数', dataIndex: 'count', width: 80 },
  ];

  const doctorColumns = [
    { title: '排名', dataIndex: 'rank', width: 60 },
    { title: '医生', dataIndex: 'doctorName', width: 80 },
    { title: '职称', dataIndex: 'title', width: 80 },
    { title: '科室', dataIndex: 'departmentName' },
    { title: '预约数', dataIndex: 'count', width: 70 },
  ];

  return (
    <PageContainer>
      <Spin spinning={loading}>
        {/* 统计卡片 */}
        <Row gutter={[16, 16]}>
          <Col xs={24} sm={12} lg={6}>
            <ProCard>
              <Statistic
                title="今日预约"
                value={overview?.todayAppointments || 0}
                icon={<CalendarOutlined style={{ color: '#1890ff' }} />}
              />
            </ProCard>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <ProCard>
              <Statistic
                title="今日就诊"
                value={overview?.todayVisits || 0}
                icon={<CheckCircleOutlined style={{ color: '#52c41a' }} />}
              />
            </ProCard>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <ProCard>
              <Statistic
                title="总患者数"
                value={overview?.totalPatients || 0}
                icon={<TeamOutlined style={{ color: '#722ed1' }} />}
              />
            </ProCard>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <ProCard>
              <Statistic
                title="本月收入"
                value={overview?.monthRevenue || 0}
                precision={2}
                suffix="元"
                icon={<PayCircleOutlined style={{ color: '#fa8c16' }} />}
              />
            </ProCard>
          </Col>
        </Row>

        {/* 图表区域 */}
        <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
          <Col xs={24} lg={16}>
            <ProCard title="近7天预约趋势" headerBordered>
              {trendData.length > 0 ? (
                <Line {...trendConfig} />
              ) : (
                <div style={{ height: 280, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#999' }}>
                  暂无数据
                </div>
              )}
            </ProCard>
          </Col>
          <Col xs={24} lg={8}>
            <ProCard title="科室预约分布" headerBordered>
              {deptRanking.length > 0 ? (
                <Pie {...pieConfig} />
              ) : (
                <div style={{ height: 280, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#999' }}>
                  暂无数据
                </div>
              )}
            </ProCard>
          </Col>
        </Row>

        {/* 排行榜 */}
        <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
          <Col xs={24} lg={12}>
            <ProCard 
              title="科室预约排行" 
              headerBordered
              extra={<a onClick={loadData}>刷新</a>}
            >
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
            </ProCard>
          </Col>
          <Col xs={24} lg={12}>
            <ProCard 
              title="医生预约排行" 
              headerBordered
              extra={<a onClick={loadData}>刷新</a>}
            >
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
            </ProCard>
          </Col>
        </Row>
      </Spin>
    </PageContainer>
  );
};

export default Dashboard;
