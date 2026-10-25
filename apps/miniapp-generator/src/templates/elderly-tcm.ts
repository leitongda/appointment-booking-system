import type { MiniappStyleTemplate } from './types';

/**
 * 模板：长辈友好/中医康养
 * 适合中医馆、康养门诊、老年用户为主的医疗机构
 * 核心体验：低认知负担、大按钮、强引导、温暖
 */
export const elderlyTcm: MiniappStyleTemplate = {
  code: 'elderly-tcm',
  name: '长辈友好/中医康养',
  description: '面向55岁以上长辈用户，大按钮、低信息密度、口语化文案，清新绿主色',
  category: 'tcm',
  audience: ['中医馆', '康养门诊', '老年用户为主的医疗机构'],

  navSchema: {
    tabs: [
      { pagePath: '/pages/index/index', text: '首页', iconKey: 'home', activeIconKey: 'home-active' },
      { pagePath: '/pages/org/index', text: '机构中心', iconKey: 'org', activeIconKey: 'org-active' },
      { pagePath: '/pages/profile/index', text: '我的', iconKey: 'profile', activeIconKey: 'profile-active' },
    ],
    height: 120,
  },

  homeSchema: [
    { id: 'notice', type: 'notice', visible: true, order: 1, config: {} },
    { id: 'quick_action', type: 'quick_action', visible: true, order: 2, config: { columns: 2 } },
    { id: 'health_card', type: 'patient_card', visible: true, order: 3, config: {} },
    { id: 'simple_notice', type: 'simple_notice', visible: true, order: 4, config: {} },
    { id: 'recent_doctor', type: 'recent_doctor', visible: true, order: 5, config: { maxItems: 3 } },
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
    primary: '#4E8064', // 深绿以满足 WCAG AA (4.5:1 对比度)
    primarySoft: '#EAF3EE',
    accent: '#3A6350', // 进一步深化以保持层次感
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
      gradientPrimary: 'linear-gradient(135deg, #5F8F74, #3E6B52)',
      // 首页四宫格贴片色（对应竞品绿色主题）
      tilePrimary: '#5F8F74',
      tileSecondary: '#4E8064',
      tileTertiary: '#7CA98B',
      tileQuaternary: '#3E6B52',
    },
  },

  assets: {
    iconStyle: 'bold',
    tabBarIconStyle: 'filled',
    decorationStyle: 'traditional',
  },

  tone: {
    bookingLabel: '预约挂号',
    patientLabel: '我的就诊卡',
    addressMode: '您',
    emptyBookingText: '您还没有挂过号，点这里挂号',
    confirmSuccessText: '挂号成功！请在看病当天带着身份证来医院',
    custom: {
      confirmBooking: '确认挂号',
      guideText: '点击这里挂号',
      nextStep: '下一步',
      appointmentRecordsLabel: '预约记录',
      onlineServiceLabel: '在线客服',
      healthCardTitle: '添加健康卡',
      healthCardSubtitle: '记录您的健康',
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
