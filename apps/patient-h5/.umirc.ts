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

export default defineConfig({
  npmClient: 'pnpm',
  plugins: [
    '@umijs/plugins/dist/model',
    '@umijs/plugins/dist/request',
  ],
  model: {},
  request: {},
  routes: [
    {
      path: '/',
      component: '@/layouts/index',
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
        { path: '/records', component: '@/pages/records' },
        { path: '/records/:id', component: '@/pages/records/detail' },
        { path: '/profile', component: '@/pages/profile' },
        { path: '/profile/patient', component: '@/pages/profile/patient' },
        { path: '/profile/patient/edit', component: '@/pages/profile/patient/edit' },
        { path: '/message', component: '@/pages/message' },
        { path: '/feedback', component: '@/pages/feedback' },
      ],
    },
    { path: '/login', component: '@/pages/login' },
  ],
  proxy: {
    '/api': {
      target: 'http://localhost:8000',
      changeOrigin: true,
    },
  },
});

