import { NavBar, List, Switch, Dialog, Toast } from 'antd-mobile';
import { history } from 'umi';
import { useState } from 'react';
import { removeToken, removeStorage, STORAGE_KEYS } from '@hospital/shared';
import styles from './index.less';

const SettingsPage: React.FC = () => {
  const [pushEnabled, setPushEnabled] = useState(true);

  const handleClearCache = async () => {
    const result = await Dialog.confirm({
      content: '确定要清除缓存吗？',
    });

    if (result) {
      // 清除本地缓存（保留登录状态）
      const token = localStorage.getItem('token');
      const refreshToken = localStorage.getItem('refreshToken');
      const userId = localStorage.getItem('userId');
      
      localStorage.clear();
      
      // 恢复登录状态
      if (token) localStorage.setItem('token', token);
      if (refreshToken) localStorage.setItem('refreshToken', refreshToken);
      if (userId) localStorage.setItem('userId', userId);
      
      Toast.show({ content: '缓存已清除', icon: 'success' });
    }
  };

  const handleLogout = async () => {
    const result = await Dialog.confirm({
      content: '确定要退出登录吗？',
    });

    if (result) {
      removeToken();
      removeStorage(STORAGE_KEYS.USER_INFO);
      localStorage.removeItem('userId');
      Toast.show({ content: '已退出登录' });
      history.push('/login');
    }
  };

  return (
    <div className={styles.container}>
      <NavBar onBack={() => history.back()}>设置</NavBar>

      <List header="通知设置" className={styles.list}>
        <List.Item
          extra={
            <Switch
              checked={pushEnabled}
              onChange={setPushEnabled}
            />
          }
        >
          推送通知
        </List.Item>
      </List>

      <List header="其他" className={styles.list}>
        <List.Item onClick={handleClearCache} arrow>
          清除缓存
        </List.Item>
        <List.Item>
          版本号 <span className={styles.version}>v1.0.0</span>
        </List.Item>
      </List>

      <div className={styles.logout}>
        <List.Item onClick={handleLogout} className={styles.logoutItem}>
          退出登录
        </List.Item>
      </div>
    </div>
  );
};

export default SettingsPage;

