import { PageContainer, ProCard } from '@ant-design/pro-components';
import { Typography, Row, Col, Card } from 'antd';
import {
  DashboardOutlined,
  TeamOutlined,
  UserOutlined,
  CalendarOutlined,
  ScheduleOutlined,
  SettingOutlined,
  ShopOutlined,
  BarChartOutlined,
} from '@ant-design/icons';
import { history } from '@umijs/max';

const { Title, Paragraph } = Typography;

const features = [
  { icon: <DashboardOutlined />, title: '仪表盘', desc: '查看系统运营数据', path: '/dashboard', color: '#1890ff' },
  { icon: <ShopOutlined />, title: '门店管理', desc: '管理医院门店', path: '/store', color: '#52c41a' },
  { icon: <TeamOutlined />, title: '科室管理', desc: '管理科室设置', path: '/department', color: '#722ed1' },
  { icon: <UserOutlined />, title: '医生管理', desc: '管理医生信息', path: '/doctor/list', color: '#13c2c2' },
  { icon: <CalendarOutlined />, title: '排班管理', desc: '设置出诊排班', path: '/schedule/rule', color: '#fa8c16' },
  { icon: <ScheduleOutlined />, title: '预约管理', desc: '处理预约挂号', path: '/appointment/list', color: '#eb2f96' },
  { icon: <BarChartOutlined />, title: '统计分析', desc: '查看统计报表', path: '/statistics', color: '#f5222d' },
  { icon: <SettingOutlined />, title: '系统设置', desc: '系统配置管理', path: '/system/settings', color: '#595959' },
];

const Welcome: React.FC = () => {
  return (
    <PageContainer>
      <ProCard>
        <Typography>
          <Title level={2}>👋 欢迎使用医院挂号管理系统</Title>
          <Paragraph style={{ fontSize: 16, color: '#666' }}>
            这是一个功能完善的医院挂号预约管理平台，支持门店管理、科室管理、医生管理、排班管理、预约管理等核心功能。
          </Paragraph>
        </Typography>
      </ProCard>

      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        {features.map((item) => (
          <Col key={item.path} xs={24} sm={12} md={8} lg={6}>
            <Card
              hoverable
              onClick={() => history.push(item.path)}
              style={{ textAlign: 'center', cursor: 'pointer' }}
            >
              <div style={{ fontSize: 40, color: item.color, marginBottom: 12 }}>
                {item.icon}
              </div>
              <div style={{ fontSize: 16, fontWeight: 500, marginBottom: 4 }}>{item.title}</div>
              <div style={{ fontSize: 13, color: '#999' }}>{item.desc}</div>
            </Card>
          </Col>
        ))}
      </Row>
    </PageContainer>
  );
};

export default Welcome;
