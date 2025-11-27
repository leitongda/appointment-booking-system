import { PageContainer, ProCard, StatisticCard } from '@ant-design/pro-components';
import { Col, Row, DatePicker } from 'antd';

const { Statistic } = StatisticCard;
const { RangePicker } = DatePicker;

const StatisticsPage: React.FC = () => {
  return (
    <PageContainer extra={<RangePicker />}>
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} lg={6}>
          <ProCard><Statistic title="本月就诊" value={128} suffix="人次" /></ProCard>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <ProCard><Statistic title="本月预约" value={156} suffix="人次" /></ProCard>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <ProCard><Statistic title="完成率" value={82.1} suffix="%" /></ProCard>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <ProCard><Statistic title="爽约率" value={5.2} suffix="%" /></ProCard>
        </Col>
      </Row>
      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col span={24}>
          <ProCard title="就诊趋势">
            <div style={{ height: 300, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#999' }}>
              图表区域（待实现）
            </div>
          </ProCard>
        </Col>
      </Row>
    </PageContainer>
  );
};

export default StatisticsPage;

