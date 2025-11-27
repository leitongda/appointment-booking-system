import { Swiper, Grid, Card, Image } from 'antd-mobile';
import { history } from 'umi';
import styles from './index.less';

const menus = [
  { icon: '🏥', title: '预约挂号', path: '/department' },
  { icon: '📋', title: '我的预约', path: '/appointment' },
  { icon: '📝', title: '就诊记录', path: '/records' },
  { icon: '👤', title: '个人中心', path: '/profile' },
];

const HomePage: React.FC = () => {
  return (
    <div className={styles.container}>
      {/* 轮播图 */}
      <Swiper autoplay loop className={styles.banner}>
        {[1, 2, 3].map((i) => (
          <Swiper.Item key={i}>
            <div className={styles.bannerItem} style={{ background: `linear-gradient(135deg, #667eea ${i * 10}%, #764ba2 100%)` }}>
              Banner {i}
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
        <Grid columns={4} gap={8}>
          {['内科', '外科', '儿科', '妇科', '骨科', '眼科', '口腔科', '更多'].map((name) => (
            <Grid.Item key={name} onClick={() => history.push('/department')}>
              <div className={styles.deptItem}>{name}</div>
            </Grid.Item>
          ))}
        </Grid>
      </Card>

      {/* 推荐医生 */}
      <Card title="推荐医生" className={styles.section}>
        <div className={styles.doctorList}>
          {[1, 2, 3].map((i) => (
            <div key={i} className={styles.doctorCard} onClick={() => history.push(`/doctor/${i}`)}>
              <Image src="" width={60} height={60} fit="cover" style={{ borderRadius: '50%', background: '#eee' }} />
              <div className={styles.doctorInfo}>
                <div className={styles.doctorName}>医生{i} <span className={styles.doctorTitle}>主任医师</span></div>
                <div className={styles.doctorDept}>内科</div>
                <div className={styles.doctorSpec}>擅长：心血管疾病...</div>
              </div>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
};

export default HomePage;

