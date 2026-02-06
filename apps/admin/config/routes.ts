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
    access: 'canStore',
    routes: [
      { path: '/store', redirect: '/store/list' },
      { path: '/store/list', name: '门店列表', component: './store' },
      { path: '/store/create', name: '新增门店', component: './store/form', hideInMenu: true },
      { path: '/store/:id/edit', name: '编辑门店', component: './store/form', hideInMenu: true },
      { path: '/store/:storeId/fee-types', name: '门店诊费类型', component: './store/fee-types', hideInMenu: true },
      { path: '/store/:storeId/fee-templates', name: '门店诊费模板', component: './store/fee-templates', hideInMenu: true },
      { path: '/store/:storeId/visit-type-config', name: '复诊规则配置', component: './store/visit-type-config', hideInMenu: true },
    ],
  },
  // 科室管理
  {
    path: '/department',
    name: '科室管理',
    icon: 'apartment',
    access: 'canDepartment',
    routes: [
      { path: '/department', redirect: '/department/list' },
      { path: '/department/list', name: '科室列表', component: './department' },
      { path: '/department/create', name: '新增科室', component: './department/form', hideInMenu: true },
      { path: '/department/:id/edit', name: '编辑科室', component: './department/form', hideInMenu: true },
    ],
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
      { path: '/doctor/booking-setting/create', name: '添加预约设置', component: './doctor/booking-setting-form', hideInMenu: true },
      { path: '/doctor/booking-setting/:id/edit', name: '编辑预约设置', component: './doctor/booking-setting-form', hideInMenu: true },
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
      { path: '/schedule', redirect: '/schedule/rule' },
      { path: '/schedule/rule', name: '排班规则设置', component: './schedule/rule' },
      { path: '/schedule/rule/create', name: '新增排班规则', component: './schedule/rule/form', hideInMenu: true },
      { path: '/schedule/rule/:id/edit', name: '编辑排班规则', component: './schedule/rule/form', hideInMenu: true },
      { path: '/schedule/list', name: '排班列表', component: './schedule/detail' },
      { path: '/schedule/calendar', name: '排班日历', component: './schedule/calendar' },
      { path: '/schedule/gantt', name: '排班甘特图', component: './schedule/gantt' },
      { path: '/schedule/custom', name: '自定义排班', component: './schedule/custom' },
      { path: '/schedule/custom/create', name: '添加自定义排班', component: './schedule/custom-form', hideInMenu: true },
      { path: '/schedule/rest-day', name: '休息日设置', component: './schedule/rest-day' },
      { path: '/schedule/rest-day/create', name: '添加休息日', component: './schedule/rest-day-form', hideInMenu: true },
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
      { path: '/appointment/queue', name: '签到队列', component: './appointment/queue' },
      { path: '/appointment/statistics', name: '预约统计', component: './appointment/statistics' },
      { path: '/appointment/:id', name: '预约详情', component: './appointment/detail', hideInMenu: true },
    ],
  },
  // 患者管理
  {
    path: '/user',
    name: '患者管理',
    icon: 'team',
    access: 'canPatient',
    routes: [
      { path: '/user', redirect: '/user/list' },
      { path: '/user/list', name: '患者列表', component: './user' },
      { path: '/user/:id', name: '患者详情', component: './user/detail', hideInMenu: true },
    ],
  },
  // 就诊卡管理
  {
    path: '/medical-card',
    name: '就诊卡管理',
    icon: 'idcard',
    access: 'canPatient',
    routes: [
      { path: '/medical-card', redirect: '/medical-card/list' },
      { path: '/medical-card/list', name: '就诊卡列表', component: './patient' },
      { path: '/medical-card/:id', name: '就诊卡详情', component: './patient/detail', hideInMenu: true },
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
    access: 'canMessage',
    routes: [
      { path: '/message', redirect: '/message/list' },
      { path: '/message/list', name: '消息列表', component: './message' },
      { path: '/message/create', name: '发送消息', component: './message/form', hideInMenu: true },
    ],
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
      { path: '/content/news/create', name: '发布新闻', component: './content/news-form', hideInMenu: true },
      { path: '/content/news/:id/edit', name: '编辑新闻', component: './content/news-form', hideInMenu: true },
      { path: '/content/notice', name: '公告管理', component: './content/notice' },
      { path: '/content/notice/create', name: '发布公告', component: './content/notice-form', hideInMenu: true },
      { path: '/content/notice/:id/edit', name: '编辑公告', component: './content/notice-form', hideInMenu: true },
      { path: '/content/banner', name: '轮播图', component: './content/banner' },
      { path: '/content/banner/create', name: '新增轮播图', component: './content/banner-form', hideInMenu: true },
      { path: '/content/banner/:id/edit', name: '编辑轮播图', component: './content/banner-form', hideInMenu: true },
    ],
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
      { path: '/system/role/create', name: '新增角色', component: './system/role-form', hideInMenu: true },
      { path: '/system/role/:id/edit', name: '编辑角色', component: './system/role-form', hideInMenu: true },
      { path: '/system/role/:id/permissions', name: '分配权限', component: './system/role-permissions', hideInMenu: true },
      { path: '/system/user', name: '用户管理', component: './system/user' },
      { path: '/system/user/create', name: '新增用户', component: './system/user-form', hideInMenu: true },
      { path: '/system/user/:id/edit', name: '编辑用户', component: './system/user-form', hideInMenu: true },
      { path: '/system/settings', name: '系统配置', component: './system/settings' },
      { path: '/system/shift-types', name: '班次类型', component: './system/shift-types' },
      { path: '/system/shift-types/create', name: '新增班次类型', component: './system/shift-type-form', hideInMenu: true },
      { path: '/system/shift-types/:id/edit', name: '编辑班次类型', component: './system/shift-type-form', hideInMenu: true },
      { path: '/system/consultation-fee-types', name: '诊费类型', component: './system/consultation-fee-types' },
      { path: '/system/consultation-fee-types/create', name: '新增诊费类型', component: './system/consultation-fee-type-form', hideInMenu: true },
      { path: '/system/consultation-fee-types/:id/edit', name: '编辑诊费类型', component: './system/consultation-fee-type-form', hideInMenu: true },
      { path: '/system/consultation-fee-templates', name: '诊费模板', component: './system/consultation-fee-templates' },
      { path: '/system/email-templates', name: '邮件模板', component: './system/email-templates' },
      { path: '/system/email-templates/create', name: '新增邮件模板', component: './system/email-template-form', hideInMenu: true },
      { path: '/system/email-templates/:id/edit', name: '编辑邮件模板', component: './system/email-template-form', hideInMenu: true },
      { path: '/system/email-recipients', name: '邮件接收人', component: './system/email-recipients' },
      { path: '/system/booking-notice', name: '预约须知', component: './system/booking-notice' },
      { path: '/system/rule-sets', name: '规则组管理', component: './system/rule-sets' },
      { path: '/system/rule-sets/create', name: '新增规则组', component: './system/rule-set-form', hideInMenu: true },
      { path: '/system/rule-sets/:id/edit', name: '编辑规则组', component: './system/rule-set-form', hideInMenu: true },
      { path: '/system/checkin-audit-logs', name: '签到审计日志', component: './system/checkin-audit-logs' },
      { path: '/system/log', name: '操作日志', component: './system/log' },
      { path: '/system/analytics', name: '用户行为分析', component: './system/analytics' },
      { path: '/system/online-users', name: '在线用户', component: './system/online-users' },
    ],
  },
  // 个人设置（不显示在菜单中）
  {
    path: '/account',
    hideInMenu: true,
    routes: [
      { path: '/account', redirect: '/account/settings' },
      { path: '/account/settings', name: '个人设置', component: './account/settings' },
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
