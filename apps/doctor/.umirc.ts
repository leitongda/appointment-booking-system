/*
 * @Author: Lei TongDa ebian123@qq.com
 * @Date: 2025-11-27 12:23:44
 * @LastEditors: Lei TongDa ebian123@qq.com
 * @LastEditTime: 2025-12-15 15:29:22
 * @FilePath: /appointment-booking-system/apps/doctor/.umirc.ts
 * @Description: 
 * 
 * Copyright (c) 2025 by ${git_name_email}, All Rights Reserved. 
 */
/*
 * @Author: Lei TongDa ebian123@qq.com
 * @Date: 2025-11-27 12:23:44
 * @LastEditors: Lei TongDa ebian123@qq.com
 * @LastEditTime: 2025-12-15 15:29:20
 * @FilePath: /appointment-booking-system/apps/doctor/.umirc.ts
 * @Description: 
 * 
 * Copyright (c) 2025 by ${git_name_email}, All Rights Reserved. 
 */
import { defineConfig } from 'umi';

const { 
  API_BASE_URL = '/api/v1', 
  PROXY_TARGET = 'http://localhost:9000',
  WS_URL = '',  // WebSocket URL，为空时自动从当前页面推断
} = process.env;

// Tauri 桌面壳分支：desktop:dev / desktop:build 脚本注入 TAURI_DESKTOP=1 时切 hash 路由
// （与 apps/admin/config/config.ts 同一策略：整页跳转经 utils/hardNavigate 适配）。
// web 构建不注入该变量，路由模式不变。
const TAURI_DESKTOP = process.env.TAURI_DESKTOP === '1';

export default defineConfig({
  // 定义全局环境变量
  define: {
    'process.env.API_BASE_URL': API_BASE_URL,
    'process.env.WS_URL': WS_URL,
  },
  // 路由 history 模式：web 默认 browser；Tauri 桌面壳用 hash
  history: TAURI_DESKTOP ? { type: 'hash' } : { type: 'browser' },
  npmClient: 'pnpm',
  plugins: [
    '@umijs/plugins/dist/antd',
    '@umijs/plugins/dist/initial-state',
    '@umijs/plugins/dist/model',
    '@umijs/plugins/dist/request',
    '@umijs/plugins/dist/access',
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
    { path: '/leave-request', name: '停诊调班', icon: 'ExceptionOutlined', component: '@/pages/leave-request' },
    { path: '/attendance', name: '我的考勤', icon: 'ClockCircleOutlined', component: '@/pages/attendance/my-records' },
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
    { path: '/follow-up', name: '诊后随访', icon: 'HeartOutlined', routes: [
      { path: '/follow-up', redirect: '/follow-up/tasks' },
      { path: '/follow-up/tasks', name: '随访任务', component: '@/pages/follow-up/tasks' },
      { path: '/follow-up/records', name: '随访记录', component: '@/pages/follow-up/records' },
    ]},
    { path: '/statistics', name: '数据统计', icon: 'BarChartOutlined', component: '@/pages/statistics' },
    { path: '/rules', name: '预约规则', icon: 'SafetyCertificateOutlined', component: '@/pages/rules' },
    { path: '/message', name: '消息中心', icon: 'BellOutlined', component: '@/pages/message' },
    { path: '/profile', name: '个人资料', component: '@/pages/profile', hideInMenu: true },
    { path: '/settings/notification', name: '通知设置', icon: 'SettingOutlined', component: '@/pages/settings/notification-settings' },
  ],
  links: [
    { rel: 'manifest', href: '/manifest.json' },
  ],
  metas: [
    { name: 'theme-color', content: '#1677ff' },
  ],
  proxy: {
    '/api': { target: PROXY_TARGET, changeOrigin: true },
  },
});

