import type { MiniappStyleTemplate } from './types';

/**
 * 模板：亲子儿科
 * 面向儿童医院、儿科门诊、家庭健康场景
 * 核心体验：亲和、活泼、家庭成员管理突出
 */
export const familyPediatrics: MiniappStyleTemplate = {
  code: 'family-pediatrics',
  name: '亲子儿科',
  description: '面向儿童医院、儿科门诊、家庭健康场景，突出亲和、活泼、家庭成员管理',
  category: 'pediatrics',
  audience: ['儿童医院', '儿科门诊', '家庭健康中心'],

  navSchema: {
    tabs: [
      { pagePath: '/pages/index/index', text: '首页', iconKey: 'home', activeIconKey: 'home-active' },
      { pagePath: '/pages/appointment/index', text: '预约', iconKey: 'appointment', activeIconKey: 'appointment-active' },
      { pagePath: '/pages/profile/index', text: '成长', iconKey: 'profile', activeIconKey: 'profile-active' },
    ],
    height: 100,
  },

  homeSchema: [
    { id: 'family_switcher', type: 'family_switcher', visible: true, order: 1, config: {} },
    { id: 'banner', type: 'banner', visible: true, order: 2, config: {} },
    { id: 'quick_menu', type: 'quick_menu', visible: true, order: 3, config: { columns: 3, rows: 2 } },
    { id: 'common_service', type: 'common_service', visible: true, order: 4, config: {} },
    { id: 'recommend_doctor', type: 'recommend_doctor', visible: true, order: 5, config: {} },
  ],

  pageShells: {
    home: 'home-family',
    department: 'dept-colorful',
    doctorList: 'cards',
    doctorDetail: 'doctor-detail-family',
    appointment: 'tabs',
    profile: 'profile-family',
  },

  designTokens: {
    primary: '#3A7AB3', // 进一步深化以满足 WCAG AA (4.5:1)
    primarySoft: '#EDF4FB',
    accent: '#C58603',
    bodyFontSize: 30,
    displayFontSize: 64,
    radiusMd: 20,
    radiusLg: 28,
    spacingMultiplier: 1.05,
    touchTargetMin: 88,
    customColors: {
      success: '#52C41A',
      warning: '#FAAD14',
      danger: '#FF6B6B',
      gradientPrimary: 'linear-gradient(135deg, #5B9BD5, #7EC8E3)',
      fun1: '#FFB6C1',
      fun2: '#98D8C8',
      fun3: '#FFE66D',
    },
  },

  assets: {
    iconStyle: 'filled',
    tabBarIconStyle: 'filled',
    decorationStyle: 'playful',
  },

  tone: {
    bookingLabel: '预约挂号',
    patientLabel: '宝宝',
    addressMode: '您',
    emptyBookingText: '还没有预约记录，给宝宝挂个号吧',
    confirmSuccessText: '预约成功！请带好宝宝的预防接种证和医保卡',
    custom: {
      babyLabel: '宝宝',
      parentLabel: '家长',
      growthLabel: '成长',
    },
  },

  constraints: {
    lockedPages: [
      'packageBooking/pages/booking/index',
      'packageBooking/pages/booking/result',
      'packageBooking/pages/checkin/scan',
      'packageBooking/pages/checkin/select',
    ],
    forceElderMode: false,
    confirmBeforeAction: false,
  },
};
