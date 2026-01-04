/**
 * 代理配置
 * @doc https://umijs.org/docs/guides/proxy
 */

// const target_url = 'http://localhost:8000'; // 本地开发环境
const target_url = 'https://yy.aicm.online'; // 本地开发环境

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

