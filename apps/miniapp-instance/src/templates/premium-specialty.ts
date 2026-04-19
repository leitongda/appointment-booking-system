import type { MiniappStyleTemplate } from './types';

export const premiumSpecialty: MiniappStyleTemplate = {
  code: 'premium-specialty',
  name: '高端专科门诊',
  description: '面向口腔、医美、私立专科、会员制门诊，突出品牌感、精致、专家驱动',
  category: 'specialty',
  audience: ['口腔诊所', '医美机构', '私立专科', '会员制门诊'],

  navSchema: {
    tabs: [
      { pagePath: '/pages/index/index', text: '首页', iconKey: 'home', activeIconKey: 'home-active' },
      { pagePath: '/pages/doctor/index', text: '专家', iconKey: 'doctor', activeIconKey: 'doctor-active' },
      { pagePath: '/pages/appointment/index', text: '预约', iconKey: 'appointment', activeIconKey: 'appointment-active' },
      { pagePath: '/pages/profile/index', text: '我的', iconKey: 'profile', activeIconKey: 'profile-active' },
    ],
    height: 100,
  },

  homeSchema: [
    { id: 'banner', type: 'banner', visible: true, order: 1, config: {} },
    { id: 'featured_doctor', type: 'featured_doctor', visible: true, order: 2, config: {} },
    { id: 'featured_service', type: 'featured_service', visible: true, order: 3, config: {} },
    { id: 'quick_menu', type: 'quick_menu', visible: true, order: 4, config: { columns: 4 } },
    { id: 'brand_story', type: 'brand_story', visible: true, order: 5, config: {} },
  ],

  pageShells: {
    home: 'home-premium',
    department: 'dept-minimal',
    doctorList: 'doctor-showcase',
    doctorDetail: 'doctor-detail-premium',
    appointment: 'tabs',
    profile: 'profile-premium',
  },

  designTokens: {
    primary: '#7B6345', // 深化棕色以满足 WCAG AA (4.5:1)
    primarySoft: '#F6F0E3',
    accent: '#5B4730',
    bodyFontSize: 28,
    displayFontSize: 56,
    radiusMd: 12,
    radiusLg: 16,
    spacingMultiplier: 1.1,
    touchTargetMin: 88,
    customColors: {
      success: '#52C41A',
      warning: '#FAAD14',
      danger: '#C0392B',
      gradientPrimary: 'linear-gradient(135deg, #8B7355, #6B5740)',
    },
  },

  assets: {
    iconStyle: 'thin',
    tabBarIconStyle: 'outlined',
    decorationStyle: 'minimal',
  },

  tone: {
    bookingLabel: '预约咨询',
    patientLabel: '就诊人',
    addressMode: '您',
    emptyBookingText: '暂无预约记录，立即预约专家',
    confirmSuccessText: '您的专属专家已确认预约，请准时到院',
    custom: {
      confirmBooking: '确认预约',
      expertLabel: '专家',
      serviceLabel: '服务项目',
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
