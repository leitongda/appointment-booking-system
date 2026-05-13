import { PropsWithChildren, useEffect, useRef, useState } from 'react';
import Taro from '@tarojs/taro';
// 占位组件引用：确保 Taro 生成对应的 WXML 模板
// NutUI Switch 组件内部使用了 checkbox，需要显式引用以生成 tmpl_0_24
import { View, Checkbox, CheckboxGroup, Label, Radio, RadioGroup } from '@tarojs/components';
// NutUI 样式按需加载 - 通过 babel-plugin-import 自动导入
// 详情见 babel.config.js
import './app.less';
import { initTracker, getTracker, STORAGE_KEYS, createStoreContext } from '@hospital/shared';
import { setHttpClient, createTaroAdapter, storeApi, authApi, tenantApi } from '@hospital/api';
import { validateStoreConfig, getStoreId, getStoreCode } from '@/utils/store';
import { setTenantStatus } from '@/hooks/useTenantGuard';
import {
  initThemeFromStore,
  getCurrentTheme,
  getThemeStyleObject,
  registerThemeRouteSync,
  subscribeThemeChange,
} from '@/utils/theme';
import { initFontMode } from '@/utils/fontMode';
import { clearAuthSession, getRefreshToken, getToken, updateAccessToken } from '@/utils/auth';

// API 配置
// TARO_APP_API_URL 应该是完整的 API 基础 URL，如 https://api.example.com/api/v1
// 开发环境使用本地服务器
const DEFAULT_API_HOST = process.env.NODE_ENV === 'production' 
  ? 'https://api.example.com' 
  : 'http://127.0.0.1:9000';
console.log("🚀 ~ DEFAULT_API_HOST:", DEFAULT_API_HOST)
const DEFAULT_API_PATH = '/api/v1';
console.log("🚀 ~ DEFAULT_API_PATH:", DEFAULT_API_PATH)

// 完整的 API 基础 URL
const apiBaseUrl = process.env.TARO_APP_API_URL || `${DEFAULT_API_HOST}${DEFAULT_API_PATH}`;
console.log("🚀 ~ process.env.TARO_APP_API_URL:", process.env.TARO_APP_API_URL)
console.log("🚀 ~ apiBaseUrl:", apiBaseUrl)

const STORE_ID_EXCLUDE_PATHS = ['/stores/by-code/', '/auth/', '/analytics/'];
const SKIP_AUTH_REFRESH_PATHS = ['/auth/refresh', '/auth/wechat/', '/stores/by-code/', '/analytics/'];

let refreshPromise: Promise<void> | null = null;

const shouldSkipStoreId = (url = '') => STORE_ID_EXCLUDE_PATHS.some((path) => url.includes(path));
const shouldSkipAuthRefresh = (url = '') => SKIP_AUTH_REFRESH_PATHS.some((path) => url.includes(path));

const createRequestError = (message: string, code: number, data?: any, config?: any) => {
  const error = new Error(message);
  (error as any).code = code;
  (error as any).data = data;
  (error as any).config = config;
  return error;
};

