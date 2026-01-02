import { NavBar, Radio, Toast, Dialog, Skeleton, Empty } from 'antd-mobile';
import { history, useParams, useSearchParams } from 'umi';
import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { doctorApi, userApi, appointmentApi } from '@hospital/api';
import { TIME_SLOT_MAP } from '@hospital/shared';
import type { Doctor, Patient } from '@hospital/shared';
import { Card, Button } from '@/components/ui';
import { fadeInUp, stagger } from '@/components/ui/animations';

const BookingPage: React.FC = () => {
  const { doctorId } = useParams<{ doctorId: string }>();
  const [searchParams] = useSearchParams();
  const scheduleId = searchParams.get('scheduleId');
  const date = searchParams.get('date');
  const timeSlot = searchParams.get('timeSlot');
  
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [doctor, setDoctor] = useState<Doctor | null>(null);
  const [patients, setPatients] = useState<Patient[]>([]);
  const [selectedPatientId, setSelectedPatientId] = useState<string>('');

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

    const result = await Dialog.confirm({
      content: '确定要预约吗？',
    });

    if (!result) return;

    setSubmitting(true);
    try {
      const appointment = await appointmentApi.create({
        scheduleId: scheduleId!,
        patientId: selectedPatientId,
      });
      
      Toast.show({ content: '预约成功', icon: 'success' });
      history.replace(`/booking/confirm?appointmentNo=${appointment.appointmentNo}`);
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
                <span className="text-foreground">{TIME_SLOT_MAP[timeSlot || 'AM']}</span>
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
