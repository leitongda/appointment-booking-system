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
  antd: {},
  model: {},
  request: {},
  access: {},
  initialState: {},
  layout: {
    title: '医生工作台',
    locale: false,
  },
  routes: [
    { path: '/login', component: '@/pages/login', layout: false },
    { path: '/', redirect: '/dashboard' },
    { path: '/dashboard', name: '工作台', icon: 'DashboardOutlined', component: '@/pages/dashboard' },
    { path: '/schedule', name: '我的排班', icon: 'CalendarOutlined', component: '@/pages/schedule' },
    { path: '/appointment', name: '预约管理', icon: 'UnorderedListOutlined', routes: [
      { path: '/appointment', redirect: '/appointment/today' },
      { path: '/appointment/today', name: '今日预约', component: '@/pages/appointment/today' },
      { path: '/appointment/history', name: '历史预约', component: '@/pages/appointment/history' },
    ]},
    { path: '/consultation', name: '就诊管理', icon: 'MedicineBoxOutlined', component: '@/pages/consultation' },
    { path: '/medical-record', name: '病历管理', icon: 'FileTextOutlined', routes: [
      { path: '/medical-record', redirect: '/medical-record/list' },
      { path: '/medical-record/list', name: '病历列表', component: '@/pages/medical-record/list' },
      { path: '/medical-record/create', name: '填写病历', component: '@/pages/medical-record/form', hideInMenu: true },
    ]},
    { path: '/statistics', name: '数据统计', icon: 'BarChartOutlined', component: '@/pages/statistics' },
  ],
  proxy: {
    '/api': { target: 'http://localhost:8000', changeOrigin: true },
  },
});

