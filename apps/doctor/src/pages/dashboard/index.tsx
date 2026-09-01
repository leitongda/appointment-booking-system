import { PageContainer, ProCard, StatisticCard } from '@ant-design/pro-components';
import { Col, Row, List, Avatar, Tag, Button, Empty, message, Badge } from 'antd';
import { UserOutlined, CheckCircleOutlined, ClockCircleOutlined, BellOutlined } from '@ant-design/icons';
import { useState, useEffect, useCallback, useMemo } from 'react';
import { history } from 'umi';
import { appointmentApi, doctorQueueApi } from '@hospital/api';
import { APPOINTMENT_STATUS_MAP, APPOINTMENT_STATUS_COLOR, TIME_SLOT_MAP } from '@hospital/shared';
import type { Appointment, AppointmentStatistics } from '@hospital/shared';
import { useWebSocket, ConnectionStatus } from '@/hooks';
import { ConnectionTag, ConnectionBanner } from '@/components/ConnectionStatus';

const { Statistic } = StatisticCard;

const Dashboard: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [statistics, setStatistics] = useState<AppointmentStatistics>({
    total: 0, confirmed: 0, signedIn: 0, inProgress: 0, completed: 0, cancelled: 0, noShow: 0
  });
  const [todayAppointments, setTodayAppointments] = useState<Appointment[]>([]);
  const [currentPatient, setCurrentPatient] = useState<Appointment | null>(null);

  // 获取医生 ID
  const doctorId = useMemo(() => {
    try {
      const doctorStr = localStorage.getItem('doctor');
      if (doctorStr) {
        const doctor = JSON.parse(doctorStr);
        return doctor.id || doctor.doctorId || '';
      }
    } catch (e) {
      console.error('解析医生信息失败:', e);
    }
    return '';
  }, []);

  const loadData = useCallback(async () => {
    try {
      const [stats, appointments] = await Promise.all([
        appointmentApi.getStatistics(),
        appointmentApi.getToday(),
      ]);
      setStatistics(stats);
      setTodayAppointments(appointments);
      
      // 找到正在就诊的患者（status=4 对应 SEEING 就诊中）
      const inProgress = appointments.find((a: Appointment) => a.status === 4);
      setCurrentPatient(inProgress || null);
    } catch (error) {
      console.error('加载数据失败', error);
    } finally {
      setLoading(false);
    }
  }, []);

  // WebSocket 连接
  const { status: wsStatus, reconnect } = useWebSocket({
    doctorId,
    onPatientSignedIn: () => loadData(),
    onQueueUpdated: () => loadData(),
    onNewAppointment: () => loadData(),
    showNotifications: true,
  });

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleCall = async (appointment: Appointment) => {
    try {
      await doctorQueueApi.call(appointment.id);
      message.success(`已呼叫 ${appointment.patientName}`);
      loadData();
    } catch (error: any) {
      message.error(error.message || '呼叫失败');
    }
  };

  const handleCallNext = async () => {
    // 找到下一个已签到的患者
    const nextPatient = todayAppointments.find((a) => a.status === 2);
    if (nextPatient) {
      await handleCall(nextPatient);
    } else {
      message.info('暂无待诊患者');
    }
  };

  const handleComplete = async (appointmentId: string) => {
    try {
      await doctorQueueApi.complete(appointmentId);
      message.success('就诊完成');
      history.push(`/medical-record/create?appointmentId=${appointmentId}`);
    } catch (error: any) {
      message.error(error.message || '操作失败');
    }
  };

  // 待诊队列（已签到的）
  const waitingList = todayAppointments.filter((a) => a.status === 2);
  // 待签到
  const pendingList = todayAppointments.filter((a) => a.status === 1);

  return (
    <PageContainer
      loading={loading}
      extra={<ConnectionTag status={wsStatus} onReconnect={reconnect} />}
    >
      <ConnectionBanner status={wsStatus} onReconnect={reconnect} />
      {/* 统计卡片 */}
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={8}>
          <ProCard>
            <Statistic
              title="今日预约"
              value={statistics.confirmed + statistics.signedIn + statistics.inProgress + statistics.completed}
              icon={<ClockCircleOutlined style={{ color: '#1677ff' }} />}
            />
          </ProCard>
        </Col>
        <Col xs={24} sm={8}>
          <ProCard>
            <Statistic
              title="已就诊"
              value={statistics.completed}
              icon={<CheckCircleOutlined style={{ color: '#52c41a' }} />}
            />
          </ProCard>
        </Col>
        <Col xs={24} sm={8}>
          <ProCard>
            <Statistic
              title="已签到"
              value={waitingList.length}
              icon={<UserOutlined style={{ color: '#faad14' }} />}
            />
          </ProCard>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        {/* 当前就诊 */}
        <Col xs={24} lg={8}>
          <ProCard 
            title={<><BellOutlined /> 当前就诊</>} 
            extra={currentPatient && <Tag color="processing">就诊中</Tag>}
          >
            {currentPatient ? (
              <div style={{ textAlign: 'center', padding: '20px 0' }}>
                <Avatar size={64} icon={<UserOutlined />} style={{ marginBottom: 16 }} />
                <div style={{ fontSize: 20, fontWeight: 500, marginBottom: 8 }}>
                  {currentPatient.patientName}
                </div>
                <div style={{ color: '#666', marginBottom: 16 }}>
                  {TIME_SLOT_MAP[currentPatient.timeSlot || 'morning']} 第{currentPatient.queueNumber}号
                </div>
                <Button type="primary" onClick={() => handleComplete(currentPatient.id)}>
                  完成就诊
                </Button>
              </div>
            ) : (
              <Empty description="暂无正在就诊的患者">
                <Button type="primary" onClick={handleCallNext}>呼叫下一位</Button>
              </Empty>
            )}
          </ProCard>
        </Col>

        {/* 待诊队列 */}
        <Col xs={24} lg={8}>
          <ProCard 
            title="待诊队列"
            extra={<Badge count={waitingList.length} style={{ backgroundColor: '#faad14' }} />}
          >
            {waitingList.length === 0 ? (
              <Empty description="暂无待诊患者" />
            ) : (
              <List
                size="small"
                dataSource={waitingList.slice(0, 5)}
                renderItem={(item, index) => (
                  <List.Item 
                    actions={[
                      <Button size="small" type="primary" onClick={() => handleCall(item)}>
                        呼叫
                      </Button>
                    ]}
                  >
                    <List.Item.Meta
                      avatar={<Avatar size="small">{index + 1}</Avatar>}
                      title={item.patientName}
                      description={`第${item.queueNumber}号 · ${item.signInTime?.substring(11, 16) || ''}`}
                    />
                  </List.Item>
                )}
              />
            )}
          </ProCard>
        </Col>

        {/* 待签到 */}
        <Col xs={24} lg={8}>
          <ProCard 
            title="待签到" 
            extra={<Badge count={pendingList.length} />}
          >
            {pendingList.length === 0 ? (
              <Empty description="暂无待签到患者" />
            ) : (
              <List
                size="small"
                dataSource={pendingList.slice(0, 5)}
                renderItem={(item) => (
                  <List.Item>
                    <List.Item.Meta
                      avatar={<Avatar icon={<UserOutlined />} />}
                      title={item.patientName}
                      description={`第${item.queueNumber}号 · ${TIME_SLOT_MAP[item.timeSlot || 'morning']}`}
                    />
                    <Tag>待签到</Tag>
                  </List.Item>
                )}
              />
            )}
          </ProCard>
        </Col>
      </Row>
    </PageContainer>
  );
};

export default Dashboard;
