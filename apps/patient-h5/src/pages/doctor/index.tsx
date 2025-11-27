import { NavBar, List, Image, Tag, Skeleton, Empty } from 'antd-mobile';
import { history, useSearchParams } from 'umi';
import { useState, useEffect } from 'react';
import { doctorApi } from '@hospital/api';
import type { Doctor } from '@hospital/shared';
import styles from './index.less';

const DoctorPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const departmentId = searchParams.get('departmentId');
  const departmentName = searchParams.get('departmentName');
  
  const [loading, setLoading] = useState(true);
  const [doctors, setDoctors] = useState<Doctor[]>([]);

  useEffect(() => {
    if (departmentId) {
      loadDoctors();
    }
  }, [departmentId]);

  const loadDoctors = async () => {
    try {
      const data = await doctorApi.getByDepartment(departmentId!);
      setDoctors(data);
    } catch (error) {
      console.error('加载医生列表失败', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className={styles.container}>
        <NavBar onBack={() => history.back()}>{departmentName || '选择医生'}</NavBar>
        <Skeleton.Paragraph lineCount={8} animated />
      </div>
    );
  }

  return (
    <div className={styles.container}>
      <NavBar onBack={() => history.back()}>{departmentName || '选择医生'}</NavBar>
      {doctors.length === 0 ? (
        <Empty description="暂无医生" />
      ) : (
        <List className={styles.list}>
          {doctors.map((doctor) => (
            <List.Item
              key={doctor.id}
              prefix={
                <Image 
                  src={doctor.avatar || ''} 
                  width={60} 
                  height={60} 
                  fit="cover" 
                  style={{ borderRadius: 8, background: '#f5f5f5' }} 
                />
              }
              description={
                <div className={styles.doctorInfo}>
                  <div className={styles.doctorDept}>{doctor.departmentName}</div>
                  <div className={styles.doctorSpec}>擅长：{doctor.specialty || '暂无'}</div>
                  <div className={styles.doctorFee}>挂号费：¥{doctor.registrationFee}</div>
                </div>
              }
              onClick={() => history.push(`/doctor/${doctor.id}`)}
              arrow
            >
              <div className={styles.doctorName}>
                {doctor.name}
                {doctor.title && (
                  <Tag color="primary" fill="outline" className={styles.doctorTitle}>
                    {doctor.title}
                  </Tag>
                )}
              </div>
            </List.Item>
          ))}
        </List>
      )}
    </div>
  );
};

export default DoctorPage;
