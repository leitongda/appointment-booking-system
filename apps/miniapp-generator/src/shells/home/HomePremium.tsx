import { View, Text, Swiper, SwiperItem, Image, ScrollView, RichText } from '@tarojs/components';
import Taro, { usePullDownRefresh, useDidShow } from '@tarojs/taro';
import { useState, useEffect, useCallback } from 'react';
import { contentApi, doctorApi, userApi, commonServiceApi } from '@hospital/api';
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
import { useTemplate } from '../../contexts/TemplateContext';
import { AUTH_EVENTS, getToken, subscribeAuthChange } from '../../utils/auth';
import { useThemePrimaryColor } from '../../utils/theme';
import { getImageUrl } from '../../utils/url';
import { triggerCheckinScan } from '../../utils/checkin';
import './HomePremium.less';

// 功能菜单配置
const menus = [
  { icon: HospitalIcon, title: '预约咨询', path: '/pages/department/index' },
  { icon: CalendarIcon, title: '我的预约', path: '/pages/appointment/index' },
  { icon: ChatIcon, title: '活动资讯', action: 'news' },
  { icon: ScanIcon, title: '联系客服', action: 'contact' },
];

// 特色服务配置（优先从后端获取，fallback 到本地默认）
const defaultFeaturedServices = [
  { id: '1', title: '口腔种植', icon: DoctorIcon, desc: '数字化种植 精准修复', path: '/pages/department/index?dept=implant' },
  { id: '2', title: '正畸矫治', icon: CalendarIcon, desc: '隐形矫正 美丽笑容', path: '/pages/department/index?dept=orthodontics' },
  { id: '3', title: '美学修复', icon: CardIcon, desc: '全瓷贴面 美白修复', path: '/pages/department/index?dept=cosmetic' },
];

// 默认轮播图
const defaultBanners = [
  { id: '1', title: '专业医疗 优质服务', imageUrl: '', linkType: 0 },
];

// 需要登录的菜单路径
const requireLoginPaths = [
  '/pages/appointment/index',
];

type PatientLoadState = 'unauthenticated' | 'no_patient' | 'has_patient' | 'load_failed';

/**
 * 首页壳层 -- 高端专科版
 * 突出品牌感和专家驱动：品牌轮播 -> 明星专家 -> 特色项目 -> 快捷入口4宫格 -> 机构介绍
 */
