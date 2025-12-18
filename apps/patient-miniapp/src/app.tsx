import { PropsWithChildren, useEffect } from 'react';
import Taro from '@tarojs/taro';
import '@nutui/nutui-react-taro/dist/style.css';
import './app.less';
import { initTracker, getTracker } from '@hospital/shared';

// 初始化用户行为追踪器
initTracker({
  apiBaseUrl: process.env.NODE_ENV === 'production' ? 'https://api.example.com' : 'http://localhost:8000',
  platform: 'miniapp',
  enabled: true,
  enableInDev: true,
  batchSize: 10,
  batchInterval: 5000,
  debug: process.env.NODE_ENV === 'development',
});

function App({ children }: PropsWithChildren) {
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

  return children;
}

export default App;

