/**
 * 代理配置
 * @doc https://umijs.org/docs/guides/proxy
 */

// 从环境变量读取代理目标，默认为本地开发环境
const PROXY_TARGET = process.env.PROXY_TARGET || 'http://localhost:8000';

export default {
  dev: {
    '/api': {
      target: PROXY_TARGET,
      changeOrigin: true,
      secure: false,
      pathRewrite: { '^/api': '/api' },
    },
    '/uploads': {
      target: PROXY_TARGET,
      changeOrigin: true,
      secure: false,
    },
    '/_AMapService': {
      target: PROXY_TARGET,
      changeOrigin: true,
      secure: false,
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

