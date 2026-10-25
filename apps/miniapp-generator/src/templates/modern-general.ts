import type { MiniappStyleTemplate } from './types';

/**
 * 模板：现代综合医疗
 * 适合综合医院、门诊、连锁医疗机构
 * 突出专业、清晰、可信赖
 */
export const modernGeneral: MiniappStyleTemplate = {
  code: 'modern-general',
  name: '现代综合医疗',
  description: '通用型医院模板，面向大众用户，突出专业、清晰、可信赖',
  category: 'general',
  audience: ['综合医院', '门诊部', '连锁医疗机构'],

  navSchema: {
    tabs: [
      { pagePath: '/pages/index/index', text: '首页', iconKey: 'home', activeIconKey: 'home-active' },
      { pagePath: '/pages/appointment/index', text: '预约', iconKey: 'appointment', activeIconKey: 'appointment-active' },
      { pagePath: '/pages/profile/index', text: '我的', iconKey: 'profile', activeIconKey: 'profile-active' },
    ],
    height: 100,
  },

  homeSchema: [
    { id: 'banner', type: 'banner', visible: true, order: 1, config: {} },
    { id: 'notice', type: 'notice', visible: true, order: 2, config: {} },
    { id: 'quick_menu', type: 'quick_menu', visible: true, order: 3, config: { columns: 4 } },
    { id: 'patient_card', type: 'patient_card', visible: true, order: 4, config: {} },
    { id: 'recommend_doctor', type: 'recommend_doctor', visible: true, order: 5, config: {} },
  ],

  pageShells: {
    home: 'standard',
    department: 'sidebar',
    doctorList: 'cards',
    doctorDetail: 'standard',
    appointment: 'tabs',
    profile: 'standard',
  },

  designTokens: {
    primary: '#3D6CA8', // 深化蓝色以满足 WCAG AA (4.5:1)
    primarySoft: '#EAF1F8',
    accent: '#2D4E82',
    bodyFontSize: 30,
    displayFontSize: 60,
    radiusMd: 16,
    radiusLg: 24,
    spacingMultiplier: 1,
    touchTargetMin: 88,
    customColors: {},
  },

  assets: {
    iconStyle: 'outlined',
    tabBarIconStyle: 'filled',
    decorationStyle: 'none',
  },

  tone: {
    bookingLabel: '预约挂号',
    patientLabel: '就诊人',
    addressMode: '您',
    emptyBookingText: '暂无预约记录',
    confirmSuccessText: '预约成功！请于就诊当天携带有效身份证件到院',
    custom: {},
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
