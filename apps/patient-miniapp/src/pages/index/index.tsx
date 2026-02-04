import { View, Text, Swiper, SwiperItem, Image } from '@tarojs/components';
import Taro, { usePullDownRefresh, useDidShow } from '@tarojs/taro';
import { useState, useEffect } from 'react';
import { contentApi, doctorApi, userApi } from '@hospital/api';
import type { Banner } from '@hospital/api';
import type { Doctor, Patient } from '@hospital/shared';
import {
  HospitalIcon,
  CalendarIcon,
  ChatIcon,
  DoctorIcon,
  ScanIcon,
  CardIcon,
  AddUserIcon,
} from '../../components/Icons';
import { PageContainer } from '../../components/PageContainer';
import { getToken } from '../../utils/auth';
import { getThemePrimaryColor } from '../../utils/theme';
import LoginPopup from '../../components/LoginPopup';
import { getImageUrl } from '../../utils/url';
import { triggerCheckinScan } from '../../utils/checkin';
import './index.less';

// 功能菜单配置
const menus = [
  { icon: HospitalIcon, title: '预约挂号', path: '/pages/department/index' },
  { icon: CalendarIcon, title: '预约记录', path: '/pages/appointment/index' },
  { icon: ScanIcon, title: '扫码签到', path: '', action: 'checkin' },
  { icon: ChatIcon, title: '我的客服', path: '/packageProfile/pages/feedback/index' },
];

// 默认轮播图（API无数据时的备用）
const defaultBanners = [
  { id: '1', title: '智慧医疗', imageUrl: '', linkType: 0 },
  // { id: '2', title: '专家团队', imageUrl: '', linkType: 0 },
  // { id: '3', title: '优质服务', imageUrl: '', linkType: 0 },
];

// 需要登录的菜单路径
const requireLoginPaths = [
  '/pages/appointment/index',
  '/packageProfile/pages/feedback/index',
];

// 需要登录的 action
const requireLoginActions = ['checkin'];

