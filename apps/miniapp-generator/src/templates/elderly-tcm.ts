import type { MiniappStyleTemplate } from './types';

/**
 * 模板：长辈友好/中医康养
 * 适合中医馆、康养门诊、老年用户为主的医疗机构
 * 核心体验：低认知负担、大按钮、强引导、温暖
 */
export const elderlyTcm: MiniappStyleTemplate = {
  code: 'elderly-tcm',
  name: '长辈友好/中医康养',
  description: '面向55岁以上长辈用户，大按钮、低信息密度、口语化文案，温暖棕主色',
  category: 'tcm',
  audience: ['中医馆', '康养门诊', '老年用户为主的医疗机构'],

  navSchema: {
    tabs: [
      { pagePath: '/pages/index/index', text: '首页', iconKey: 'home', activeIconKey: 'home-active' },
      { pagePath: '/pages/appointment/index', text: '预约', iconKey: 'appointment', activeIconKey: 'appointment-active' },
      { pagePath: '/pages/profile/index', text: '我的', iconKey: 'profile', activeIconKey: 'profile-active' },
    ],
    height: 120,
  },

  homeSchema: [
    { id: 'quick_action', type: 'quick_action', visible: true, order: 1, config: { columns: 2 } },
    { id: 'simple_notice', type: 'simple_notice', visible: true, order: 2, config: {} },
    { id: 'recent_doctor', type: 'recent_doctor', visible: true, order: 3, config: { maxItems: 3 } },
  ],

  pageShells: {
    home: 'home-elderly',
    department: 'dept-large-grid',
    doctorList: 'doctor-large-cards',
    doctorDetail: 'doctor-detail-elderly',
    appointment: 'appoint-simple',
    profile: 'profile-elderly',
  },

  designTokens: {
    primary: '#6B5235', // 深化以满足 WCAG AA (4.5:1 对比度)
    primarySoft: '#F5EDE0',
    accent: '#4B3828', // 进一步深化以保持层次感
    bodyFontSize: 36,
    displayFontSize: 72,
    radiusMd: 24,
    radiusLg: 32,
    spacingMultiplier: 1.5,
    touchTargetMin: 88,
    customColors: {
      success: '#52C41A',
      warning: '#E8A838',
      danger: '#D32F2F',
      gradientPrimary: 'linear-gradient(135deg, #8B6F47, #A68B5B)',
    },
  },

  assets: {
    iconStyle: 'bold',
    tabBarIconStyle: 'filled',
    decorationStyle: 'traditional',
  },

  tone: {
    bookingLabel: '挂号',
    patientLabel: '就诊人',
    addressMode: '您',
    emptyBookingText: '您还没有挂过号，点这里挂号',
    confirmSuccessText: '挂号成功！请在看病当天带着身份证来医院',
    custom: {
      confirmBooking: '确认挂号',
      guideText: '点击这里挂号',
      nextStep: '下一步',
    },
  },

  constraints: {
    lockedPages: [
      'packageBooking/pages/booking/index',
      'packageBooking/pages/booking/result',
      'packageBooking/pages/checkin/scan',
      'packageBooking/pages/checkin/select',
    ],
    forceElderMode: true,
    confirmBeforeAction: true,
  },
};
