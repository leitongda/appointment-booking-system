import { AvatarDropdown, AvatarName } from '@/components/RightContent';
import { FullscreenButton, NotificationButton, RefreshButton } from '@/components/HeaderActions';
import { getToken, removeToken, setStorage, STORAGE_KEYS, handleTokenExpired, initTracker, getTracker } from '@hospital/shared';
import { adminApi } from '@hospital/api';
import type { Settings as LayoutSettings } from '@ant-design/pro-components';
import type { RunTimeLayoutConfig, RequestConfig } from '@umijs/max';
import { history, useLocation } from '@umijs/max';
import { App, message } from 'antd';
import { useMemo } from 'react';
import defaultSettings from '../config/defaultSettings';
import { initApiConfig } from '@/utils/request';

const loginPath = '/login';

// 初始化 API 请求配置（拦截器）
initApiConfig();

// 初始化用户行为追踪器
// apiBaseUrl 使用空字符串，请求路径为 /api/v1/analytics/batch
// 开发环境会自动走代理（/api -> localhost:8000），避免 CORS 问题
initTracker({
  apiBaseUrl: '',
  platform: 'admin',
  enabled: true,
  enableInDev: true, // 开发环境也启用，方便测试
  batchSize: 10,
  batchInterval: 5000,
  debug: process.env.NODE_ENV === 'development',
});

/**
 * 页面过渡动画包装组件
 */
const PageTransitionWrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const location = useLocation();
  
  // 使用 pathname 作为 key，当路由变化时触发动画
  const animationKey = useMemo(() => location.pathname, [location.pathname]);
  
  return (
    <div key={animationKey} className="page-transition-wrapper">
      {children}
    </div>
  );
};

/**
 * rootContainer 配置 - 用 App 组件包裹应用
 * 这样可以使用 App.useApp() hooks (message, notification, modal)
 */
export function rootContainer(container: any) {
  return <App>{container}</App>;
}

// 门店信息类型
interface StoreInfo {
  id: string;
  name: string;
  logo?: string;
  themeStyle?: string;
}

/**
 * 获取初始状态
 * @see https://umijs.org/zh-CN/plugins/plugin-initial-state
 */
export async function getInitialState(): Promise<{
  settings?: Partial<LayoutSettings>;
  currentUser?: API.CurrentUser;
  currentStore?: StoreInfo;
  loading?: boolean;
  fetchUserInfo?: () => Promise<API.CurrentUser | undefined>;
}> {
  const fetchUserInfo = async () => {
    try {
      const currentUser = await adminApi.getCurrentAdmin();
      return currentUser as API.CurrentUser;
    } catch (error) {
      removeToken();
      history.push(loginPath);
    }
    return undefined;
  };

  const { location } = history;
  const token = getToken();

  // 如果是登录页面，不执行获取用户信息
  if (location.pathname !== loginPath && token) {
    const currentUser = await fetchUserInfo();
    
    // 从 localStorage 获取登录时保存的门店信息
    let currentStore: StoreInfo | undefined;
    try {
      const storeData = localStorage.getItem('currentStore');
      if (storeData) {
        currentStore = JSON.parse(storeData);
      }
    } catch (e) {
      console.error('Failed to parse store info', e);
    }
    
    return {
      fetchUserInfo,
      currentUser,
      currentStore,
      settings: defaultSettings as Partial<LayoutSettings>,
    };
  }

  return {
    fetchUserInfo,
    settings: defaultSettings as Partial<LayoutSettings>,
  };
}

/**
 * ProLayout 运行时配置
 * @doc https://procomponents.ant.design/components/layout
 */
export const layout: RunTimeLayoutConfig = ({ initialState }) => {
  return {
    actionsRender: () => [
      <RefreshButton key="refresh" />,
      <NotificationButton key="notification" />,
      <FullscreenButton key="fullscreen" />,
    ],
    avatarProps: {
      src: initialState?.currentUser?.avatar,
      title: <AvatarName />,
      render: (_, avatarChildren) => {
        return <AvatarDropdown>{avatarChildren}</AvatarDropdown>;
      },
    },
    waterMarkProps: {
      content: initialState?.currentUser?.name,
    },
    footerRender: () => (
      <div style={{ textAlign: 'center', padding: '16px 0', color: '#999' }}>
        医院挂号管理系统 ©{new Date().getFullYear()} 版权所有
      </div>
    ),
    onPageChange: () => {
      const { location } = history;
      const token = getToken();
      // 如果没有登录，重定向到登录页
      if (!token && location.pathname !== loginPath) {
        history.push(loginPath);
        return;
      }
      // 记录上次访问的页面路径（排除登录页、欢迎页、404页等特殊页面）
      const excludePaths = [loginPath, '/welcome', '/404', '/403', '/'];
      if (token && !excludePaths.includes(location.pathname)) {
        // 保存完整路径（包含 search 和 hash）
        const fullPath = location.pathname + (location.search || '') + (location.hash || '');
        setStorage(STORAGE_KEYS.LAST_PATH, fullPath);
      }
      
      // 追踪页面访问
      const tracker = getTracker();
      if (tracker) {
        tracker.trackPageView(location.pathname, document.title);
      }
    },
    // 无权限时重定向到仪表盘
    unAccessible: <div />,
    onUnAccessible: () => {
      history.replace('/dashboard');
    },
    menuHeaderRender: undefined,
    // 路由切换动画
    childrenRender: (children: React.ReactNode) => {
      return <PageTransitionWrapper>{children}</PageTransitionWrapper>;
    },
    ...initialState?.settings,
  };
};

/**
 * 请求配置
 * 注意：主要的请求/响应拦截逻辑在 @/utils/request.ts 中通过 @hospital/api 配置
 * 这里是 umi-request 的配置，作为备用
 * @doc https://umijs.org/docs/max/request
 */
export const request: RequestConfig = {
  timeout: 30000,
  requestInterceptors: [
    (config: any) => {
      const token = getToken();
      if (token) {
        config.headers = {
          ...config.headers,
          Authorization: `Bearer ${token}`,
        };
      }
      return config;
    },
  ],
  responseInterceptors: [
    (response: any) => {
      const { data, status } = response;

      // 处理 HTTP 401 或业务码 401（无效 Token）
      if (status === 401 || data?.code === 401) {
        handleTokenExpired(() => {
          message.error(data?.message || '登录已过期，请重新登录');
          history.push(loginPath);
        });
        return response;
      }

      // 处理业务码 403（无权限）
      if (data?.code === 403) {
        message.error(data?.message || '没有权限访问该资源');
        return response;
      }

      // 处理业务码 404（资源不存在）
      if (data?.code === 404) {
        message.error(data?.message || '请求的资源不存在');
        return response;
      }

      // 处理其他非 200 的业务错误码
      if (data?.code && data.code !== 200 && data.code >= 400) {
        message.error(data?.message || '请求失败');
        return response;
      }

      return response;
    },
  ],
};
