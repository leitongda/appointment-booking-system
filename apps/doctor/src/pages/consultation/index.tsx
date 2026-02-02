import { PageContainer, ProCard } from '@ant-design/pro-components';
import { List, Avatar, Tag, Button, Empty, message, Row, Col, Badge, Popconfirm, Tooltip } from 'antd';
import { UserOutlined, SoundOutlined, StopOutlined, CheckOutlined, ReloadOutlined, WifiOutlined, DisconnectOutlined } from '@ant-design/icons';
import { useState, useEffect, useCallback, useMemo } from 'react';
import { history } from 'umi';
import { appointmentApi } from '@hospital/api';
import { TIME_SLOT_MAP } from '@hospital/shared';
import type { Appointment, QueueInfo } from '@hospital/shared';
import { useWebSocket, ConnectionStatus, WSMessageType } from '@/hooks';

const ConsultationPage: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [appointments, setAppointments] = useState<Appointment[]>([]);
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

  // 数据加载回调
  const loadData = useCallback(async () => {
    try {
      const data = await appointmentApi.getToday();
      setAppointments(data);
      setCurrentPatient(data.find((a: Appointment) => a.status === 3) || null);
    } catch (error) {
      console.error('加载数据失败', error);
    } finally {
      setLoading(false);
    }
  }, []);

  // WebSocket 连接
  const { status: wsStatus, isConnected, reconnect } = useWebSocket({
    doctorId,
    onPatientSignedIn: () => {
      // 患者签到时刷新数据
      loadData();
    },
    onQueueUpdated: () => {
      // 队列更新时刷新数据
      loadData();
    },
    showNotifications: true,
  });

  // 初始加载
  useEffect(() => {
    loadData();
  }, [loadData]);

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
    try {
      await appointmentApi.pass(appointment.id);
      message.success('已过号');
      loadData();
    } catch (error: any) {
      message.error(error.message || '操作失败');
    }
  };

  const handleRecall = async (appointment: Appointment) => {
    try {
      await appointmentApi.recall(appointment.id);
      message.success(`已重新呼叫 ${appointment.patientName}`);
      loadData();
    } catch (error: any) {
      message.error(error.message || '操作失败');
    }
  };

  const handleMarkNoShow = async (appointment: Appointment) => {
    try {
      await appointmentApi.markNoShow(appointment.id);
      message.success('已标记爽约');
      loadData();
    } catch (error: any) {
      message.error(error.message || '操作失败');
    }
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

  // 候诊队列（已签到）
  const waitingList = appointments.filter((a) => a.status === 2);
  // 已过号 (7=EXPIRED)
  const passedList = appointments.filter((a) => a.status === 7);

  // 连接状态指示器
  const connectionIndicator = useMemo(() => {
    if (wsStatus === ConnectionStatus.CONNECTED) {
      return (
        <Tooltip title="实时连接正常">
          <Tag color="success" icon={<WifiOutlined />}>实时</Tag>
        </Tooltip>
      );
    }
    if (wsStatus === ConnectionStatus.CONNECTING || wsStatus === ConnectionStatus.RECONNECTING) {
      return (
        <Tooltip title="正在连接...">
          <Tag color="processing" icon={<WifiOutlined />}>连接中</Tag>
        </Tooltip>
      );
    }
    return (
      <Tooltip title="实时连接已断开，点击重连">
        <Tag color="error" icon={<DisconnectOutlined />} style={{ cursor: 'pointer' }} onClick={reconnect}>
          离线
        </Tag>
      </Tooltip>
    );
  }, [wsStatus, reconnect]);

  return (
    <PageContainer 
      loading={loading}
      extra={
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          {connectionIndicator}
          <Button icon={<ReloadOutlined />} onClick={loadData}>
            刷新
          </Button>
        </div>
      }
    >
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
                  <Popconfirm
                    title="确定过号吗？"
                    description="过号后患者需要重新排队。"
                    onConfirm={() => handlePass(currentPatient)}
                  >
                    <Button icon={<StopOutlined />}>过号</Button>
                  </Popconfirm>
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
                  <Button size="small" type="primary" onClick={() => handleRecall(item)}>
                    重新呼叫
                  </Button>,
                  <Popconfirm
                    title="确定标记爽约吗？"
                    description="爽约记录会影响患者后续预约。"
                    onConfirm={() => handleMarkNoShow(item)}
                  >
                    <Button size="small" danger>标记爽约</Button>
                  </Popconfirm>
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
