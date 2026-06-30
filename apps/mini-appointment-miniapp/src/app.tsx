import React, { useEffect } from 'react';
import Taro, { useLaunch } from '@tarojs/taro';
import { checkLogin } from '@/utils/auth';
import './app.scss';

function App({ children }: { children?: React.ReactNode }) {
  useLaunch(() => {
    console.log('App launched.');
    // 应用启动时的初始化逻辑
    initApp();
  });

  useEffect(() => {
    // 检查更新
    checkUpdate();
  }, []);

  // 初始化应用
  const initApp = async () => {
    try {
      // 1. 加载门店信息
      await loadStoreInfo();
      
      // 2. 检查登录状态
      checkLoginStatus();
      
      // 3. 加载预约规则
      await loadBookingRules();
    } catch (error) {
      console.error('App initialization failed:', error);
    }
  };

  // 加载门店信息
  const loadStoreInfo = async () => {
    // 从环境变量或缓存中加载门店信息
    const storeId = process.env.TARO_APP_STORE_ID;
    if (storeId) {
      console.log('Store ID:', storeId);
    }
  };

  // 检查登录状态
  const checkLoginStatus = () => {
    if (checkLogin()) {
      console.log('User is logged in');
    }
  };

  // 加载预约规则
  const loadBookingRules = async () => {
    // 从 API 加载预约规则并缓存
    console.log('Loading booking rules...');
  };

  // 检查小程序更新
  const checkUpdate = () => {
    if (Taro.canIUse('getUpdateManager')) {
      const updateManager = Taro.getUpdateManager();
      
      updateManager.onCheckForUpdate((res) => {
        if (res.hasUpdate) {
          console.log('New version available');
        }
      });

      updateManager.onUpdateReady(() => {
        Taro.showModal({
          title: '更新提示',
          content: '新版本已经准备好，是否重启应用？',
          success: (res) => {
            if (res.confirm) {
              updateManager.applyUpdate();
            }
          }
        });
      });

      updateManager.onUpdateFailed(() => {
        console.error('Update failed');
      });
    }
  };

  return children;
}

export default App;
