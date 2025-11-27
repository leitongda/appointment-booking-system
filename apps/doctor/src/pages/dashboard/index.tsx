import { PageContainer, ProCard, StatisticCard } from '@ant-design/pro-components';
import { Col, Row, List, Avatar, Tag, Button } from 'antd';
import { UserOutlined, CheckCircleOutlined, ClockCircleOutlined } from '@ant-design/icons';
import { APPOINTMENT_STATUS_MAP, TIME_SLOT_MAP } from '@hospital/shared';

const { Statistic } = StatisticCard;

const mockWaiting = [
  { id: '1', name: '张三', queueNumber: 1, timeSlot: 'AM', status: 3 },
  { id: '2', name: '李四', queueNumber: 2, timeSlot: 'AM', status: 2 },
  { id: '3', name: '王五', queueNumber: 3, timeSlot: 'AM', status: 2 },
];

const Dashboard: React.FC = () => {
  return (
    <PageContainer>
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={8}>
          <ProCard><Statistic title="今日预约" value={25} icon={<ClockCircleOutlined style={{ color: '#1890ff' }} />} /></ProCard>
        </Col>
        <Col xs={24} sm={8}>
          <ProCard><Statistic title="已就诊" value={12} icon={<CheckCircleOutlined style={{ color: '#52c41a' }} />} /></ProCard>
        </Col>
        <Col xs={24} sm={8}>
          <ProCard><Statistic title="候诊中" value={8} icon={<UserOutlined style={{ color: '#faad14' }} />} /></ProCard>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} lg={12}>
          <ProCard title="候诊列表" extra={<Button type="primary">呼叫下一位</Button>}>
            <List
              dataSource={mockWaiting}
              renderItem={(item) => (
                <List.Item actions={[<Button size="small" type="primary">呼叫</Button>]}>
                  <List.Item.Meta
                    avatar={<Avatar icon={<UserOutlined />} />}
                    title={<span>{item.name} <Tag>{TIME_SLOT_MAP[item.timeSlot]}第{item.queueNumber}号</Tag></span>}
                    description={<Tag color={item.status === 3 ? 'processing' : 'default'}>{APPOINTMENT_STATUS_MAP[item.status]}</Tag>}
                  />
                </List.Item>
              )}
            />
          </ProCard>
        </Col>
        <Col xs={24} lg={12}>
          <ProCard title="本周排班">
            <div style={{ height: 200, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#999' }}>
              排班日历（待实现）
            </div>
          </ProCard>
        </Col>
      </Row>
    </PageContainer>
  );
};

export default Dashboard;

