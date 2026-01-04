/*
 * @Author: Lei TongDa ebian123@qq.com
 * @Date: 2025-12-03 09:32:33
 * @LastEditors: Lei TongDa ebian123@qq.com
 * @LastEditTime: 2026-01-04 22:11:54
 * @FilePath: /appointment-booking-system/apps/admin/config/proxy.ts
 * @Description: 
 * 
 * Copyright (c) 2026 by ${git_name_email}, All Rights Reserved. 
 */
/**
 * 代理配置
 * @doc https://umijs.org/docs/guides/proxy
 */

const target_url = 'http://localhost:8000'; // 本地开发环境
// const target_url = 'https://yy.aicm.online'; // 本地开发环境

export default {
  dev: {
    '/api': {
      target: target_url,
      changeOrigin: true,
      pathRewrite: { '^/api': '/api' },
    },
    '/uploads': {
      target: target_url,
      changeOrigin: true,
    },
    '/_AMapService': {
      target: target_url,
      changeOrigin: true,
    },
  },
  test: {
    '/api': {
      target: target_url,
      changeOrigin: true,
      pathRewrite: { '^/api': '/api' },
    },
    '/uploads': {
      target: target_url,
      changeOrigin: true,
    },
  },
  pre: {
    '/api': {
      target: target_url,
      changeOrigin: true,
      pathRewrite: { '^/api': '/api' },
    },
    '/uploads': {
      target: target_url,
      changeOrigin: true,
    },
  },
};

