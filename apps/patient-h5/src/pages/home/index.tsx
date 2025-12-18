import { Swiper, Grid, Card, Image, Skeleton, SearchBar } from 'antd-mobile';
import { history } from 'umi';
import { useState, useEffect } from 'react';
import { departmentApi, doctorApi, contentApi } from '@hospital/api';
import type { Department, Doctor } from '@hospital/shared';
import type { Banner } from '@hospital/api';
import styles from './index.less';

const menus = [
  { icon: '🏥', title: '预约挂号', path: '/department' },
  { icon: '📋', title: '我的预约', path: '/appointment' },
  { icon: '📝', title: '就诊记录', path: '/records' },
  { icon: '🔔', title: '消息中心', path: '/message' },
  { icon: '💬', title: '意见反馈', path: '/feedback' },
  { icon: '👤', title: '个人中心', path: '/profile' },
];

// 默认轮播图（API无数据时使用）
const defaultBanners = [
  { id: '1', title: '便捷挂号', imageUrl: '', color: '#667eea' },
  { id: '2', title: '专家坐诊', imageUrl: '', color: '#f093fb' },
  { id: '3', title: '在线问诊', imageUrl: '', color: '#4facfe' },
];

const HomePage: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [hotDepts, setHotDepts] = useState<Department[]>([]);
  const [recommendDoctors, setRecommendDoctors] = useState<Doctor[]>([]);
  const [banners, setBanners] = useState<Banner[]>([]);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [depts, doctors, bannerList] = await Promise.all([
        departmentApi.getHot(8),
        doctorApi.getRecommended(6),
        contentApi.getActiveBanners('home').catch(() => []),
      ]);
      setHotDepts(depts);
      setRecommendDoctors(doctors);
      setBanners(bannerList);
    } catch (error) {
      console.error('加载首页数据失败', error);
    } finally {
      setLoading(false);
    }
  };

  const handleBannerClick = (banner: Banner) => {
    if (banner.linkType === 1 && banner.linkUrl) {
      // 内部链接
      history.push(banner.linkUrl);
    } else if (banner.linkType === 2 && banner.linkUrl) {
      // 外部链接
      window.location.href = banner.linkUrl;
    }
  };

  const handleSearchFocus = () => {
    history.push('/search');
  };

  // 使用API返回的轮播图或默认轮播图
  const displayBanners = banners.length > 0 ? banners : null;

  return (
    <div className={styles.container}>
      {/* 搜索栏 */}
      <div className={styles.searchWrapper}>
        <SearchBar 
          placeholder="搜索科室/医生" 
          onFocus={handleSearchFocus}
          className={styles.searchBar}
        />
      </div>

      {/* 轮播图 */}
      <Swiper autoplay loop className={styles.banner}>
        {displayBanners ? (
          displayBanners.map((banner) => (
            <Swiper.Item key={banner.id} onClick={() => handleBannerClick(banner)}>
              <div className={styles.bannerItem}>
                {banner.imageUrl ? (
                  <Image src={banner.imageUrl} fit="cover" className={styles.bannerImage} />
                ) : (
                  <div 
                    className={styles.bannerPlaceholder}
                    style={{ background: `linear-gradient(135deg, #667eea 0%, #764ba2 100%)` }}
                  >
                    <div className={styles.bannerText}>
                      <h2>{banner.title || '医院挂号系统'}</h2>
                      <p>便捷预约，健康生活</p>
                    </div>
                  </div>
                )}
              </div>
            </Swiper.Item>
          ))
        ) : (
          defaultBanners.map((item) => (
            <Swiper.Item key={item.id}>
              <div 
                className={styles.bannerItem} 
                style={{ background: `linear-gradient(135deg, ${item.color} 0%, #764ba2 100%)` }}
              >
                <div className={styles.bannerText}>
                  <h2>{item.title}</h2>
                  <p>便捷预约，健康生活</p>
                </div>
              </div>
            </Swiper.Item>
          ))
        )}
      </Swiper>

      {/* 快捷入口 */}
      <Card className={styles.menuCard}>
        <Grid columns={3} gap={8}>
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
