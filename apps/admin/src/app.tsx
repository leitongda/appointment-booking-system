import { AvatarDropdown, AvatarName } from '@/components/RightContent';
import { FullscreenButton, NotificationButton, RefreshButton, StoreSwitcher } from '@/components/HeaderActions';
import TenantSwitcher from '@/components/TenantSwitcher';
import TenantStatusBanner from '@/components/TenantStatusBanner';
import { getToken, removeToken, setStorage, getStorage, removeStorage, STORAGE_KEYS, handleTokenExpired, initTracker, getTracker, initCrossTabSync, destroyCrossTabSync, isPublicEntryRoute, shouldSilenceAuthExpiredFeedback, markAuthExpired, subscribeTenantSuspended, initPerformanceMonitoring, recordRouteChange } from '@hospital/shared';
import type { CrossTabEvent, MiniappStoreThemeValue } from '@hospital/shared';
import { adminApi, setBaseURL } from '@hospital/api';
import type { Settings as LayoutSettings, MenuDataItem } from '@ant-design/pro-components';
import type { RunTimeLayoutConfig, RequestConfig } from '@umijs/max';
import { history, useLocation } from '@umijs/max';
import { App, Button, message, Modal, ConfigProvider, theme, notification } from 'antd';
import { useMemo, useEffect } from 'react';
import defaultSettings from '../config/defaultSettings';
import { APP_TITLE } from '@config/appConfig';
import useIllustrationTheme from './illustrationTheme';
import { initApiConfig } from '@/utils/request';
import { getSpacingMode, applySpacingCSSVariables, SPACING_CONFIG } from '@/utils/spacing';

// 设置 API 基础路径（从环境变量读取，支持动态配置）
const apiBaseUrl = process.env.API_BASE_URL || '/api/v1';
setBaseURL(apiBaseUrl);
console.log(`✓ API 基础路径已设置: ${apiBaseUrl}`);

/**
 * 动态菜单配置
 * 用于在访问隐藏的编辑/新增页面时，动态显示对应的菜单项
 */
interface DynamicMenuConfig {
  // 路由匹配正则
  pattern: RegExp;
  // 父级菜单路径
  parentPath: string;
  // 动态菜单项配置
  menuItem: {
    name: string;
    path: string;
  };
}

// 动态菜单规则配置
const dynamicMenuRules: DynamicMenuConfig[] = [
  // 科室管理
  {
    pattern: /^\/organization\/department\/create$/,
    parentPath: '/organization/department',
    menuItem: { name: '新增科室', path: '/organization/department/create' },
  },
  {
    pattern: /^\/organization\/department\/[^/]+\/edit$/,
    parentPath: '/organization/department',
    menuItem: { name: '编辑科室', path: '/organization/department/:id/edit' },
  },
  // 门店管理
  {
    pattern: /^\/organization\/store\/create$/,
    parentPath: '/organization/store',
    menuItem: { name: '新增门店', path: '/organization/store/create' },
  },
  {
    pattern: /^\/organization\/store\/[^/]+\/edit$/,
    parentPath: '/organization/store',
    menuItem: { name: '编辑门店', path: '/organization/store/:id/edit' },
  },
  // 医生管理
  {
    pattern: /^\/medical-services\/doctor\/create$/,
    parentPath: '/medical-services/doctor',
    menuItem: { name: '新增医生', path: '/medical-services/doctor/create' },
  },
  {
    pattern: /^\/medical-services\/doctor\/[^/]+\/edit$/,
    parentPath: '/medical-services/doctor',
    menuItem: { name: '编辑医生', path: '/medical-services/doctor/:id/edit' },
  },
  {
    pattern: /^\/medical-services\/doctor\/(?!list$|create$|booking-setting)[^/]+$/,
    parentPath: '/medical-services/doctor',
    menuItem: { name: '医生详情', path: '/medical-services/doctor/:id' },
  },
  // 预约设置
  {
    pattern: /^\/medical-services\/doctor\/booking-setting\/create$/,
    parentPath: '/medical-services/doctor',
    menuItem: { name: '添加预约设置', path: '/medical-services/doctor/booking-setting/create' },
  },
  {
    pattern: /^\/medical-services\/doctor\/booking-setting\/[^/]+\/edit$/,
    parentPath: '/medical-services/doctor',
    menuItem: { name: '编辑预约设置', path: '/medical-services/doctor/booking-setting/:id/edit' },
  },
  // 角色权限
  {
    pattern: /^\/system\/role\/create$/,
    parentPath: '/system/role',
    menuItem: { name: '新增角色', path: '/system/role/create' },
  },
  {
    pattern: /^\/system\/role\/[^/]+\/edit$/,
    parentPath: '/system/role',
    menuItem: { name: '编辑角色', path: '/system/role/:id/edit' },
  },
  {
    pattern: /^\/system\/role\/[^/]+\/permissions$/,
    parentPath: '/system/role',
    menuItem: { name: '分配权限', path: '/system/role/:id/permissions' },
  },
  // 员工管理
  {
    pattern: /^\/organization\/staff\/create$/,
    parentPath: '/organization/staff',
    menuItem: { name: '新增员工', path: '/organization/staff/create' },
  },
  {
    pattern: /^\/organization\/staff\/[^/]+\/edit$/,
    parentPath: '/organization/staff',
    menuItem: { name: '编辑员工', path: '/organization/staff/:id/edit' },
  },
];

