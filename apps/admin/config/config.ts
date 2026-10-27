/*
 * @Author: Lei TongDa ebian123@qq.com
 * @Date: 2025-12-16 23:35:00
 * @LastEditors: Lei TongDa ebian123@qq.com
 * @LastEditTime: 2026-01-03 10:30:00
 * @FilePath: /appointment-booking-system/apps/admin/config/config.ts
 * @Description: umi 装配入口；具体配置已按子领域拆分至 constants/ layout/ webpack/ build/ proxy/ routes/。
 *
 * Copyright (c) 2025 by ${git_name_email}, All Rights Reserved.
 */
import path from 'path';
import { defineConfig } from '@umijs/max';

import { APP_TITLE } from './constants/app';
import { AMAP_KEY, AMAP_SERVICE_HOST, API_BASE_URL, REACT_APP_ENV } from './constants/env';
import layout from './layout';
import routes from './routes';
import proxy from './proxy';
import codeSplitting from './build/codeSplitting';
import mfsu from './build/mfsu';
import targets from './build/targets';
import chainWebpack from './webpack';

// Tauri 桌面壳分支：desktop:dev / desktop:build 脚本注入 TAURI_DESKTOP=1。
// 桌面壳选 hash 路由是保守选择：生产态由自定义协议（tauri://localhost /
// http://tauri.localhost）加载静态 dist，Tauri 资产协议对未命中路径会回退
// index.html，browser history 深链刷新其实也能恢复；但 admin 有多处 pathname
// 直用与整页 href 跳转，hash 不依赖资产协议回退行为、跨平台语义最可控
// （跳转经 utils/hardNavigate、路径记录经 currentRoutePath 适配）。web 构建
// 不注入该变量，路由模式不变。
const TAURI_DESKTOP = process.env.TAURI_DESKTOP === '1';

export default defineConfig({
  // 路径别名配置
  alias: {
    '@config': path.resolve(__dirname),
  },

  // 定义全局变量
  define: {
    'process.env.API_BASE_URL': API_BASE_URL,
    'process.env.AMAP_SERVICE_HOST': AMAP_SERVICE_HOST,
  },

  // 外部脚本注入（高德地图 JS SDK 2.0）
  headScripts: AMAP_KEY
    ? [{ src: `https://webapi.amap.com/maps?v=2.0&key=${AMAP_KEY}`, defer: true }]
    : [],

  // 构建产物文件名加 hash（注：这是 dist 产物 hash 选项，不是路由 history 模式）
  hash: true,

  // 路由 history 模式：web 默认 browser；Tauri 桌面壳（TAURI_DESKTOP=1）用 hash
  history: TAURI_DESKTOP ? { type: 'hash' } : { type: 'browser' },

  // umi 内置功能
  antd: {},
  access: {},
  model: {},
  initialState: {},
  request: {},

  // 布局配置（构建期）
  layout,

  // 路由配置
  routes,

  // 代理配置（按环境装配）
  proxy: proxy[REACT_APP_ENV as keyof typeof proxy],

  // npm 客户端
  npmClient: 'pnpm',

  // 开发配置
  mfsu,

  // 构建目标
  targets,

  // 修复 esbuild helpers 冲突
  esbuildMinifyIIFE: true,

  // 网页标题
  title: APP_TITLE,

  // favicon
  favicons: ['/favicon.ico'],

  // 点击组件配置
  clickToComponent: {},

  // 代码分割
  codeSplitting,

  // Webpack 链式配置（仅生产环境注入 gzip + splitChunks）
  chainWebpack,

  // PWA manifest + 主题色
  links: [
    { rel: 'manifest', href: '/manifest.json' },
  ],
  metas: [
    { name: 'theme-color', content: '#1677ff' },
  ],
});
