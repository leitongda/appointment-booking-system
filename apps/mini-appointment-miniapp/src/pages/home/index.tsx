import { View, Swiper, SwiperItem, Image, Text } from '@tarojs/components';
import { useState, useEffect } from 'react';
import Taro from '@tarojs/taro';
import { getActiveBanners, getPublishedNotices, getHospitalInfo } from '@/services/user';
import { getRecommendedDoctors, getHotDepartments } from '@/services/schedule';
import type { Banner, Notice, HospitalInfo, Doctor, Department } from '@/types/api';
import './index.scss';

export default function Home() {
  const [banners, setBanners] = useState<Banner[]>([]);
  const [notices, setNotices] = useState<Notice[]>([]);
  const [hospitalInfo, setHospitalInfo] = useState<HospitalInfo | null>(null);
  const [recommendedDoctors, setRecommendedDoctors] = useState<Doctor[]>([]);
  const [hotDepartments, setHotDepartments] = useState<Department[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadPageData();
  }, []);

  const loadPageData = async () => {
    try {
      setLoading(true);
      
      // 并发加载数据
      const [bannersData, noticesData, hospitalData, doctorsData, departmentsData] = await Promise.all([
        getActiveBanners('home'),
        getPublishedNotices(5),
        getHospitalInfo(),
        getRecommendedDoctors(6),
        getHotDepartments(8)
      ]);

      setBanners(bannersData);
      setNotices(noticesData);
      setHospitalInfo(hospitalData);
      setRecommendedDoctors(doctorsData);
      setHotDepartments(departmentsData);
    } catch (error) {
      console.error('Load page data failed:', error);
    } finally {
      setLoading(false);
    }
  };

  // 点击轮播图
  const handleBannerClick = (banner: Banner) => {
    if (banner.linkUrl) {
      // 根据 linkType 处理跳转
      if (banner.linkType === 1) {
        // 小程序内部页面
        Taro.navigateTo({ url: banner.linkUrl });
      } else if (banner.linkType === 2) {
        // 外部链接
        Taro.navigateTo({
          url: `/pages/webview/index?url=${encodeURIComponent(banner.linkUrl)}`
        });
      }
    }
  };

  // 点击公告
  const handleNoticeClick = (notice: Notice) => {
    Taro.showModal({
      title: notice.title,
      content: notice.content,
      showCancel: false
    });
  };

  // 点击科室
  const handleDepartmentClick = (department: Department) => {
    Taro.navigateTo({
      url: `/pages/appointment/doctor/index?departmentId=${department.id}`
    });
  };

  // 点击医生
  const handleDoctorClick = (doctor: Doctor) => {
    Taro.navigateTo({
      url: `/pages/appointment/schedule/index?doctorId=${doctor.id}`
    });
  };

  // 快捷功能
  const quickActions = [
    { icon: '📅', title: '预约挂号', url: '/pages/appointment/department/index' },
    { icon: '📋', title: '预约记录', url: '/pages/profile/appointments/index' },
    { icon: '👤', title: '就诊人', url: '/pages/profile/patients/index' },
    { icon: '⭐', title: '我的收藏', url: '/pages/profile/favorites/index' }
  ];

  const handleQuickAction = (url: string) => {
    Taro.navigateTo({ url });
  };

  if (loading) {
    return (
      <View className='home-loading'>
        <Text>加载中...</Text>
      </View>
    );
  }

  return (
    <View className='home-page'>
      {/* 轮播图 */}
      {banners.length > 0 && (
        <View className='banner-section'>
          <Swiper
            className='banner-swiper'
            indicatorDots
            autoplay
            interval={5000}
            duration={500}
            circular
          >
            {banners.map((banner) => (
              <SwiperItem key={banner.id}>
                <Image
                  className='banner-image'
                  src={banner.imageUrl}
                  mode='aspectFill'
                  onClick={() => handleBannerClick(banner)}
                />
              </SwiperItem>
            ))}
          </Swiper>
        </View>
      )}

      {/* 公告栏 */}
      {notices.length > 0 && (
        <View className='notice-section'>
          <View className='notice-icon'>📢</View>
          <Swiper
            className='notice-swiper'
            vertical
            autoplay
            interval={3000}
            duration={500}
            circular
          >
            {notices.map((notice) => (
              <SwiperItem key={notice.id}>
                <Text
                  className='notice-text'
                  onClick={() => handleNoticeClick(notice)}
                >
                  {notice.title}
                </Text>
              </SwiperItem>
            ))}
          </Swiper>
        </View>
      )}

      {/* 快捷功能 */}
      <View className='quick-actions'>
        {quickActions.map((action, index) => (
          <View
            key={index}
            className='action-item'
            onClick={() => handleQuickAction(action.url)}
          >
            <View className='action-icon'>{action.icon}</View>
            <Text className='action-title'>{action.title}</Text>
          </View>
        ))}
      </View>

      {/* 热门科室 */}
      {hotDepartments.length > 0 && (
        <View className='section'>
          <View className='section-header'>
            <Text className='section-title'>热门科室</Text>
          </View>
          <View className='department-grid'>
            {hotDepartments.map((dept) => (
              <View
                key={dept.id}
                className='department-item'
                onClick={() => handleDepartmentClick(dept)}
              >
                <View className='department-icon'>{dept.icon || '🏥'}</View>
                <Text className='department-name'>{dept.name}</Text>
              </View>
            ))}
          </View>
        </View>
      )}

      {/* 推荐医生 */}
      {recommendedDoctors.length > 0 && (
        <View className='section'>
          <View className='section-header'>
            <Text className='section-title'>推荐医生</Text>
          </View>
          <View className='doctor-list'>
            {recommendedDoctors.map((doctor) => (
              <View
                key={doctor.id}
                className='doctor-item'
                onClick={() => handleDoctorClick(doctor)}
              >
                <Image
                  className='doctor-avatar'
                  src={doctor.avatar || '/assets/images/default-avatar.png'}
                  mode='aspectFill'
                />
                <View className='doctor-info'>
                  <Text className='doctor-name'>{doctor.name}</Text>
                  <Text className='doctor-title'>{doctor.title}</Text>
                  <Text className='doctor-department'>{doctor.departmentName}</Text>
                </View>
              </View>
            ))}
          </View>
        </View>
      )}

      {/* 医院信息 */}
      {hospitalInfo && (
        <View className='hospital-info'>
          <Text className='hospital-name'>{hospitalInfo.hospitalName}</Text>
          <Text className='hospital-address'>{hospitalInfo.address}</Text>
          <Text className='hospital-phone'>电话：{hospitalInfo.phone}</Text>
        </View>
      )}
    </View>
  );
}
