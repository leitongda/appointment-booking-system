import { NavBar, Card, Image, Button, Tag, Skeleton, Toast } from 'antd-mobile';
import { history, useParams } from 'umi';
import { useState, useEffect } from 'react';
import { doctorApi, scheduleApi } from '@hospital/api';
import { TIME_SLOT_MAP } from '@hospital/shared';
import type { Doctor, AvailableSchedule } from '@hospital/shared';
import dayjs from 'dayjs';
import styles from './detail.less';

const WEEKDAY_NAMES = ['周日', '周一', '周二', '周三', '周四', '周五', '周六'];

const DoctorDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [loading, setLoading] = useState(true);
  const [doctor, setDoctor] = useState<Doctor | null>(null);
  const [schedules, setSchedules] = useState<AvailableSchedule[]>([]);

  useEffect(() => {
    if (id) {
      loadData();
    }
  }, [id]);

  const loadData = async () => {
    try {
      const [doctorData, scheduleData] = await Promise.all([
        doctorApi.getDetail(id!),
        scheduleApi.getAvailable(id!, 14),
      ]);
      setDoctor(doctorData);
      setSchedules(scheduleData);
    } catch (error) {
      console.error('加载数据失败', error);
      Toast.show({ content: '加载失败', icon: 'fail' });
    } finally {
      setLoading(false);
    }
  };

  const handleBook = (schedule: AvailableSchedule) => {
    if (schedule.availableSlots <= 0) {
      Toast.show({ content: '该时段已约满' });
      return;
    }
    history.push(`/booking/${id}?scheduleId=${schedule.id}&date=${schedule.scheduleDate}&timeSlot=${schedule.timeSlot}`);
  };

  // 按日期分组排班
  const groupedSchedules = schedules.reduce((acc, schedule) => {
    const date = schedule.scheduleDate;
    if (!acc[date]) {
      acc[date] = [];
    }
    acc[date].push(schedule);
    return acc;
  }, {} as Record<string, AvailableSchedule[]>);

  if (loading) {
    return (
      <div className={styles.container}>
        <NavBar onBack={() => history.back()}>医生详情</NavBar>
        <Skeleton.Paragraph lineCount={10} animated />
      </div>
    );
  }

  if (!doctor) {
    return (
      <div className={styles.container}>
        <NavBar onBack={() => history.back()}>医生详情</NavBar>
        <div style={{ textAlign: 'center', padding: 40 }}>医生信息不存在</div>
      </div>
    );
  }

  return (
    <div className={styles.container}>
      <NavBar onBack={() => history.back()}>医生详情</NavBar>
      
      <Card className={styles.doctorCard}>
        <div className={styles.doctorHeader}>
          <Image 
            src={doctor.avatar || ''} 
            width={80} 
            height={80} 
            fit="cover" 
            style={{ borderRadius: 8, background: '#f5f5f5' }} 
          />
          <div className={styles.doctorInfo}>
            <div className={styles.doctorName}>
              {doctor.name}
              {doctor.title && <Tag color="primary">{doctor.title}</Tag>}
            </div>
            <div className={styles.doctorDept}>{doctor.departmentName}</div>
            <div className={styles.doctorFee}>挂号费：¥{doctor.registrationFee}</div>
          </div>
        </div>
        <div className={styles.doctorSpec}>
          <div className={styles.specLabel}>擅长</div>
          <div>{doctor.specialty || '暂无信息'}</div>
        </div>
        <div className={styles.doctorIntro}>
          <div className={styles.specLabel}>简介</div>
          <div>{doctor.introduction || '暂无简介'}</div>
        </div>
      </Card>

      <Card title="选择就诊时间" className={styles.scheduleCard}>
        {Object.keys(groupedSchedules).length === 0 ? (
          <div className={styles.noSchedule}>暂无可预约时段</div>
        ) : (
          Object.entries(groupedSchedules).map(([date, daySchedules]) => (
            <div key={date} className={styles.scheduleItem}>
              <div className={styles.scheduleDate}>
                <span>{dayjs(date).format('MM-DD')}</span>
                <span className={styles.weekday}>{WEEKDAY_NAMES[dayjs(date).day()]}</span>
              </div>
              <div className={styles.scheduleSlots}>
                {daySchedules.map((schedule) => (
                  <Button
                    key={schedule.id}
                    size="small"
                    color={schedule.availableSlots > 0 ? 'primary' : 'default'}
                    fill={schedule.availableSlots > 0 ? 'solid' : 'outline'}
                    disabled={schedule.availableSlots === 0}
                    onClick={() => handleBook(schedule)}
                    className={styles.slotBtn}
                  >
                    {TIME_SLOT_MAP[schedule.timeSlot]}
                    <br />
                    {schedule.availableSlots > 0 ? `余${schedule.availableSlots}` : '约满'}
                  </Button>
                ))}
              </div>
            </div>
          ))
        )}
      </Card>
    </div>
  );
};

export default DoctorDetailPage;
