/**
 * 路由配置
 * @name 配置名称
 * @icon 菜单图标
 * @access 权限配置
 * @hideInMenu 隐藏菜单
 */
export default [
  // 登录页
  {
    path: '/login',
    layout: false,
    component: './login',
  },
  // 欢迎页
  {
    path: '/welcome',
    name: '欢迎',
    icon: 'smile',
    component: './welcome',
  },
  // 仪表盘
  {
    path: '/dashboard',
    name: '仪表盘',
    icon: 'dashboard',
    component: './dashboard',
    access: 'canDashboard',
  },
  // 门店管理
  {
    path: '/store',
    name: '门店管理',
    icon: 'shop',
    component: './store',
    access: 'canStore',
  },
  // 科室管理
  {
    path: '/department',
    name: '科室管理',
    icon: 'apartment',
    component: './department',
    access: 'canDepartment',
  },
  // 医生管理
  {
    path: '/doctor',
    name: '医生管理',
    icon: 'user',
    access: 'canDoctor',
    routes: [
      { path: '/doctor', redirect: '/doctor/list' },
      { path: '/doctor/list', name: '医生列表', component: './doctor/list' },
      { path: '/doctor/booking-setting', name: '预约设置', component: './doctor/booking-setting' },
      { path: '/doctor/create', name: '新增医生', component: './doctor/form', hideInMenu: true },
      { path: '/doctor/:id', name: '医生详情', component: './doctor/detail', hideInMenu: true },
      { path: '/doctor/:id/edit', name: '编辑医生', component: './doctor/form', hideInMenu: true },
    ],
  },
  // 排班管理
  {
    path: '/schedule',
    name: '排班管理',
    icon: 'calendar',
    access: 'canSchedule',
    routes: [
      { path: '/schedule', redirect: '/schedule/list' },
      { path: '/schedule/list', name: '排班列表', component: './schedule/list' },
      { path: '/schedule/template', name: '排班模板', component: './schedule/template' },
      { path: '/schedule/custom', name: '自定义排班', component: './schedule/custom' },
      { path: '/schedule/rest-day', name: '休息日设置', component: './schedule/rest-day' },
      { path: '/schedule/suspension', name: '停诊管理', component: './schedule/suspension' },
      { path: '/schedule/statistics', name: '排班统计', component: './schedule/statistics' },
    ],
  },
  // 预约管理
  {
    path: '/appointment',
    name: '预约管理',
    icon: 'schedule',
    access: 'canAppointment',
    routes: [
      { path: '/appointment', redirect: '/appointment/list' },
      { path: '/appointment/list', name: '预约列表', component: './appointment/list' },
      { path: '/appointment/statistics', name: '预约统计', component: './appointment/statistics' },
      { path: '/appointment/:id', name: '预约详情', component: './appointment/detail', hideInMenu: true },
    ],
  },
  // 患者管理
  {
    path: '/patient',
    name: '患者管理',
    icon: 'team',
    access: 'canPatient',
    routes: [
      { path: '/patient', redirect: '/patient/list' },
      { path: '/patient/list', name: '患者列表', component: './patient' },
      { path: '/patient/:id', name: '患者详情', component: './patient/detail', hideInMenu: true },
    ],
  },
  // 停诊审核
  {
    path: '/leave-request',
    name: '停诊审核',
    icon: 'exception',
    component: './leave-request',
    access: 'canLeaveRequest',
  },
  // 用户反馈
  {
    path: '/feedback',
    name: '用户反馈',
    icon: 'comment',
    component: './feedback',
    access: 'canFeedback',
  },
  // 消息管理
  {
    path: '/message',
    name: '消息管理',
    icon: 'bell',
    component: './message',
    access: 'canMessage',
  },
  // 内容管理
  {
    path: '/content',
    name: '内容管理',
    icon: 'fileText',
    access: 'canContent',
    routes: [
      { path: '/content', redirect: '/content/news' },
      { path: '/content/news', name: '新闻管理', component: './content/news' },
      { path: '/content/notice', name: '公告管理', component: './content/notice' },
      { path: '/content/banner', name: '轮播图', component: './content/banner' },
    ],
  },
  // 统计分析
  {
    path: '/statistics',
    name: '统计分析',
    icon: 'barChart',
    component: './statistics',
    access: 'canStatistics',
  },
  // 系统设置
  {
    path: '/system',
    name: '系统设置',
    icon: 'setting',
    access: 'canSystem',
    routes: [
      { path: '/system', redirect: '/system/role' },
      { path: '/system/role', name: '角色管理', component: './system/role' },
      { path: '/system/admin', name: '管理员', component: './system/admin' },
      { path: '/system/settings', name: '系统配置', component: './system/settings' },
      { path: '/system/consultation-fee-types', name: '诊费类型', component: './system/consultation-fee-types' },
      { path: '/system/consultation-fee-templates', name: '诊费模板', component: './system/consultation-fee-templates' },
      { path: '/system/log', name: '操作日志', component: './system/log' },
    ],
  },
  // 根路由重定向
  {
    path: '/',
    redirect: '/dashboard',
  },
  // 404
  {
    path: '*',
    layout: false,
    component: './404',
  },
];
