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
  // 主包页面：tabBar 页面和高频访问页面
  pages: [
    'pages/index/index',           // 首页 (tabBar)
    'pages/appointment/index',     // 预约列表 (tabBar)
    'pages/profile/index',         // 我的 (tabBar)
    'pages/department/index',      // 科室列表 (首页入口)
    'pages/doctor/index',          // 医生列表 (首页入口)
  ],
  // 分包配置：将低频页面分离到子包
  subPackages: [
    {
      // 预约相关子包
      root: 'packageBooking',
      name: 'booking',
      pages: [
        'pages/doctor/detail',       // 医生详情
        'pages/booking/index',       // 预约挂号
        'pages/booking/result',      // 预约结果
        'pages/appointment/detail',  // 预约详情
        'pages/checkin/scan',        // 扫码签到
        'pages/checkin/select',      // 选择预约签到
      ],
    },
    {
      // 个人中心相关子包
      root: 'packageProfile',
      name: 'profile',
      pages: [
        'pages/profile/edit',        // 个人信息编辑
        'pages/patient/index',       // 就诊人列表
        'pages/patient/edit',        // 就诊人编辑
        'pages/favorite/index',      // 我的收藏
        'pages/records/index',       // 就诊记录
        'pages/records/detail',      // 记录详情
        'pages/message/index',       // 消息中心
        'pages/feedback/index',      // 意见反馈
        'pages/feedback/history',    // 反馈历史
        'pages/settings/index',      // 设置
      ],
    },
    {
      // 其他功能子包
      root: 'packageOther',
      name: 'other',
      pages: [
        'pages/search/index',        // 搜索
        'pages/about/index',         // 关于
        'pages/webview/index',       // 网页
        'pages/agreement/index',     // 协议
      ],
    },
  ],
  // 分包预下载规则 - 优化跳转延迟
  preloadRule: {
    'pages/index/index': {
      network: 'all',
      packages: ['booking', 'profile', 'other'],  // 首页预下载所有分包，用户最常从首页跳转
    },
    'pages/department/index': {
      network: 'all',
      packages: ['booking'],  // 科室页预下载预约包（用户接下来会选医生预约）
    },
    'pages/doctor/index': {
      network: 'all',
      packages: ['booking'],  // 医生列表页预下载预约包
    },
    'pages/profile/index': {
      network: 'all',
      packages: ['profile', 'other'],  // 我的页面预下载个人中心和其他子包
    },
    'pages/appointment/index': {
      network: 'all',
      packages: ['booking'],  // 预约列表页预下载预约详情等
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
    selectedColor: '',  // 使用 CSS 变量动态控制主题色
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

