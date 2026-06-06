/**
 * 系统管理
 *
 * 子菜单：
 *   - 角色权限（canRoleManagement）
 *   - 系统配置（canSystemConfig，含 hospital-info / wechat / email-config / image-config / email-templates / email-recipients）
 *   - 黑名单管理（canBlacklistSettings）
 *   - 系统监控（canSystemMonitoring，含 log / notification-logs / notification-quota / checkin-audit-logs / online-users）
 *   - 数据管理（canSystemMonitoring，含 import-export / backup）
 *
 * 顶层 access: canSystemManagement
 */
const system = [
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
          { path: '/system/config/sms', name: '短信通知', icon: 'message', component: './system/settings', access: 'canSmsSettings' },
          { path: '/system/config/security', name: '安全策略', icon: 'safety-certificate', component: './system/settings', access: 'canSecuritySettings' },
          { path: '/system/config/source-release', name: '号源释放', icon: 'clock-circle', component: './system/settings', access: 'canSourceReleaseSettings' },
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
      {
        path: '/system/data',
        name: '数据管理',
        icon: 'database',
        access: 'canSystemMonitoring',
        routes: [
          { path: '/system/data', redirect: '/system/data/import-export' },
          { path: '/system/data/import-export', name: '导入导出', icon: 'swap', component: './system/import-export' },
          { path: '/system/data/backup', name: '数据备份', icon: 'cloud', component: './system/data-backup' },
        ],
      },
    ],
  },
];

export default system;
