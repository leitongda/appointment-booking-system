/*
 * @Author: Lei TongDa ebian123@qq.com
 * @Date: 2025-12-16 23:35:00
 * @LastEditors: Lei TongDa ebian123@qq.com
 * @LastEditTime: 2026-01-03 10:30:00
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
import { APP_TITLE } from './appConfig';

const {
  REACT_APP_ENV = 'dev',
  API_BASE_URL = '/api/v1',  // API 基础路径，支持动态配置
} = process.env;

export default defineConfig({
  // 路径别名配置
  alias: {
    '@config': path.resolve(__dirname),
  },

  // 定义全局变量
  define: {
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
    title: APP_TITLE,
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
    siderMenuType: 'sub',
    splitMenus: false,
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
  title: APP_TITLE,

  // favicon
  favicons: ['/favicon.ico'],

  // 点击组件配置
  clickToComponent: {},

  // 代码分割优化 - 使用 depPerChunk 策略将每个 npm 包单独打包
  codeSplitting: {
    jsStrategy: 'depPerChunk',
    jsStrategyOptions: {
      // 大于 50KB 的包单独打包
      minSize: 50000,
    },
  },

  // Webpack 链式配置
  chainWebpack(config) {
    // 生产环境优化
    if (process.env.NODE_ENV === 'production') {
      // gzip 预压缩
      config.plugin('compression-gzip').use(CompressionPlugin, [{
        algorithm: 'gzip',
        test: /\.(js|css|html|svg)$/,
        threshold: 10240, // 仅压缩大于 10KB 的文件
        minRatio: 0.8,
        filename: '[path][base].gz',
      }]);

      // 优化 splitChunks 配置
      config.optimization.splitChunks({
        chunks: 'all',
        minSize: 20000,
        minChunks: 1,
        maxAsyncRequests: 30,
        maxInitialRequests: 30,
        automaticNameDelimiter: '-',
        cacheGroups: {
          // antd 相关库单独打包
          antd: {
            name: 'antd-lib',
            test: /[\\/]node_modules[\\/](antd|@ant-design\/icons)[\\/]/,
            priority: 30,
            chunks: 'all',
          },
          // @ant-design/pro-components 单独打包
          proComponents: {
            name: 'pro-components-lib',
            test: /[\\/]node_modules[\\/]@ant-design[\\/]pro-/,
            priority: 25,
            chunks: 'all',
          },
          // @ant-design/charts 和 @antv 相关单独打包（图表库）
          charts: {
            name: 'charts-lib',
            test: /[\\/]node_modules[\\/](@ant-design[\\/]charts|@ant-design[\\/]plots|@antv)[\\/]/,
            priority: 20,
            chunks: 'async', // 仅异步加载
          },
          // React 相关
          react: {
            name: 'react-lib',
            test: /[\\/]node_modules[\\/](react|react-dom|scheduler)[\\/]/,
            priority: 40,
            chunks: 'all',
          },
          // 其他常用工具库
          utils: {
            name: 'utils-lib',
            test: /[\\/]node_modules[\\/](lodash|lodash-es|dayjs|moment)[\\/]/,
            priority: 15,
            chunks: 'all',
          },
          // 通用第三方库
          vendors: {
            name: 'vendors',
            test: /[\\/]node_modules[\\/]/,
            priority: 10,
            chunks: 'all',
            minChunks: 2,
          },
          // 公共组件
          common: {
            name: 'common',
            minChunks: 2,
            priority: 5,
            reuseExistingChunk: true,
          },
        },
      });
    }
  },
});