const refreshAccessToken = async () => {
  if (refreshPromise) {
    return refreshPromise;
  }

  const refreshToken = getRefreshToken();
  if (!refreshToken) {
    clearAuthSession('expired');
    throw createRequestError('登录已失效，请重新登录', 401);
  }

  refreshPromise = (async () => {
    try {
      const result = await authApi.refreshToken(refreshToken);
      updateAccessToken({
        accessToken: result.accessToken,
        refreshToken: result.refreshToken,
      });
    } catch (error) {
      clearAuthSession('expired');
      throw error;
    } finally {
      refreshPromise = null;
    }
  })();

  return refreshPromise;
};

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
  taroAdapter.interceptors.request.use(async (config: any) => {
    const relativeUrl = config._relativeUrl || config.url;
    config._relativeUrl = relativeUrl;

    const token = getToken();
    console.log(`🔐 [请求拦截器] URL: ${config.url}, Token: ${token ? token.substring(0, 20) + '...' : '无'}`);
    if (token && !config.header?.Authorization) {
      config.header = {
        ...config.header,
        Authorization: `Bearer ${token}`,
      };
    }

    if (shouldSkipAuthRefresh(relativeUrl)) {
      config._skipAuthRefresh = true;
    }

    const storeId = getStoreId();
    if (
      storeId &&
      config.url &&
      config.method === 'GET' &&
      !config._storeIdInjected &&
      !shouldSkipStoreId(relativeUrl)
    ) {
      if (!config.url.includes('store_id=')) {
        const separator = config.url.includes('?') ? '&' : '?';
        config.url = `${config.url}${separator}store_id=${storeId}`;
      }
      config._storeIdInjected = true;
    }

    return config;
  });

  taroAdapter.interceptors.response.use(async (response: any) => {
    const data = response.data;
    const config = response.config || {};
    const unauthorized =
      response.statusCode === 401 ||
      (data && typeof data === 'object' && data.code === 401);

    if (unauthorized) {
      if (config._skipAuthRefresh || config._retry) {
        clearAuthSession('expired');
        throw createRequestError(
          data?.detail || data?.message || '登录已失效，请重新登录',
          401,
          data,
          config
        );
      }

      if (!getRefreshToken()) {
        clearAuthSession('expired');
        throw createRequestError('登录已失效，请重新登录', 401, data, config);
      }

      await refreshAccessToken();

      const nextToken = getToken();
      if (!nextToken) {
        clearAuthSession('expired');
        throw createRequestError('登录已失效，请重新登录', 401, data, config);
      }

      if (!taroAdapter.request) {
        clearAuthSession('expired');
        throw createRequestError('请求适配器不支持重试', 500, data, config);
      }

      return taroAdapter.request({
        ...config,
        _retry: true,
        header: {
          ...(config.header || {}),
          Authorization: `Bearer ${nextToken}`,
        },
      });
    }

    if (!data || typeof data !== 'object') {
      return data;
    }

    if (response.statusCode >= 400) {
      // 租户暂停错误码识别
      const errorCode = data?.error_code;
      if (
        response.statusCode === 403 &&
        (errorCode === 'TENANT_SUSPENDED_WRITE' ||
          errorCode === 'TENANT_OVERDUE' ||
          errorCode === 'TENANT_DISABLED' ||
          errorCode === 'TENANT_TRIAL_EXPIRED')
      ) {
        Taro.showModal({
          title: '机构暂停服务',
          content: data.message || '该机构订阅已到期，暂不支持新预约/支付，请联系机构续费。',
          showCancel: false,
          confirmText: '我知道了',
        });
      }
      throw createRequestError(
        data.detail || data.message || '请求失败',
        response.statusCode,
        data,
        config
      );
    }

    if (data.code && (data.code < 200 || data.code >= 300)) {
      throw createRequestError(data.message || '请求失败', data.code, data.data, config);
    }

    if ('total' in data && typeof data.total === 'number' && 'data' in data) {
      return {
        data: data.data,
        total: data.total,
        success: true,
        page: data.page ?? 1,
        pageSize: data.pageSize ?? data.page_size ?? 10,
      };
    }

    if ('code' in data && 'data' in data) {
      return data.data;
    }

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

    const bootstrap = async () => {
      validateStoreConfig();

      const storeId = getStoreId();
      const storeCode = getStoreCode();
      const cachedStoreContext = Taro.getStorageSync(STORAGE_KEYS.STORE_CONTEXT);
      let storeTheme: string | undefined;
      let effectiveStoreId = storeId || cachedStoreContext?.storeId || '';

      if (storeCode) {
        try {
          const store = await storeApi.getByCode(storeCode);
          Taro.setStorageSync(STORAGE_KEYS.STORE_CONTEXT, createStoreContext(store));
          storeTheme = store.themeStyle;
          effectiveStoreId = store.id || effectiveStoreId;

          // 并行获取租户公开状态，写入全局供 useTenantGuard 使用
          try {
            const tenantPublic = await tenantApi.getCurrentTenantPublic();
            setTenantStatus({
              status: tenantPublic.status,
              subscriptionEndAt: tenantPublic.subscriptionEndAt ?? null,
              isSubscriptionActive: tenantPublic.isSubscriptionActive,
            });
          } catch { /* 获取失败不阻断启动 */ }
        } catch (error) {
          console.error('加载门店主题失败:', error);
        }
      }

      if (!storeTheme && cachedStoreContext?.storeId === effectiveStoreId) {
        storeTheme = cachedStoreContext.storeTheme;
      }

      const themeConfig = initThemeFromStore(storeTheme, effectiveStoreId);
      console.log(`✓ 主题已初始化: ${themeConfig.primary}`);
      registerThemeRouteSync();
      setCurrentTheme(getCurrentTheme());

      const fontModeConfig = initFontMode();
      console.log(`✓ 字体模式已初始化: ${fontModeConfig.name}`);
    };

    bootstrap();
  }, []);

  useEffect(
    () =>
      subscribeThemeChange(({ themeName }) => {
        setCurrentTheme(themeName);
      }),
    []
  );

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

  return (
    <View className="app-root" style={getThemeStyleObject(currentTheme)}>
      {children}
      <TaroComponentPlaceholder />
    </View>
  );
}

export default App;
