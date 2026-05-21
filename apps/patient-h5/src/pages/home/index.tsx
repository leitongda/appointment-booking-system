import { Swiper, Grid, Image, Skeleton, SearchBar } from 'antd-mobile';
import { history } from 'umi';
import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { departmentApi, doctorApi, contentApi } from '@hospital/api';
import type { Department, Doctor } from '@hospital/shared';
import type { Banner } from '@hospital/api';
import { Card, SectionLabel } from '@/components/ui';
import { fadeInUp, stagger, viewportOptions } from '@/components/ui/animations';

// Menu items with SVG icons
const menus = [
  { 
    icon: (
      <svg className="w-7 h-7" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
      </svg>
    ), 
    title: '预约挂号', 
    path: '/department' 
  },
  { 
    icon: (
      <svg className="w-7 h-7" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01" />
      </svg>
    ), 
    title: '我的预约', 
    path: '/appointment' 
  },
  { 
    icon: (
      <svg className="w-7 h-7" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
      </svg>
    ), 
    title: '就诊记录', 
    path: '/records' 
  },
  { 
    icon: (
      <svg className="w-7 h-7" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
      </svg>
    ), 
    title: '消息中心', 
    path: '/message' 
  },
  { 
    icon: (
      <svg className="w-7 h-7" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
      </svg>
    ), 
    title: '意见反馈', 
    path: '/feedback' 
  },
  { 
    icon: (
      <svg className="w-7 h-7" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
      </svg>
    ), 
    title: '个人中心', 
    path: '/profile' 
  },
];

