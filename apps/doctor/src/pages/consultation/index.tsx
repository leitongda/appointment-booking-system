import { PageContainer, ProCard } from '@ant-design/pro-components';
import { List, Avatar, Tag, Button, Empty, message, Modal, Input, Row, Col, Statistic, Badge } from 'antd';
import { UserOutlined, SoundOutlined, StopOutlined, CheckOutlined } from '@ant-design/icons';
import { useState, useEffect } from 'react';
import { history } from 'umi';
import { appointmentApi } from '@hospital/api';
import { APPOINTMENT_STATUS_MAP, APPOINTMENT_STATUS_COLOR, TIME_SLOT_MAP } from '@hospital/shared';
import type { Appointment } from '@hospital/shared';

const ConsultationPage: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [currentPatient, setCurrentPatient] = useState<Appointment | null>(null);

  useEffect(() => {
    loadData();
    // 定时刷新
    const timer = setInterval(loadData, 30000);
    return () => clearInterval(timer);
  }, []);

  const loadData = async () => {
    try {
      const data = await appointmentApi.getToday();
      setAppointments(data);
      setCurrentPatient(data.find((a: Appointment) => a.status === 3) || null);
    } catch (error) {
      console.error('加载数据失败', error);
    } finally {
      setLoading(false);
    }
  };

  const handleCall = async (appointment: Appointment) => {
    try {
      await appointmentApi.call(appointment.id);
      message.success(`已呼叫 ${appointment.patientName}，请到诊室就诊`);
      loadData();
    } catch (error: any) {
      message.error(error.message || '呼叫失败');
    }
  };

  const handleCallNext = async () => {
    const nextPatient = waitingList[0];
    if (nextPatient) {
      await handleCall(nextPatient);
    } else {
      message.info('暂无候诊患者');
    }
  };

  const handlePass = async (appointment: Appointment) => {
    Modal.confirm({
      title: '确认过号',
      content: `确定将 ${appointment.patientName} 过号吗？过号后患者需要重新排队。`,
      onOk: async () => {
        try {
          // TODO: 实现过号 API
          message.success('已过号');
          loadData();
        } catch (error: any) {
          message.error(error.message || '操作失败');
        }
      },
    });
  };

  const handleComplete = async () => {
    if (!currentPatient) return;
    
    try {
      await appointmentApi.complete(currentPatient.id);
      message.success('就诊完成');
      history.push(`/medical-record/create?appointmentId=${currentPatient.id}`);
    } catch (error: any) {
      message.error(error.message || '操作失败');
    }
  };

  // 候诊队列
  const waitingList = appointments.filter((a) => a.status === 2);
  // 已过号
  const passedList = appointments.filter((a) => a.status === 4);

  return (
    <PageContainer loading={loading}>
      <Row gutter={16}>
        {/* 当前就诊 */}
        <Col xs={24} lg={10}>
          <ProCard 
            title="当前就诊" 
            extra={currentPatient && <Tag color="processing">就诊中</Tag>}
            style={{ minHeight: 400 }}
          >
            {currentPatient ? (
              <div style={{ textAlign: 'center', padding: '40px 0' }}>
                <Avatar size={80} icon={<UserOutlined />} style={{ marginBottom: 20, backgroundColor: '#1890ff' }} />
                <div style={{ fontSize: 24, fontWeight: 500, marginBottom: 8 }}>
                  {currentPatient.patientName}
                </div>
                <div style={{ fontSize: 16, color: '#666', marginBottom: 8 }}>
                  {currentPatient.patientPhone?.replace(/(\d{3})\d{4}(\d{4})/, '$1****$2')}
                </div>
                <div style={{ marginBottom: 24 }}>
                  <Tag color="blue" style={{ fontSize: 14, padding: '4px 12px' }}>
                    {TIME_SLOT_MAP[currentPatient.timeSlot || 'AM']} 第{currentPatient.queueNumber}号
                  </Tag>
                </div>
                <div style={{ display: 'flex', gap: 16, justifyContent: 'center' }}>
                  <Button icon={<StopOutlined />} onClick={() => handlePass(currentPatient)}>
                    过号
                  </Button>
                  <Button type="primary" icon={<CheckOutlined />} onClick={handleComplete}>
                    完成就诊
                  </Button>
                </div>
              </div>
            ) : (
              <Empty 
                description="暂无正在就诊的患者" 
                style={{ padding: '60px 0' }}
              >
                <Button type="primary" size="large" icon={<SoundOutlined />} onClick={handleCallNext}>
                  呼叫下一位
                </Button>
              </Empty>
            )}
          </ProCard>
        </Col>

        {/* 候诊队列 */}
        <Col xs={24} lg={14}>
          <ProCard 
            title="候诊队列"
            extra={
              <div>
                <Badge count={waitingList.length} style={{ marginRight: 16 }}>
                  <Tag>候诊中</Tag>
                </Badge>
                <Button type="primary" onClick={handleCallNext} disabled={!waitingList.length}>
                  呼叫下一位
                </Button>
              </div>
            }
            style={{ minHeight: 400 }}
          >
            {waitingList.length === 0 ? (
              <Empty description="暂无候诊患者" />
            ) : (
              <List
                dataSource={waitingList}
                renderItem={(item, index) => (
                  <List.Item
                    actions={[
                      <Button 
                        type="primary" 
                        icon={<SoundOutlined />}
                        onClick={() => handleCall(item)}
                      >
                        呼叫
                      </Button>
                    ]}
                  >
                    <List.Item.Meta
                      avatar={
                        <Avatar 
                          style={{ 
                            backgroundColor: index === 0 ? '#52c41a' : '#1890ff',
                            fontSize: 16 
                          }}
                        >
                          {index + 1}
                        </Avatar>
                      }
                      title={
                        <span style={{ fontSize: 16 }}>
                          {item.patientName}
                          <Tag color="blue" style={{ marginLeft: 8 }}>第{item.queueNumber}号</Tag>
                        </span>
                      }
                      description={
                        <span>
                          签到时间：{item.signInTime?.substring(11, 16) || '-'}
                        </span>
                      }
                    />
                  </List.Item>
                )}
              />
            )}
          </ProCard>
        </Col>
      </Row>

      {/* 已过号列表 */}
      {passedList.length > 0 && (
        <ProCard title="已过号" style={{ marginTop: 16 }} collapsible defaultCollapsed>
          <List
            size="small"
            dataSource={passedList}
            renderItem={(item) => (
              <List.Item
                actions={[
                  <Button size="small" onClick={() => handleCall(item)}>重新呼叫</Button>
                ]}
              >
                <List.Item.Meta
                  avatar={<Avatar icon={<UserOutlined />} />}
                  title={item.patientName}
                  description={`第${item.queueNumber}号`}
                />
                <Tag color="orange">已过号</Tag>
              </List.Item>
            )}
          />
        </ProCard>
      )}
    </PageContainer>
  );
};

export default ConsultationPage;
