import { View, Text, Swiper, SwiperItem, Image } from '@tarojs/components';
import Taro from '@tarojs/taro';
import { useState, useEffect } from 'react';
import { contentApi, departmentApi, doctorApi } from '@hospital/api';
import type { Banner } from '@hospital/api';
import type { Department, Doctor } from '@hospital/shared';
import {
  HospitalIcon,
  CalendarIcon,
  RecordIcon,
  UserIcon,
  DoctorIcon,
  FlashIcon,
  SearchIcon,
  getDeptIcon,
  MoreIcon,
} from '../../components/Icons';
import { PageContainer } from '../../components/PageContainer';
import './index.less';

// 功能菜单配置
const menus = [
  { icon: HospitalIcon, title: '预约挂号', path: '/pages/department/index' },
  { icon: CalendarIcon, title: '我的预约', path: '/pages/appointment/index' },
  { icon: RecordIcon, title: '就诊记录', path: '/packageProfile/pages/records/index' },
  { icon: UserIcon, title: '个人中心', path: '/pages/profile/index' },
];

// 默认轮播图（API无数据时的备用）
const defaultBanners = [
  { id: '1', title: '智慧医疗', imageUrl: '', linkType: 0 },
  { id: '2', title: '专家团队', imageUrl: '', linkType: 0 },
  { id: '3', title: '优质服务', imageUrl: '', linkType: 0 },
];

