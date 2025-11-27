import { NavBar, Card, List, Button, Radio, Toast, Dialog, Skeleton, Empty } from 'antd-mobile';
import { history, useParams, useSearchParams } from 'umi';
import { useState, useEffect } from 'react';
import { AddOutline } from 'antd-mobile-icons';
import { doctorApi, scheduleApi, userApi, appointmentApi } from '@hospital/api';
import { TIME_SLOT_MAP } from '@hospital/shared';
import type { Doctor, Patient, AvailableSchedule } from '@hospital/shared';
import styles from './index.less';

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
      
      // 默认选择第一个就诊人或默认就诊人
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
      <div className={styles.container}>
        <NavBar onBack={() => history.back()}>确认预约</NavBar>
        <Skeleton.Paragraph lineCount={8} animated />
      </div>
    );
  }

  return (
    <div className={styles.container}>
      <NavBar onBack={() => history.back()}>确认预约</NavBar>

      <Card title="预约信息" className={styles.card}>
        <div className={styles.row}>
          <span>医生</span>
          <span>{doctor?.name} - {doctor?.title}</span>
        </div>
        <div className={styles.row}>
          <span>科室</span>
          <span>{doctor?.departmentName}</span>
        </div>
        <div className={styles.row}>
          <span>日期</span>
          <span>{date}</span>
        </div>
        <div className={styles.row}>
          <span>时段</span>
          <span>{TIME_SLOT_MAP[timeSlot || 'AM']}</span>
        </div>
        <div className={styles.row}>
          <span>挂号费</span>
          <span className={styles.fee}>¥{doctor?.registrationFee || 0}</span>
        </div>
      </Card>

      <Card 
        title="选择就诊人" 
        className={styles.card} 
        extra={
          <Button 
            size="mini" 
            onClick={() => history.push('/profile/patient/edit')}
          >
            <AddOutline /> 新增
          </Button>
        }
      >
        {patients.length === 0 ? (
          <Empty description="请先添加就诊人" />
        ) : (
          <Radio.Group value={selectedPatientId} onChange={(v) => setSelectedPatientId(v as string)}>
            <List>
              {patients.map((patient) => (
                <List.Item key={patient.id} prefix={<Radio value={patient.id} />}>
                  {patient.name}
                  <span className={styles.patientPhone}>
                    ({patient.phone.replace(/(\d{3})\d{4}(\d{4})/, '$1****$2')})
                  </span>
                  {patient.isDefault && <span className={styles.defaultTag}>默认</span>}
                </List.Item>
              ))}
            </List>
          </Radio.Group>
        )}
      </Card>

      <div className={styles.footer}>
        <div className={styles.total}>
          <span>合计：</span>
          <span className={styles.price}>¥{doctor?.registrationFee || 0}</span>
        </div>
        <Button 
          color="primary" 
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
