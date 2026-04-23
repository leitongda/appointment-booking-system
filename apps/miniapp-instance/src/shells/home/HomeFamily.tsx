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
  DoctorIcon,
  ScanIcon,
  BabyIcon,
  TeamIcon,
} from '../../components/Icons';
import { PageContainer } from '../../components/PageContainer';
import { useTemplate } from '../../contexts/TemplateContext';
import { AUTH_EVENTS, getToken, subscribeAuthChange } from '../../utils/auth';
import { useThemePrimaryColor } from '../../utils/theme';
import { getImageUrl } from '../../utils/url';
import { triggerCheckinScan } from '../../utils/checkin';
import './HomeFamily.less';

// 功能菜单配置 - 亲子儿科专用
const menus = [
  { icon: HospitalIcon, title: '预约挂号', path: '/pages/department/index' },
  { icon: CalendarIcon, title: '预约记录', path: '/pages/appointment/index' },
  { icon: ScanIcon, title: '扫码签到', path: '', action: 'checkin' },
  { icon: ChatIcon, title: '我的客服', path: '/packageOther/pages/feedback/index' },
  { icon: BabyIcon, title: '儿保预约', path: '/pages/department/index' },
  { icon: DoctorIcon, title: '疫苗接种', path: '/packageOther/pages/webview/index' },
];

// 常见服务（3列活泼卡片）
// TODO: 后端需要新增常见服务列表 API
// 目前使用本地 mock 数据
const commonServices = [
  { id: '1', name: '感冒护理', variant: 'blue' as const, path: '/pages/department/index?dept=cold' },
  { id: '2', name: '发烧处理', variant: 'orange' as const, path: '/pages/department/index?dept=fever' },
  { id: '3', name: '腹泻应对', variant: 'green' as const, path: '/pages/department/index?dept=diarrhea' },
  { id: '4', name: '过敏护理', variant: 'pink' as const, path: '/pages/department/index?dept=allergy' },
  { id: '5', name: '疫苗咨询', variant: 'purple' as const, path: '/packageOther/pages/webview/index?type=vaccine' },
  { id: '6', name: '体检套餐', variant: 'cyan' as const, path: '/packageOther/pages/package/index' },
];

// 默认轮播图
const defaultBanners = [
  { id: '1', title: '守护宝贝健康', imageUrl: '', linkType: 0 },
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
 * 首页壳层 -- 亲子儿科版
 * 模块：家庭切换器 -> Banner 轮播 -> 6宫格快捷入口 -> 按年龄分组的常见服务 -> 推荐医生列表
 */
export function HomeFamily() {
  const { template, tokens, tone } = useTemplate();
  const primaryColor = useThemePrimaryColor();

  const [banners, setBanners] = useState<Banner[]>([]);
  const [doctors, setDoctors] = useState<Doctor[]>([]);
  const [patients, setPatients] = useState<Patient[]>([]);
  const [selectedPatientId, setSelectedPatientId] = useState<string>('');
  const [patientLoadState, setPatientLoadState] = useState<PatientLoadState>('unauthenticated');
  const [loading, setLoading] = useState(true);
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
      setPatients([]);
      setSelectedPatientId('');
      setPatientLoadState('unauthenticated');
      return 'unauthenticated';
    }
    try {
      const patientList = await userApi.getPatients();
      setPatients(patientList);
      const defaultOne = patientList.find(p => p.isDefault) || patientList[0];
      if (defaultOne) {
        setSelectedPatientId(defaultOne.id);
      }
      const nextState: PatientLoadState = patientList.length > 0 ? 'has_patient' : 'no_patient';
      setPatientLoadState(nextState);
      return nextState;
    } catch {
      setPatients([]);
      setSelectedPatientId('');
      setPatientLoadState('load_failed');
      return 'load_failed';
    }
  }, []);

  useEffect(
    () =>
      subscribeAuthChange(payload => {
        if (payload.type === AUTH_EVENTS.LOGOUT || payload.type === AUTH_EVENTS.EXPIRED) {
          setPatients([]);
          setSelectedPatientId('');
          setPatientLoadState('unauthenticated');
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

  const handlePatientSelect = (patient: Patient) => {
    setSelectedPatientId(patient.id);
  };

  const handleAddPatient = () => {
    const token = getToken();
    if (!token) {
      Taro.showToast({ title: '请先登录', icon: 'none' });
      return;
    }
    Taro.navigateTo({ url: '/packageProfile/pages/patient/edit' });
  };

  const handleDoctorClick = (doctorId: string) => {
    Taro.navigateTo({ url: `/packageBooking/pages/doctor/detail?id=${doctorId}` });
  };

  // 按模块类型渲染
  const renderModule = (mod: typeof modules[0]) => {
    switch (mod.type) {
      case 'family_switcher':
        return (
          <View key={mod.id} className="family-switcher">
            <ScrollView className="patient-list" scrollX enhanced showScrollbar={false}>
              {patients.map(patient => (
                <View
                  key={patient.id}
                  className={`patient-item ${selectedPatientId === patient.id ? 'active' : ''}`}
                  onClick={() => handlePatientSelect(patient)}
                >
                  <View className="patient-avatar">
                    {patient.avatar ? (
                      <Image className="avatar-image" src={getImageUrl(patient.avatar)} mode="aspectFill" />
                    ) : (
                      <BabyIcon size={24} color={selectedPatientId === patient.id ? '#fff' : primaryColor} />
                    )}
                  </View>
                  <Text className="patient-name">{patient.name}</Text>
                </View>
              ))}
              <View className="patient-item add-patient" onClick={handleAddPatient}>
                <View className="patient-avatar">
                  <Text className="add-icon">+</Text>
                </View>
                <Text className="patient-name">添加</Text>
              </View>
            </ScrollView>
            {!getToken() && (
              <View className="login-tip">
                <Text>登录后管理家庭成员</Text>
              </View>
            )}
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
            <View className="menu-grid">
              {menus.map((menu, index) => {
                const IconComponent = menu.icon;
                return (
                  <View key={menu.action || menu.path} className="menu-item" onClick={() => handleMenuClick(menu)}>
                    <View className="menu-icon-wrap">
                      <View className="menu-icon-wrap-inner">
                        <IconComponent size={28} color="#fff" />
                      </View>
                    </View>
                    <Text className="menu-title">{menu.title}</Text>
                  </View>
                );
              })}
            </View>
          </View>
        );

      case 'common_service':
        return (
          <View key={mod.id} className="common-services-section">
            <View className="section-header">
              <Text className="section-title">常见服务</Text>
            </View>
            <View className="common-services-grid">
              {commonServices.map(service => (
                <View
                  key={service.id}
                  className={`common-service-item variant-${service.variant}`}
                  onClick={() => navigateTo(service.path)}
                >
                  <View className="service-icon">
                    <Text className="service-icon-text">{service.name.substring(0, 2)}</Text>
                  </View>
                  <Text className="service-name">{service.name}</Text>
                </View>
              ))}
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
                      <View className="doctor-tags">
                        <Text className="tag specialty-tag">擅长儿童{doctor.specialty?.substring(0, 4) || '常见病'}</Text>
                      </View>
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
    <PageContainer className="home-container home-family">
      {modules.map(renderModule)}
    </PageContainer>
  );
}
