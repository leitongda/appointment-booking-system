import { PageContainer, ProCard, StatisticCard } from '@ant-design/pro-components';
import { Col, Row, Table, Empty, Spin } from 'antd';
import {
  CalendarOutlined,
  CheckCircleOutlined,
  TeamOutlined,
  UserOutlined,
  RiseOutlined,
  PayCircleOutlined,
} from '@ant-design/icons';
import { useEffect, useState } from 'react';
import { statisticsApi } from '@hospital/api';
import type {
  OverviewData,
  TrendItem,
  DepartmentRankingItem,
  DoctorRankingItem,
} from '@hospital/api';

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
      const [overviewRes, trendRes, deptRes, doctorRes] = await Promise.allSettled([
        statisticsApi.getOverview(),
        statisticsApi.getAppointmentTrend(7),
        statisticsApi.getDepartmentRanking(5),
        statisticsApi.getDoctorRanking(5),
      ]);

      if (overviewRes.status === 'fulfilled') setOverview(overviewRes.value);
      if (trendRes.status === 'fulfilled') setTrendData(trendRes.value);
      if (deptRes.status === 'fulfilled') setDeptRanking(deptRes.value);
      if (doctorRes.status === 'fulfilled') setDoctorRanking(doctorRes.value);
    } catch (error) {
      console.error('加载数据失败', error);
    } finally {
      setLoading(false);
    }
  };

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
    <PageContainer>
      <Spin spinning={loading}>
        {/* 统计卡片 */}
        <Row gutter={[16, 16]}>
          <Col xs={24} sm={12} lg={6}>
            <ProCard hoverable>
              <Statistic
                title="今日预约"
                value={overview?.todayAppointments ?? '-'}
                icon={<CalendarOutlined style={{ fontSize: 40, color: '#1890ff' }} />}
              />
            </ProCard>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <ProCard hoverable>
              <Statistic
                title="今日就诊"
                value={overview?.todayVisits ?? '-'}
                icon={<CheckCircleOutlined style={{ fontSize: 40, color: '#52c41a' }} />}
              />
            </ProCard>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <ProCard hoverable>
              <Statistic
                title="总患者数"
                value={overview?.totalPatients ?? '-'}
                icon={<TeamOutlined style={{ fontSize: 40, color: '#722ed1' }} />}
              />
            </ProCard>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <ProCard hoverable>
              <Statistic
                title="医生数量"
                value={overview?.totalDoctors ?? '-'}
                icon={<UserOutlined style={{ fontSize: 40, color: '#13c2c2' }} />}
              />
            </ProCard>
          </Col>
        </Row>

        {/* 月度统计 */}
        <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
          <Col xs={24} sm={12}>
            <ProCard hoverable>
              <Statistic
                title="本月预约"
                value={overview?.monthAppointments ?? '-'}
                icon={<RiseOutlined style={{ fontSize: 40, color: '#fa8c16' }} />}
              />
            </ProCard>
          </Col>
          <Col xs={24} sm={12}>
            <ProCard hoverable>
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

        {/* 预约趋势 */}
        <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
          <Col xs={24}>
            <ProCard title="近7天预约趋势" headerBordered>
              {trendData.length > 0 ? (
                <div style={{ display: 'flex', alignItems: 'flex-end', height: 200, gap: 16, padding: '0 16px' }}>
                  {trendData.map((item, index) => {
                    const max = Math.max(...trendData.map((d) => d.count), 1);
                    const height = (item.count / max) * 160;
                    return (
                      <div key={index} style={{ flex: 1, textAlign: 'center' }}>
                        <div
                          style={{
                            height: height || 4,
                            background: 'linear-gradient(180deg, #1890ff 0%, #69c0ff 100%)',
                            borderRadius: '4px 4px 0 0',
                            marginBottom: 8,
                            transition: 'height 0.3s',
                          }}
                        />
                        <div style={{ fontSize: 12, color: '#666' }}>{item.count}</div>
                        <div style={{ fontSize: 11, color: '#999' }}>{item.date.slice(5)}</div>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <Empty description="暂无数据" style={{ padding: 40 }} />
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
                dataSource={deptRanking.map((item) => ({ ...item, key: item.departmentId }))}
                pagination={false}
                size="small"
                locale={{ emptyText: <Empty description="暂无数据" /> }}
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
                dataSource={doctorRanking.map((item) => ({ ...item, key: item.doctorId }))}
                pagination={false}
                size="small"
                locale={{ emptyText: <Empty description="暂无数据" /> }}
              />
            </ProCard>
          </Col>
        </Row>
      </Spin>
    </PageContainer>
  );
};

export default Dashboard;
