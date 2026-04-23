import type { MiniappStyleTemplate } from './types';

export const womensHealth: MiniappStyleTemplate = {
  code: 'womens-health',
  name: '女性健康',
  description: '面向妇科、产康、女性体检、专科中心，突出安心、柔和、细致、陪伴感',
  category: 'womens',
  audience: ['妇科医院', '产康中心', '女性体检中心', '专科诊所'],

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
    { id: 'health_service', type: 'health_service', visible: true, order: 2, config: {} },
    { id: 'quick_menu', type: 'quick_menu', visible: true, order: 3, config: { columns: 4 } },
    { id: 'health_reminder', type: 'health_reminder', visible: true, order: 4, config: {} },
    { id: 'recommend_doctor', type: 'recommend_doctor', visible: true, order: 5, config: {} },
  ],

  pageShells: {
    home: 'home-womens',
    department: 'dept-soft',
    doctorList: 'doctor-cards-soft',
    doctorDetail: 'doctor-detail-womens',
    appointment: 'tabs',
    profile: 'profile-womens',
  },

  designTokens: {
    primary: '#703030', // 进一步深化以满足 WCAG AA (4.5:1)
    primarySoft: '#FBF0F0',
    accent: '#502020', // 进一步深化以保持层次感
    bodyFontSize: 30,
    displayFontSize: 60,
    radiusMd: 20,
    radiusLg: 28,
    spacingMultiplier: 1,
    touchTargetMin: 88,
    customColors: {
      success: '#7AC74F',
      warning: '#F5C542',
      danger: '#E07B7B',
      gradientPrimary: 'linear-gradient(135deg, #C4908D, #E8B4B8)',
      warmBg: '#FFF9F5',
    },
  },

  assets: {
    iconStyle: 'thin',
    tabBarIconStyle: 'outlined',
    decorationStyle: 'floral',
  },

  tone: {
    bookingLabel: '预约挂号',
    patientLabel: '就诊人',
    addressMode: '您',
    emptyBookingText: '暂无预约，关爱自己从一次检查开始',
    confirmSuccessText: '预约成功！记得按时到院，如有不适可随时咨询',
    custom: {
      warmGreeting: '亲爱的',
      reminderPrefix: '关爱提示',
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
