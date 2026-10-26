import { AvatarDropdown, AvatarName } from '@/components/RightContent';
import { FullscreenButton, NotificationButton, RefreshButton, StoreSwitcher } from '@/components/HeaderActions';
import TenantSwitcher from '@/components/TenantSwitcher';
import TenantStatusBanner from '@/components/TenantStatusBanner';
import PageTransitionWrapper from '@/components/PageTransitionWrapper';
import GuidedTour from '@/components/GuidedTour';
import { getToken, removeToken, setStorage, getStorage, removeStorage, STORAGE_KEYS, initCrossTabSync, isPublicEntryRoute, subscribeTenantSuspended, getTracker, recordRouteChange, rememberReturnPath } from '@hospital/shared';
import type { MiniappStoreThemeValue } from '@hospital/shared';
import { adminApi, isTauriDesktop, isTauriPackaged, applyDesktopBaseUrl } from '@hospital/api';
import type { Settings as LayoutSettings } from '@ant-design/pro-components';
import type { RunTimeLayoutConfig } from '@umijs/max';
import { history, useLocation } from '@umijs/max';
import { App, ConfigProvider, Modal, notification } from 'antd';
import { useEffect } from 'react';
import defaultSettings from '../config/defaultSettings';
import { APP_TITLE } from '@config/appConfig';
import { getThemeConfig } from '@/themes';
import { processMenuData, computeParentOpenKeys } from '@/utils/menu';
import { handleCrossTabEvent } from '@/utils/crossTab';
import { initVisibilityAuthCheck } from '@/utils/visibilityAuth';
import { hardNavigate, currentRoutePath } from '@/utils/hardNavigate';
import { initApp } from '@/utils/initApp';
import { applySpacingCSSVariables, getSpacingMode } from '@/utils/spacing';
import { getDefaultRoute } from '@/utils/getDefaultRoute';
import access from '@/access';
import { LOGIN_PATH } from '@/constants/paths';

// PWA Service Worker 注册
// 桌面壳（Tauri webview 自定义协议）内禁用：SW 在该环境注册会拦截/缓存请求产生干扰
if ('serviceWorker' in navigator && !isTauriDesktop()) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js').catch(() => {});
  });
}

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

  // 记录初始路由性能（桌面壳 hash 路由下 pathname 恒为 '/'，需从 location.hash 归一化）
  let routeStartTime = performance.now();
  let lastPathname = currentRoutePath();

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
  // Tauri 桌面壳把关：getInitialState 是首个业务请求（fetchUserInfo）前的最后一道
  // 异步关口，在此等待桌面 baseURL 覆盖完成，避免与 initApp 的同步 setBaseURL 竞态。
  // web 端 applyDesktopBaseUrl() 立即返回 null，零影响。
  if (isTauriDesktop()) {
    const desktopBaseUrl = await applyDesktopBaseUrl();
    // 打包态（自定义协议）下相对路径无同源后端可打，未配置机构地址时所有请求都会
    // 失败——给出可见指引而不是静默失败。tauri dev 走 devUrl（http），不弹窗。
    if (!desktopBaseUrl && isTauriPackaged()) {
      Modal.warning({
        title: '桌面端尚未配置后端地址',
        content:
          '请在应用数据目录的 desktop-config.json 中写入 {"desktop.baseUrl": "http://<机构服务器>:9000/api/v1"} 后重启应用。'
          + 'macOS: ~/Library/Application Support/online.aicm.hospital.admin/；'
          + 'Windows: %APPDATA%\\online.aicm.hospital.admin\\',
        okText: '知道了',
      });
    }
  }

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
      // 会话失效（如刷新页面时 token 过期）：在清 token / 跳登录前记忆当前业务页，
      // 供重新登录后回跳。onPageChange 此时因 token 已清除不会写入 LAST_PATH。
      const { pathname, search, hash } = history.location;
      rememberReturnPath(pathname, search || undefined, hash || undefined);
      removeToken();
      history.push(LOGIN_PATH);
    }
    return undefined;
  };

  const { location } = history;
  const token = getToken();

  if (location.pathname !== LOGIN_PATH && token) {
    const currentUser = await fetchUserInfo();

    const currentStore = getStorage<StoreInfo>(STORAGE_KEYS.CURRENT_STORE) || undefined;

    const currentTenantId = getStorage<string>(STORAGE_KEYS.CURRENT_TENANT_ID) || undefined;
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
        hardNavigate('/tenant-suspended');
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
        // 无 token 访问业务页（如 token 被其它标签页清除后又在当前页导航）：
        // 跳登录前记忆当前路径，供重新登录后回跳。
        rememberReturnPath(location.pathname, location.search || undefined, location.hash || undefined);
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
      const { pathname } = history.location;
      // 基于当前用户权限选出第一个可访问的叶子路由作为兜底。
      // 避免硬编码 /dashboard —— 若用户无 dashboard 权限，再跳 /dashboard 会
      // 再次触发 onUnAccessible，形成死循环。
      const defaultPath = getDefaultRoute(access(initialState));

      // 若默认路由与当前路径相同（说明连默认路由都无权限，或当前已是默认路由），
      // 再 replace 会陷入死循环 —— 跳到 404（layout:false，不触发 access 检查）终止跳转。
      if (pathname === defaultPath) {
        history.replace('/404');
        return;
      }
      history.replace(defaultPath);
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
          <GuidedTour autoTrigger />
        </>
      );
    },
    ...initialState?.settings,
    ...storeCustomSettings,
  };
};
/* eslint-enable react-hooks/rules-of-hooks */
