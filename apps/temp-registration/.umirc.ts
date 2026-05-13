import { defineConfig } from 'umi';

const { API_BASE_URL = '/api/v1' } = process.env;

export default defineConfig({
  // 定义全局环境变量
  define: {
    'process.env.API_BASE_URL': API_BASE_URL,
  },
  npmClient: 'pnpm',
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
    { path: '/', component: '@/pages/index' },
    { path: '/doctor', component: '@/pages/doctor' },
    { path: '/time-slot', component: '@/pages/time-slot' },
    { path: '/patient-info', component: '@/pages/patient-info' },
    { path: '/confirm', component: '@/pages/confirm' },
    { path: '/queue', component: '@/pages/queue' },
  ],
  proxy: {
    '/api': {
      target: 'http://localhost:9000',
      changeOrigin: true,
    },
  },
});



