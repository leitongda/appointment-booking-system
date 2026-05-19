/**
 * 旧路径重定向
 *
 * 三大块：
 *   - /configuration/*：旧的「配置中心」入口，已分散到 organization/medical-config、medical-services/consultation-fee、system/* 等
 *   - /monitoring/*：旧的监控入口，已迁移到 /system/monitoring/*；analytics 迁移至 /content-center/statistics
 *   - /operations/system/settings/*：旧的运营中心系统设置入口，已迁移到 organization/medical-config、system/*
 *
 * 这些路由全部 `hideInMenu: true`，且必须放在新菜单路由之后、`*` 通配之前。
 */
const redirects = [
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
];

export default redirects;
