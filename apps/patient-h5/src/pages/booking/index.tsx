import { NavBar, Card, List, Button, Radio, Toast } from 'antd-mobile';
import { history, useParams, useSearchParams } from 'umi';
import { useState } from 'react';
import { TIME_SLOT_MAP } from '@hospital/shared';
import styles from './index.less';

const mockPatients = [
  { id: '1', name: '张三', phone: '138****8000', isDefault: true },
  { id: '2', name: '李四', phone: '138****8001', isDefault: false },
];

const BookingPage: React.FC = () => {
  const { doctorId } = useParams<{ doctorId: string }>();
  const [searchParams] = useSearchParams();
  const date = searchParams.get('date');
  const timeSlot = searchParams.get('timeSlot');
  
  const [selectedPatient, setSelectedPatient] = useState(mockPatients[0]?.id);

  const handleSubmit = () => {
    if (!selectedPatient) {
      Toast.show('请选择就诊人');
      return;
    }
    Toast.show('预约成功');
    history.push('/appointment');
  };

  return (
    <div className={styles.container}>
      <NavBar onBack={() => history.back()}>确认预约</NavBar>

      <Card title="预约信息" className={styles.card}>
        <div className={styles.row}><span>医生</span><span>张医生 - 主任医师</span></div>
        <div className={styles.row}><span>科室</span><span>心内科</span></div>
        <div className={styles.row}><span>日期</span><span>{date}</span></div>
        <div className={styles.row}><span>时段</span><span>{TIME_SLOT_MAP[timeSlot || 'AM']}</span></div>
        <div className={styles.row}><span>挂号费</span><span className={styles.fee}>¥50.00</span></div>
      </Card>

      <Card title="选择就诊人" className={styles.card} extra={<a onClick={() => history.push('/profile/patient/edit')}>新增</a>}>
        <Radio.Group value={selectedPatient} onChange={(v) => setSelectedPatient(v as string)}>
          <List>
            {mockPatients.map((patient) => (
              <List.Item key={patient.id} prefix={<Radio value={patient.id} />}>
                {patient.name} ({patient.phone})
              </List.Item>
            ))}
          </List>
        </Radio.Group>
      </Card>

      <div className={styles.footer}>
        <div className={styles.total}>
          <span>合计：</span>
          <span className={styles.price}>¥50.00</span>
        </div>
        <Button color="primary" onClick={handleSubmit}>确认预约</Button>
      </div>
    </div>
  );
};

export default BookingPage;