// Default banners when API returns empty
const defaultBanners = [
  { id: '1', title: '便捷挂号', imageUrl: '', color: '#0052FF' },
  { id: '2', title: '专家坐诊', imageUrl: '', color: '#4D7CFF' },
  { id: '3', title: '在线问诊', imageUrl: '', color: '#0052FF' },
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
      history.push(banner.linkUrl);
    } else if (banner.linkType === 2 && banner.linkUrl) {
      window.location.href = banner.linkUrl;
    }
  };

  const handleSearchFocus = () => {
    history.push('/search');
  };

  const displayBanners = banners.length > 0 ? banners : null;

  return (
    <div className="min-h-screen bg-background pb-4" role="main">
      {/* Search bar with gradient header */}
      <div className="bg-gradient-to-r from-accent to-accent-secondary px-4 pt-12 pb-6">
        <SearchBar
          placeholder="搜索科室/医生"
          onFocus={handleSearchFocus}
          className="!rounded-full"
          aria-label="搜索科室或医生"
          style={{
            '--background': 'rgba(255, 255, 255, 0.95)',
            '--border-radius': '9999px',
            '--height': '44px',
          } as React.CSSProperties}
        />
      </div>

      {/* Banner Swiper */}
      <Swiper 
        autoplay 
        loop 
        className="!h-40"
        indicatorProps={{
          style: {
            '--dot-color': 'rgba(0, 82, 255, 0.3)',
            '--active-dot-color': '#0052FF',
          } as React.CSSProperties,
        }}
      >
        {displayBanners ? (
          displayBanners.map((banner) => (
            <Swiper.Item key={banner.id} onClick={() => handleBannerClick(banner)}>
              <div className="h-40 flex items-center justify-center cursor-pointer">
                {banner.imageUrl ? (
                  <Image src={banner.imageUrl} fit="cover" className="w-full h-full" />
                ) : (
                  <div 
                    className="w-full h-full flex items-center justify-center"
                    style={{ 
                      background: `linear-gradient(135deg, #0052FF 0%, #4D7CFF 100%)` 
                    }}
                  >
                    <div className="text-center text-white">
                      <h2 className="font-display text-2xl mb-2">{banner.title || '医院挂号系统'}</h2>
                      <p className="text-sm opacity-80">便捷预约，健康生活</p>
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
                className="h-40 flex items-center justify-center"
                style={{ 
                  background: `linear-gradient(135deg, ${item.color} 0%, #4D7CFF 100%)` 
                }}
              >
                <div className="text-center text-white">
                  <h2 className="font-display text-2xl mb-2">{item.title}</h2>
                  <p className="text-sm opacity-80">便捷预约，健康生活</p>
                </div>
              </div>
            </Swiper.Item>
          ))
        )}
      </Swiper>

      {/* Quick Menu Grid */}
      <motion.div
        variants={stagger}
        initial="hidden"
        animate="visible"
      >
        <Card variant="default" padding="md" className="mx-3 -mt-4 relative z-10">
          <Grid columns={3} gap={8}>
            {menus.map((menu, index) => (
              <Grid.Item key={menu.path}>
                <motion.div
                  variants={fadeInUp}
                  className="flex flex-col items-center py-3 cursor-pointer active:opacity-70 transition-opacity"
                  onClick={() => history.push(menu.path)}
                  role="link"
                  tabIndex={0}
                  aria-label={`进入${menu.title}`}
                  onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); history.push(menu.path); } }}
                >
                  <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-accent to-accent-secondary flex items-center justify-center text-white shadow-accent mb-2">
                    {menu.icon}
                  </div>
                  <span className="text-sm text-foreground font-medium">{menu.title}</span>
                </motion.div>
              </Grid.Item>
            ))}
          </Grid>
        </Card>
      </motion.div>

      {/* Hot Departments */}
      <motion.div
        className="mx-3 mt-4"
        variants={fadeInUp}
        initial="hidden"
        whileInView="visible"
        viewport={viewportOptions}
      >
        <Card variant="default" padding="md">
          <div className="flex items-center justify-between mb-4">
            <SectionLabel animated={false}>热门科室</SectionLabel>
            <button 
              onClick={() => history.push('/department')}
              className="text-sm text-accent hover:text-accent-secondary transition-colors"
            >
              查看全部
              <span aria-hidden="true"> →</span>
            </button>
          </div>

          {loading ? (
            <Skeleton.Paragraph lineCount={2} animated />
          ) : (
            <Grid columns={4} gap={8} aria-label="热门科室列表">
              {hotDepts.map((dept) => (
                <Grid.Item
                  key={dept.id}
                  onClick={() => history.push(`/doctor?departmentId=${dept.id}&departmentName=${encodeURIComponent(dept.name)}`)}
                >
                  <div
                    className="text-center py-3 rounded-xl bg-muted hover:bg-accent/5 transition-colors cursor-pointer active:bg-accent/10"
                    role="link"
                    tabIndex={0}
                    aria-label={`进入${dept.name}科室`}
                    onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); history.push(`/doctor?departmentId=${dept.id}&departmentName=${encodeURIComponent(dept.name)}`); } }}
                  >
                    <span className="text-sm text-foreground">{dept.name}</span>
                  </div>
                </Grid.Item>
              ))}
            </Grid>
          )}
        </Card>
      </motion.div>

      {/* Recommended Doctors */}
      <motion.div
        className="mx-3 mt-4"
        variants={fadeInUp}
        initial="hidden"
        whileInView="visible"
        viewport={viewportOptions}
      >
        <Card variant="default" padding="md">
          <div className="flex items-center justify-between mb-4">
            <SectionLabel animated={false}>推荐医生</SectionLabel>
            <button 
              onClick={() => history.push('/doctor')}
              className="text-sm text-accent hover:text-accent-secondary transition-colors"
            >
              查看全部
              <span aria-hidden="true"> →</span>
            </button>
          </div>

          {loading ? (
            <Skeleton.Paragraph lineCount={4} animated />
          ) : (
            <div className="flex flex-col gap-3" role="list" aria-label="推荐医生列表">
              {recommendDoctors.map((doctor) => (
                <motion.div
                  key={doctor.id}
                  className="flex items-center gap-3 p-3 rounded-xl bg-muted hover:bg-accent/5 transition-all cursor-pointer active:scale-[0.99]"
                  onClick={() => history.push(`/doctor/${doctor.id}`)}
                  whileHover={{ y: -2 }}
                  whileTap={{ scale: 0.98 }}
                  role="link"
                  tabIndex={0}
                  aria-label={`查看${doctor.name}${doctor.title ? ` ${doctor.title}` : ''} ${doctor.departmentName}的详情`}
                  onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); history.push(`/doctor/${doctor.id}`); } }}
                >
                  <Image 
                    src={doctor.avatar || ''} 
                    width={56} 
                    height={56} 
                    fit="cover" 
                    className="rounded-full bg-border flex-shrink-0"
                  />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-foreground">{doctor.name}</span>
                      {doctor.title && (
                        <span className="text-xs text-accent bg-accent/10 px-2 py-0.5 rounded-full">
                          {doctor.title}
                        </span>
                      )}
                    </div>
                    <p className="text-sm text-muted-foreground mt-1">{doctor.departmentName}</p>
                    <p className="text-xs text-muted-foreground/70 mt-1 truncate">
                      擅长：{doctor.specialty || '暂无'}
                    </p>
                  </div>
                </motion.div>
              ))}
            </div>
          )}
        </Card>
      </motion.div>
    </div>
  );
};

export default HomePage;
