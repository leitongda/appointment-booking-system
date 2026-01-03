/*
 * @Author: Lei TongDa ebian123@qq.com
 * @Date: 2025-12-16 23:35:00
 * @LastEditors: Lei TongDa ebian123@qq.com
 * @LastEditTime: 2026-01-02 22:51:10
 * @FilePath: /appointment-booking-system/apps/admin/config/config.ts
 * @Description: 
 * 
 * Copyright (c) 2025 by ${git_name_email}, All Rights Reserved. 
 */
import { defineConfig } from '@umijs/max';
import path from 'path';
import CompressionPlugin from 'compression-webpack-plugin';
import routes from './routes';
import proxy from './proxy';

const {
  REACT_APP_ENV = 'dev',
  AMAP_KEY = '',
  TINYMCE_API_KEY = '',
  API_BASE_URL = '/api/v1',  // API 基础路径，支持动态配置
} = process.env;

export default defineConfig({
  // 路径别名配置
  alias: {
    '@config': path.resolve(__dirname),
  },

  // 高德地图 SDK
  headScripts: AMAP_KEY ? [
    {
      src: `https://webapi.amap.com/maps?v=2.0&key=${AMAP_KEY}&plugin=AMap.PlaceSearch,AMap.Geocoder,AMap.AutoComplete`,
      async: true,
    },
  ] : [],

  // 定义全局变量
  define: {
    'process.env.TINYMCE_API_KEY': TINYMCE_API_KEY,
    'process.env.API_BASE_URL': API_BASE_URL,
  },

  // 使用 hash 路由
  hash: true,

  // antd 配置
  antd: {},

  // 权限配置
  access: {},

  // 数据流配置
  model: {},

  // 初始状态配置
  initialState: {},

  // 请求配置
  request: {},

  // 布局配置
  layout: {
    title: '医院挂号管理系统',
    locale: false,


    navTheme: 'light',
    colorPrimary: '#722ED1',
    layout: 'mix',
    contentWidth: 'Fluid',
    fixedHeader: true,
    fixSiderbar: true,
    pwa: true,
    logo: 'https://gw.alipayobjects.com/zos/rmsportal/KDpgvguMpGfqaHPjicRK.svg',
    token: {},
    siderMenuType: 'group',
    splitMenus: true,


  },

  // 路由配置
  routes,

  // 代理配置
  proxy: proxy[REACT_APP_ENV as keyof typeof proxy],

  // npm 客户端
  npmClient: 'pnpm',

  // 开发配置
  mfsu: {
    strategy: 'normal',
    exclude: ['react-image-crop'],
  },

  // 构建配置
  targets: {
    chrome: 80,
  },

  // 修复 esbuild helpers 冲突
  esbuildMinifyIIFE: true,

  // 网页标题
  title: '医院挂号管理系统',

  // favicon
  favicons: ['/favicon.ico'],

  // 点击组件配置
  clickToComponent: {},

  // 代码分割优化
  codeSplitting: {
    jsStrategy: 'granularChunks',
  },

  // Webpack 链式配置
  chainWebpack(config) {
    // 生产环境启用 gzip 预压缩
    if (process.env.NODE_ENV === 'production') {
      config.plugin('compression-gzip').use(CompressionPlugin, [{
        algorithm: 'gzip',
        test: /\.(js|css|html|svg)$/,
        threshold: 10240, // 仅压缩大于 10KB 的文件
        minRatio: 0.8,
        filename: '[path][base].gz',
      }]);
    }
  },
});
