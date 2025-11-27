import { NavBar, Tabs, Card, Tag, Empty, Button } from 'antd-mobile';
import { history } from 'umi';
import { APPOINTMENT_STATUS_MAP, TIME_SLOT_MAP } from '@hospital/shared';
import styles from './index.less';

const mockAppointments = [
  { id: '1', appointmentNo: 'YY001', doctorName: '张医生', deptName: '心内科', date: '2024-11-28', timeSlot: 'AM', queueNumber: 5, status: 1 },
  { id: '2', appointmentNo: 'YY002', doctorName: '李医生', deptName: '消化内科', date: '2024-11-20', timeSlot: 'PM', queueNumber: 3, status: 5 },
];

const AppointmentPage: React.FC = () => {
  return (
    <div className={styles.container}>
      <div className={styles.header}>我的预约</div>
      <Tabs defaultActiveKey="all" className={styles.tabs}>
        <Tabs.Tab title="全部" key="all" />
        <Tabs.Tab title="待就诊" key="1" />
        <Tabs.Tab title="已完成" key="5" />
        <Tabs.Tab title="已取消" key="6" />
      </Tabs>
      <div className={styles.list}>
        {mockAppointments.length === 0 ? (
          <Empty description="暂无预约记录" />
        ) : (
          mockAppointments.map((item) => (
            <Card key={item.id} className={styles.card} onClick={() => history.push(`/appointment/${item.id}`)}>
              <div className={styles.cardHeader}>
                <span className={styles.appointmentNo}>预约单号：{item.appointmentNo}</span>
                <Tag color={item.status === 1 ? 'primary' : 'default'}>{APPOINTMENT_STATUS_MAP[item.status]}</Tag>
              </div>
              <div className={styles.cardBody}>
                <div className={styles.info}>
                  <div className={styles.doctorName}>{item.doctorName}</div>
                  <div className={styles.deptName}>{item.deptName}</div>
                </div>
                <div className={styles.time}>
                  <div>{item.date}</div>
                  <div>{TIME_SLOT_MAP[item.timeSlot]} 第{item.queueNumber}号</div>
                </div>
              </div>
              {item.status === 1 && (
                <div className={styles.cardFooter}>
                  <Button size="small" onClick={(e) => { e.stopPropagation(); }}>取消预约</Button>
                  <Button size="small" color="primary">签到</Button>
                </div>
              )}
            </Card>
          ))
        )}
      </div>
    </div>
  );
};

export default AppointmentPage;

