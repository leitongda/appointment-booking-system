import { NavBar, Radio, Toast, Dialog, Skeleton, Empty, TextArea } from 'antd-mobile';
import { history, useParams, useSearchParams } from 'umi';
import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { doctorApi, userApi, appointmentApi } from '@hospital/api';
import { TIME_SLOT_MAP } from '@hospital/shared';
import type { Doctor, Patient } from '@hospital/shared';
import { Card, Button } from '@/components/ui';
import { fadeInUp, stagger } from '@/components/ui/animations';

const BookingPage: React.FC = () => {
  const { doctorId } = useParams() as { doctorId: string };
  const [searchParams] = useSearchParams();
  const scheduleId = searchParams.get('scheduleId');
  const date = searchParams.get('date');
  const timeSlot = searchParams.get('timeSlot');
  
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [doctor, setDoctor] = useState<Doctor | null>(null);
  const [patients, setPatients] = useState<Patient[]>([]);
  const [selectedPatientId, setSelectedPatientId] = useState<string>('');
  const [symptoms, setSymptoms] = useState<string>('');

  useEffect(() => {
    loadData();
  }, [doctorId]);

  const loadData = async () => {
    try {
      const [doctorData, patientsData] = await Promise.all([
        doctorApi.getDetail(doctorId!),
        userApi.getPatients(),
      ]);
      setDoctor(doctorData);
      setPatients(patientsData);
      
      const defaultPatient = patientsData.find((p) => p.isDefault) || patientsData[0];
      if (defaultPatient) {
        setSelectedPatientId(defaultPatient.id);
      }
    } catch (error) {
      console.error('加载数据失败', error);
      Toast.show({ content: '加载失败', icon: 'fail' });
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async () => {
    if (!selectedPatientId) {
      Toast.show({ content: '请选择就诊人' });
      return;
    }

    setSubmitting(true);
    try {
      // 重复预约检查
      try {
        const duplicateResult = await appointmentApi.checkDuplicate(scheduleId!, selectedPatientId);
        if (duplicateResult.hasDuplicate && duplicateResult.appointments.length > 0) {
          const existingAppt = duplicateResult.appointments[0];
          const statusText = existingAppt.status === 1 ? '已预约' :
                            existingAppt.status === 2 ? '已签到' :
                            existingAppt.status === 4 ? '就诊中' :
                            existingAppt.status === 3 ? '历史候诊' : '已有进行中';
          const message = `您已有${statusText}的预约（${existingAppt.scheduleDate} ${existingAppt.timeSlot}），是否继续创建新预约？`;

          const confirmResult = await Dialog.confirm({
            content: message,
          });

          if (!confirmResult) {
            setSubmitting(false);
            return;
          }
        }
      } catch (checkError: any) {
        // 重复检查失败时，记录日志但不阻止预约流程
        console.warn('重复预约检查失败，继续预约流程:', checkError);
      }

      const appointment = await appointmentApi.create({
        scheduleId: scheduleId!,
        patientId: selectedPatientId,
        symptomDescription: symptoms.trim() || undefined,
      });

      const createdAppointment = 'appointment' in appointment ? appointment.appointment : appointment;
      const paymentRequired =
        'payment_required' in appointment ? Boolean(appointment.payment_required) : createdAppointment.status === 0;

      if (paymentRequired) {
        Toast.show({
          content: '预约已创建，请前往详情查看待支付状态并使用可支付端完成支付',
          icon: 'success',
        });
        history.replace(`/appointment/${createdAppointment.id}`);
        return;
      }

      Toast.show({ content: '预约成功', icon: 'success' });
      history.replace(`/booking/confirm?appointmentNo=${createdAppointment.appointmentNo}`);
    } catch (error: any) {
      Toast.show({ content: error.message || '预约失败', icon: 'fail' });
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-background">
        <NavBar 
          onBack={() => history.back()}
          className="!bg-card border-b border-border"
        >
          确认预约
        </NavBar>
        <div className="p-4">
          <Skeleton.Paragraph lineCount={8} animated />
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background pb-24">
      <NavBar 
        onBack={() => history.back()}
        className="!bg-card border-b border-border"
      >
        确认预约
      </NavBar>

      <motion.div
        className="p-4 space-y-4"
        variants={stagger}
        initial="hidden"
        animate="visible"
      >
        {/* Appointment Info */}
        <motion.div variants={fadeInUp}>
          <Card variant="default" padding="lg">
            <h3 className="font-semibold text-foreground mb-4">预约信息</h3>
            <div className="space-y-3">
              <div className="flex justify-between">
                <span className="text-muted-foreground">医生</span>
                <span className="text-foreground font-medium">
                  {doctor?.name} - {doctor?.title}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">科室</span>
                <span className="text-foreground">{doctor?.departmentName}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">日期</span>
                <span className="text-foreground">{date}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">时段</span>
                <span className="text-foreground">{TIME_SLOT_MAP[timeSlot || 'morning']}</span>
              </div>
            </div>
          </Card>
        </motion.div>

        {/* Patient Selection */}
        <motion.div variants={fadeInUp}>
          <Card variant="default" padding="lg">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-semibold text-foreground">选择就诊人</h3>
              <Button 
                variant="ghost" 
                size="sm"
                onClick={() => history.push('/profile/patient/edit')}
                icon={
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                  </svg>
                }
              >
                新增
              </Button>
            </div>

            {patients.length === 0 ? (
              <Empty description="请先添加就诊人" />
            ) : (
              <Radio.Group 
                value={selectedPatientId} 
                onChange={(v) => setSelectedPatientId(v as string)}
              >
                <div className="space-y-2">
                  {patients.map((patient) => (
                    <div 
                      key={patient.id}
                      className={`
                        flex items-center gap-3 p-4 rounded-xl border transition-all cursor-pointer
                        ${selectedPatientId === patient.id 
                          ? 'border-accent bg-accent/5' 
                          : 'border-border bg-muted hover:border-accent/30'
                        }
                      `}
                      onClick={() => setSelectedPatientId(patient.id)}
                    >
                      <Radio value={patient.id} />
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <span className="font-medium text-foreground">{patient.name}</span>
                          {patient.isDefault && (
                            <span className="text-xs text-accent bg-accent/10 px-2 py-0.5 rounded-full">
                              默认
                            </span>
                          )}
                        </div>
                        <p className="text-sm text-muted-foreground mt-1">
                          {patient.phone.replace(/(\d{3})\d{4}(\d{4})/, '$1****$2')}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              </Radio.Group>
            )}
          </Card>
        </motion.div>

        {/* Symptoms Description */}
        <motion.div variants={fadeInUp}>
          <Card variant="default" padding="lg">
            <h3 className="font-semibold text-foreground mb-4">病情描述</h3>
            <TextArea
              placeholder="请简要描述您的病情或症状（选填）"
              value={symptoms}
              onChange={(val) => setSymptoms(val)}
              rows={3}
              maxLength={500}
              showCount
            />
          </Card>
        </motion.div>
      </motion.div>

      {/* Fixed Footer */}
      <div className="fixed bottom-0 left-0 right-0 bg-card border-t border-border p-4 safe-area-inset-bottom">
        <Button 
          size="lg"
          block
          onClick={handleSubmit}
          loading={submitting}
          disabled={!selectedPatientId}
        >
          确认预约
        </Button>
      </div>
    </div>
  );
};

export default BookingPage;
