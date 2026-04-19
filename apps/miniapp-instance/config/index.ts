import { defineConfig, type UserConfigExport } from '@tarojs/cli';
import path from 'path';
import { writeFileSync } from 'fs';
import { resolve } from 'path';

// Webpack plugin to write build-info.json after compilation
class BuildInfoPlugin {
  apply(compiler) {
    compiler.hooks.done.tap('BuildInfoPlugin', (stats) => {
      const templateCode = process.env.TARO_APP_TEMPLATE_CODE || 'modern-general';
      const templateVersion = process.env.TARO_APP_TEMPLATE_VERSION || '1.0.0';
      const instanceId = process.env.TARO_APP_MINIAPP_INSTANCE_ID || '';

      const buildInfo = {
        templateCode,
        templateVersion,
        instanceId,
        buildTime: new Date().toISOString(),
        buildDuration: `${(stats.endTime - stats.startTime / 1000).toFixed(1)}s`,
        buildTool: 'taro@4.1.9',
        webpackHash: stats.hash,
      };

      const outputPath = resolve(__dirname, '..', 'dist', 'build-info.json');
      try {
        writeFileSync(outputPath, JSON.stringify(buildInfo, null, 2));
      } catch (error) {
        console.warn('[BuildInfoPlugin] Failed to write build-info.json:', error.message);
      }
    });
  }
}

export default defineConfig(async () => {
  const baseConfig: UserConfigExport = {
    projectName: 'hospital-miniapp-instance',
    date: '2026-1-1',
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
    alias: {
      '@': path.resolve(__dirname, '..', 'src'),
      'axios': path.resolve(__dirname, '..', 'src', 'utils', 'empty-axios.ts'),
      'jsencrypt': path.resolve(__dirname, '..', 'src', 'utils', 'empty-module.ts'),
      '@ant-design/pro-components': path.resolve(__dirname, '..', 'src', 'utils', 'empty-module.ts'),
      'antd': path.resolve(__dirname, '..', 'src', 'utils', 'empty-module.ts'),
      '@ant-design/icons': path.resolve(__dirname, '..', 'src', 'utils', 'empty-module.ts'),
    },
    defineConstants: {
      'process.env.TARO_APP_API_URL': JSON.stringify(process.env.TARO_APP_API_URL || ''),
      'process.env.TARO_APP_STORE_ID': JSON.stringify(process.env.TARO_APP_STORE_ID || ''),
      'process.env.TARO_APP_STORE_CODE': JSON.stringify(process.env.TARO_APP_STORE_CODE || ''),
      'process.env.TARO_APP_STORE_NAME': JSON.stringify(process.env.TARO_APP_STORE_NAME || ''),
      'process.env.TARO_APP_TEMPLATE_CODE': JSON.stringify(process.env.TARO_APP_TEMPLATE_CODE || 'modern-general'),
      'process.env.TARO_APP_TEMPLATE_VERSION': JSON.stringify(process.env.TARO_APP_TEMPLATE_VERSION || '1.0.0'),
      'process.env.TARO_APP_TENANT_CODE': JSON.stringify(process.env.TARO_APP_TENANT_CODE || ''),
      'process.env.TARO_APP_MINIAPP_INSTANCE_ID': JSON.stringify(process.env.TARO_APP_MINIAPP_INSTANCE_ID || ''),
    },
    copy: {
      patterns: [
        { from: 'src/assets/tabbar/', to: 'dist/assets/tabbar/' },
      ],
      options: {},
    },
    framework: 'react',
    compiler: {
      type: 'webpack5',
      prebundle: { enable: false },
    },
    cache: {
      enable: process.env.NODE_ENV === 'production',
    },
    mini: {
      enableSourceMap: process.env.NODE_ENV !== 'production',
      minifyXML: { collapseWhitespace: true },
      compile: {
        include: [
          (modulePath: string) => modulePath.includes('@hospital/api'),
          (modulePath: string) => modulePath.includes('@hospital/shared'),
          (modulePath: string) => modulePath.includes('packages/api'),
          (modulePath: string) => modulePath.includes('packages/shared'),
        ],
        exclude: [],
      },
      postcss: {
        pxtransform: { enable: true, config: {} },
        cssModules: {
          enable: true,
          config: {
            namingPattern: 'module',
            generateScopedName: process.env.NODE_ENV === 'production'
              ? '[hash:base64:5]'
              : '[name]__[local]___[hash:base64:5]',
          },
        },
      },
      sass: {
        resource: [
          path.resolve(__dirname, '..', 'node_modules', '@nutui', 'nutui-react-taro', 'dist', 'styles', 'variables.scss'),
        ],
      },
      miniCssExtractPluginOption: { ignoreOrder: true },
      webpackChain(chain) {
        // 添加 BuildInfoPlugin
        chain.plugin('build-info').use(BuildInfoPlugin);
        const reactPath = path.resolve(__dirname, '..', 'node_modules', 'react');
        chain.resolve.alias.set('react', reactPath);
        chain.resolve.alias.set('react/jsx-runtime', path.resolve(reactPath, 'jsx-runtime.js'));
        chain.resolve.alias.set('react/jsx-dev-runtime', path.resolve(reactPath, 'jsx-dev-runtime.js'));
        chain.performance
          .maxAssetSize(800 * 1024)
          .maxEntrypointSize(800 * 1024)
          .hints(process.env.NODE_ENV === 'production' ? 'warning' : false);
        chain.merge({
          ignoreWarnings: [
            (warning: any) => {
              const msg = warning?.message || '';
              return msg.includes('CaseSensitiveModulesWarning') && msg.includes('@nutui/nutui-react-taro');
            },
            (warning: any) => {
              const msg = warning?.message || '';
              return msg.includes('Deprecation Warning') && msg.includes('@nutui/nutui-react-taro');
            },
          ],
        });
      },
    } as any,
    h5: {
      publicPath: '/',
      staticDirectory: 'static',
      postcss: {
        autoprefixer: { enable: true, config: {} },
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
