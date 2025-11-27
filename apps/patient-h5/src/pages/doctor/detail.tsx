import { NavBar, Card, Image, Button, Grid, Tag } from 'antd-mobile';
import { history, useParams } from 'umi';
import { TIME_SLOT_MAP } from '@hospital/shared';
import styles from './detail.less';

const mockSchedules = [
  { date: '2024-11-28', weekday: '周四', slots: [{ timeSlot: 'AM', available: 5 }, { timeSlot: 'PM', available: 0 }] },
  { date: '2024-11-29', weekday: '周五', slots: [{ timeSlot: 'AM', available: 10 }, { timeSlot: 'PM', available: 8 }] },
  { date: '2024-11-30', weekday: '周六', slots: [{ timeSlot: 'AM', available: 0 }] },
];

const DoctorDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();

  const handleBook = (date: string, timeSlot: string) => {
    history.push(`/booking/${id}?date=${date}&timeSlot=${timeSlot}`);
  };

  return (
    <div className={styles.container}>
      <NavBar onBack={() => history.back()}>医生详情</NavBar>
      
      <Card className={styles.doctorCard}>
        <div className={styles.doctorHeader}>
          <Image src="" width={80} height={80} fit="cover" style={{ borderRadius: 8, background: '#eee' }} />
          <div className={styles.doctorInfo}>
            <div className={styles.doctorName}>张医生 <Tag color="primary">主任医师</Tag></div>
            <div className={styles.doctorDept}>心内科</div>
            <div className={styles.doctorFee}>挂号费：¥50</div>
          </div>
        </div>
        <div className={styles.doctorSpec}>
          <div className={styles.specLabel}>擅长</div>
          <div>心血管疾病、高血压、冠心病的诊断与治疗</div>
        </div>
        <div className={styles.doctorIntro}>
          <div className={styles.specLabel}>简介</div>
          <div>从医20年，发表论文30余篇，擅长心血管疾病的诊断与治疗...</div>
        </div>
      </Card>

      <Card title="选择就诊时间" className={styles.scheduleCard}>
        {mockSchedules.map((schedule) => (
          <div key={schedule.date} className={styles.scheduleItem}>
            <div className={styles.scheduleDate}>
              <span>{schedule.date}</span>
              <span className={styles.weekday}>{schedule.weekday}</span>
            </div>
            <div className={styles.scheduleSlots}>
              {schedule.slots.map((slot) => (
                <Button
                  key={slot.timeSlot}
                  size="small"
                  color={slot.available > 0 ? 'primary' : 'default'}
                  disabled={slot.available === 0}
                  onClick={() => handleBook(schedule.date, slot.timeSlot)}
                  className={styles.slotBtn}
                >
                  {TIME_SLOT_MAP[slot.timeSlot]} {slot.available > 0 ? `余${slot.available}` : '约满'}
                </Button>
              ))}
            </div>
          </div>
        ))}
      </Card>
    </div>
  );
};

export default DoctorDetailPage;

