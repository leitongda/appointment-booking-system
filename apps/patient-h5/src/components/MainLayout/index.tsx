import { Outlet, useLocation, history } from 'umi';
import { TabBar } from 'antd-mobile';
import { AppOutline, UnorderedListOutline, UserOutline } from 'antd-mobile-icons';
import { useEffect, useState } from 'react';
import { initApiConfig } from '@/utils/request';
import { initTracker, getTracker, getToken } from '@hospital/shared';
import { setBaseURL } from '@hospital/api';
import { StoreProvider } from '@/components/StoreProvider';
import { LiveRegion } from '@/components/ui';

// 设置 API 基础路径（从环境变量读取，支持动态配置）
const apiBaseUrl = process.env.API_BASE_URL || '/api/v1';
setBaseURL(apiBaseUrl);

// 初始化 API 请求配置（拦截器，包含门店ID自动注入）
initApiConfig();

// 初始化用户行为追踪器
// 使用配置的 API 基础路径，支持动态版本
initTracker({
  apiBaseUrl: '',
  apiPath: `${apiBaseUrl}/analytics/batch`,
  platform: 'h5',
  enabled: true,
  enableInDev: true,
  batchSize: 10,
  batchInterval: 5000,
  debug: process.env.NODE_ENV === 'development',
});

const tabs = [
  { key: '/home', title: '首页', icon: <AppOutline /> },
  { key: '/appointment', title: '预约', icon: <UnorderedListOutline /> },
  { key: '/profile', title: '我的', icon: <UserOutline /> },
];

// 不需要登录的页面
const publicPaths = ['/login', '/register', '/home', '/', '/department', '/doctor', '/search'];

// 检查路径是否是公开页面
const isPublicPath = (pathname: string) => {
  // 完全匹配
  if (publicPaths.includes(pathname)) return true;
  // 前缀匹配（如 /doctor/xxx）
  if (pathname.startsWith('/doctor/')) return true;
  if (pathname.startsWith('/department/')) return true;
  return false;
};

const Layout: React.FC = () => {
  const location = useLocation();
  const [checked, setChecked] = useState(false);
  const showTabBar = ['/', '/home', '/appointment', '/profile'].includes(location.pathname);

  // 登录状态检查
  useEffect(() => {
    const token = getToken();
    const isPublic = isPublicPath(location.pathname);

    if (!token && !isPublic) {
      // 未登录且访问需要登录的页面，跳转到登录页
      history.replace('/login');
    } else {
      setChecked(true);
    }
  }, [location.pathname]);

  // 追踪页面访问
  useEffect(() => {
    const tracker = getTracker();
    if (tracker) {
      tracker.trackPageView(location.pathname, document.title);
    }
  }, [location.pathname]);

  // 等待登录检查完成
  if (!checked && !isPublicPath(location.pathname)) {
    return null;
  }

  return (
    <StoreProvider>
      <div className="flex flex-col h-screen bg-background">
        {/* Global a11y live region for screen reader announcements */}
        <LiveRegion />
        {/* Main content area */}
        <div className="flex-1 overflow-y-auto overscroll-contain" role="main">
          <Outlet />
        </div>

        {/* Tab bar */}
        {showTabBar && (
          <div className="flex-shrink-0 border-t border-border bg-card safe-area-inset-bottom">
            <TabBar
              activeKey={location.pathname}
              onChange={(key) => history.push(key)}
              className="!bg-transparent"
              aria-label="主导航"
            >
              {tabs.map((tab) => (
                <TabBar.Item 
                  key={tab.key} 
                  icon={tab.icon} 
                  title={tab.title}
                />
              ))}
            </TabBar>
          </div>
        )}
      </div>
    </StoreProvider>
  );
};

export default Layout;
