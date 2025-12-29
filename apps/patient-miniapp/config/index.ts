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
    plugins: ['@tarojs/plugin-framework-react', '@tarojs/plugin-html'],
    // 小程序环境不支持的库替换为空模块
    // 1. jsencrypt - 依赖 Web Crypto API，小程序不支持
    // 2. @ant-design/pro-components 和 antd - PC端组件库，小程序不需要
    // 3. react-dom - 在 @hospital/shared 导出的 PC 组件中使用，需要提供空的 flushSync
    alias: {
      '@': path.resolve(__dirname, '..', 'src'),
      'jsencrypt': path.resolve(__dirname, '..', 'src', 'utils', 'empty-module.ts'),
      '@ant-design/pro-components': path.resolve(__dirname, '..', 'src', 'utils', 'empty-antd.ts'),
      'antd': path.resolve(__dirname, '..', 'src', 'utils', 'empty-antd.ts'),
      '@ant-design/icons': path.resolve(__dirname, '..', 'src', 'utils', 'empty-antd.ts'),
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
    // 使用 webpack5 编译器并禁用 prebundle
    // 禁用 prebundle 以解决 NutUI 图标样式加载问题
    // 详情: https://github.com/NutUI/nutui-react/issues/1889
    compiler: {
      type: 'webpack5',
      prebundle: {
        enable: false,
      },
    },
    mini: {
      compile: {
        include: [],
        exclude: [],
      },
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

