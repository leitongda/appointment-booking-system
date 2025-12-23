import { defineConfig } from '@umijs/max';
import routes from './routes';
import proxy from './proxy';

const { 
  REACT_APP_ENV = 'dev', 
  AMAP_KEY = '', 
  TINYMCE_API_KEY = '',
  API_BASE_URL = '/api/v1',  // API 基础路径，支持动态配置
} = process.env;

export default defineConfig({
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

  // 网页标题
  title: '医院挂号管理系统',

  // favicon
  favicons: ['/favicon.ico'],
});
