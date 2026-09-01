import { View, Text, Swiper, SwiperItem, Image } from '@tarojs/components';
import Taro, { usePullDownRefresh, useDidShow } from '@tarojs/taro';
import { useState, useEffect, useCallback } from 'react';
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
import { useTemplate } from '../../contexts/TemplateContext';
import { AUTH_EVENTS, getToken, subscribeAuthChange } from '../../utils/auth';
import { useThemePrimaryColor } from '../../utils/theme';
import { getImageUrl } from '../../utils/url';
import { triggerCheckinScan } from '../../utils/checkin';
import { LoadFailedErrorState } from '../../components/EmptyState';
import './HomeStandard.less';

// 功能菜单配置
const menus = [
  { icon: HospitalIcon, title: '预约挂号', path: '/pages/department/index' },
  { icon: CalendarIcon, title: '预约记录', path: '/pages/appointment/index' },
  { icon: ScanIcon, title: '扫码签到', path: '', action: 'checkin' },
  { icon: ChatIcon, title: '我的客服', path: '/packageOther/pages/feedback/index' },
];

// 默认轮播图
const defaultBanners = [
  { id: '1', title: '智慧医疗', imageUrl: '', linkType: 0 },
];

// 需要登录的菜单路径
const requireLoginPaths = [
  '/pages/appointment/index',
  '/packageOther/pages/feedback/index',
];

// 需要登录的 action
const requireLoginActions = ['checkin'];

type PatientLoadState = 'unauthenticated' | 'no_patient' | 'has_patient' | 'load_failed';

/**
 * 首页壳层 -- 现代综合医疗标准版
 * 模块按 homeSchema 配置渲染：Banner 轮播 -> 4宫格快捷入口 -> 就诊卡入口 -> 推荐医生列表
 */
export function HomeStandard() {
  const { template, tokens, tone } = useTemplate();
  const primaryColor = useThemePrimaryColor();

  const [banners, setBanners] = useState<Banner[]>([]);
  const [doctors, setDoctors] = useState<Doctor[]>([]);
  const [defaultPatient, setDefaultPatient] = useState<Patient | null>(null);
  const [patientLoadState, setPatientLoadState] = useState<PatientLoadState>('unauthenticated');
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(false);
  const [pendingPatientCardNav, setPendingPatientCardNav] = useState(false);
  const [pendingCheckinAction, setPendingCheckinAction] = useState(false);

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
    setLoadError(false);
    try {
      const [bannersData, doctorsData] = await Promise.all([
        contentApi.getActiveBanners('home').catch(() => []),
        doctorApi.getRecommended(6).catch(() => []),
      ]);

      setBanners(bannersData.length > 0 ? bannersData : defaultBanners as any);
      setDoctors(doctorsData);
      await loadPatients();
    } catch (error) {
      console.error('[首页] 加载数据失败', error);
      setLoadError(true);
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
          setPendingPatientCardNav(false);
          setPendingCheckinAction(false);
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

  const handlePatientCardClick = () => {
    const token = getToken();
    if (!token) {
      setPendingPatientCardNav(true);
      Taro.showToast({ title: '请先登录', icon: 'none' });
      return;
    }
    if (defaultPatient) {
      Taro.navigateTo({ url: '/packageProfile/pages/patient/index' });
    } else {
      Taro.navigateTo({ url: '/packageProfile/pages/patient/edit' });
    }
  };

  const handleDoctorClick = (doctorId: string) => {
    Taro.navigateTo({ url: `/packageBooking/pages/doctor/detail?id=${doctorId}` });
  };

  // 按模块类型渲染
  const renderModule = (mod: typeof modules[0]) => {
    switch (mod.type) {
      case 'banner':
        return (
          <Swiper key={mod.id} className="banner" autoplay circular indicatorDots indicatorActiveColor="#fff">
            {banners.map(banner => (
              <SwiperItem key={banner.id}>
                <View className="banner-item" onClick={() => handleBannerClick(banner)} aria-label={`查看${banner.title || '轮播'}详情`} role="button">
                  {banner.imageUrl ? (
                    <Image className="banner-image" src={getImageUrl(banner.imageUrl)} mode="aspectFill" />
                  ) : (
                    <View className="banner-content">
                      <Text className="banner-title">{banner.title || tone.bookingLabel}</Text>
                    </View>
                  )}
                </View>
              </SwiperItem>
            ))}
          </Swiper>
        );

      case 'quick_menu':
        return (
          <View key={mod.id} className="menu-card">
            <View className="dept-grid">
              {menus.map(menu => {
                const IconComponent = menu.icon;
                return (
                  <View key={menu.action || menu.path} className="menu-item" onClick={() => handleMenuClick(menu)} aria-label={menu.title} role="button">
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

      case 'patient_card':
        return (
          <View key={mod.id} className="patient-card-entry" onClick={handlePatientCardClick} aria-label={defaultPatient ? `查看就诊卡${defaultPatient.name}` : '添加就诊卡'} role="button">
            {defaultPatient ? (
              <>
                <View className="card-icon">
                  <CardIcon size={32} color={primaryColor} />
                </View>
                <View className="card-info">
                  <Text className="card-name">{defaultPatient.name}</Text>
                  <Text className="card-relation">
                    {defaultPatient.relationship || '本人'} -- 默认就诊人
                  </Text>
                </View>
                <Text className="card-arrow">{'>'}</Text>
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
                <Text className="card-arrow">{'>'}</Text>
              </>
            )}
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
                  <View key={doctor.id} className="doctor-card" onClick={() => handleDoctorClick(doctor.id)} aria-label={`查看医生${doctor.name}的详情`} role="button">
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
      {loadError ? (
        <LoadFailedErrorState onRetry={loadData} />
      ) : (
        modules.map(renderModule)
      )}
    </PageContainer>
  );
}
