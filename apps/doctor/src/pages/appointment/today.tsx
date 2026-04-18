import { PageContainer, ProTable, ProCard } from '@ant-design/pro-components';
import type { ProColumns, ActionType } from '@ant-design/pro-components';
import { Tag, Button, Space, message, Row, Col, Statistic, Badge, Tooltip, Popconfirm } from 'antd';
import { SoundOutlined, CheckOutlined, UserOutlined, ClockCircleOutlined, WifiOutlined, DisconnectOutlined, StopOutlined } from '@ant-design/icons';
import { useRef, useState, useEffect, useCallback, useMemo } from 'react';
import { history } from 'umi';
import { appointmentApi } from '@hospital/api';
import { APPOINTMENT_STATUS, APPOINTMENT_STATUS_MAP, APPOINTMENT_STATUS_COLOR, TIME_SLOT_MAP } from '@hospital/shared';
import type { Appointment } from '@hospital/shared';
import { useWebSocket, ConnectionStatus } from '@/hooks';

const TodayAppointmentPage: React.FC = () => {
  const actionRef = useRef<ActionType>();
  const [loading, setLoading] = useState(true);
  const [appointments, setAppointments] = useState<Appointment[]>([]);

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
      const data = await appointmentApi.getToday();
      setAppointments(data);
    } catch (error) {
      console.error('加载失败', error);
    } finally {
      setLoading(false);
    }
  }, []);

  // WebSocket 连接
  const { status: wsStatus, reconnect } = useWebSocket({
    doctorId,
    onPatientSignedIn: () => loadData(),
    onQueueUpdated: () => loadData(),
    showNotifications: true,
  });

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleCall = async (appointment: Appointment) => {
    try {
      await appointmentApi.call(appointment.id);
      message.success(`已呼叫 ${appointment.patientName}`);
      loadData();
      actionRef.current?.reload();
    } catch (error: any) {
      message.error(error.message || '呼叫失败');
    }
  };

  const handleComplete = async (appointmentId: string) => {
    try {
      await appointmentApi.complete(appointmentId);
      message.success('就诊完成');
      history.push(`/medical-record/create?appointmentId=${appointmentId}`);
    } catch (error: any) {
      message.error(error.message || '操作失败');
    }
  };

  const handlePass = async (appointment: Appointment) => {
    try {
      await appointmentApi.pass(appointment.id);
      message.success('已过号');
      loadData();
      actionRef.current?.reload();
    } catch (error: any) {
      message.error(error.message || '操作失败');
    }
  };

  // 统计
  const stats = {
    total: appointments.length,
    pending: appointments.filter((a) => a.status === APPOINTMENT_STATUS.CONFIRMED).length,
    signedIn: appointments.filter((a) => a.status === APPOINTMENT_STATUS.SIGNED).length,
    inProgress: appointments.filter((a) => a.status === APPOINTMENT_STATUS.SEEING).length,
    completed: appointments.filter((a) => a.status === APPOINTMENT_STATUS.COMPLETED).length,
  };

  const columns: ProColumns<Appointment>[] = [
    { 
      title: '队列号', 
      dataIndex: 'queueNumber', 
      width: 80, 
      render: (_, r) => <Tag color="blue">第{r.queueNumber}号</Tag> 
    },
    { 
      title: '患者姓名', 
      dataIndex: 'patientName', 
      width: 140,
      render: (_, r) => (
        <Space>
          {r.patientName}
          {r.isFollowUp ? (
            <Tag color="purple" style={{ marginLeft: 4 }}>复诊</Tag>
          ) : (
            <Tag color="green" style={{ marginLeft: 4 }}>初诊</Tag>
          )}
        </Space>
      )
    },
    { 
      title: '手机号', 
      dataIndex: 'patientPhone', 
      width: 130,
      render: (_, r) => r.patientPhone?.replace(/(\d{3})\d{4}(\d{4})/, '$1****$2')
    },
    { 
      title: '时段', 
      dataIndex: 'timeSlot', 
      width: 80, 
      render: (_, r) => TIME_SLOT_MAP[r.timeSlot || 'morning'] 
    },
    { 
      title: '状态', 
      dataIndex: 'status', 
      width: 100, 
      render: (_, r) => (
        <Tag color={APPOINTMENT_STATUS_COLOR[r.status]}>
          {APPOINTMENT_STATUS_MAP[r.status]}
        </Tag>
      )
    },
    { 
      title: '签到时间', 
      dataIndex: 'signInTime', 
      width: 100,
      render: (_, r) => r.signInTime?.substring(11, 16) || '-'
    },
    { 
      title: '操作', 
      valueType: 'option',
      width: 220, 
      render: (_, r) => (
        <Space>
          {r.status === APPOINTMENT_STATUS.SIGNED && (
            <Button 
              size="small" 
              type="primary" 
              icon={<SoundOutlined />}
              onClick={() => handleCall(r)}
            >
              呼叫
            </Button>
          )}
          {r.status === APPOINTMENT_STATUS.SEEING && (
            <>
              <Button 
                size="small" 
                type="primary"
                icon={<CheckOutlined />}
                onClick={() => handleComplete(r.id)}
              >
                完成
              </Button>
              <Popconfirm
                title="确定过号吗？"
                description="过号后患者需要重新排队。"
                onConfirm={() => handlePass(r)}
              >
                <Button size="small" icon={<StopOutlined />}>
                  过号
                </Button>
              </Popconfirm>
            </>
          )}
          {(r.status === APPOINTMENT_STATUS.SEEING || r.status === APPOINTMENT_STATUS.COMPLETED) && (
            <Button 
              size="small"
              onClick={() => history.push(`/medical-record/create?appointmentId=${r.id}`)}
            >
              病历
            </Button>
          )}
        </Space>
      )
    },
  ];

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
    <PageContainer extra={connectionIndicator}>
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <ProCard>
            <Statistic 
              title="今日预约" 
              value={stats.total} 
              prefix={<UserOutlined />}
            />
          </ProCard>
        </Col>
        <Col span={6}>
          <ProCard>
            <Statistic
              title="已签到"
              value={stats.signedIn}
              valueStyle={{ color: '#faad14' }}
              prefix={<ClockCircleOutlined />}
            />
          </ProCard>
        </Col>
        <Col span={6}>
          <ProCard>
            <Statistic 
              title="就诊中" 
              value={stats.inProgress}
              valueStyle={{ color: '#1890ff' }}
              prefix={<Badge status="processing" />}
            />
          </ProCard>
        </Col>
        <Col span={6}>
          <ProCard>
            <Statistic 
              title="已完成" 
              value={stats.completed}
              valueStyle={{ color: '#52c41a' }}
              prefix={<CheckOutlined />}
            />
          </ProCard>
        </Col>
      </Row>

      <ProTable<Appointment>
        actionRef={actionRef}
        rowKey="id"
        columns={columns}
        loading={loading}
        dataSource={appointments}
        search={false}
        pagination={false}
        toolBarRender={() => [
          <Button key="refresh" onClick={loadData}>刷新</Button>,
          <Button 
            key="consultation" 
            type="primary"
            onClick={() => history.push('/consultation')}
          >
            进入就诊
          </Button>,
        ]}
      />
    </PageContainer>
  );
};

export default TodayAppointmentPage;
