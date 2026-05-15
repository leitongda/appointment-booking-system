/**
 * 路由配置 — 业务流程导向分组（方案 A）
 *
 * 一级菜单：
 *   仪表盘 / 平台管理 / 医疗服务 / 组织架构 / 运营中心 / 系统管理
 *
 * @name 配置名称
 * @icon 菜单图标
 * @access 权限配置
 * @hideInMenu 隐藏菜单
 */
export default [
  // ==================== 认证页面 ====================
  { path: '/login', layout: false, component: './login' },
  { path: '/tenant-suspended', layout: false, component: './tenant-suspended' },

  // ==================== 仪表盘 ====================
  { path: '/dashboard', name: '仪表盘', icon: 'dashboard', component: './dashboard', access: 'canDashboard' },

  // ==================== 平台管理（SaaS 超管）====================
  {
    path: '/platform',
    name: '平台管理',
    icon: 'cloudServer',
    access: 'canPlatformManagement',
    routes: [
      { path: '/platform', redirect: '/platform/tenant' },
      {
        path: '/platform/tenant',
        name: '租户管理',
        icon: 'team',
        access: 'canTenant',
        routes: [
          { path: '/platform/tenant', redirect: '/platform/tenant/list' },
          { path: '/platform/tenant/list', name: '租户列表', component: './tenant' },
          { path: '/platform/tenant/create', name: '新增租户', component: './tenant/form', hideInMenu: true },
          { path: '/platform/tenant/:id', name: '租户详情', component: './tenant/detail', hideInMenu: true },
          { path: '/platform/tenant/:id/edit', name: '编辑租户', component: './tenant/form', hideInMenu: true },
        ],
      },
      {
        path: '/platform/tenant/plans',
        name: '订阅计划',
        icon: 'profile',
        access: 'canTenantPlans',
        routes: [
          { path: '/platform/tenant/plans', component: './tenant/plans' },
          { path: '/platform/tenant/plans/create', name: '新增计划', component: './tenant/plan-form', hideInMenu: true },
          { path: '/platform/tenant/plans/:id/edit', name: '编辑计划', component: './tenant/plan-form', hideInMenu: true },
        ],
      },
      {
        path: '/platform/miniapp-platform',
        name: '小程序平台',
        icon: 'appstore',
        access: 'canMiniappPlatform',
        routes: [
          { path: '/platform/miniapp-platform', redirect: '/platform/miniapp-platform/company' },
          {
            path: '/platform/miniapp-platform/company',
            name: '公司管理',
            routes: [
              { path: '/platform/miniapp-platform/company', component: './miniapp-platform/company' },
              { path: '/platform/miniapp-platform/company/create', name: '新增公司', component: './miniapp-platform/company/form', hideInMenu: true },
              { path: '/platform/miniapp-platform/company/:id', name: '公司详情', component: './miniapp-platform/company/form', hideInMenu: true },
              { path: '/platform/miniapp-platform/company/:id/edit', name: '编辑公司', component: './miniapp-platform/company/form', hideInMenu: true },
            ],
          },
          {
            path: '/platform/miniapp-platform/payment-profile',
            name: '支付配置',
            routes: [
              { path: '/platform/miniapp-platform/payment-profile', component: './miniapp-platform/payment-profile' },
              { path: '/platform/miniapp-platform/payment-profile/create', name: '新增支付配置', component: './miniapp-platform/payment-profile/form', hideInMenu: true },
              { path: '/platform/miniapp-platform/payment-profile/:id', name: '支付配置详情', component: './miniapp-platform/payment-profile/form', hideInMenu: true },
              { path: '/platform/miniapp-platform/payment-profile/:id/edit', name: '编辑支付配置', component: './miniapp-platform/payment-profile/form', hideInMenu: true },
            ],
          },
          {
            path: '/platform/miniapp-platform/instance',
            name: '小程序实例',
            routes: [
              { path: '/platform/miniapp-platform/instance', component: './miniapp-platform/instance' },
              { path: '/platform/miniapp-platform/instance/create', name: '新增实例', component: './miniapp-platform/instance/form', hideInMenu: true },
              { path: '/platform/miniapp-platform/instance/:id', name: '实例详情', component: './miniapp-platform/instance/form', hideInMenu: true },
              { path: '/platform/miniapp-platform/instance/:id/edit', name: '编辑实例', component: './miniapp-platform/instance/form', hideInMenu: true },
            ],
          },
          {
            path: '/platform/miniapp-platform/template',
            name: '模板管理',
            component: './miniapp-platform/template/index',
          },
          {
            path: '/platform/miniapp-platform/build',
            name: '构建管理',
            component: './miniapp-platform/build/index',
          },
          {
            path: '/platform/miniapp-platform/release',
            name: '发布管理',
            component: './miniapp-platform/release/index',
          },
        ],
      },
    ],
  },

  // ==================== 医疗服务（核心业务域）====================
  {
    path: '/medical-services',
    name: '医疗服务',
    icon: 'medicineBox',
    access: 'canClinicalOperations',
    routes: [
      { path: '/medical-services', redirect: '/medical-services/doctor' },
      {
        path: '/medical-services/doctor',
        name: '医生管理',
        icon: 'user',
        access: 'canDoctor',
        routes: [
          { path: '/medical-services/doctor', redirect: '/medical-services/doctor/list' },
          { path: '/medical-services/doctor/list', name: '医生列表', component: './doctor/list' },
          { path: '/medical-services/doctor/booking-setting', name: '预约设置', component: './doctor/booking-setting' },
          { path: '/medical-services/doctor/booking-setting/create', name: '添加预约设置', component: './doctor/booking-setting-form', hideInMenu: true },
          { path: '/medical-services/doctor/booking-setting/:id/edit', name: '编辑预约设置', component: './doctor/booking-setting-form', hideInMenu: true },
          { path: '/medical-services/doctor/create', name: '新增医生', component: './doctor/form', hideInMenu: true },
          { path: '/medical-services/doctor/:id', name: '医生详情', component: './doctor/detail', hideInMenu: true },
          { path: '/medical-services/doctor/:id/edit', name: '编辑医生', component: './doctor/form', hideInMenu: true },
        ],
      },
      {
        path: '/medical-services/schedule',
        name: '排班管理',
        icon: 'calendar',
        access: 'canSchedule',
        routes: [
          { path: '/medical-services/schedule', redirect: '/medical-services/schedule/rule' },
          { path: '/medical-services/schedule/rule', name: '排班规则设置', component: './schedule/rule' },
          { path: '/medical-services/schedule/rule/create', name: '新增排班规则', component: './schedule/rule/form', hideInMenu: true },
          { path: '/medical-services/schedule/rule/:id/edit', name: '编辑排班规则', component: './schedule/rule/form', hideInMenu: true },
          { path: '/medical-services/schedule/list', name: '排班列表', component: './schedule/detail' },
          { path: '/medical-services/schedule/calendar', name: '排班日历', component: './schedule/calendar' },
          { path: '/medical-services/schedule/gantt', name: '排班甘特图', component: './schedule/gantt' },
          { path: '/medical-services/schedule/custom', name: '自定义排班', component: './schedule/custom' },
          { path: '/medical-services/schedule/custom/create', name: '添加自定义排班', component: './schedule/custom-form', hideInMenu: true },
          { path: '/medical-services/schedule/rest-day', name: '休息日设置', component: './schedule/rest-day' },
          { path: '/medical-services/schedule/rest-day/create', name: '添加休息日', component: './schedule/rest-day-form', hideInMenu: true },
          { path: '/medical-services/schedule/suspension', name: '停诊管理', component: './schedule/suspension' },
          { path: '/medical-services/schedule/leave-request', name: '停诊审核', component: './leave-request', access: 'canLeaveRequest' },
          { path: '/medical-services/schedule/statistics', name: '排班统计', component: './schedule/statistics' },
        ],
      },
      {
        path: '/medical-services/appointment',
        name: '预约管理',
        icon: 'schedule',
        access: 'canAppointment',
        routes: [
          { path: '/medical-services/appointment', redirect: '/medical-services/appointment/list' },
          { path: '/medical-services/appointment/list', name: '预约列表', component: './appointment/list' },
          { path: '/medical-services/appointment/queue', name: '签到队列', component: './appointment/queue' },
          { path: '/medical-services/appointment/statistics', name: '预约统计', component: './appointment/statistics' },
          { path: '/medical-services/appointment/:id', name: '预约详情', component: './appointment/detail', hideInMenu: true },
        ],
      },
      {
        path: '/medical-services/patient',
        name: '患者管理',
        icon: 'usergroupAdd',
        access: 'canPatient',
        routes: [
          { path: '/medical-services/patient', redirect: '/medical-services/patient/list' },
          { path: '/medical-services/patient/list', name: '患者列表', component: './user' },
          { path: '/medical-services/patient/:id', name: '患者详情', component: './user/detail', hideInMenu: true },
          { path: '/medical-services/patient/card/list', name: '就诊卡列表', component: './patient' },
          { path: '/medical-services/patient/card/:id', name: '就诊卡详情', component: './patient/detail', hideInMenu: true },
        ],
      },
      {
        path: '/medical-services/medical-record',
        name: '病历管理',
        icon: 'fileProtect',
        component: './medical-record',
        access: 'canMedicalRecord',
      },
      {
        path: '/medical-services/consultation-fee',
        name: '诊费管理',
        icon: 'dollarCircle',
        access: 'canConsultationFee',
        routes: [
          { path: '/medical-services/consultation-fee', redirect: '/medical-services/consultation-fee/types' },
          { path: '/medical-services/consultation-fee/types', name: '诊费类型', component: './system/consultation-fee-types' },
          { path: '/medical-services/consultation-fee/types/create', name: '新增诊费类型', component: './system/consultation-fee-type-form', hideInMenu: true },
          { path: '/medical-services/consultation-fee/types/:id/edit', name: '编辑诊费类型', component: './system/consultation-fee-type-form', hideInMenu: true },
          { path: '/medical-services/consultation-fee/templates', name: '诊费模板', component: './system/consultation-fee-templates' },
        ],
      },
    ],
  },

  // ==================== 组织架构 ====================
  {
    path: '/organization',
    name: '组织架构',
    icon: 'apartment',
    access: 'canOrganizationManagement',
    routes: [
      { path: '/organization', redirect: '/organization/store' },
      {
        path: '/organization/store',
        name: '门店管理',
        icon: 'shop',
        access: 'canStore',
        routes: [
          { path: '/organization/store', redirect: '/organization/store/list' },
          { path: '/organization/store/list', name: '门店列表', component: './store' },
          { path: '/organization/store/create', name: '新增门店', component: './store/form', hideInMenu: true },
          { path: '/organization/store/:id/edit', name: '编辑门店', component: './store/form', hideInMenu: true },
          { path: '/organization/store/:storeId/fee-types', name: '门店诊费类型', redirect: '/medical-services/consultation-fee/types', hideInMenu: true },
          { path: '/organization/store/:storeId/fee-templates', name: '门店诊费模板', redirect: '/medical-services/consultation-fee/templates', hideInMenu: true },
          { path: '/organization/store/:storeId/visit-type-config', name: '复诊规则配置', component: './store/visit-type-config', hideInMenu: true },
        ],
      },
      {
        path: '/organization/department',
        name: '科室管理',
        icon: 'build',
        access: 'canDepartment',
        routes: [
          { path: '/organization/department', redirect: '/organization/department/list' },
          { path: '/organization/department/list', name: '科室列表', component: './department' },
          { path: '/organization/department/create', name: '新增科室', component: './department/form', hideInMenu: true },
          { path: '/organization/department/:id/edit', name: '编辑科室', component: './department/form', hideInMenu: true },
        ],
      },
      {
        path: '/organization/medical-config',
        name: '医疗配置',
        icon: 'tool',
        access: 'canMedicalConfig',
        routes: [
          { path: '/organization/medical-config', redirect: '/organization/medical-config/booking-rules' },
          { path: '/organization/medical-config/booking-rules', name: '预约规则', icon: 'clockCircle', component: './system/settings', access: 'canBookingRules' },
          { path: '/organization/medical-config/booking-fields', name: '预约字段', icon: 'orderedList', component: './system/settings', access: 'canBookingFields' },
          { path: '/organization/medical-config/booking-notice', name: '预约须知', icon: 'fileDone', component: './system/booking-notice', access: 'canBookingNotice' },
          { path: '/organization/medical-config/patient-card', name: '就诊卡配置', icon: 'idcard', component: './system/settings', access: 'canPatientCardConfig' },
          {
            path: '/organization/medical-config/shift-types',
            name: '班次类型',
            icon: 'clockCircle',
            access: 'canShiftTypes',
            routes: [
              { path: '/organization/medical-config/shift-types', component: './system/shift-types' },
              { path: '/organization/medical-config/shift-types/create', name: '新增班次类型', component: './system/shift-type-form', hideInMenu: true },
              { path: '/organization/medical-config/shift-types/:id/edit', name: '编辑班次类型', component: './system/shift-type-form', hideInMenu: true },
            ],
          },
          {
            path: '/organization/medical-config/rule-sets',
            name: '规则组管理',
            icon: 'cluster',
            access: 'canRuleSets',
            routes: [
              { path: '/organization/medical-config/rule-sets', component: './system/rule-sets' },
              { path: '/organization/medical-config/rule-sets/create', name: '新增规则组', component: './system/rule-set-form', hideInMenu: true },
              { path: '/organization/medical-config/rule-sets/:id/edit', name: '编辑规则组', component: './system/rule-set-form', hideInMenu: true },
              { path: '/organization/medical-config/rule-sets/:id/audit', name: '变更历史', component: './system/rule-set-audit', hideInMenu: true },
            ],
          },
        ],
      },
      {
        path: '/organization/staff',
        name: '员工管理',
        icon: 'userSwitch',
        access: 'canUserManagement',
        routes: [
          { path: '/organization/staff', component: './system/user' },
          { path: '/organization/staff/create', name: '新增员工', component: './system/user-form', hideInMenu: true },
          { path: '/organization/staff/:id/edit', name: '编辑员工', component: './system/user-form', hideInMenu: true },
        ],
      },
    ],
  },

  // ==================== 运营中心 ====================
  {
    path: '/content-center',
    name: '运营中心',
    icon: 'notification',
    access: 'canContentOperations',
    routes: [
      { path: '/content-center', redirect: '/content-center/content' },
      {
        path: '/content-center/content',
        name: '内容管理',
        icon: 'fileText',
        access: 'canContent',
        routes: [
          { path: '/content-center/content', redirect: '/content-center/content/news' },
          { path: '/content-center/content/news', name: '新闻管理', component: './content/news' },
          { path: '/content-center/content/news/create', name: '发布新闻', component: './content/news-form', hideInMenu: true },
          { path: '/content-center/content/news/:id/edit', name: '编辑新闻', component: './content/news-form', hideInMenu: true },
          { path: '/content-center/content/notice', name: '公告管理', component: './content/notice' },
          { path: '/content-center/content/notice/create', name: '发布公告', component: './content/notice-form', hideInMenu: true },
          { path: '/content-center/content/notice/:id/edit', name: '编辑公告', component: './content/notice-form', hideInMenu: true },
          { path: '/content-center/content/banner', name: '轮播图', component: './content/banner' },
          { path: '/content-center/content/banner/create', name: '新增轮播图', component: './content/banner-form', hideInMenu: true },
          { path: '/content-center/content/banner/:id/edit', name: '编辑轮播图', component: './content/banner-form', hideInMenu: true },
        ],
      },
      {
        path: '/content-center/message',
        name: '消息管理',
        icon: 'bell',
        access: 'canMessage',
        routes: [
          { path: '/content-center/message', redirect: '/content-center/message/list' },
          { path: '/content-center/message/list', name: '消息列表', component: './message' },
          { path: '/content-center/message/create', name: '发送消息', component: './message/form', hideInMenu: true },
          { path: '/content-center/message/templates', name: '统一模板', component: './message/templates' },
          { path: '/content-center/message/recipient-rules', name: '收件人规则', component: './message/recipient-rules' },
        ],
      },
      {
        path: '/content-center/feedback',
        name: '用户反馈',
        icon: 'comment',
        component: './feedback',
        access: 'canFeedback',
      },
      {
        path: '/content-center/statistics',
        name: '数据统计',
        icon: 'lineChart',
        component: './system/analytics',
        access: 'canAnalytics',
      },
    ],
  },

  // ==================== 系统管理 ====================
  {
    path: '/system',
    name: '系统管理',
    icon: 'setting',
    access: 'canSystemManagement',
    routes: [
      { path: '/system', redirect: '/system/role' },
      {
        path: '/system/role',
        name: '角色权限',
        icon: 'safetyCertificate',
        access: 'canRoleManagement',
        routes: [
          { path: '/system/role', component: './system/role' },
          { path: '/system/role/create', name: '新增角色', component: './system/role-form', hideInMenu: true },
          { path: '/system/role/:id/edit', name: '编辑角色', component: './system/role-form', hideInMenu: true },
          { path: '/system/role/:id/permissions', name: '分配权限', component: './system/role-permissions', hideInMenu: true },
        ],
      },
      {
        path: '/system/config',
        name: '系统配置',
        icon: 'control',
        access: 'canSystemConfig',
        routes: [
          { path: '/system/config', redirect: '/system/config/hospital-info' },
          { path: '/system/config/hospital-info', name: '医院信息', icon: 'home', component: './system/settings', access: 'canHospitalInfo' },
          { path: '/system/config/wechat', name: '微信配置', icon: 'wechat', component: './system/settings', access: 'canWechatSettings' },
          { path: '/system/config/email-config', name: '邮件配置', icon: 'mail', component: './system/settings', access: 'canEmailConfig' },
          { path: '/system/config/image-config', name: '图片配置', icon: 'picture', component: './system/settings', access: 'canImageConfig' },
          {
            path: '/system/config/email-templates',
            name: '邮件模板',
            icon: 'form',
            access: 'canEmailTemplates',
            routes: [
              { path: '/system/config/email-templates', component: './system/email-templates' },
              { path: '/system/config/email-templates/create', name: '新增邮件模板', component: './system/email-template-form', hideInMenu: true },
              { path: '/system/config/email-templates/:id/edit', name: '编辑邮件模板', component: './system/email-template-form', hideInMenu: true },
            ],
          },
          { path: '/system/config/email-recipients', name: '邮件接收人', icon: 'contacts', component: './system/email-recipients', access: 'canEmailRecipients' },
        ],
      },
      {
        path: '/system/blacklist',
        name: '黑名单管理',
        icon: 'stop',
        component: './system/settings',
        access: 'canBlacklistSettings',
      },
      {
        path: '/system/monitoring',
        name: '系统监控',
        icon: 'monitor',
        access: 'canSystemMonitoring',
        routes: [
          { path: '/system/monitoring', redirect: '/system/monitoring/log' },
          { path: '/system/monitoring/log', name: '操作日志', icon: 'fileSearch', component: './system/log', access: 'canSystemLogs' },
          { path: '/system/monitoring/notification-logs', name: '通知日志', icon: 'alert', component: './system/notification-logs', access: 'canSystemLogs' },
          { path: '/system/monitoring/notification-quota', name: '通知配额', icon: 'alert', component: './system/notification-quota', access: 'canSystemLogs' },
          { path: '/system/monitoring/checkin-audit-logs', name: '签到审计', icon: 'audit', component: './system/checkin-audit-logs', access: 'canCheckinAuditLogs' },
          { path: '/system/monitoring/online-users', name: '在线用户', icon: 'team', component: './system/online-users', access: 'canOnlineUsers' },
        ],
      },
    ],
  },

  // ==================== 旧路径重定向 ====================
  {
    path: '/configuration',
    hideInMenu: true,
    routes: [
      { path: '/configuration', redirect: '/organization/medical-config/booking-rules' },
      { path: '/configuration/consultation-fee-types', redirect: '/medical-services/consultation-fee/types' },
      { path: '/configuration/consultation-fee-templates', redirect: '/medical-services/consultation-fee/templates' },
      { path: '/configuration/shift-types', redirect: '/organization/medical-config/shift-types' },
      { path: '/configuration/rule-sets', redirect: '/organization/medical-config/rule-sets' },
      { path: '/configuration/booking-rules', redirect: '/organization/medical-config/booking-rules' },
      { path: '/configuration/booking-fields', redirect: '/organization/medical-config/booking-fields' },
      { path: '/configuration/booking-notice', redirect: '/organization/medical-config/booking-notice' },
      { path: '/configuration/patient-card', redirect: '/organization/medical-config/patient-card' },
      { path: '/configuration/blacklist', redirect: '/system/blacklist' },
      { path: '/configuration/hospital-info', redirect: '/system/config/hospital-info' },
      { path: '/configuration/wechat', redirect: '/system/config/wechat' },
      { path: '/configuration/email-config', redirect: '/system/config/email-config' },
      { path: '/configuration/image-config', redirect: '/system/config/image-config' },
      { path: '/configuration/email-templates', redirect: '/system/config/email-templates' },
      { path: '/configuration/email-recipients', redirect: '/system/config/email-recipients' },
    ],
  },
  {
    path: '/monitoring',
    hideInMenu: true,
    routes: [
      { path: '/monitoring/log', redirect: '/system/monitoring/log' },
      { path: '/monitoring/notification-logs', redirect: '/system/monitoring/notification-logs' },
      { path: '/monitoring/notification-quota', redirect: '/system/monitoring/notification-quota' },
      { path: '/monitoring/checkin-audit-logs', redirect: '/system/monitoring/checkin-audit-logs' },
      { path: '/monitoring/online-users', redirect: '/system/monitoring/online-users' },
      { path: '/monitoring/analytics', redirect: '/content-center/statistics' },
    ],
  },
  {
    path: '/operations/system/settings',
    hideInMenu: true,
    routes: [
      { path: '/operations/system/settings', redirect: '/organization/medical-config/booking-rules' },
      { path: '/operations/system/settings/booking', redirect: '/organization/medical-config/booking-rules' },
      { path: '/operations/system/settings/blacklist', redirect: '/system/blacklist' },
      { path: '/operations/system/settings/wechat', redirect: '/system/config/wechat' },
      { path: '/operations/system/settings/base', redirect: '/system/config/hospital-info' },
    ],
  },
  {
    path: '/account',
    hideInMenu: true,
    routes: [
      { path: '/account', redirect: '/account/settings' },
      { path: '/account/settings', name: '个人设置', component: './account/settings' },
    ],
  },

  // ==================== 默认路由 ====================
  { path: '/', redirect: '/dashboard' },
  { path: '*', layout: false, component: './404' },
];
