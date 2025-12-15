import { AvatarDropdown, AvatarName } from '@/components/RightContent';
import { FullscreenButton, NotificationButton, RefreshButton } from '@/components/HeaderActions';
import { getToken, removeToken } from '@hospital/shared';
import { adminApi } from '@hospital/api';
import type { Settings as LayoutSettings } from '@ant-design/pro-components';
import type { RunTimeLayoutConfig, RequestConfig } from '@umijs/max';
import { history, useLocation } from '@umijs/max';
import { App } from 'antd';
import { useMemo } from 'react';
import defaultSettings from '../config/defaultSettings';
import { initApiConfig } from '@/utils/request';

const loginPath = '/login';

// 初始化 API 请求配置（拦截器）
initApiConfig();

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

/**
 * 获取初始状态
 * @see https://umijs.org/zh-CN/plugins/plugin-initial-state
 */
export async function getInitialState(): Promise<{
  settings?: Partial<LayoutSettings>;
  currentUser?: API.CurrentUser;
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
    return {
      fetchUserInfo,
      currentUser,
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
      }
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

      // 401 未授权
      if (status === 401 || data?.code === 401) {
        removeToken();
        history.push(loginPath);
        return response;
      }

      return response;
    },
  ],
};
