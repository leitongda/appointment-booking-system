/*
 * @Author: Lei TongDa ebian123@qq.com
 * @Date: 2025-11-27 12:16:57
 * @LastEditors: Lei TongDa ebian123@qq.com
 * @LastEditTime: 2025-12-15 15:29:18
 * @FilePath: /appointment-booking-system/apps/patient-h5/.umirc.ts
 * @Description: 
 * 
 * Copyright (c) 2025 by ${git_name_email}, All Rights Reserved. 
 */
import { defineConfig } from 'umi';

const { API_BASE_URL = '/api/v1', PROXY_TARGET = 'http://localhost:9000' } = process.env;

export default defineConfig({
  // 定义全局环境变量
  define: {
    'process.env.API_BASE_URL': API_BASE_URL,
  },
  npmClient: 'pnpm',
  mfsu: {
    exclude: [/dayjs/],
  },
  plugins: [
    '@umijs/plugins/dist/model',
    '@umijs/plugins/dist/request',
  ],
  model: {},
  request: {},
  // PostCSS plugins for Tailwind CSS
  extraPostCSSPlugins: [
    require('tailwindcss'),
    require('autoprefixer'),
  ],
  // Import global CSS files
  styles: [
    '/src/global.css',
    '/src/theme.css',
  ],
  routes: [
    {
      path: '/',
      component: '@/components/MainLayout/index',
      routes: [
        { path: '/', redirect: '/home' },
        { path: '/home', component: '@/pages/home' },
        { path: '/department', component: '@/pages/department' },
        { path: '/department/:id', component: '@/pages/department/detail' },
        { path: '/doctor', component: '@/pages/doctor' },
        { path: '/doctor/:id', component: '@/pages/doctor/detail' },
        { path: '/booking/:doctorId', component: '@/pages/booking' },
        { path: '/booking/confirm', component: '@/pages/booking/confirm' },
        { path: '/appointment', component: '@/pages/appointment' },
        { path: '/appointment/:id', component: '@/pages/appointment/detail' },
        { path: '/waitlist', component: '@/pages/waitlist' },
        { path: '/waitlist/:id', component: '@/pages/waitlist/detail' },
        { path: '/records', component: '@/pages/records' },
        { path: '/records/:id', component: '@/pages/records/detail' },
        { path: '/follow-up/tasks', component: '@/pages/follow-up/tasks' },
        { path: '/follow-up/tasks/:id', component: '@/pages/follow-up/task-detail' },
        { path: '/follow-up/records', component: '@/pages/follow-up/records' },
        { path: '/follow-up/report', component: '@/pages/follow-up/report' },
        { path: '/follow-up/report/:taskId', component: '@/pages/follow-up/report' },
        { path: '/profile', component: '@/pages/profile' },
        { path: '/profile/patient', component: '@/pages/profile/patient' },
        { path: '/profile/patient/edit', component: '@/pages/profile/patient/edit' },
        { path: '/profile/change-password', component: '@/pages/profile/change-password' },
        { path: '/profile/notification-settings', component: '@/pages/profile/notification-settings' },
        { path: '/message', component: '@/pages/message' },
        { path: '/feedback', component: '@/pages/feedback' },
      ],
    },
    { path: '/login', component: '@/pages/login' },
    { path: '/login/forgot-password', component: '@/pages/login/forgot-password' },
    { path: '/login/email-login', component: '@/pages/login/email-login' },
    { path: '/register', component: '@/pages/register' },
    { path: '/search', component: '@/pages/search' },
    { path: '/settings', component: '@/pages/settings' },
  ],
  links: [
    { rel: 'manifest', href: '/manifest.json' },
  ],
  metas: [
    { name: 'theme-color', content: '#1677ff' },
  ],
  proxy: {
    '/api': {
      target: PROXY_TARGET,
      changeOrigin: true,
    },
  },
});
