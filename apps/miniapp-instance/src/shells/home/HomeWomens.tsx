import { View, Text, Swiper, SwiperItem, Image, ScrollView } from '@tarojs/components';
import Taro, { usePullDownRefresh, useDidShow } from '@tarojs/taro';
import { useState, useEffect, useCallback } from 'react';
import { contentApi, doctorApi, userApi } from '@hospital/api';
import type { Banner } from '@hospital/api';
import type { Doctor, Patient } from '@hospital/shared';
import {
  HospitalIcon,
  CalendarIcon,
  ChatIcon,
  ScanIcon,
  DoctorIcon,
  StethoscopeIcon,
  BookIcon,
  HealthIcon,
  CardIcon,
  AddUserIcon,
} from '../../components/Icons';
import { PageContainer } from '../../components/PageContainer';
import { useTemplate } from '../../contexts/TemplateContext';
import { AUTH_EVENTS, getToken, subscribeAuthChange } from '../../utils/auth';
import { useThemePrimaryColor } from '../../utils/theme';
import { getImageUrl } from '../../utils/url';
import { triggerCheckinScan } from '../../utils/checkin';
import './HomeWomens.less';

const menus = [
  { icon: HospitalIcon, title: '预约挂号', path: '/pages/department/index' },
  { icon: CalendarIcon, title: '预约记录', path: '/pages/appointment/index' },
  { icon: ScanIcon, title: '扫码签到', path: '', action: 'checkin' },
  { icon: ChatIcon, title: '我的客服', path: '/packageOther/pages/feedback/index' },
];

const healthServices = [
  { icon: StethoscopeIcon, title: '检查预约', desc: '妇科检查', path: '/pages/department/index' },
  { icon: DoctorIcon, title: '套餐服务', desc: '体检套餐', path: '/packageOther/pages/package/index' },
  { icon: ChatIcon, title: '在线咨询', desc: '医生咨询', path: '/packageOther/pages/consult/index' },
  { icon: BookIcon, title: '健康知识', desc: '科普文章', path: '/packageOther/pages/article/index' },
];

const defaultBanners = [
  { id: '1', title: '关爱女性健康', imageUrl: '', linkType: 0 },
];

const requireLoginPaths = [
  '/pages/appointment/index',
  '/packageOther/pages/feedback/index',
];

const requireLoginActions = ['checkin'];

type PatientLoadState = 'unauthenticated' | 'no_patient' | 'has_patient' | 'load_failed';

