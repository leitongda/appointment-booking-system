import { AvatarDropdown, AvatarName } from '@/components/RightContent';
import { FullscreenButton, NotificationButton, RefreshButton, SpacingButton } from '@/components/HeaderActions';
import { getToken, removeToken, setStorage, getStorage, STORAGE_KEYS, handleTokenExpired, initTracker, getTracker } from '@hospital/shared';
import { adminApi, setBaseURL } from '@hospital/api';
import type { Settings as LayoutSettings, MenuDataItem } from '@ant-design/pro-components';
import type { RunTimeLayoutConfig, RequestConfig } from '@umijs/max';
import { history, useLocation } from '@umijs/max';
import { App, message, ConfigProvider, theme } from 'antd';
import { useMemo } from 'react';
import defaultSettings from '../config/defaultSettings';
import { initApiConfig } from '@/utils/request';
import { getSpacingMode, applySpacingCSSVariables, SPACING_CONFIG } from '@/utils/spacing';

/**
 * 菜单展开状态管理
 * 使用模块级变量存储当前展开的菜单 keys，避免每次渲染重新读取 localStorage
 */
let currentMenuOpenKeys: string[] = [];

// 初始化时从 localStorage 读取
if (typeof window !== 'undefined') {
  const savedKeys = getStorage<string[]>(STORAGE_KEYS.MENU_OPEN_KEYS);
  if (savedKeys && Array.isArray(savedKeys)) {
    currentMenuOpenKeys = savedKeys;
  }
}

/**
 * 获取当前菜单展开状态
 */
const getMenuOpenKeys = (): string[] => {
  return currentMenuOpenKeys;
};

/**
 * 设置菜单展开状态并持久化到 localStorage
 */
const setMenuOpenKeys = (keys: string[]): void => {
  currentMenuOpenKeys = keys;
  setStorage(STORAGE_KEYS.MENU_OPEN_KEYS, keys);
};

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
    pattern: /^\/department\/create$/,
    parentPath: '/department',
    menuItem: { name: '新增科室', path: '/department/create' },
  },
  {
    pattern: /^\/department\/[^/]+\/edit$/,
    parentPath: '/department',
    menuItem: { name: '编辑科室', path: '/department/:id/edit' },
  },
  // 门店管理
  {
    pattern: /^\/store\/create$/,
    parentPath: '/store',
    menuItem: { name: '新增门店', path: '/store/create' },
  },
  {
    pattern: /^\/store\/[^/]+\/edit$/,
    parentPath: '/store',
    menuItem: { name: '编辑门店', path: '/store/:id/edit' },
  },
  // 医生管理
  {
    pattern: /^\/doctor\/create$/,
    parentPath: '/doctor',
    menuItem: { name: '新增医生', path: '/doctor/create' },
  },
  {
    pattern: /^\/doctor\/[^/]+\/edit$/,
    parentPath: '/doctor',
    menuItem: { name: '编辑医生', path: '/doctor/:id/edit' },
  },
  {
    // 排除 list, create, booking-setting 等已知路由，只匹配实际的 ID
    pattern: /^\/doctor\/(?!list$|create$|booking-setting)[^/]+$/,
    parentPath: '/doctor',
    menuItem: { name: '医生详情', path: '/doctor/:id' },
  },
  // 预约设置
  {
    pattern: /^\/doctor\/booking-setting\/create$/,
    parentPath: '/doctor',
    menuItem: { name: '添加预约设置', path: '/doctor/booking-setting/create' },
  },
  {
    pattern: /^\/doctor\/booking-setting\/[^/]+\/edit$/,
    parentPath: '/doctor',
    menuItem: { name: '编辑预约设置', path: '/doctor/booking-setting/:id/edit' },
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

const loginPath = '/login';

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
  
  return (
    <ConfigProvider
      theme={{
        algorithm,
        token: tokenConfig,
      }}
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
  userStores?: StoreInfo[];
  isAggregateMode?: boolean;
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
    let isAggregateMode = false;
    try {
      const storeData = localStorage.getItem('currentStore');
      if (storeData) {
        currentStore = JSON.parse(storeData);
      } else if (currentUser?.canViewAllStores) {
        // 没有选中门店且可以查看所有门店，则为聚合模式
        isAggregateMode = true;
      }
    } catch (e) {
      console.error('Failed to parse store info', e);
    }
    
    // 获取用户绑定的门店列表
    const userStores = currentUser?.stores || [];
    
    return {
      fetchUserInfo,
      currentUser,
      currentStore,
      userStores,
      isAggregateMode,
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
  const { currentStore } = initialState || {};

  // 门店用户：使用门店的 logo 和名称
  // 如果有门店信息，则覆盖默认设置
  const storeCustomSettings = currentStore ? {
    logo: currentStore.logo || defaultSettings.logo,
    title: currentStore.name || defaultSettings.title,
  } : {};

  return {
    // 允许多个子菜单同时展开
    subMenuCloseAll: false,
    // 菜单属性：设置初始展开状态并持久化
    // 使用 defaultOpenKeys（非受控模式）设置初始值，onOpenChange 保存状态
    menuProps: {
      defaultOpenKeys: getMenuOpenKeys(),
      onOpenChange: (keys: string[]) => {
        setMenuOpenKeys(keys);
      },
    },
    actionsRender: () => [
      <SpacingButton key="spacing" />,
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
      gap: [10, 10],                      // 水印间距 [水平, 垂直]
      rotate: -22,                        // 旋转角度

    zIndex: 11,
    offset: undefined,
    },
    footerRender: () => (
      <div style={{ textAlign: 'center', padding: '16px 0', color: '#999' }}>
        {currentStore?.name || '医院挂号管理系统'} ©{new Date().getFullYear()} 版权所有
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
    // 动态菜单渲染：根据当前路由动态显示编辑/新增等隐藏菜单项
    menuDataRender: (menuData) => {
      const { pathname } = history.location;
      return processMenuData(menuData, pathname);
    },
    // 路由切换动画
    childrenRender: (children: React.ReactNode) => {
      return <PageTransitionWrapper>{children}</PageTransitionWrapper>;
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
