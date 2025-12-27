import { PropsWithChildren, useEffect } from 'react';
import Taro from '@tarojs/taro';
import '@nutui/nutui-react-taro/dist/style.css';
import './app.less';
import { initTracker, getTracker, STORAGE_KEYS } from '@hospital/shared';
import { setHttpClient, createTaroAdapter } from '@hospital/api';
import { validateStoreConfig, getStoreId } from '@/utils/store';

/**
 * 获取 Token（小程序版本，使用 Taro Storage）
 */
const getToken = (): string | null => {
  try {
    return Taro.getStorageSync(STORAGE_KEYS.TOKEN) || null;
  } catch {
    return null;
  }
};

// API 配置
// TARO_APP_API_URL 应该是完整的 API 基础 URL，如 https://api.example.com/api/v1
// 开发环境使用本地服务器
const DEFAULT_API_HOST = process.env.NODE_ENV === 'production' 
  ? 'https://api.example.com' 
  : 'http://localhost:8000';
const DEFAULT_API_PATH = '/api/v1';

// 完整的 API 基础 URL
const apiBaseUrl = process.env.TARO_APP_API_URL || `${DEFAULT_API_HOST}${DEFAULT_API_PATH}`;

// 验证门店配置
validateStoreConfig();

// 设置 Taro 请求适配器（替换默认的 axios）
const taroAdapter = createTaroAdapter(Taro as any, {
  baseURL: apiBaseUrl,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 添加请求拦截器：自动添加 token 和 store_id
if (taroAdapter.interceptors) {
  taroAdapter.interceptors.request.use((config: any) => {
    // 1. 添加 Authorization token
    const token = getToken();
    if (token) {
      config.header = {
        ...config.header,
        Authorization: `Bearer ${token}`,
      };
    }
    
    // 2. 自动添加 store_id 到 URL 参数（多门店隔离）
    const storeId = getStoreId();
    if (storeId && config.url) {
      // 排除门店验证等不需要 store_id 的接口
      const excludePaths = ['/stores/by-code/', '/auth/', '/analytics/'];
      const shouldAddStoreId = !excludePaths.some(path => config.url.includes(path));
      
      if (shouldAddStoreId && config.method === 'GET') {
        // 对于 GET 请求，将 store_id 添加到 URL
        const separator = config.url.includes('?') ? '&' : '?';
        config.url = `${config.url}${separator}store_id=${storeId}`;
      }
    }
    
    return config;
  });
}

setHttpClient(taroAdapter);
console.log(`✓ 小程序 API 适配器已设置: ${apiBaseUrl}`);

// 初始化用户行为追踪器
// 小程序需要完整 URL（不走代理）
// Analytics API 路径基于 apiBaseUrl 构建
initTracker({
  apiBaseUrl: '',  // 使用空字符串，让 apiPath 包含完整 URL
  apiPath: `${apiBaseUrl}/analytics/batch`,
  platform: 'miniapp',
  enabled: true,
  enableInDev: true,
  batchSize: 10,
  batchInterval: 5000,
  debug: process.env.NODE_ENV === 'development',
});

function App({ children }: PropsWithChildren) {
  // 监听页面显示，追踪页面访问
  useEffect(() => {
    // 小程序路由监听
    const handleRouteChange = () => {
      const pages = Taro.getCurrentPages();
      if (pages.length > 0) {
        const currentPage = pages[pages.length - 1];
        const tracker = getTracker();
        if (tracker && currentPage) {
          const pagePath = '/' + currentPage.route;
          tracker.trackPageView(pagePath, currentPage.config?.navigationBarTitleText || '');
        }
      }
    };

    // 初始追踪
    handleRouteChange();

    // 由于 Taro 没有全局路由监听，我们在每个页面的 useDidShow 中追踪
    // 这里只处理初始页面
  }, []);

  return children;
}

export default App;

