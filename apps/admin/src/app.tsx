import { AvatarDropdown, AvatarName } from '@/components/RightContent';
import { FullscreenButton, NotificationButton, RefreshButton, StoreSwitcher } from '@/components/HeaderActions';
import TenantSwitcher from '@/components/TenantSwitcher';
import TenantStatusBanner from '@/components/TenantStatusBanner';
import PageTransitionWrapper from '@/components/PageTransitionWrapper';
import { getToken, removeToken, setStorage, getStorage, removeStorage, STORAGE_KEYS, initCrossTabSync, isPublicEntryRoute, subscribeTenantSuspended, getTracker, recordRouteChange } from '@hospital/shared';
import type { MiniappStoreThemeValue } from '@hospital/shared';
import { adminApi } from '@hospital/api';
import type { Settings as LayoutSettings } from '@ant-design/pro-components';
import type { RunTimeLayoutConfig } from '@umijs/max';
import { history, useLocation } from '@umijs/max';
import { App, ConfigProvider, Modal, notification } from 'antd';
import { useEffect } from 'react';
import defaultSettings from '../config/defaultSettings';
import { APP_TITLE } from '@config/appConfig';
import { shadcnThemeConfig, getThemeConfig } from '@/themes';
import { processMenuData, computeParentOpenKeys } from '@/utils/menu';
import { handleCrossTabEvent } from '@/utils/crossTab';
import { initVisibilityAuthCheck } from '@/utils/visibilityAuth';
import { initApp } from '@/utils/initApp';
import { applySpacingCSSVariables, getSpacingMode } from '@/utils/spacing';
import { LOGIN_PATH } from '@/constants/paths';

// 初始化应用（API、追踪器、性能监控）
initApp();

// 门店信息类型
interface StoreInfo {
  id: string;
  name: string;
  logo?: string;
  themeStyle?: MiniappStoreThemeValue;
}

/**
 * rootContainer 配置 - 用 App 和 ConfigProvider 组件包裹应用
 */
export function rootContainer(container: any) {
  const { algorithm, tokenConfig } = getThemeConfig();

  if (typeof window !== 'undefined') {
    applySpacingCSSVariables(getSpacingMode());
  }

  initCrossTabSync(handleCrossTabEvent);
  initVisibilityAuthCheck();

  // 记录初始路由性能
  let routeStartTime = performance.now();
  let lastPathname = window.location.pathname;

  const _unlisten = history.listen(({ location }: any) => {
    const routeEndTime = performance.now();
    const routeDuration = routeEndTime - routeStartTime;

    const publicPaths = ['/login', '/404', '/403', '/tenant-suspended'];
    if (!publicPaths.includes(lastPathname)) {
      recordRouteChange(lastPathname, routeDuration);
    }

    routeStartTime = performance.now();
    lastPathname = location.pathname;
  });

  // const configProps = shadcnThemeConfig;

  return (
    <ConfigProvider
      theme={{
        algorithm,
        token: tokenConfig,
      }}
      // {...configProps}
    >
      <App>{container}</App>
    </ConfigProvider>
  );
}

/**
 * 获取初始状态
 */
