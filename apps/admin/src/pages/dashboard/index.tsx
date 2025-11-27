import { PageContainer, ProCard, StatisticCard } from '@ant-design/pro-components';
import { Col, Row } from 'antd';
import {
  UserOutlined,
  CalendarOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
} from '@ant-design/icons';

const { Statistic } = StatisticCard;

const Dashboard: React.FC = () => {
  return (
    <PageContainer>
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} lg={6}>
          <ProCard>
            <Statistic
              title="今日预约"
              value={128}
              icon={<CalendarOutlined style={{ color: '#1890ff' }} />}
            />
          </ProCard>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <ProCard>
            <Statistic
              title="已就诊"
              value={86}
              icon={<CheckCircleOutlined style={{ color: '#52c41a' }} />}
            />
          </ProCard>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <ProCard>
            <Statistic
              title="候诊中"
              value={32}
              icon={<UserOutlined style={{ color: '#faad14' }} />}
            />
          </ProCard>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <ProCard>
            <Statistic
              title="已取消"
              value={10}
              icon={<CloseCircleOutlined style={{ color: '#ff4d4f' }} />}
            />
          </ProCard>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} lg={16}>
          <ProCard title="预约趋势" headerBordered>
            <div style={{ height: 300, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#999' }}>
              图表区域（待实现）
            </div>
          </ProCard>
        </Col>
        <Col xs={24} lg={8}>
          <ProCard title="科室分布" headerBordered>
            <div style={{ height: 300, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#999' }}>
              图表区域（待实现）
            </div>
          </ProCard>
        </Col>
      </Row>
    </PageContainer>
  );
};

export default Dashboard;