/**
 * 处理菜单数据，根据当前路由动态添加菜单项
 */
const processMenuData = (menuData: MenuDataItem[], pathname: string): MenuDataItem[] => {
  // 查找匹配的动态菜单规则
  const matchedRule = dynamicMenuRules.find((rule) => rule.pattern.test(pathname));

  if (!matchedRule) {
    return menuData;
  }

  // 递归处理菜单数据
  return menuData.map((item) => {
    // 找到父级菜单
    if (item.path === matchedRule.parentPath) {
      // 创建动态菜单项
      const dynamicMenuItem: MenuDataItem = {
        name: matchedRule.menuItem.name,
        path: pathname, // 使用实际路径，确保高亮
        hideInMenu: false,
      };

      // 在子菜单末尾添加动态菜单项
      return {
        ...item,
        children: [...(item.children || []), dynamicMenuItem],
      };
    }

    // 递归处理子菜单
    if (item.children) {
      return {
        ...item,
        children: processMenuData(item.children, pathname),
      };
    }

    return item;
  });
};

/**
 * 根据当前路径计算需要展开的父级菜单 key
 * 例如 '/medical-services/doctor/create' -> ['/medical-services', '/medical-services/doctor']
 */
const computeParentOpenKeys = (pathname: string): string[] => {
  const segments = pathname.split('/').filter(Boolean);
  const keys: string[] = [];
  let current = '';
  for (let i = 0; i < segments.length - 1; i++) {
    current += '/' + segments[i];
    keys.push(current);
  }
  return keys;
};

const loginPath = '/login';

/**
 * 跨 Tab 状态变更处理
 * 当其他 Tab 修改了 token/租户/门店时，弹框提示并刷新
 */
function handleCrossTabEvent(event: CrossTabEvent) {
  // 公共入口页不弹框，避免用户已经回到登录页或根路由时再次被打断
  if (isPublicEntryRoute()) return;

  switch (event.type) {
    case 'auth-change':
      if (event.action === 'logout') {
        Modal.confirm({
          title: '登录状态变更',
          content: '您已在其他页面退出登录，请重新登录。',
          okText: '重新登录',
          cancelButtonProps: { style: { display: 'none' } },
          closable: false,
          maskClosable: false,
          onOk: () => {
            Modal.destroyAll();
            window.location.href = loginPath;
          },
        });
      } else if (event.action === 'switch-user') {
        Modal.confirm({
          title: '登录账号已变更',
          content: '检测到您在其他页面切换了登录账号，当前页面需要刷新以保持一致。',
          okText: '刷新页面',
          cancelButtonProps: { style: { display: 'none' } },
          closable: false,
          maskClosable: false,
          onOk: () => { window.location.reload(); },
        });
      }
      // login（同用户换 token）— 静默忽略
      break;

    case 'tenant-change':
      notification.warning({
        key: 'tenant-change',
        message: '租户已切换',
        description: '当前页面需要刷新以保持一致',
        placement: 'topRight',
        duration: 15,
        btn: (
          <Button type="primary" size="small" onClick={() => {
            const { pathname, search, hash } = history.location;
            if (!/\/(create|edit)($|\/)/.test(pathname)) {
              setStorage(STORAGE_KEYS.SWITCH_REDIRECT_PATH, pathname + (search || '') + (hash || ''));
            }
            window.location.reload();
          }}>
            立即刷新
          </Button>
        ),
      });
      break;

    case 'store-change':
      notification.warning({
        key: 'store-change',
        message: '门店已切换',
        description: event.newStoreName
          ? `门店已切换为「${event.newStoreName}」，当前页面需要刷新以保持一致。`
          : '门店已切换，当前页面需要刷新以保持一致。',
        placement: 'topRight',
        duration: 15,
        btn: (
          <Button type="primary" size="small" onClick={() => {
            const { pathname, search, hash } = history.location;
            if (!/\/(create|edit)($|\/)/.test(pathname)) {
              setStorage(STORAGE_KEYS.SWITCH_REDIRECT_PATH, pathname + (search || '') + (hash || ''));
            }
            window.location.reload();
          }}>
            立即刷新
          </Button>
        ),
      });
      break;
  }
}

