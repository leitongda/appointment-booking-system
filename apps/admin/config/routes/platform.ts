/**
 * 平台管理（SaaS 超管域）
 *
 * 子菜单：
 *   - 租户管理（canTenant）
 *   - 订阅计划（canTenantPlans）
 *   - 小程序平台（canMiniappPlatform）：公司 / 支付配置 / 实例 / 模板 / 构建 / 发布
 *
 * 顶层 access: canPlatformManagement
 */
const platform = [
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
        path: '/platform/announcement',
        name: '平台公告',
        icon: 'notification',
        access: 'canPlatformAnnouncement',
        routes: [
          { path: '/platform/announcement', redirect: '/platform/announcement/list' },
          { path: '/platform/announcement/list', name: '公告列表', component: './platform/platform-announcement' },
          { path: '/platform/announcement/create', name: '发布公告', component: './platform/platform-announcement-form', hideInMenu: true },
          { path: '/platform/announcement/:id/edit', name: '编辑公告', component: './platform/platform-announcement-form', hideInMenu: true },
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
];

export default platform;
