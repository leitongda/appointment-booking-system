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
    // 开启持久化缓存，提升二次编译速度
    // 详情: https://docs.taro.zone/docs/config-detail#cache
    cache: {
      enable: true,
    },
    mini: {
      // 生产环境禁用 source map 以减小包体积
      enableSourceMap: process.env.NODE_ENV !== 'production',
      // 生产环境开启代码压缩
      minifyXML: {
        collapseWhitespace: true,
      },
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
            generateScopedName: process.env.NODE_ENV === 'production' 
              ? '[hash:base64:5]'  // 生产环境使用更短的类名
              : '[name]__[local]___[hash:base64:5]',
          },
        },
      },
      // Sass 配置：导入 NutUI 变量文件
      sass: {
        resource: [
          path.resolve(__dirname, '..', 'node_modules', '@nutui', 'nutui-react-taro', 'dist', 'styles', 'variables.scss'),
        ],
      },
      // CSS 优化配置
      miniCssExtractPluginOption: {
        ignoreOrder: true,
      },
      // Webpack 配置优化
      webpackChain(chain) {
        // 调整 performance 配置
        // 微信小程序分包后，主包限制是 2MB，单个分包限制是 2MB
        // 对于共享公共代码的小程序，入口点包含所有公共 chunks 是正常现象
        // 将警告阈值调高到 800KB，避免不必要的警告干扰开发
        chain.performance
          .maxAssetSize(800 * 1024) // 800 KiB
          .maxEntrypointSize(800 * 1024) // 800 KiB
          .hints(process.env.NODE_ENV === 'production' ? 'warning' : false);

        // 优化 splitChunks 配置，更细粒度地拆分 vendors
        chain.optimization.splitChunks({
          chunks: 'all',
          maxInitialRequests: Infinity,
          minSize: 20000,
          cacheGroups: {
            // NutUI 组件库单独打包
            nutui: {
              name: 'nutui',
              test: /[\\/]node_modules[\\/]@nutui[\\/]/,
              priority: 20,
            },
            // Taro 相关依赖单独打包
            taro: {
              name: 'taro',
              test: /[\\/]node_modules[\\/]@tarojs[\\/]/,
              priority: 15,
            },
            // React 单独打包
            react: {
              name: 'react',
              test: /[\\/]node_modules[\\/](react|react-dom|scheduler)[\\/]/,
              priority: 12,
            },
            // 其他 node_modules 依赖
            vendors: {
              name: 'vendors',
              test: /[\\/]node_modules[\\/]/,
              priority: 10,
            },
          },
        });

        // 生产环境额外优化
        if (process.env.NODE_ENV === 'production') {
          // 优化模块 ID，减小输出大小
          chain.optimization.set('moduleIds', 'deterministic');
          chain.optimization.set('chunkIds', 'deterministic');
        }
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


