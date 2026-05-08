import { PageContainer, ProCard } from '@ant-design/pro-components';
import { List, Avatar, Tag, Button, Empty, message, Row, Col, Badge, Popconfirm, Drawer, Spin, Timeline, Modal, Select, Space } from 'antd';
import { UserOutlined, SoundOutlined, StopOutlined, CheckOutlined, ReloadOutlined, HistoryOutlined, FileTextOutlined, CalendarOutlined, PlusOutlined } from '@ant-design/icons';
import { useState, useEffect, useCallback, useMemo } from 'react';
import { history } from 'umi';
import { appointmentApi, scheduleApi } from '@hospital/api';
import type { AvailableSchedule } from '@hospital/api';

// 患者历史就诊记录项类型
interface PatientHistoryItem {
  id: string;
  appointmentNo: string;
  scheduleDate: string | null;
  timeSlot: string | null;
  status: number;
  completeTime: string | null;
  symptomDescription: string | null;
  hasMedicalRecord: boolean;
}
import { APPOINTMENT_STATUS, APPOINTMENT_STATUS_MAP, TIME_SLOT_MAP } from '@hospital/shared';
import type { Appointment, QueueInfo } from '@hospital/shared';
import { useWebSocket, ConnectionStatus, WSMessageType } from '@/hooks';
import { ConnectionTag, ConnectionBanner } from '@/components/ConnectionStatus';

