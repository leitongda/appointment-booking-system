import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';
import Sitemap from 'vite-plugin-sitemap';
import path from 'node:path';

const routes = [
  '/products',
  '/experience',
  '/pricing',
  '/login',
  '/register',
];

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  return {
    plugins: [
      react(),
      tailwindcss(),
      Sitemap({
        hostname: 'https://appointment.example.com',
        dynamicRoutes: routes,
        exclude: ['/console', '/profile'],
      }),
    ],
    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src'),
      },
    },
    server: {
      proxy: {
        '/api': {
          target: env.PROXY_TARGET || 'http://localhost:9000',
          changeOrigin: true,
        },
      },
    },
  };
});
