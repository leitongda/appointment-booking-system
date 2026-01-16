import { PropsWithChildren, useEffect, useRef, useState } from 'react';
import Taro from '@tarojs/taro';
// 占位组件引用：确保 Taro 生成对应的 WXML 模板
// NutUI Switch 组件内部使用了 checkbox，需要显式引用以生成 tmpl_0_24
import { View, Checkbox, CheckboxGroup, Label, Radio, RadioGroup } from '@tarojs/components';
// NutUI 样式按需加载 - 通过 babel-plugin-import 自动导入
// 详情见 babel.config.js
import './app.less';
import { initTracker, getTracker, STORAGE_KEYS } from '@hospital/shared';
import { setHttpClient, createTaroAdapter } from '@hospital/api';
import { validateStoreConfig, getStoreId } from '@/utils/store';
import { initThemeFromStore, getCurrentTheme, getThemeClass } from '@/utils/theme';
import { initFontMode } from '@/utils/fontMode';

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
  : 'http://127.0.0.1:8000';
console.log("🚀 ~ DEFAULT_API_HOST:", DEFAULT_API_HOST)
const DEFAULT_API_PATH = '/api/v1';
console.log("🚀 ~ DEFAULT_API_PATH:", DEFAULT_API_PATH)

// 完整的 API 基础 URL
const apiBaseUrl = process.env.TARO_APP_API_URL || `${DEFAULT_API_HOST}${DEFAULT_API_PATH}`;
console.log("🚀 ~ process.env.TARO_APP_API_URL:", process.env.TARO_APP_API_URL)
console.log("🚀 ~ apiBaseUrl:", apiBaseUrl)

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
    console.log(`🔐 [请求拦截器] URL: ${config.url}, Token: ${token ? token.substring(0, 20) + '...' : '无'}`);
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
  
  // 添加响应拦截器：解析服务端统一返回格式
  // 注意：这里直接返回解包后的数据，而不是整个 response 对象
  taroAdapter.interceptors.response.use((response: any) => {
    const data = response.data;
    
    // 如果 data 不是对象，直接返回 data
    if (!data || typeof data !== 'object') {
      return data;
    }
    
    // 处理 HTTP 错误状态码
    if (response.statusCode >= 400) {
      const message = data.detail || data.message || '请求失败';
      const error = new Error(message);
      (error as any).code = response.statusCode;
      (error as any).data = data;
      throw error;
    }
    
    // 处理业务错误（code 不是 2xx 成功状态码）
    if (data.code && (data.code < 200 || data.code >= 300)) {
      const error = new Error(data.message || '请求失败');
      (error as any).code = data.code;
      (error as any).data = data.data;
      throw error;
    }
    
    // 分页响应：包含 total 字段，直接返回解包后的格式
    if ('total' in data && typeof data.total === 'number' && 'data' in data) {
      return {
        data: data.data,
        total: data.total,
        success: true,
        page: data.page ?? 1,
        pageSize: data.pageSize ?? data.page_size ?? 10,
      };
    }
    
    // 统一响应格式：包含 code 和 data 字段，直接返回内部 data
    if ('code' in data && 'data' in data) {
      return data.data;
    }
    
    // 其他情况直接返回 data
    return data;
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

/**
 * 占位组件：确保 Taro 为 NutUI 内部使用的原生组件生成 WXML 模板
 * 
 * 背景：NutUI 的 Switch 等组件内部使用了微信小程序原生组件（如 checkbox）
 * 但 Taro 在编译时可能无法识别这些间接依赖，导致 base.wxml 中缺少对应模板
 * 通过在这里显式使用这些组件，可以确保 Taro 生成完整的模板
 * 
 * 错误示例：Template `tmpl_0_24` not found (24 对应 checkbox 组件)
 */
function TaroComponentPlaceholder() {
  // 使用隐藏样式，确保组件被 Taro 识别但不影响页面展示
  // 注意：不能使用条件渲染，否则可能被 tree-shaking 优化掉
  return (
    <View style={{ position: 'absolute', left: '-9999px', width: 0, height: 0, overflow: 'hidden' }}>
      <CheckboxGroup>
        <Label><Checkbox value="placeholder" /></Label>
      </CheckboxGroup>
      <RadioGroup>
        <Label><Radio value="placeholder" /></Label>
      </RadioGroup>
    </View>
  );
}

function App({ children }: PropsWithChildren) {
  // 使用 useRef 确保初始化只执行一次
  const isInitialized = useRef(false);
  // 主题状态
  const [currentTheme, setCurrentTheme] = useState(() => getCurrentTheme());

  // 初始化配置 - 只在运行时执行一次
  useEffect(() => {
    if (isInitialized.current) return;
    isInitialized.current = true;

    // 验证门店配置
    validateStoreConfig();

    // 初始化主题（从门店配置加载）
    const themeConfig = initThemeFromStore();
    console.log(`✓ 主题已初始化: ${themeConfig.primary}`);
    setCurrentTheme(getCurrentTheme());

    // 初始化字体模式（从本地存储读取用户偏好）
    const fontModeConfig = initFontMode();
    console.log(`✓ 字体模式已初始化: ${fontModeConfig.name}`);
  }, []);

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

  // 获取主题对应的 CSS 类名
  const themeClass = getThemeClass(currentTheme);

  return (
    <View className={`app-root theme-${themeClass}`}>
      {children}
      <TaroComponentPlaceholder />
    </View>
  );
}

export default App;