const ConsultationPage: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [currentPatient, setCurrentPatient] = useState<Appointment | null>(null);
  
  // 历史记录抽屉状态
  const [historyDrawerOpen, setHistoryDrawerOpen] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyData, setHistoryData] = useState<PatientHistoryItem[]>([]);
  const [selectedPatient, setSelectedPatient] = useState<Appointment | null>(null);
  
  // 复诊预约弹窗状态
  const [followUpModalOpen, setFollowUpModalOpen] = useState(false);
  const [followUpLoading, setFollowUpLoading] = useState(false);
  const [scheduleLoading, setScheduleLoading] = useState(false);
  const [availableSchedules, setAvailableSchedules] = useState<AvailableSchedule[]>([]);
  const [selectedScheduleId, setSelectedScheduleId] = useState<string>('');
  const [selectedAppointmentForFollowUp, setSelectedAppointmentForFollowUp] = useState<PatientHistoryItem | null>(null);

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
      setCurrentPatient(data.find((a: Appointment) => a.status === APPOINTMENT_STATUS.SEEING) || null);
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
      message.info('暂无待诊患者');
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

  // 查看患者历史记录
  const handleViewHistory = async (patient: Appointment) => {
    if (!patient.patientId) {
      message.warning('无法获取患者信息');
      return;
    }
    
    setSelectedPatient(patient);
    setHistoryDrawerOpen(true);
    setHistoryLoading(true);
    
    try {
      const result = await appointmentApi.getPatientHistory(patient.patientId, {
        pageSize: 20,
      });
      setHistoryData(result.items);
    } catch (error: any) {
      message.error(error.message || '加载历史记录失败');
      setHistoryData([]);
    } finally {
      setHistoryLoading(false);
    }
  };

  // 打开复诊预约弹窗
  const handleOpenFollowUp = async (historyItem: PatientHistoryItem) => {
    setSelectedAppointmentForFollowUp(historyItem);
    setFollowUpModalOpen(true);
    setScheduleLoading(true);
    setSelectedScheduleId('');
    
    try {
      // 加载当前医生的可用排班（未来14天）
      const schedules = await scheduleApi.getAvailable(doctorId, 14);
      setAvailableSchedules(schedules);
    } catch (error: any) {
      message.error(error.message || '加载排班失败');
      setAvailableSchedules([]);
    } finally {
      setScheduleLoading(false);
    }
  };

  // 创建复诊预约
  const handleCreateFollowUp = async () => {
    if (!selectedAppointmentForFollowUp || !selectedScheduleId) {
      message.warning('请选择排班');
      return;
    }
    
    setFollowUpLoading(true);
    try {
      const result = await appointmentApi.createFollowUp(
        selectedAppointmentForFollowUp.id,
        selectedScheduleId
      );
      message.success(`复诊预约创建成功，预约号：${result.appointmentNo}`);
      setFollowUpModalOpen(false);
      setSelectedAppointmentForFollowUp(null);
      setSelectedScheduleId('');
    } catch (error: any) {
      message.error(error.message || '创建复诊预约失败');
    } finally {
      setFollowUpLoading(false);
    }
  };

  // 待诊队列（已签到）
  const waitingList = appointments.filter((a) => a.status === APPOINTMENT_STATUS.SIGNED);
  // 已过号 (EXPIRED)
  const passedList = appointments.filter((a) => a.status === APPOINTMENT_STATUS.EXPIRED);

  return (
    <PageContainer
      loading={loading}
      extra={
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <ConnectionTag status={wsStatus} onReconnect={reconnect} />
          <Button icon={<ReloadOutlined />} onClick={loadData}>
            刷新
          </Button>
        </div>
      }
    >
      <ConnectionBanner status={wsStatus} onReconnect={reconnect} />
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
                  {currentPatient.isFollowUp ? (
                    <Tag color="purple" style={{ marginLeft: 8, fontSize: 12 }}>复诊</Tag>
                  ) : (
                    <Tag color="green" style={{ marginLeft: 8, fontSize: 12 }}>初诊</Tag>
                  )}
                </div>
                <div style={{ fontSize: 16, color: '#666', marginBottom: 8 }}>
                  {currentPatient.patientPhone?.replace(/(\d{3})\d{4}(\d{4})/, '$1****$2')}
                </div>
                <div style={{ marginBottom: 24 }}>
                  <Tag color="blue" style={{ fontSize: 14, padding: '4px 12px' }}>
                    {TIME_SLOT_MAP[currentPatient.timeSlot || 'morning']} 第{currentPatient.queueNumber}号
                  </Tag>
                </div>
                <div style={{ display: 'flex', gap: 16, justifyContent: 'center', flexWrap: 'wrap' }}>
                  <Button 
                    icon={<HistoryOutlined />} 
                    onClick={() => handleViewHistory(currentPatient)}
                  >
                    历史记录
                  </Button>
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

        {/* 待诊队列 */}
        <Col xs={24} lg={14}>
          <ProCard 
            title="待诊队列"
            extra={
              <div>
                <Badge count={waitingList.length} style={{ marginRight: 16 }}>
                  <Tag>已签到</Tag>
                </Badge>
                <Button type="primary" onClick={handleCallNext} disabled={!waitingList.length}>
                  呼叫下一位
                </Button>
              </div>
            }
            style={{ minHeight: 400 }}
          >
            {waitingList.length === 0 ? (
              <Empty description="暂无待诊患者" />
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
                          {item.isFollowUp ? (
                            <Tag color="purple" style={{ marginLeft: 8 }}>复诊</Tag>
                          ) : (
                            <Tag color="green" style={{ marginLeft: 8 }}>初诊</Tag>
                          )}
                          <Tag color="blue" style={{ marginLeft: 4 }}>第{item.queueNumber}号</Tag>
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
                  title={
                    <span>
                      {item.patientName}
                      {item.isFollowUp ? (
                        <Tag color="purple" style={{ marginLeft: 8 }}>复诊</Tag>
                      ) : (
                        <Tag color="green" style={{ marginLeft: 8 }}>初诊</Tag>
                      )}
                    </span>
                  }
                  description={`第${item.queueNumber}号`}
                />
                <Tag color="orange">已过号</Tag>
              </List.Item>
            )}
          />
        </ProCard>
      )}

      {/* 患者历史记录抽屉 */}
      <Drawer
        title={`${selectedPatient?.patientName || '患者'}的就诊历史`}
        open={historyDrawerOpen}
        onClose={() => {
          setHistoryDrawerOpen(false);
          setSelectedPatient(null);
          setHistoryData([]);
        }}
        width={480}
      >
        {historyLoading ? (
          <div style={{ textAlign: 'center', padding: '40px 0' }}>
            <Spin tip="加载中..." />
          </div>
        ) : historyData.length === 0 ? (
          <Empty description="暂无就诊记录" />
        ) : (
          <Timeline
            items={historyData.map((item) => ({
              color: item.status === APPOINTMENT_STATUS.COMPLETED ? 'green' : 'gray',
              children: (
                <div style={{ marginBottom: 16 }}>
                  <div style={{ marginBottom: 8 }}>
                    <Tag color="blue">{item.scheduleDate}</Tag>
                    <Tag>{TIME_SLOT_MAP[item.timeSlot || 'morning']}</Tag>
                    <Tag color={item.status === APPOINTMENT_STATUS.COMPLETED ? 'green' : 'default'}>
                      {APPOINTMENT_STATUS_MAP[item.status] || '未知'}
                    </Tag>
                  </div>
                  <div style={{ fontSize: 12, color: '#666', marginBottom: 4 }}>
                    预约号：{item.appointmentNo}
                  </div>
                  {item.symptomDescription && (
                    <div style={{ fontSize: 12, color: '#666', marginBottom: 4 }}>
                      病情描述：{item.symptomDescription}
                    </div>
                  )}
                  <Space size="small">
                    {item.hasMedicalRecord && (
                      <Button 
                        size="small" 
                        type="link" 
                        icon={<FileTextOutlined />}
                        style={{ padding: 0 }}
                        onClick={() => history.push(`/medical-record/view?appointmentId=${item.id}`)}
                      >
                        查看病历
                      </Button>
                    )}
                    {item.status === APPOINTMENT_STATUS.COMPLETED && (
                      <Button 
                        size="small" 
                        type="link" 
                        icon={<PlusOutlined />}
                        style={{ padding: 0 }}
                        onClick={() => handleOpenFollowUp(item)}
                      >
                        预约复诊
                      </Button>
                    )}
                  </Space>
                </div>
              ),
            }))}
          />
        )}
      </Drawer>

      {/* 复诊预约弹窗 */}
      <Modal
        title={
          <span>
            <CalendarOutlined style={{ marginRight: 8 }} />
            为{selectedPatient?.patientName || '患者'}预约复诊
          </span>
        }
        open={followUpModalOpen}
        onCancel={() => {
          setFollowUpModalOpen(false);
          setSelectedAppointmentForFollowUp(null);
          setSelectedScheduleId('');
        }}
        onOk={handleCreateFollowUp}
        confirmLoading={followUpLoading}
        okText="确认预约"
        cancelText="取消"
        okButtonProps={{ disabled: !selectedScheduleId }}
      >
        <div style={{ marginBottom: 16 }}>
          <p style={{ color: '#666', marginBottom: 8 }}>
            原预约号：{selectedAppointmentForFollowUp?.appointmentNo}
          </p>
          <p style={{ color: '#666' }}>
            请选择复诊时间：
          </p>
        </div>
        <Select
          style={{ width: '100%' }}
          placeholder="请选择排班"
          loading={scheduleLoading}
          value={selectedScheduleId || undefined}
          onChange={(value) => setSelectedScheduleId(value)}
          options={availableSchedules.map((s) => ({
            value: s.id,
            label: (
              <span>
                {s.scheduleDate} {TIME_SLOT_MAP[s.timeSlot || 'morning']}
                <Tag color="blue" style={{ marginLeft: 8 }}>
                  剩余 {s.availableSlots} 号
                </Tag>
              </span>
            ),
            disabled: s.availableSlots <= 0,
          }))}
          notFoundContent={scheduleLoading ? <Spin size="small" /> : <Empty description="暂无可用排班" image={Empty.PRESENTED_IMAGE_SIMPLE} />}
        />
      </Modal>
    </PageContainer>
  );
};

export default ConsultationPage;
