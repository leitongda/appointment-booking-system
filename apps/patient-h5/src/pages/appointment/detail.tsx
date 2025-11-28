import { NavBar, Card, Steps, Button, Dialog, Toast, Skeleton, Empty, Tag } from 'antd-mobile';
import { history, useParams } from 'umi';
import { useState, useEffect } from 'react';
import { appointmentApi } from '@hospital/api';
import { APPOINTMENT_STATUS_MAP, APPOINTMENT_STATUS_COLOR, TIME_SLOT_MAP } from '@hospital/shared';
import type { Appointment } from '@hospital/shared';
import styles from './detail.less';

const { Step } = Steps;

const AppointmentDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [loading, setLoading] = useState(true);
  const [appointment, setAppointment] = useState<Appointment | null>(null);

  useEffect(() => {
    if (id) {
      loadData();
    }
  }, [id]);

  const loadData = async () => {
    try {
      const data = await appointmentApi.getDetail(id!);
      setAppointment(data);
    } catch (error: any) {
      Toast.show({ content: error.message || '加载失败', icon: 'fail' });
    } finally {
      setLoading(false);
    }
  };

  const handleCancel = async () => {
    const result = await Dialog.confirm({ 
      content: '确定要取消预约吗？取消后号源将被释放。',
      confirmText: '确定取消',
      cancelText: '再想想',
    });
    
    if (result) {
      try {
        await appointmentApi.cancel(id!);
        Toast.show({ content: '取消成功', icon: 'success' });
        loadData();
      } catch (error: any) {
        Toast.show({ content: error.message || '取消失败', icon: 'fail' });
      }
    }
  };

  const handleSignIn = async () => {
    try {
      const result = await appointmentApi.signIn(id!);
      Toast.show({ 
        content: `签到成功，您是第 ${result.queueNumber} 号`, 
        icon: 'success' 
      });
      loadData();
    } catch (error: any) {
      Toast.show({ content: error.message || '签到失败', icon: 'fail' });
    }
  };

  const getStepsCurrent = (status: number) => {
    switch (status) {
      case 1: return 0; // 待就诊
      case 2: return 1; // 已签到
      case 3: return 2; // 就诊中
      case 5: return 3; // 已完成
      case 6: return -1; // 已取消
      case 7: return -1; // 爽约
      default: return 0;
    }
  };

  const formatDate = (date?: string) => {
    if (!date) return '-';
    return date.substring(0, 10);
  };

  const formatTime = (date?: string) => {
    if (!date) return '-';
    return date.substring(0, 16).replace('T', ' ');
  };

  if (loading) {
    return (
      <div className={styles.container}>
        <NavBar onBack={() => history.back()}>预约详情</NavBar>
        <div style={{ padding: 16 }}>
          <Skeleton.Paragraph lineCount={10} animated />
        </div>
      </div>
    );
  }

  if (!appointment) {
    return (
      <div className={styles.container}>
        <NavBar onBack={() => history.back()}>预约详情</NavBar>
        <Empty description="预约不存在" style={{ marginTop: 100 }} />
      </div>
    );
  }

  const isCancelled = appointment.status === 6;
  const isCompleted = appointment.status === 5;
  const isNoShow = appointment.status === 7;
  const canCancel = appointment.status === 1; // 只有待就诊可取消
  const canSignIn = appointment.status === 1; // 只有待就诊可签到

  return (
    <div className={styles.container}>
      <NavBar onBack={() => history.back()}>预约详情</NavBar>

      {/* 状态展示 */}
      <div className={styles.statusBar} style={{ 
        backgroundColor: isCancelled || isNoShow ? '#ff4d4f' : isCompleted ? '#52c41a' : '#1890ff' 
      }}>
        <div className={styles.statusText}>
          {APPOINTMENT_STATUS_MAP[appointment.status]}
        </div>
        {appointment.status === 2 && (
          <div className={styles.queueInfo}>
            您是第 {appointment.queueNumber} 号，请耐心等待叫号
          </div>
        )}
      </div>

      <Card title="预约信息" className={styles.card}>
        <div className={styles.row}><span>预约单号</span><span>{appointment.appointmentNo}</span></div>
        <div className={styles.row}><span>预约日期</span><span>{formatDate(appointment.scheduleDate)}</span></div>
        <div className={styles.row}>
          <span>就诊时段</span>
          <span>{TIME_SLOT_MAP[appointment.timeSlot || 'AM']} 第{appointment.queueNumber}号</span>
        </div>
        <div className={styles.row}><span>挂号费</span><span className={styles.fee}>¥{appointment.fee?.toFixed(2) || '0.00'}</span></div>
      </Card>

      <Card title="就诊人信息" className={styles.card}>
        <div className={styles.row}><span>姓名</span><span>{appointment.patientName}</span></div>
        <div className={styles.row}>
          <span>手机号</span>
          <span>{appointment.patientPhone?.replace(/(\d{3})\d{4}(\d{4})/, '$1****$2')}</span>
        </div>
      </Card>

      <Card title="医生信息" className={styles.card}>
        <div className={styles.row}><span>医生</span><span>{appointment.doctorName}</span></div>
        <div className={styles.row}><span>职称</span><span>{appointment.doctorTitle}</span></div>
        <div className={styles.row}><span>科室</span><span>{appointment.departmentName}</span></div>
      </Card>

      {!isCancelled && !isNoShow && (
        <Card title="就诊进度" className={styles.card}>
          <Steps current={getStepsCurrent(appointment.status)} direction="vertical">
            <Step 
              title="已预约" 
              description={formatTime(appointment.createdAt)} 
            />
            <Step 
              title="已签到" 
              description={appointment.signInTime ? formatTime(appointment.signInTime) : '等待签到'} 
            />
            <Step 
              title="就诊中" 
              description={appointment.callTime ? formatTime(appointment.callTime) : ''} 
            />
            <Step 
              title="已完成" 
              description={appointment.completeTime ? formatTime(appointment.completeTime) : ''} 
            />
          </Steps>
        </Card>
      )}

      {isCancelled && (
        <Card title="取消信息" className={styles.card}>
          <div className={styles.row}><span>取消时间</span><span>{formatTime(appointment.cancelTime)}</span></div>
          {appointment.cancelReason && (
            <div className={styles.row}><span>取消原因</span><span>{appointment.cancelReason}</span></div>
          )}
        </Card>
      )}

      {(canCancel || canSignIn) && (
        <div className={styles.footer}>
          {canCancel && (
            <Button block onClick={handleCancel}>取消预约</Button>
          )}
          {canSignIn && (
            <Button block color="primary" onClick={handleSignIn}>签到</Button>
          )}
        </div>
      )}
    </div>
  );
};

export default AppointmentDetailPage;
