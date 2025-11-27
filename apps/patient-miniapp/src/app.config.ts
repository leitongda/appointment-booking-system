export default defineAppConfig({
  pages: [
    'pages/index/index',
    'pages/department/index',
    'pages/doctor/index',
    'pages/doctor/detail',
    'pages/booking/index',
    'pages/appointment/index',
    'pages/appointment/detail',
    'pages/profile/index',
    'pages/profile/patient/index',
    'pages/records/index',
    'pages/login/index',
  ],
  window: {
    backgroundTextStyle: 'light',
    navigationBarBackgroundColor: '#667eea',
    navigationBarTitleText: '医院挂号',
    navigationBarTextStyle: 'white',
  },
  tabBar: {
    color: '#999',
    selectedColor: '#667eea',
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
        pagePath: 'pages/profile/index',
        text: '我的',
        iconPath: 'assets/tabbar/profile.png',
        selectedIconPath: 'assets/tabbar/profile-active.png',
      },
    ],
  },
});

