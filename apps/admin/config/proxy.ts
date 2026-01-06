/*
 * @Author: Lei TongDa ebian123@qq.com
 * @Date: 2025-12-03 09:32:33
 * @LastEditors: Lei TongDa ebian123@qq.com
 * @LastEditTime: 2026-01-06 21:48:54
 * @FilePath: /appointment-booking-system/apps/admin/config/proxy.ts
 * @Description: 
 * 
 * Copyright (c) 2026 by ${git_name_email}, All Rights Reserved. 
 */
/**
 * 代理配置
 * @doc https://umijs.org/docs/guides/proxy
 */

// 从环境变量读取代理目标，默认为本地开发环境
const PROXY_TARGET = process.env.PROXY_TARGET || 'http://localhost:8000';
console.log("🚀 ~ PROXY_TARGET:", PROXY_TARGET)

export default {
  dev: {
    '/api': {
      target: PROXY_TARGET,
      changeOrigin: true,
      pathRewrite: { '^/api': '/api' },
    },
    '/uploads': {
      target: PROXY_TARGET,
      changeOrigin: true,
    },
    '/_AMapService': {
      target: PROXY_TARGET,
      changeOrigin: true,
    },
  },
  test: {
    '/api': {
      target: PROXY_TARGET,
      changeOrigin: true,
      pathRewrite: { '^/api': '/api' },
    },
    '/uploads': {
      target: PROXY_TARGET,
      changeOrigin: true,
    },
  },
  pre: {
    '/api': {
      target: PROXY_TARGET,
      changeOrigin: true,
      pathRewrite: { '^/api': '/api' },
    },
    '/uploads': {
      target: PROXY_TARGET,
      changeOrigin: true,
    },
  },
};

