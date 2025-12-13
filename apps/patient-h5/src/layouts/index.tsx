import { Outlet, useLocation, history } from 'umi';
import { TabBar } from 'antd-mobile';
import { AppOutline, UnorderedListOutline, UserOutline } from 'antd-mobile-icons';
import styles from './index.less';
import { initApiConfig } from '@/utils/request';

// 初始化 API 请求配置（拦截器）
initApiConfig();

const tabs = [
  { key: '/home', title: '首页', icon: <AppOutline /> },
  { key: '/appointment', title: '预约', icon: <UnorderedListOutline /> },
  { key: '/profile', title: '我的', icon: <UserOutline /> },
];

const Layout: React.FC = () => {
  const location = useLocation();
  const showTabBar = ['/', '/home', '/appointment', '/profile'].includes(location.pathname);

  return (
    <div className={styles.layout}>
      <div className={styles.content}>
        <Outlet />
      </div>
      {showTabBar && (
        <div className={styles.tabBar}>
          <TabBar activeKey={location.pathname} onChange={(key) => history.push(key)}>
            {tabs.map((tab) => (
              <TabBar.Item key={tab.key} icon={tab.icon} title={tab.title} />
            ))}
          </TabBar>
        </div>
      )}
    </div>
  );
};

export default Layout;

