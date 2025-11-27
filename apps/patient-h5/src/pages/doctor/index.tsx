import { NavBar, List, Image, Tag } from 'antd-mobile';
import { history, useSearchParams } from 'umi';
import styles from './index.less';

const mockDoctors = [
  { id: '1', name: '张医生', title: '主任医师', department: '心内科', specialty: '心血管疾病、高血压', fee: 50 },
  { id: '2', name: '李医生', title: '副主任医师', department: '心内科', specialty: '冠心病、心律失常', fee: 30 },
  { id: '3', name: '王医生', title: '主治医师', department: '心内科', specialty: '心脏康复', fee: 20 },
];

const DoctorPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const departmentId = searchParams.get('departmentId');

  return (
    <div className={styles.container}>
      <NavBar onBack={() => history.back()}>选择医生</NavBar>
      <List className={styles.list}>
        {mockDoctors.map((doctor) => (
          <List.Item
            key={doctor.id}
            prefix={<Image src="" width={60} height={60} fit="cover" style={{ borderRadius: 8, background: '#eee' }} />}
            description={
              <div className={styles.doctorInfo}>
                <div className={styles.doctorDept}>{doctor.department}</div>
                <div className={styles.doctorSpec}>擅长：{doctor.specialty}</div>
                <div className={styles.doctorFee}>¥{doctor.fee}</div>
              </div>
            }
            onClick={() => history.push(`/doctor/${doctor.id}`)}
            arrow
          >
            <div className={styles.doctorName}>
              {doctor.name}
              <Tag color="primary" fill="outline" className={styles.doctorTitle}>{doctor.title}</Tag>
            </div>
          </List.Item>
        ))}
      </List>
    </div>
  );
};

export default DoctorPage;

