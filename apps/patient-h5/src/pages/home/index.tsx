import { Swiper, Grid, Card, Image, Skeleton, Toast } from 'antd-mobile';
import { history } from 'umi';
import { useState, useEffect } from 'react';
import { departmentApi, doctorApi } from '@hospital/api';
import type { Department, Doctor } from '@hospital/shared';
import styles from './index.less';

const menus = [
  { icon: '🏥', title: '预约挂号', path: '/department' },
  { icon: '📋', title: '我的预约', path: '/appointment' },
  { icon: '📝', title: '就诊记录', path: '/records' },
  { icon: '👤', title: '个人中心', path: '/profile' },
];

const HomePage: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [hotDepts, setHotDepts] = useState<Department[]>([]);
  const [recommendDoctors, setRecommendDoctors] = useState<Doctor[]>([]);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [depts, doctors] = await Promise.all([
        departmentApi.getHot(8),
        doctorApi.getRecommended(6),
      ]);
      setHotDepts(depts);
      setRecommendDoctors(doctors);
    } catch (error) {
      console.error('加载首页数据失败', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={styles.container}>
      {/* 轮播图 */}
      <Swiper autoplay loop className={styles.banner}>
        {[1, 2, 3].map((i) => (
          <Swiper.Item key={i}>
            <div 
              className={styles.bannerItem} 
              style={{ background: `linear-gradient(135deg, #667eea ${i * 10}%, #764ba2 100%)` }}
            >
              <div className={styles.bannerText}>
                <h2>便捷挂号</h2>
                <p>随时随地，轻松预约</p>
              </div>
            </div>
          </Swiper.Item>
        ))}
      </Swiper>

      {/* 快捷入口 */}
      <Card className={styles.menuCard}>
        <Grid columns={4} gap={8}>
          {menus.map((menu) => (
            <Grid.Item key={menu.path} onClick={() => history.push(menu.path)}>
              <div className={styles.menuItem}>
                <span className={styles.menuIcon}>{menu.icon}</span>
                <span className={styles.menuTitle}>{menu.title}</span>
              </div>
            </Grid.Item>
          ))}
        </Grid>
      </Card>

      {/* 热门科室 */}
      <Card title="热门科室" className={styles.section}>
        {loading ? (
          <Skeleton.Paragraph lineCount={2} animated />
        ) : (
          <Grid columns={4} gap={8}>
            {hotDepts.map((dept) => (
              <Grid.Item key={dept.id} onClick={() => history.push(`/doctor?departmentId=${dept.id}&departmentName=${encodeURIComponent(dept.name)}`)}>
                <div className={styles.deptItem}>{dept.name}</div>
              </Grid.Item>
            ))}
            <Grid.Item onClick={() => history.push('/department')}>
              <div className={styles.deptItem}>更多 &gt;</div>
            </Grid.Item>
          </Grid>
        )}
      </Card>

      {/* 推荐医生 */}
      <Card title="推荐医生" className={styles.section}>
        {loading ? (
          <Skeleton.Paragraph lineCount={4} animated />
        ) : (
          <div className={styles.doctorList}>
            {recommendDoctors.map((doctor) => (
              <div 
                key={doctor.id} 
                className={styles.doctorCard} 
                onClick={() => history.push(`/doctor/${doctor.id}`)}
              >
                <Image 
                  src={doctor.avatar || ''} 
                  width={60} 
                  height={60} 
                  fit="cover" 
                  style={{ borderRadius: '50%', background: '#f5f5f5' }} 
                />
                <div className={styles.doctorInfo}>
                  <div className={styles.doctorName}>
                    {doctor.name}
                    {doctor.title && <span className={styles.doctorTitle}>{doctor.title}</span>}
                  </div>
                  <div className={styles.doctorDept}>{doctor.departmentName}</div>
                  <div className={styles.doctorSpec}>擅长：{doctor.specialty || '暂无'}</div>
                </div>
                <div className={styles.doctorFee}>¥{doctor.registrationFee}</div>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
};

export default HomePage;