const IndexPage = () => {
  const [banners, setBanners] = useState<Banner[]>([]);
  const [doctors, setDoctors] = useState<Doctor[]>([]);
  const [defaultPatient, setDefaultPatient] = useState<Patient | null>(null);
  const [loading, setLoading] = useState(true);
  const [showLoginPopup, setShowLoginPopup] = useState(false);
  const [pendingPatientCardNav, setPendingPatientCardNav] = useState(false);
  const [pendingCheckinAction, setPendingCheckinAction] = useState(false);

  useEffect(() => {
    loadData();
  }, []);

  // 页面显示时刷新就诊卡（可能用户新增了就诊卡）
  useDidShow(() => {
    loadPatients();
    // 更新 TabBar 选中状态
    Taro.eventCenter.trigger('tabbar:change', 0);
  });

  // 下拉刷新
  usePullDownRefresh(() => {
    loadData().finally(() => {
      Taro.stopPullDownRefresh();
    });
  });

  const loadData = async () => {
    try {
      console.log('[首页] 开始加载数据...');
      
      const [bannersData, doctorsData] = await Promise.all([
        contentApi.getActiveBanners('home').catch((err) => {
          console.error('[首页] 加载轮播图失败:', err);
          return [];
        }),
        doctorApi.getRecommended(6).catch((err) => {
          console.error('[首页] 加载推荐医生失败:', err);
          return [];
        }),
      ]);
      
      console.log('[首页] 数据加载结果:', {
        banners: bannersData.length,
        doctors: doctorsData.length,
      });
      
      setBanners(bannersData.length > 0 ? bannersData : defaultBanners as any);
      setDoctors(doctorsData);

      // 加载就诊卡（需要登录）
      await loadPatients();
    } catch (error) {
      console.error('加载首页数据失败', error);
    } finally {
      setLoading(false);
    }
  };

  const loadPatients = async () => {
    const token = getToken();
    if (!token) {
      setDefaultPatient(null);
      return;
    }
    try {
      const patients = await userApi.getPatients();
      // 找到默认就诊卡，如果没有默认则取第一个
      const defaultOne = patients.find((p) => p.isDefault) || patients[0] || null;
      setDefaultPatient(defaultOne);
    } catch (error) {
      console.error('[首页] 加载就诊卡失败:', error);
      setDefaultPatient(null);
    }
  };

  // 跳转到就诊卡页面（根据是否有就诊卡决定跳转到列表还是新增）
  const navigateToPatientPage = async () => {
    try {
      const patients = await userApi.getPatients();
      if (patients.length > 0) {
        // 有就诊卡，跳转到列表管理页面
        Taro.navigateTo({ url: '/packageProfile/pages/patient/index' });
      } else {
        // 无就诊卡，跳转到新增页面
        Taro.navigateTo({ url: '/packageProfile/pages/patient/edit' });
      }
    } catch (error) {
      console.error('[首页] 获取就诊卡失败:', error);
      // 出错时默认跳转到新增页面
      Taro.navigateTo({ url: '/packageProfile/pages/patient/edit' });
    }
  };

  // 登录成功回调
  const handleLoginSuccess = async () => {
    setShowLoginPopup(false);
    await loadPatients();
    
    // 如果是从就诊卡入口触发的登录，自动跳转
    if (pendingPatientCardNav) {
      setPendingPatientCardNav(false);
      navigateToPatientPage();
    }
    
    // 如果是从扫码签到入口触发的登录，自动触发扫码
    if (pendingCheckinAction) {
      setPendingCheckinAction(false);
      triggerCheckinScan();
    }
  };

  const navigateTo = (path: string, checkLogin = false) => {
    // 检查是否需要登录
    if (checkLogin || requireLoginPaths.includes(path)) {
      const token = getToken();
      if (!token) {
        setShowLoginPopup(true);
        return;
      }
    }
    
    if (path === '/pages/profile/index' || path === '/pages/appointment/index') {
      Taro.switchTab({ url: path });
    } else {
      Taro.navigateTo({ url: path });
    }
  };

  // 处理菜单点击（支持 path 跳转和 action 操作）
  const handleMenuClick = (menu: typeof menus[0]) => {
    // 如果有 action，执行对应操作
    if (menu.action) {
      // 检查是否需要登录
      if (requireLoginActions.includes(menu.action)) {
        const token = getToken();
        if (!token) {
          if (menu.action === 'checkin') {
            setPendingCheckinAction(true);
          }
          setShowLoginPopup(true);
          return;
        }
      }
      
      // 执行 action
      if (menu.action === 'checkin') {
        triggerCheckinScan();
      }
      return;
    }
    
    // 否则按路径跳转
    if (menu.path) {
      navigateTo(menu.path);
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

  const handlePatientCardClick = () => {
    // 未登录时弹出登录弹窗
    const token = getToken();
    if (!token) {
      setPendingPatientCardNav(true);  // 标记需要跳转
      setShowLoginPopup(true);
      return;
    }

    // 执行跳转逻辑
    navigateToPatientPage();
  };

  // 处理推荐医生卡片点击
  const handleDoctorClick = (doctorId: string) => {
    // 医生详情页无需登录即可浏览，登录检查在预约确认页进行
    Taro.navigateTo({
      url: `/packageBooking/pages/doctor/detail?id=${doctorId}`,
    });
  };

  return (
    <PageContainer className="container">
      {/* Banner 轮播 */}
      <Swiper className="banner" autoplay circular indicatorDots indicatorActiveColor="#fff">
        {banners.map((banner) => (
          <SwiperItem key={banner.id} onClick={() => handleBannerClick(banner)}>
            <View className="banner-item">
              {banner.imageUrl ? (
                <Image className="banner-image" src={getImageUrl(banner.imageUrl)} mode="aspectFill" />
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
              <View key={menu.action || menu.path} className="menu-item" onClick={() => handleMenuClick(menu)}>
                <View className="menu-icon-wrap">
                  <IconComponent size={28} color={getThemePrimaryColor()} />
                </View>
                <Text className="menu-title">{menu.title}</Text>
              </View>
            );
          })}
        </View>
      </View>

      {/* 就诊卡快捷入口 */}
      <View className="patient-card-entry" onClick={handlePatientCardClick}>
        {defaultPatient ? (
          <>
            <View className="card-icon">
              <CardIcon size={32} color={getThemePrimaryColor()} />
            </View>
            <View className="card-info">
              <Text className="card-name">{defaultPatient.name}</Text>
              <Text className="card-relation">
                {defaultPatient.relationship || '本人'} · 默认就诊人
              </Text>
            </View>
            <Text className="card-arrow">›</Text>
          </>
        ) : (
          <>
            <View className="card-icon add-icon">
              <AddUserIcon size={32} color="#10B981" />
            </View>
            <View className="card-info">
              <Text className="card-name">添加就诊卡</Text>
              <Text className="card-relation">添加就诊人信息，快速预约挂号</Text>
            </View>
            <Text className="card-arrow">›</Text>
          </>
        )}
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
                onClick={() => handleDoctorClick(doctor.id)}
              >
                <View className="doctor-avatar">
                  {doctor.avatar ? (
                    <Image className="avatar-image" src={getImageUrl(doctor.avatar)} mode="aspectFill" />
                  ) : (
                    <DoctorIcon size={32} color={getThemePrimaryColor()} />
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
                <View className={`slot-tag ${doctor.hasAvailableSlots ? 'available' : 'unavailable'}`}>
                  <Text>{doctor.hasAvailableSlots ? '有号' : '无号'}</Text>
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

      {/* 登录弹窗 */}
      <LoginPopup
        visible={showLoginPopup}
        onClose={() => setShowLoginPopup(false)}
        onSuccess={handleLoginSuccess}
      />
    </PageContainer>
  );
};

export default IndexPage;
