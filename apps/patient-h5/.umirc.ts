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

