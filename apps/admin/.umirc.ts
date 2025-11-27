import { defineConfig } from 'umi';

export default defineConfig({
  npmClient: 'pnpm',
  plugins: [
    '@umijs/plugins/dist/antd',
    '@umijs/plugins/dist/model',
    '@umijs/plugins/dist/request',
    '@umijs/plugins/dist/access',
    '@umijs/plugins/dist/initial-state',
    '@umijs/plugins/dist/layout',
  ],
  antd: {
    configProvider: {},
    dark: false,
    compact: false,
  },
  model: {},
  request: {},
  access: {},
  initialState: {},
  layout: {
    title: '医院挂号管理系统',
    locale: false,
  },
  routes: [
    {
      path: '/login',
      component: '@/pages/login',
      layout: false,
    },
    {
      path: '/',
      redirect: '/dashboard',
    },
    {
      path: '/dashboard',
      name: '仪表盘',
      icon: 'DashboardOutlined',
      component: '@/pages/dashboard',
    },
    {
      path: '/department',
      name: '科室管理',
      icon: 'ApartmentOutlined',
      component: '@/pages/department',
    },
    {
      path: '/doctor',
      name: '医生管理',
      icon: 'UserOutlined',
      routes: [
        { path: '/doctor', redirect: '/doctor/list' },
        { path: '/doctor/list', name: '医生列表', component: '@/pages/doctor/list' },
        { path: '/doctor/create', name: '新增医生', component: '@/pages/doctor/form', hideInMenu: true },
        { path: '/doctor/:id', name: '医生详情', component: '@/pages/doctor/detail', hideInMenu: true },
        { path: '/doctor/:id/edit', name: '编辑医生', component: '@/pages/doctor/form', hideInMenu: true },
      ],
    },
    {
      path: '/schedule',
      name: '排班管理',
      icon: 'CalendarOutlined',
      routes: [
        { path: '/schedule', redirect: '/schedule/list' },
        { path: '/schedule/list', name: '排班列表', component: '@/pages/schedule/list' },
        { path: '/schedule/template', name: '排班模板', component: '@/pages/schedule/template' },
      ],
    },
    {
      path: '/appointment',
      name: '预约管理',
      icon: 'ScheduleOutlined',
      routes: [
        { path: '/appointment', redirect: '/appointment/list' },
        { path: '/appointment/list', name: '预约列表', component: '@/pages/appointment/list' },
        { path: '/appointment/:id', name: '预约详情', component: '@/pages/appointment/detail', hideInMenu: true },
      ],
    },
    {
      path: '/patient',
      name: '患者管理',
      icon: 'TeamOutlined',
      component: '@/pages/patient',
    },
    {
      path: '/content',
      name: '内容管理',
      icon: 'FileTextOutlined',
      routes: [
        { path: '/content', redirect: '/content/news' },
        { path: '/content/news', name: '新闻管理', component: '@/pages/content/news' },
        { path: '/content/notice', name: '公告管理', component: '@/pages/content/notice' },
        { path: '/content/banner', name: '轮播图', component: '@/pages/content/banner' },
      ],
    },
    {
      path: '/system',
      name: '系统设置',
      icon: 'SettingOutlined',
      routes: [
        { path: '/system', redirect: '/system/role' },
        { path: '/system/role', name: '角色管理', component: '@/pages/system/role' },
        { path: '/system/admin', name: '管理员', component: '@/pages/system/admin' },
        { path: '/system/settings', name: '系统配置', component: '@/pages/system/settings' },
        { path: '/system/log', name: '操作日志', component: '@/pages/system/log' },
      ],
    },
  ],
  proxy: {
    '/api': {
      target: 'http://localhost:8000',
      changeOrigin: true,
    },
  },
});