export async function getInitialState(): Promise<{
  settings?: Partial<LayoutSettings>;
  currentUser?: API.CurrentUser;
  currentStore?: StoreInfo;
  userStores?: StoreInfo[];
  currentTenantId?: string;
  loading?: boolean;
  fetchUserInfo?: () => Promise<API.CurrentUser | undefined>;
}> {
  const fetchUserInfo = async () => {
    try {
      const currentUser = await adminApi.getCurrentAdmin();
      const user = currentUser as API.CurrentUser;
      if (!user.roleType) {
        user.roleType = 'admin';
      }
      return user;
    } catch (error: any) {
      if (error?.isUnauthorized?.()) return undefined;
      removeToken();
      history.push(LOGIN_PATH);
    }
    return undefined;
  };

  const { location } = history;
  const token = getToken();

  if (location.pathname !== LOGIN_PATH && token) {
    const currentUser = await fetchUserInfo();

    let currentStore: StoreInfo | undefined;
    try {
      const storeData = localStorage.getItem('hospital_current_store');
      if (storeData) {
        currentStore = JSON.parse(storeData);
      }
    } catch (e) {
      console.error('Failed to parse store info', e);
    }

    const currentTenantId = localStorage.getItem('hospital_current_tenant_id') || undefined;
    const userStores = currentUser?.stores || [];

    return {
      fetchUserInfo,
      currentUser,
      currentStore,
      userStores: userStores as any,
      currentTenantId,
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
 */
/* eslint-disable react-hooks/rules-of-hooks -- Umi RunTimeLayoutConfig 在 React 组件上下文中执行 */
export const layout: RunTimeLayoutConfig = ({ initialState, setInitialState }: any) => {
  const location = useLocation();
  const { currentStore } = initialState || {};

  useEffect(() => {
    if (!isPublicEntryRoute(location.pathname)) return;

    Modal.destroyAll();
    notification.destroy('tenant-change');
    notification.destroy('store-change');
  }, [location.pathname]);

  useEffect(() => {
    if (isPublicEntryRoute(location.pathname)) return;
    const unsubscribe = subscribeTenantSuspended(() => {
      if (location.pathname !== '/tenant-suspended') {
        window.location.href = '/tenant-suspended';
      }
    });
    return unsubscribe;
  }, [location.pathname]);

  useEffect(() => {
    const redirectPath = getStorage<string>(STORAGE_KEYS.SWITCH_REDIRECT_PATH);
    if (redirectPath) {
      removeStorage(STORAGE_KEYS.SWITCH_REDIRECT_PATH);
      const currentPath = history.location.pathname + (history.location.search || '');
      if (redirectPath !== currentPath) {
        history.push(redirectPath);
      }
    }
  }, []);

  const menuOpenKeys = (initialState as any)?.menuOpenKeys
    || computeParentOpenKeys(history.location.pathname);

  const storeCustomSettings = currentStore ? {
    logo: currentStore.logo || defaultSettings.logo,
    title: currentStore.name || defaultSettings.title,
  } : {};

  return {
    actionsRender: () => [
      <TenantSwitcher key="tenant" />,
      <StoreSwitcher key="store" />,
      <RefreshButton key="refresh" />,
      <NotificationButton key="notification" />,
      <FullscreenButton key="fullscreen" />,
    ],
    avatarProps: {
      src: initialState?.currentUser?.avatar,
      title: <AvatarName />,
      render: (_: any, avatarChildren: React.ReactNode) => {
        return <AvatarDropdown>{avatarChildren}</AvatarDropdown>;
      },
    },
    waterMarkProps: undefined,
    footerRender: () => (
      <div style={{ textAlign: 'center', padding: '16px 0', color: '#999' }}>
        {currentStore?.name || APP_TITLE} ©{new Date().getFullYear()} 版权所有
      </div>
    ),
    onPageChange: () => {
      const { location } = history;
      const token = getToken();
      if (!token && location.pathname !== LOGIN_PATH) {
        history.push(LOGIN_PATH);
        return;
      }
      const excludePaths = [LOGIN_PATH, '/welcome', '/404', '/403', '/'];
      if (token && !excludePaths.includes(location.pathname)) {
        const fullPath = location.pathname + (location.search || '') + (location.hash || '');
        setStorage(STORAGE_KEYS.LAST_PATH, fullPath);
      }

      const tracker = getTracker();
      if (tracker) {
        tracker.trackPageView(location.pathname, document.title);
      }

      const newKeys = computeParentOpenKeys(location.pathname);
      if (newKeys.length > 0) {
        setInitialState?.((s: any) => {
          const existingKeys = (s as any)?.menuOpenKeys || [];
          const mergedKeys = [...new Set([...existingKeys, ...newKeys])];
          if (mergedKeys.length === existingKeys.length) return s;
          return { ...s, menuOpenKeys: mergedKeys };
        });
      }
    },
    unAccessible: <div />,
    onUnAccessible: () => {
      history.replace('/dashboard');
    },
    menuHeaderRender: undefined,
    menuProps: {
      openKeys: menuOpenKeys,
      onOpenChange: (keys: string[]) => {
        setInitialState?.((s: any) => ({ ...s, menuOpenKeys: keys }));
      },
    },
    menuDataRender: (menuData: any[]) => {
      const { pathname } = history.location;
      return processMenuData(menuData, pathname);
    },
    childrenRender: (children: React.ReactNode) => {
      return (
        <>
          <TenantStatusBanner />
          <PageTransitionWrapper>{children}</PageTransitionWrapper>
        </>
      );
    },
    ...initialState?.settings,
    ...storeCustomSettings,
  };
};
/* eslint-enable react-hooks/rules-of-hooks */

export { umiRequestConfig as request } from '@/utils/requestInterceptors';
