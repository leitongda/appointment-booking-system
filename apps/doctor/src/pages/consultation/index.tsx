import { PageContainer, ProCard } from '@ant-design/pro-components';
import { List, Avatar, Tag, Button, Empty, message } from 'antd';
import { UserOutlined } from '@ant-design/icons';
import { history } from 'umi';
import { APPOINTMENT_STATUS_MAP } from '@hospital/shared';

const mockWaiting = [
  { id: '1', name: '张三', queueNumber: 1, status: 3 },
  { id: '2', name: '李四', queueNumber: 2, status: 2 },
  { id: '3', name: '王五', queueNumber: 3, status: 2 },
];

const ConsultationPage: React.FC = () => {
  const handleCall = (id: string) => {
    message.success('已呼叫患者');
  };

  const handleComplete = (id: string) => {
    history.push(`/medical-record/create?appointmentId=${id}`);
  };

  return (
    <PageContainer>
      <ProCard title="候诊队列" extra={<Button type="primary" onClick={() => handleCall('next')}>呼叫下一位</Button>}>
        {mockWaiting.length === 0 ? (
          <Empty description="暂无候诊患者" />
        ) : (
          <List
            dataSource={mockWaiting}
            renderItem={(item) => (
              <List.Item
                actions={[
                  item.status === 2 && <Button size="small" onClick={() => handleCall(item.id)}>呼叫</Button>,
                  item.status === 3 && <Button size="small" onClick={() => {}}>过号</Button>,
                  item.status === 4 && <Button size="small" type="primary" onClick={() => handleComplete(item.id)}>完成就诊</Button>,
                ].filter(Boolean)}
              >
                <List.Item.Meta
                  avatar={<Avatar size={48} icon={<UserOutlined />} />}
                  title={<span style={{ fontSize: 16 }}>{item.name} <Tag color="blue">第{item.queueNumber}号</Tag></span>}
                  description={<Tag color={item.status === 3 ? 'processing' : item.status === 4 ? 'warning' : 'default'}>{APPOINTMENT_STATUS_MAP[item.status]}</Tag>}
                />
              </List.Item>
            )}
          />
        )}
      </ProCard>
    </PageContainer>
  );
};

export default ConsultationPage;

