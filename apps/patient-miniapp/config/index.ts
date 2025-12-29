import { defineConfig, type UserConfigExport } from '@tarojs/cli';
import path from 'path';

export default defineConfig(async (merge) => {
  const baseConfig: UserConfigExport = {
    projectName: 'hospital-patient-miniapp',
    date: '2024-1-1',
    designWidth: 375,
    deviceRatio: {
      640: 2.34 / 2,
      750: 1,
      375: 2,
      828: 1.81 / 2,
    },
    sourceRoot: 'src',
    outputRoot: 'dist',
    plugins: ['@tarojs/plugin-framework-react'],
    // 小程序不需要 jsencrypt（RSA 加密），将其替换为空模块
    // 这解决了 "Cannot read property 'crypto' of undefined" 错误
    alias: {
      '@': path.resolve(__dirname, '..', 'src'),
      'jsencrypt': path.resolve(__dirname, '..', 'src', 'utils', 'empty-module.ts'),
    },
    // 定义全局环境变量
    // 门店配置说明：
    // - TARO_APP_STORE_ID: 门店UUID，用于API请求过滤
    // - TARO_APP_STORE_CODE: 门店编码，用于显示和调试
    // - TARO_APP_STORE_NAME: 门店名称，用于页面显示
    // 构建示例: TARO_APP_STORE_ID=xxx TARO_APP_STORE_CODE=beijing TARO_APP_STORE_NAME=北京门店 pnpm build:weapp
    defineConstants: {
      'process.env.TARO_APP_API_URL': JSON.stringify(process.env.TARO_APP_API_URL || ''),
      'process.env.TARO_APP_STORE_ID': JSON.stringify(process.env.TARO_APP_STORE_ID || ''),
      'process.env.TARO_APP_STORE_CODE': JSON.stringify(process.env.TARO_APP_STORE_CODE || ''),
      'process.env.TARO_APP_STORE_NAME': JSON.stringify(process.env.TARO_APP_STORE_NAME || ''),
    },
    copy: {
      patterns: [],
      options: {},
    },
    framework: 'react',
    compiler: 'webpack5',
    mini: {
      postcss: {
        pxtransform: {
          enable: true,
          config: {},
        },
        cssModules: {
          enable: true,
          config: {
            namingPattern: 'module',
            generateScopedName: '[name]__[local]___[hash:base64:5]',
          },
        },
      },
    },
    h5: {
      publicPath: '/',
      staticDirectory: 'static',
      postcss: {
        autoprefixer: {
          enable: true,
          config: {},
        },
        cssModules: {
          enable: true,
          config: {
            namingPattern: 'module',
            generateScopedName: '[name]__[local]___[hash:base64:5]',
          },
        },
      },
    },
  };

  return baseConfig;
});