export function HomePremium() {
  const { template, tokens, tone } = useTemplate();
  const primaryColor = useThemePrimaryColor();

  const [banners, setBanners] = useState<Banner[]>([]);
  const [doctors, setDoctors] = useState<Doctor[]>([]);
  const [defaultPatient, setDefaultPatient] = useState<Patient | null>(null);
  const [patientLoadState, setPatientLoadState] = useState<PatientLoadState>('unauthenticated');
  const [loading, setLoading] = useState(true);
  const [brandStory, setBrandStory] = useState<{ title: string; content: string } | null>(null);
  const [featuredServices, setFeaturedServices] = useState(defaultFeaturedServices);

  // 获取可见模块排序
  const modules = template.homeSchema.filter(m => m.visible).sort((a, b) => a.order - b.order);

  useEffect(() => {
    loadData();
  }, []);

  useDidShow(() => {
    void loadPatients();
    Taro.eventCenter.trigger('tabbar:change', 0);
  });

  usePullDownRefresh(() => {
    loadData().finally(() => {
      Taro.stopPullDownRefresh();
    });
  });

  const loadData = async () => {
    try {
      const [bannersData, doctorsData] = await Promise.all([
        contentApi.getActiveBanners('home').catch(() => []),
        doctorApi.getRecommended(3).catch(() => []),
      ]);

      setBanners(bannersData.length > 0 ? bannersData : defaultBanners as any);
      setDoctors(doctorsData);
      await loadPatients();

      // 加载品牌故事
      const brandContent = await contentApi.getActiveBanners('brand-story').catch(() => []);
      if (brandContent.length > 0) {
        setBrandStory({ title: '关于我们', content: brandContent[0].description || '' });
      }

      // 加载特色服务（从常见服务 API 获取，支持科室映射）
      const servicesData = await commonServiceApi.getCommonServices().then(r => r.items).catch(() => []);
      if (servicesData.length > 0) {
        setFeaturedServices(servicesData.map(s => ({
          id: s.id,
          title: s.name,
          icon: DoctorIcon,
          desc: s.description || '',
          path: s.linkUrl || (s.departmentId ? `/pages/department/index?dept=${s.departmentId}` : '/pages/department/index'),
        })));
      }
    } catch (error) {
      console.error('[首页] 加载数据失败', error);
    } finally {
      setLoading(false);
    }
  };

  const loadPatients = useCallback(async (): Promise<PatientLoadState> => {
    const token = getToken();
    if (!token) {
      setDefaultPatient(null);
      setPatientLoadState('unauthenticated');
      return 'unauthenticated';
    }
    try {
      const patients = await userApi.getPatients();
      const defaultOne = patients.find(p => p.isDefault) || patients[0] || null;
      setDefaultPatient(defaultOne);
      const nextState: PatientLoadState = patients.length > 0 ? 'has_patient' : 'no_patient';
      setPatientLoadState(nextState);
      return nextState;
    } catch {
      setDefaultPatient(null);
      setPatientLoadState('load_failed');
      return 'load_failed';
    }
  }, []);

  useEffect(
    () =>
      subscribeAuthChange(payload => {
        if (payload.type === AUTH_EVENTS.LOGOUT || payload.type === AUTH_EVENTS.EXPIRED) {
          setDefaultPatient(null);
          setPatientLoadState('unauthenticated');
          return;
        }
        if (payload.type === AUTH_EVENTS.LOGIN || payload.type === AUTH_EVENTS.UPDATED) {
          void loadPatients();
        }
      }),
    [loadPatients]
  );

  const navigateTo = (path: string, checkLogin = false) => {
    if (checkLogin || requireLoginPaths.includes(path)) {
      if (!getToken()) {
        Taro.showToast({ title: '请先登录', icon: 'none' });
        return;
      }
    }
    if (path === '/pages/profile/index' || path === '/pages/appointment/index') {
      Taro.switchTab({ url: path });
    } else {
      Taro.navigateTo({ url: path });
    }
  };

  const handleMenuClick = (menu: typeof menus[0]) => {
    if (menu.action === 'news') {
      Taro.navigateTo({ url: '/packageOther/pages/webview/index' });
      return;
    }
    if (menu.action === 'contact') {
      Taro.navigateTo({ url: '/packageOther/pages/feedback/index' });
      return;
    }
    if (menu.path) {
      navigateTo(menu.path);
    }
  };

  const handleBannerClick = (banner: Banner) => {
    if (banner.linkType === 1 && banner.linkUrl) {
      navigateTo(banner.linkUrl);
    } else if (banner.linkType === 2 && banner.linkUrl) {
      Taro.navigateTo({ url: `/packageOther/pages/webview/index?url=${encodeURIComponent(banner.linkUrl)}` });
    }
  };

  const handleDoctorClick = (doctorId: string) => {
    Taro.navigateTo({ url: `/packageBooking/pages/doctor/detail?id=${doctorId}` });
  };

  const handleServiceClick = (service: typeof featuredServices[0]) => {
    navigateTo(service.path || '/pages/department/index');
  };

  // 按模块类型渲染
  const renderModule = (mod: typeof modules[0]) => {
    switch (mod.type) {
      case 'banner':
        return (
          <View key={mod.id} className="banner-section">
            <Swiper
              className="banner-swiper"
              autoplay
              circular
              interval={5000}
              duration={500}
              indicatorDots
              indicatorColor="rgba(255, 255, 255, 0.5)"
              indicatorActiveColor="#fff"
            >
              {banners.map(banner => (
                <SwiperItem key={banner.id} onClick={() => handleBannerClick(banner)}>
                  <View className="banner-item">
                    {banner.imageUrl ? (
                      <Image className="banner-image" src={getImageUrl(banner.imageUrl)} mode="aspectFill" />
                    ) : (
                      <View className="banner-placeholder">
                        <Text className="banner-title">{banner.title || tone.bookingLabel}</Text>
                      </View>
                    )}
                  </View>
                </SwiperItem>
              ))}
            </Swiper>
          </View>
        );

      case 'featured_doctor':
        return (
          <View key={mod.id} className="section featured-doctor-section">
            <View className="section-header">
              <Text className="section-title">明星专家</Text>
              <Text className="section-more" onClick={() => navigateTo('/pages/doctor/index')}>
                全部专家
              </Text>
            </View>
            <ScrollView className="doctor-scroll" scrollX enhanced showScrollbar={false}>
              <View className="doctor-scroll-content">
                {doctors.map(doctor => (
                  <View key={doctor.id} className="doctor-card-featured" onClick={() => handleDoctorClick(doctor.id)}>
                    <View className="doctor-avatar-wrap-featured">
                      {doctor.avatar ? (
                        <Image className="doctor-avatar" src={getImageUrl(doctor.avatar)} mode="aspectFill" />
                      ) : (
                        <View className="doctor-avatar-placeholder">
                          <DoctorIcon size={40} color={primaryColor} />
                        </View>
                      )}
                    </View>
                    <Text className="doctor-name">{doctor.name}</Text>
                    {doctor.title && <Text className="doctor-title">{doctor.title}</Text>}
                    <Text className="doctor-dept">{doctor.departmentName}</Text>
                    <View className={`doctor-status ${doctor.hasAvailableSlots ? 'available' : 'unavailable'}`}>
                      <Text>{doctor.hasAvailableSlots ? '可预约' : '暂无号'}</Text>
                    </View>
                  </View>
                ))}
              </View>
            </ScrollView>
          </View>
        );

      case 'featured_service':
        return (
          <View key={mod.id} className="section featured-service-section">
            <View className="service-list">
              {featuredServices.map(service => {
                const IconComponent = service.icon;
                return (
                  <View key={service.id} className="service-item" onClick={() => handleServiceClick(service)}>
                    <View className="service-icon-wrap">
                      <IconComponent size={32} color={primaryColor} />
                    </View>
                    <View className="service-info">
                      <Text className="service-title">{service.title}</Text>
                      <Text className="service-desc">{service.desc}</Text>
                    </View>
                  </View>
                );
              })}
            </View>
          </View>
        );

      case 'quick_menu':
        return (
          <View key={mod.id} className="section quick-menu-section">
            <View className="menu-grid">
              {menus.map(menu => {
                const IconComponent = menu.icon;
                return (
                  <View key={menu.action || menu.path} className="menu-item" onClick={() => handleMenuClick(menu)}>
                    <View className="menu-icon-wrap">
                      <IconComponent size={28} color={primaryColor} />
                    </View>
                    <Text className="menu-title">{menu.title}</Text>
                  </View>
                );
              })}
            </View>
          </View>
        );

      case 'brand_story':
        return (
          <View key={mod.id} className="section brand-story-section">
            <View className="brand-card">
              <Text className="brand-title">品牌故事</Text>
              <Text className="brand-content">
                {brandStory?.content || '我们致力于为每一位患者提供专业、优质、温馨的医疗服务体验，守护您的健康与笑容。'}
              </Text>
              <View className="brand-action" onClick={() => navigateTo('/packageOther/pages/webview/index?type=brand')}>
                <Text className="brand-action-text">了解更多</Text>
                <Text className="brand-action-arrow">→</Text>
              </View>
            </View>
          </View>
        );

      default:
        return null;
    }
  };

  return (
    <PageContainer className="home-premium-container">
      {modules.map(renderModule)}
    </PageContainer>
  );
}
