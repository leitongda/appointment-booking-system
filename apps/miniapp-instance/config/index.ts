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

        // 确保从 @hospital/shared 引用的组件也能正确解析 Taro/NutUI 依赖
        // Taro weapp 构建时将 @tarojs/components alias 到 plugin-platform-weapp/dist/components-react
        // 但 webpack 从 shared 包上下文解析时找不到 plugin-platform-weapp，需要显式 alias
        const miniappNm = path.resolve(__dirname, '..', 'node_modules');
        chain.resolve.alias.set('@tarojs/plugin-platform-weapp', path.resolve(miniappNm, '@tarojs/plugin-platform-weapp'));
        chain.resolve.alias.set('@nutui/nutui-react-taro', path.resolve(miniappNm, '@nutui/nutui-react-taro'));
        chain.resolve.alias.set('@hospital/api', path.resolve(miniappNm, '@hospital/api'));

        chain.performance
          .maxAssetSize(800 * 1024)
          .maxEntrypointSize(800 * 1024)
          .hints(process.env.NODE_ENV === 'production' ? 'warning' : false);
        chain.set('ignoreWarnings', [
          /CaseSensitiveModulesWarning[\s\S]*@nutui\/nutui-react-taro/,
          /Deprecation Warning[\s\S]*@nutui\/nutui-react-taro[\s\S]*Sass @import/,
        ]);

        // 兜底方案：通过 webpack plugin 直接过滤 compilation.warnings
        // 确保即使 ignoreWarnings 被 Taro 覆盖，警告也能被过滤
        class SuppressNutUIWarningsPlugin {
          apply(compiler: any) {
            compiler.hooks.compilation.tap('SuppressNutUIWarnings', (compilation: any) => {
              compilation.hooks.afterSeal.tap('SuppressNutUIWarnings', () => {
                compilation.warnings = compilation.warnings.filter((w: any) => {
                  const msg = w?.message || '';
                  if (msg.includes('CaseSensitiveModulesWarning') && msg.includes('@nutui')) return false;
                  if (msg.includes('Deprecation Warning') && msg.includes('@nutui') && msg.includes('Sass @import')) return false;
                  return true;
                });
              });
            });
          }
        }
        chain.plugin('suppress-nutui-warnings').use(SuppressNutUIWarningsPlugin);
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
