import { useState, useEffect, useCallback } from 'react';
import { MedicineBoxOutlined } from '@ant-design/icons';
import { App, Tabs } from 'antd';
import { history, useModel } from '@umijs/max';
import { setToken, STORAGE_KEYS, setStorage, getStorage, removeStorage, removeToken, resetTokenExpiredState } from '@hospital/shared';
import { adminApi } from '@hospital/api';
import defaultSettings from '@config/defaultSettings';
import { APP_TITLE } from '@config/appConfig';
import {
  AccountLogin, UserOutlined,
  PhoneLogin, MobileOutlined,
  WechatLogin, WechatOutlined
} from './components';
import styles from './index.less';

type LoginType = 'wechat' | 'phone' | 'account';

const Login: React.FC = () => {
  const { message } = App.useApp();
  const { setInitialState } = useModel('@@initialState');
  
  // 登录方式（从 localStorage 读取，实现刷新后保持选中状态）
  const [loginType, setLoginType] = useState<LoginType>(
    () => getStorage<LoginType>(STORAGE_KEYS.LOGIN_TYPE) || 'wechat'
  );

  // 延迟启用动画，避免初始化时的切换效果
  const [enableAnimation, setEnableAnimation] = useState(false);

  // 组件挂载后启用动画
  useEffect(() => {
    const timer = setTimeout(() => setEnableAnimation(true), 50);
    return () => clearTimeout(timer);
  }, []);

  // 登录成功后的处理
  const handleLoginSuccess = useCallback(async (result: any) => {
    // 重置 token 失效处理状态
    resetTokenExpiredState();
    
    setToken(result.accessToken);
    setStorage(STORAGE_KEYS.REFRESH_TOKEN, result.refreshToken);

    // 保存租户 ID 到 localStorage，请求拦截器会自动将其添加到 X-Tenant-ID Header
    const tenantId = result.admin?.tenantId;
    if (tenantId) {
      localStorage.setItem('hospital_current_tenant_id', tenantId);
    } else {
      localStorage.removeItem('hospital_current_tenant_id');
    }
    
    // 保存门店信息到 localStorage
    // 支持单门店 (result.store) 和多门店 (result.stores) 场景
    let currentStore: any = null;
    if (result.stores && result.stores.length > 0) {
      // 多门店管理员，默认选择第一个门店
      currentStore = result.stores[0];
      localStorage.setItem('currentStore', JSON.stringify(currentStore));
    } else if (result.store) {
      // 兼容旧的单门店返回
      currentStore = result.store;
      localStorage.setItem('currentStore', JSON.stringify(currentStore));
    } else {
      // 超级管理员没有门店
      localStorage.removeItem('currentStore');
    }
    
    message.success('登录成功！');
    
    // 登录接口已经返回了用户信息，直接使用，无需再次请求
    const currentUser = result.admin;
    const userStores = result.stores || (result.store ? [result.store] : []);
    
    // 创建 fetchUserInfo 函数（用于后续刷新用户信息）
    const fetchUserInfo = async () => {
      try {
        const user = await adminApi.getCurrentAdmin();
        return user as any;
      } catch (error: any) {
        // 401 已由响应拦截器处理（弹框 + 清 token），不再重复操作
        if (error?.isUnauthorized?.()) return undefined;
        removeToken();
        history.push('/login');
        return undefined;
      }
    };
    
    // 更新初始状态，避免整页刷新
    // 使用函数式更新，保留原有字段（如 settings），并设置新的用户信息
    setInitialState((s: any) => ({
      ...s,
      fetchUserInfo,
      currentUser: currentUser as any,
      currentStore: currentStore || undefined,
      userStores: userStores,
      settings: s?.settings || defaultSettings as any,
    }));
    
    // 获取上次访问的页面路径
    const lastPath = getStorage<string>(STORAGE_KEYS.LAST_PATH);
    // 清除存储的路径（只使用一次）
    removeStorage(STORAGE_KEYS.LAST_PATH);
    
    // 使用 history.push 进行路由跳转，不会触发整页刷新
    // 使用 setTimeout 确保状态更新完成后再跳转
    const targetPath = lastPath && lastPath !== '/' ? lastPath : '/dashboard';
    setTimeout(() => {
      history.push(targetPath);
    }, 0);
  }, [message, setInitialState]);

  const tabItems = [
    {
      key: 'wechat',
      label: (
        <span>
          <WechatOutlined />
          微信登录
        </span>
      ),
      children: <WechatLogin onSuccess={handleLoginSuccess} />,
    },
    {
      key: 'phone',
      label: (
        <span>
          <MobileOutlined />
          手机号登录
        </span>
      ),
      children: <PhoneLogin onSuccess={handleLoginSuccess} />,
    },
    {
      key: 'account',
      label: (
        <span>
          <UserOutlined />
          账号登录
        </span>
      ),
      children: <AccountLogin onSuccess={handleLoginSuccess} />,
    },
  ];

  return (
    <div className={styles.container}>
      <div className={styles.background} />
      <div className={styles.content}>
        <div className={styles.card}>
          <div className={styles.header}>
            <div className={styles.logo}><MedicineBoxOutlined /></div>
            <h1 className={styles.title}>{APP_TITLE}</h1>
          </div>
          
          <Tabs
            activeKey={loginType}
            onChange={(key) => {
              const newType = key as LoginType;
              setLoginType(newType);
              setStorage(STORAGE_KEYS.LOGIN_TYPE, newType);
            }}
            items={tabItems.map(item => ({ ...item, destroyOnHidden: true }))}
            centered
            className={styles.loginTabs}
            animated={enableAnimation}
          />
        </div>
      </div>
      <div className={styles.footer}>
        <a 
          href="https://beian.miit.gov.cn/" 
          target="_blank" 
          rel="noopener noreferrer"
        >
          蜀ICP备2022022726号-2
        </a>
      </div>
    </div>
  );
};

export default Login;
