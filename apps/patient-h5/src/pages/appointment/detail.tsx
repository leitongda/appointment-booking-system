import { NavBar, Steps, Dialog, Toast, Skeleton, Empty } from 'antd-mobile';
import { history, useParams } from 'umi';
import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { appointmentApi } from '@hospital/api';
import { APPOINTMENT_STATUS_MAP, TIME_SLOT_MAP } from '@hospital/shared';
import type { Appointment } from '@hospital/shared';
import { Card, Button, InvertedSection } from '@/components/ui';
import { fadeInUp, stagger } from '@/components/ui/animations';

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
      const result = await appointmentApi.signIn(id!, { checkin_method: 'PHONE' });
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
      case 1: return 0;
      case 2: return 1;
      case 3: return 2;
      case 5: return 3;
      case 6: return -1;
      case 7: return -1;
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

  const getStatusColor = (status: number) => {
    // 6=已取消, 7=已过期, 8=已关闭(爽约)
    if (status === 6 || status === 7 || status === 8) return 'from-red-500 to-red-600';
    if (status === 5) return 'from-green-500 to-green-600';
    return 'from-accent to-accent-secondary';
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-background">
        <NavBar 
          onBack={() => history.back()}
          className="!bg-card border-b border-border"
        >
          预约详情
        </NavBar>
        <div className="p-4">
          <Skeleton.Paragraph lineCount={10} animated />
        </div>
      </div>
    );
  }

  if (!appointment) {
    return (
      <div className="min-h-screen bg-background">
        <NavBar 
          onBack={() => history.back()}
          className="!bg-card border-b border-border"
        >
          预约详情
        </NavBar>
        <div className="flex items-center justify-center h-64">
          <Empty description="预约不存在" />
        </div>
      </div>
    );
  }

  const isCancelled = appointment.status === 6;
  const isCompleted = appointment.status === 5;
  const isNoShow = appointment.status === 8;  // 8=CLOSED(爽约)
  const canCancel = appointment.status === 1;
  const canSignIn = appointment.status === 1;

  return (
    <div className="min-h-screen bg-background pb-24">
      <NavBar 
        onBack={() => history.back()}
        className="!bg-transparent absolute top-0 left-0 right-0 z-20 text-white"
      >
        预约详情
      </NavBar>

      {/* Status Header */}
      <div className={`bg-gradient-to-r ${getStatusColor(appointment.status)} pt-16 pb-8 px-4`}>
        <div className="text-center text-white">
          <h2 className="text-2xl font-display mb-2">
            {APPOINTMENT_STATUS_MAP[appointment.status]}
          </h2>
          {appointment.status === 2 && (
            <p className="text-white/80">
              您是第 {appointment.queueNumber} 号，请耐心等待叫号
            </p>
          )}
        </div>
      </div>

      <motion.div
        className="px-4 -mt-4 relative z-10 space-y-4"
        variants={stagger}
        initial="hidden"
        animate="visible"
      >
        {/* Appointment Info */}
        <motion.div variants={fadeInUp}>
          <Card variant="elevated" padding="lg">
            <h3 className="font-semibold text-foreground mb-4">预约信息</h3>
            <div className="space-y-3">
              <div className="flex justify-between">
                <span className="text-muted-foreground">预约单号</span>
                <span className="font-mono text-foreground">{appointment.appointmentNo}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">预约日期</span>
                <span className="text-foreground">{formatDate(appointment.scheduleDate)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">就诊时段</span>
                <span className="text-foreground">
                  {TIME_SLOT_MAP[appointment.timeSlot || 'AM']} 第{appointment.queueNumber}号
                </span>
              </div>
            </div>
          </Card>
        </motion.div>

        {/* Patient Info */}
        <motion.div variants={fadeInUp}>
          <Card variant="default" padding="lg">
            <h3 className="font-semibold text-foreground mb-4">就诊人信息</h3>
            <div className="space-y-3">
              <div className="flex justify-between">
                <span className="text-muted-foreground">姓名</span>
                <span className="text-foreground">{appointment.patientName}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">手机号</span>
                <span className="text-foreground">
                  {appointment.patientPhone?.replace(/(\d{3})\d{4}(\d{4})/, '$1****$2')}
                </span>
              </div>
            </div>
          </Card>
        </motion.div>

        {/* Doctor Info */}
        <motion.div variants={fadeInUp}>
          <Card variant="default" padding="lg">
            <h3 className="font-semibold text-foreground mb-4">医生信息</h3>
            <div className="space-y-3">
              <div className="flex justify-between">
                <span className="text-muted-foreground">医生</span>
                <span className="text-foreground">{appointment.doctorName}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">职称</span>
                <span className="text-foreground">{appointment.doctorTitle}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">科室</span>
                <span className="text-foreground">{appointment.departmentName}</span>
              </div>
            </div>
          </Card>
        </motion.div>

        {/* Progress Steps */}
        {!isCancelled && !isNoShow && (
          <motion.div variants={fadeInUp}>
            <Card variant="default" padding="lg">
              <h3 className="font-semibold text-foreground mb-4">就诊进度</h3>
              <Steps 
                current={getStepsCurrent(appointment.status)} 
                direction="vertical"
                style={{
                  '--adm-color-primary': '#0052FF',
                } as React.CSSProperties}
              >
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
          </motion.div>
        )}

        {/* Cancel Info */}
        {isCancelled && (
          <motion.div variants={fadeInUp}>
            <Card variant="default" padding="lg">
              <h3 className="font-semibold text-foreground mb-4">取消信息</h3>
              <div className="space-y-3">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">取消时间</span>
                  <span className="text-foreground">{formatTime(appointment.cancelTime)}</span>
                </div>
                {appointment.cancelReason && (
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">取消原因</span>
                    <span className="text-foreground">{appointment.cancelReason}</span>
                  </div>
                )}
              </div>
            </Card>
          </motion.div>
        )}
      </motion.div>

      {/* Footer Actions */}
      {(canCancel || canSignIn) && (
        <div className="fixed bottom-0 left-0 right-0 bg-card border-t border-border p-4 flex gap-3 safe-area-inset-bottom">
          {canCancel && (
            <Button variant="outline" block onClick={handleCancel}>
              取消预约
            </Button>
          )}
          {canSignIn && (
            <Button block onClick={handleSignIn}>
              签到
            </Button>
          )}
        </div>
      )}
    </div>
  );
};

export default AppointmentDetailPage;
