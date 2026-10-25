export default defineAppConfig({
  pages: [
    'pages/index/index',
    'pages/appointment/index',
    'pages/org/index',
    'pages/profile/index',
    'pages/department/index',
    'pages/doctor/index',
  ],
  subPackages: [
    {
      root: 'packageBooking',
      name: 'booking',
      pages: [
        'pages/doctor/detail',
        'pages/booking/index',
        'pages/booking/result',
        'pages/appointment/detail',
        'pages/checkin/scan',
        'pages/checkin/select',
      ],
    },
    {
      root: 'packageProfile',
      name: 'profile',
      pages: [
        'pages/profile/edit',
        'pages/patient/index',
        'pages/patient/edit',
        'pages/favorite/index',
        'pages/records/index',
        'pages/records/detail',
        'pages/message/index',
        'pages/feedback/index',
        'pages/feedback/history',
        'pages/settings/index',
      ],
    },
    {
      root: 'packageOther',
      name: 'other',
      pages: [
        'pages/search/index',
        'pages/about/index',
        'pages/webview/index',
        'pages/agreement/index',
      ],
    },
  ],
  preloadRule: {
    'pages/index/index': {
      network: 'all',
      packages: ['booking', 'profile', 'other'],
    },
    'pages/department/index': {
      network: 'all',
      packages: ['booking'],
    },
    'pages/doctor/index': {
      network: 'all',
      packages: ['booking'],
    },
    'pages/profile/index': {
      network: 'all',
      packages: ['profile', 'other'],
    },
    'pages/appointment/index': {
      network: 'all',
      packages: ['booking'],
    },
  },
  window: {
    backgroundTextStyle: 'light',
    navigationBarBackgroundColor: '#fff',
    navigationBarTitleText: '医院挂号',
    navigationBarTextStyle: 'black',
  },
  tabBar: {
    custom: true,
    color: '#9CA3AF',
    selectedColor: '',
    backgroundColor: '#fff',
    borderStyle: 'black',
    list: [
      {
        pagePath: 'pages/index/index',
        text: '首页',
        iconPath: 'assets/tabbar/home.png',
        selectedIconPath: 'assets/tabbar/home-active.png',
      },
      {
        pagePath: 'pages/appointment/index',
        text: '预约',
        iconPath: 'assets/tabbar/appointment.png',
        selectedIconPath: 'assets/tabbar/appointment-active.png',
      },
      {
        pagePath: 'pages/org/index',
        text: '机构中心',
        iconPath: 'assets/tabbar/org.png',
        selectedIconPath: 'assets/tabbar/org-active.png',
      },
      {
        pagePath: 'pages/profile/index',
        text: '我的',
        iconPath: 'assets/tabbar/profile.png',
        selectedIconPath: 'assets/tabbar/profile-active.png',
      },
    ],
  },
});