// 初始化 API 请求配置（拦截器）
initApiConfig();

// 初始化用户行为追踪器
// 使用配置的 API 基础路径，支持动态版本
initTracker({
  apiBaseUrl: '',
  apiPath: `${apiBaseUrl}/analytics/batch`,
  platform: 'admin',
  enabled: true,
  enableInDev: true, // 开发环境也启用，方便测试
  batchSize: 10,
  batchInterval: 5000,
  debug: process.env.NODE_ENV === 'development',
});

// 初始化前端性能监控
initPerformanceMonitoring({
  report: {
    enabled: true,
    flushInterval: 30000, // 30 秒批量上报
    batchSize: 20,
  },
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
 * 获取 Ant Design 主题配置
 * 根据间距模式返回对应的主题算法和 token
 */
function getThemeConfig() {
  const spacingMode = getSpacingMode();
  const spacingValues = SPACING_CONFIG[spacingMode];
  
  // 紧凑模式使用 compactAlgorithm
  const algorithm = spacingMode === 'compact' ? theme.compactAlgorithm : theme.defaultAlgorithm;
  
  // 根据间距模式调整 token
  const tokenConfig = {
    // 组件内边距
    padding: spacingValues.padding,
    paddingLG: spacingValues.padding + 8,
    paddingSM: spacingValues.padding - 4,
    paddingXS: spacingValues.padding - 8,
    // 外边距
    margin: spacingValues.component,
    marginLG: spacingValues.section,
    marginSM: spacingValues.component - 4,
    marginXS: spacingValues.component - 8,
  };
  
  return { algorithm, tokenConfig };
}

/**
 * rootContainer 配置 - 用 App 和 ConfigProvider 组件包裹应用
 * 这样可以使用 App.useApp() hooks (message, notification, modal)
 * 同时应用间距模式的主题配置
 */
export function rootContainer(container: any) {
  const { algorithm, tokenConfig } = getThemeConfig();
  
  // 初始化时应用 CSS 变量
  if (typeof window !== 'undefined') {
    applySpacingCSSVariables(getSpacingMode());
  }

  // 初始化跨 Tab 状态同步
  initCrossTabSync(handleCrossTabEvent);

  // 记录初始路由性能
  let routeStartTime = performance.now();
  let lastPathname = window.location.pathname;

  // 监听路由变化（使用 Umi 的 history 监听）
  const unlisten = history.listen(({ location }) => {
    const routeEndTime = performance.now();
    const routeDuration = routeEndTime - routeStartTime;

    // 记录路由切换性能（排除登录页等公共页面）
    const publicPaths = ['/login', '/404', '/403', '/tenant-suspended'];
    if (!publicPaths.includes(lastPathname)) {
      recordRouteChange(lastPathname, routeDuration);
    }

    routeStartTime = performance.now();
    lastPathname = location.pathname;
  });
  const configProps = useIllustrationTheme();

  return (
    <ConfigProvider
      theme={{
        algorithm,
        token: tokenConfig,
      }}

      {...configProps}
      
    >
      <App>{container}</App>
    </ConfigProvider>
  );
}

// 门店信息类型
interface StoreInfo {
  id: string;
  name: string;
  logo?: string;
  themeStyle?: MiniappStoreThemeValue;
}

/**
 * 获取初始状态
 * @see https://umijs.org/zh-CN/plugins/plugin-initial-state
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
      // 兼容统一账号格式：如果后端返回了 roleType，直接使用；否则默认为 admin
      const user = currentUser as API.CurrentUser;
      if (!user.roleType) {
        user.roleType = 'admin';
      }
      return user;
    } catch (error: any) {
      // 401 已由响应拦截器处理（弹框 + 清 token），不再重复操作
      if (error?.isUnauthorized?.()) return undefined;
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
      const storeData = localStorage.getItem('hospital_current_store');
      if (storeData) {
        currentStore = JSON.parse(storeData);
      }
    } catch (e) {
      console.error('Failed to parse store info', e);
    }

    // 从 localStorage 获取当前租户 ID
    const currentTenantId = localStorage.getItem('hospital_current_tenant_id') || undefined;

    // 获取用户绑定的门店列表
    const userStores = currentUser?.stores || [];

    return {
      fetchUserInfo,
      currentUser,
      currentStore,
      userStores,
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
 * @doc https://procomponents.ant.design/components/layout
 */
export const layout: RunTimeLayoutConfig = ({ initialState, setInitialState }) => {
  const location = useLocation();
  const { currentStore } = initialState || {};

  useEffect(() => {
    if (!isPublicEntryRoute(location.pathname)) return;

    Modal.destroyAll();
    notification.destroy('tenant-change');
    notification.destroy('store-change');
  }, [location.pathname]);

  // 跨标签租户暂停同步：其他标签收到 403 时，本标签同步跳转
  useEffect(() => {
    if (isPublicEntryRoute(location.pathname)) return;
    const unsubscribe = subscribeTenantSuspended(() => {
      if (location.pathname !== '/tenant-suspended') {
        window.location.href = '/tenant-suspended';
      }
    });
    return unsubscribe;
  }, [location.pathname]);

  // 切换租户/门店后恢复之前的页面路径
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

  // 菜单展开状态：保持已展开的菜单，路由变化时只追加不清除
  const menuOpenKeys = (initialState as any)?.menuOpenKeys
    || computeParentOpenKeys(history.location.pathname);

  // 门店用户：使用门店的 logo 和名称
  // 如果有门店信息，则覆盖默认设置
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
      render: (_, avatarChildren) => {
        return <AvatarDropdown>{avatarChildren}</AvatarDropdown>;
      },
    },
    waterMarkProps: {
      content: [initialState?.currentUser?.name, initialState?.currentUser?.email || initialState?.currentUser?.phone],
      fontColor: 'rgba(0, 0, 0, 0.05)', // 水印颜色和透明度，数值越小越淡
      fontSize: 14,                       // 字体大小
      gap: [100, 100],                    // 水印间距 [水平, 垂直]，默认值 100
      rotate: -22,                        // 旋转角度
      zIndex: 9,                          // 使用默认 z-index
      // 注意：不要设置 style: { pointerEvents: 'none' }
      // 因为 style 会应用到 Watermark 容器（包含内容），导致内容无法点击
      // Watermark 组件内部已正确处理水印层的 pointer-events
    },
    footerRender: () => (
      <div style={{ textAlign: 'center', padding: '16px 0', color: '#999' }}>
        {currentStore?.name || APP_TITLE} ©{new Date().getFullYear()} 版权所有
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

      // 路由变化时，追加新路径的父级菜单 key（不清除已展开的菜单）
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
    // 无权限时重定向到仪表盘
    unAccessible: <div />,
    onUnAccessible: () => {
      history.replace('/dashboard');
    },
    menuHeaderRender: undefined,
    // 受控菜单展开状态：切换菜单不会导致其他已展开菜单收起
    menuProps: {
      openKeys: menuOpenKeys,
      onOpenChange: (keys: string[]) => {
        setInitialState?.((s: any) => ({ ...s, menuOpenKeys: keys }));
      },
    },
    // 动态菜单渲染：根据当前路由动态显示编辑/新增等隐藏菜单项
    menuDataRender: (menuData) => {
      const { pathname } = history.location;
      return processMenuData(menuData, pathname);
    },
    // 路由切换动画
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
        if (shouldSilenceAuthExpiredFeedback()) {
          if (getToken()) {
            markAuthExpired();
            handleTokenExpired();
          }
          return response;
        }
        markAuthExpired();
        handleTokenExpired(() => {
          Modal.confirm({
            title: '登录已过期',
            content: data?.message || '您的登录已失效，请重新登录。',
            okText: '重新登录',
            cancelButtonProps: { style: { display: 'none' } },
            closable: false,
            maskClosable: false,
            onOk: () => {
              window.location.href = loginPath;
            },
          });
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
