import { useState, useEffect, useCallback } from 'react';
import { MedicineBoxOutlined } from '@ant-design/icons';
import { App, Tabs } from 'antd';
import { setToken, STORAGE_KEYS, setStorage, getStorage, removeStorage, resetTokenExpiredState } from '@hospital/shared';
import { 
  AccountLogin, UserOutlined,
  PhoneLogin, MobileOutlined,
  WechatLogin, WechatOutlined 
} from './components';
import styles from './index.less';

type LoginType = 'wechat' | 'phone' | 'account';

const Login: React.FC = () => {
  const { message } = App.useApp();
  
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
    
    // 保存门店信息到 localStorage
    // 支持单门店 (result.store) 和多门店 (result.stores) 场景
    if (result.stores && result.stores.length > 0) {
      // 多门店管理员，默认选择第一个门店
      localStorage.setItem('currentStore', JSON.stringify(result.stores[0]));
    } else if (result.store) {
      // 兼容旧的单门店返回
      localStorage.setItem('currentStore', JSON.stringify(result.store));
    } else {
      // 超级管理员没有门店
      localStorage.removeItem('currentStore');
    }
    
    message.success('登录成功！');
    
    // 获取上次访问的页面路径
    const lastPath = getStorage<string>(STORAGE_KEYS.LAST_PATH);
    // 清除存储的路径（只使用一次）
    removeStorage(STORAGE_KEYS.LAST_PATH);
    
    // 使用 window.location.href 而不是 history.push
    // 这样会触发页面刷新，重新执行 getInitialState，确保权限正确加载
    const targetPath = lastPath && lastPath !== '/' ? lastPath : '/dashboard';
    window.location.href = targetPath;
  }, [message]);

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
            <h1 className={styles.title}>医院挂号管理系统</h1>
          </div>
          
          <Tabs
            activeKey={loginType}
            onChange={(key) => {
              const newType = key as LoginType;
              setLoginType(newType);
              setStorage(STORAGE_KEYS.LOGIN_TYPE, newType);
            }}
            items={tabItems.map(item => ({ ...item, destroyInactiveTabPane: true }))}
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