export function HomeWomens() {
  const { template, tokens, tone } = useTemplate();
  const primaryColor = useThemePrimaryColor();

  const [banners, setBanners] = useState<Banner[]>([]);
  const [doctors, setDoctors] = useState<Doctor[]>([]);
  const [defaultPatient, setDefaultPatient] = useState<Patient | null>(null);
  const [patientLoadState, setPatientLoadState] = useState<PatientLoadState>('unauthenticated');
  const [loading, setLoading] = useState(true);

  // 健康提醒数据
  // TODO: 对接 API - 从后端获取健康提醒数据
  const [healthReminder, setHealthReminder] = useState<{
    nextCheckDate?: string;
    lastCheckDate?: string;
    reminderContent?: string;
    hasData: boolean;
  }>({
    hasData: false,
    reminderContent: '暂无提醒，祝您健康',
  });

  // 问候语计算
  const getGreeting = (): string => {
    const hour = new Date().getHours();
    if (hour < 12) return '早上好';
    if (hour < 18) return '下午好';
    return '晚上好';
  };

  const greeting = getGreeting();

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
        doctorApi.getRecommended(4).catch(() => []),
      ]);

      setBanners(bannersData.length > 0 ? bannersData : defaultBanners as any);
      setDoctors(doctorsData);
      await loadPatients();
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
    if (menu.action) {
      if (requireLoginActions.includes(menu.action)) {
        if (!getToken()) {
          Taro.showToast({ title: '请先登录', icon: 'none' });
          return;
        }
      }
      if (menu.action === 'checkin') {
        triggerCheckinScan();
      }
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

  const handleServiceClick = (service: typeof healthServices[0]) => {
    navigateTo(service.path);
  };

  const handleReminderClick = () => {
    if (!getToken()) {
      Taro.showToast({ title: '请先登录', icon: 'none' });
      return;
    }
    navigateTo('/pages/department/index');
  };

  const handleDoctorClick = (doctorId: string) => {
    Taro.navigateTo({ url: `/packageBooking/pages/doctor/detail?id=${doctorId}` });
  };

  const renderModule = (mod: typeof modules[0]) => {
    switch (mod.type) {
      case 'greeting':
        return (
          <View key={mod.id} className="greeting-section">
            <Text className="greeting-text">亲爱的，{greeting}</Text>
          </View>
        );

      case 'banner':
        return (
          <Swiper key={mod.id} className="banner" autoplay circular indicatorDots indicatorActiveColor="#fff">
            {banners.map(banner => (
              <SwiperItem key={banner.id} onClick={() => handleBannerClick(banner)}>
                <View className="banner-item">
                  {banner.imageUrl ? (
                    <Image className="banner-image" src={getImageUrl(banner.imageUrl)} mode="aspectFill" />
                  ) : (
                    <View className="banner-content">
                      <Text className="banner-title">{banner.title || '关爱女性健康'}</Text>
                    </View>
                  )}
                </View>
              </SwiperItem>
            ))}
          </Swiper>
        );

      case 'health_service':
        return (
          <View key={mod.id} className="health-service-card">
            <View className="service-header">
              <Text className="service-title">健康服务</Text>
            </View>
            <ScrollView className="service-scroll" scrollX enhanced showScrollbar={false}>
              <View className="service-list">
                {healthServices.map(service => {
                  const IconComponent = service.icon;
                  return (
                    <View key={service.title} className="service-item" onClick={() => handleServiceClick(service)}>
                      <View className="service-icon-wrap">
                        <IconComponent size={24} color={primaryColor} />
                      </View>
                      <Text className="service-name">{service.title}</Text>
                      <Text className="service-desc">{service.desc}</Text>
                    </View>
                  );
                })}
              </View>
            </ScrollView>
          </View>
        );

      case 'quick_menu':
        return (
          <View key={mod.id} className="menu-card">
            <View className="dept-grid">
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

      case 'health_reminder':
        return (
          <View key={mod.id} className="reminder-card">
            <View className="reminder-header">
              <HealthIcon size={20} color={primaryColor} />
              <Text className="reminder-title">{tone.custom?.reminderPrefix || '关爱提示'}</Text>
            </View>
            {healthReminder.hasData ? (
              <>
                {healthReminder.nextCheckDate && (
                  <View className="reminder-row">
                    <Text className="reminder-label">下次检查</Text>
                    <Text className="reminder-date">{healthReminder.nextCheckDate}</Text>
                  </View>
                )}
                {healthReminder.lastCheckDate && (
                  <View className="reminder-row">
                    <Text className="reminder-label">上次检查</Text>
                    <Text className="reminder-date">{healthReminder.lastCheckDate}</Text>
                  </View>
                )}
                {healthReminder.reminderContent && (
                  <Text className="reminder-text">{healthReminder.reminderContent}</Text>
                )}
              </>
            ) : (
              <Text className="reminder-text">{healthReminder.reminderContent}</Text>
            )}
            <View className="reminder-action" onClick={handleReminderClick}>
              <Text className="reminder-btn">立即预约</Text>
            </View>
          </View>
        );

      case 'recommend_doctor':
        return (
          <View key={mod.id} className="section">
            <View className="section-header">
              <Text className="section-title">推荐医生</Text>
              <Text className="section-more" onClick={() => navigateTo('/pages/doctor/index')}>
                更多
              </Text>
            </View>
            <View className="doctor-list">
              {doctors.length > 0 ? (
                doctors.map(doctor => (
                  <View key={doctor.id} className="doctor-card" onClick={() => handleDoctorClick(doctor.id)}>
                    <View className="doctor-avatar">
                      {doctor.avatar ? (
                        <Image className="avatar-image" src={getImageUrl(doctor.avatar)} mode="aspectFill" />
                      ) : (
                        <DoctorIcon size={32} color={primaryColor} />
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
        );

      default:
        return null;
    }
  };

  return (
    <PageContainer className="home-container">
      {modules.map(renderModule)}
    </PageContainer>
  );
}
