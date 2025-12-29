/*
 * @Author: Lei TongDa ebian123@qq.com
 * @Date: 2025-11-27 12:20:26
 * @LastEditors: Lei TongDa ebian123@qq.com
 * @LastEditTime: 2025-12-29 20:57:03
 * @FilePath: /appointment-booking-system/apps/patient-miniapp/src/app.config.ts
 * @Description: 
 * 
 * Copyright (c) 2025 by ${git_name_email}, All Rights Reserved. 
 */
export default defineAppConfig({
  pages: [
    'pages/index/index',
    'pages/department/index',
    'pages/doctor/index',
    'pages/doctor/detail',
    'pages/booking/index',
    'pages/booking/result',
    'pages/appointment/index',
    'pages/appointment/detail',
    'pages/profile/index',
    'pages/profile/patient/index',
    'pages/profile/patient/edit',
    'pages/records/index',
    'pages/records/detail',
    'pages/search/index',
    'pages/login/index',
  ],
  window: {
    backgroundTextStyle: 'light',
    navigationBarBackgroundColor: '#fff',
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

