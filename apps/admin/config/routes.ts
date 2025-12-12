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
  },
  // 门店管理
  {
    path: '/store',
    name: '门店管理',
    icon: 'shop',
    component: './store',
  },
  // 科室管理
  {
    path: '/department',
    name: '科室管理',
    icon: 'apartment',
    component: './department',
  },
  // 医生管理
  {
    path: '/doctor',
    name: '医生管理',
    icon: 'user',
    routes: [
      { path: '/doctor', redirect: '/doctor/list' },
      { path: '/doctor/list', name: '医生列表', component: './doctor/list' },
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
    routes: [
      { path: '/schedule', redirect: '/schedule/list' },
      { path: '/schedule/list', name: '排班列表', component: './schedule/list' },
      { path: '/schedule/template', name: '排班模板', component: './schedule/template' },
    ],
  },
  // 预约管理
  {
    path: '/appointment',
    name: '预约管理',
    icon: 'schedule',
    routes: [
      { path: '/appointment', redirect: '/appointment/list' },
      { path: '/appointment/list', name: '预约列表', component: './appointment/list' },
      { path: '/appointment/:id', name: '预约详情', component: './appointment/detail', hideInMenu: true },
    ],
  },
  // 患者管理
  {
    path: '/patient',
    name: '患者管理',
    icon: 'team',
    component: './patient',
  },
  // 停诊审核
  {
    path: '/leave-request',
    name: '停诊审核',
    icon: 'exception',
    component: './leave-request',
  },
  // 用户反馈
  {
    path: '/feedback',
    name: '用户反馈',
    icon: 'comment',
    component: './feedback',
  },
  // 消息管理
  {
    path: '/message',
    name: '消息管理',
    icon: 'bell',
    component: './message',
  },
  // 内容管理
  {
    path: '/content',
    name: '内容管理',
    icon: 'fileText',
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
  },
  // 系统设置
  {
    path: '/system',
    name: '系统设置',
    icon: 'setting',
    routes: [
      { path: '/system', redirect: '/system/role' },
      { path: '/system/role', name: '角色管理', component: './system/role' },
      { path: '/system/admin', name: '管理员', component: './system/admin' },
      { path: '/system/settings', name: '系统配置', component: './system/settings' },
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