const IndexPage = () => {
  const [banners, setBanners] = useState<Banner[]>([]);
  const [hotDepts, setHotDepts] = useState<Department[]>([]);
  const [doctors, setDoctors] = useState<Doctor[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      console.log('[首页] 开始加载数据...');
      
      const [bannersData, deptsData, doctorsData] = await Promise.all([
        contentApi.getActiveBanners('home').catch((err) => {
          console.error('[首页] 加载轮播图失败:', err);
          return [];
        }),
        departmentApi.getHot(8).catch((err) => {
          console.error('[首页] 加载热门科室失败:', err);
          return [];
        }),
        doctorApi.getRecommended(3).catch((err) => {
          console.error('[首页] 加载推荐医生失败:', err);
          return [];
        }),
      ]);
      
      console.log('[首页] 数据加载结果:', {
        banners: bannersData.length,
        depts: deptsData.length,
        doctors: doctorsData.length,
      });
      
      setBanners(bannersData.length > 0 ? bannersData : defaultBanners as any);
      setHotDepts(deptsData);
      setDoctors(doctorsData);
    } catch (error) {
      console.error('加载首页数据失败', error);
    } finally {
      setLoading(false);
    }
  };

  const navigateTo = (path: string) => {
    if (path === '/pages/profile/index' || path === '/pages/appointment/index') {
      Taro.switchTab({ url: path });
    } else {
      Taro.navigateTo({ url: path });
    }
  };

  const handleBannerClick = (banner: Banner) => {
    if (banner.linkType === 1 && banner.linkUrl) {
      // 内部链接
      navigateTo(banner.linkUrl);
    } else if (banner.linkType === 2 && banner.linkUrl) {
      // 外部链接 - 小程序使用 webview
      Taro.navigateTo({ url: `/packageOther/pages/webview/index?url=${encodeURIComponent(banner.linkUrl)}` });
    }
  };

  const handleDeptClick = (dept?: Department) => {
    if (dept) {
      Taro.navigateTo({
        url: `/pages/doctor/index?departmentId=${dept.id}&departmentName=${encodeURIComponent(dept.name)}`,
      });
    } else {
      navigateTo('/pages/department/index');
    }
  };

  return (
    <PageContainer className="container">
      {/* Banner 轮播 */}
      <Swiper className="banner" autoplay circular indicatorDots indicatorActiveColor="#fff">
        {banners.map((banner) => (
          <SwiperItem key={banner.id} onClick={() => handleBannerClick(banner)}>
            <View className="banner-item">
              {banner.imageUrl ? (
                <Image className="banner-image" src={banner.imageUrl} mode="aspectFill" />
              ) : (
                <View className="banner-content">
                  <Text className="banner-title">{banner.title || '欢迎使用'}</Text>
                </View>
              )}
            </View>
          </SwiperItem>
        ))}
      </Swiper>

      {/* 功能菜单 */}
      <View className="menu-card">
        <View className="dept-grid">
          {menus.map((menu) => {
            const IconComponent = menu.icon;
            return (
              <View key={menu.path} className="menu-item" onClick={() => navigateTo(menu.path)}>
                <View className="menu-icon-wrap">
                  <IconComponent size={28} color="#4F46E5" />
                </View>
                <Text className="menu-title">{menu.title}</Text>
              </View>
            );
          })}
        </View>
      </View>

      {/* 快捷入口 */}
      <View className="quick-entry">
        <View className="quick-card" onClick={() => navigateTo('/pages/department/index')}>
          <View className="quick-icon">
            <FlashIcon size={24} color="#F59E0B" />
          </View>
          <Text className="quick-title">快速挂号</Text>
          <Text className="quick-desc">一键预约，省时省力</Text>
        </View>
        <View className="quick-card" onClick={() => navigateTo('/packageOther/pages/search/index')}>
          <View className="quick-icon">
            <SearchIcon size={24} color="#10B981" />
          </View>
          <Text className="quick-title">找医生</Text>
          <Text className="quick-desc">搜索专家，精准就医</Text>
        </View>
      </View>

      {/* 热门科室 */}
      <View className="section">
        <View className="section-header">
          <Text className="section-title">热门科室</Text>
          <Text className="section-more" onClick={() => navigateTo('/pages/department/index')}>
            全部
          </Text>
        </View>
        <View className="dept-grid">
          {hotDepts.length > 0 ? (
            <>
              {hotDepts.slice(0, 7).map((dept) => {
                const IconComponent = getDeptIcon(dept.name);
                return (
                  <View
                    key={dept.id}
                    className="dept-item"
                    onClick={() => handleDeptClick(dept)}
                  >
                    <View className="dept-icon-wrap">
                      <IconComponent size={24} color="#4F46E5" />
                    </View>
                    <Text className="dept-name">{dept.name}</Text>
                  </View>
                );
              })}
              <View className="dept-item" onClick={() => navigateTo('/pages/department/index')}>
                <View className="dept-icon-wrap">
                  <MoreIcon size={24} color="#4F46E5" />
                </View>
                <Text className="dept-name">更多</Text>
              </View>
            </>
          ) : (
            // 默认显示固定科室名称
            ['内科', '外科', '儿科', '妇科', '骨科', '眼科', '口腔', '更多'].map((name) => {
              const IconComponent = name === '更多' ? MoreIcon : getDeptIcon(name);
              return (
                <View
                  key={name}
                  className="dept-item"
                  onClick={() => navigateTo('/pages/department/index')}
                >
                  <View className="dept-icon-wrap">
                    <IconComponent size={24} color="#4F46E5" />
                  </View>
                  <Text className="dept-name">{name}</Text>
                </View>
              );
            })
          )}
        </View>
      </View>

      {/* 推荐医生 */}
      <View className="section">
        <View className="section-header">
          <Text className="section-title">推荐医生</Text>
          <Text className="section-more" onClick={() => navigateTo('/pages/doctor/index')}>
            更多
          </Text>
        </View>
        <View className="doctor-list">
          {doctors.length > 0 ? (
            doctors.map((doctor) => (
              <View
                key={doctor.id}
                className="doctor-card"
                onClick={() => navigateTo(`/packageBooking/pages/doctor/detail?id=${doctor.id}`)}
              >
                <View className="doctor-avatar">
                  {doctor.avatar ? (
                    <Image className="avatar-image" src={doctor.avatar} mode="aspectFill" />
                  ) : (
                    <DoctorIcon size={32} color="#4F46E5" />
                  )}
                </View>
                <View className="doctor-info">
                  <View className="doctor-header">
                    <Text className="doctor-name">{doctor.name}</Text>
                    {doctor.title && <Text className="doctor-title">{doctor.title}</Text>}
                  </View>
                  <Text className="doctor-dept">{doctor.departmentName}</Text>
                  <Text className="doctor-spec">擅长：{doctor.specialty || '暂无'}</Text>
                </View>
              </View>
            ))
          ) : !loading ? (
            <View className="empty-doctors">
              <Text>暂无推荐医生</Text>
            </View>
          ) : null}
        </View>
      </View>
    </PageContainer>
  );
};

export default IndexPage;
