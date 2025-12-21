/**
 * 代理配置
 * @doc https://umijs.org/docs/guides/proxy
 */
export default {
  dev: {
    '/api': {
      target: 'http://localhost:8000',
      changeOrigin: true,
      pathRewrite: { '^/api': '/api' },
    },
    '/uploads': {
      target: 'http://localhost:8000',
      changeOrigin: true,
    },
  },
  test: {
    '/api': {
      target: 'http://localhost:8000',
      changeOrigin: true,
      pathRewrite: { '^/api': '/api' },
    },
    '/uploads': {
      target: 'http://localhost:8000',
      changeOrigin: true,
    },
  },
  pre: {
    '/api': {
      target: 'http://localhost:8000',
      changeOrigin: true,
      pathRewrite: { '^/api': '/api' },
    },
    '/uploads': {
      target: 'http://localhost:8000',
      changeOrigin: true,
    },
  },
};

