import { List, Image, Button, Dialog, Toast } from 'antd-mobile';
import { history } from 'umi';
import { RightOutline, UserOutline, FileOutline, MessageOutline, QuestionCircleOutline, SetOutline } from 'antd-mobile-icons';
import { useState, useEffect } from 'react';
import { userApi } from '@hospital/api';
import { removeToken, removeStorage, STORAGE_KEYS } from '@hospital/shared';
import type { User } from '@hospital/shared';
import styles from './index.less';

const ProfilePage: React.FC = () => {
  const [user, setUser] = useState<User | null>(null);

  useEffect(() => {
    loadProfile();
  }, []);

  const loadProfile = async () => {
    try {
      const data = await userApi.getProfile();
      setUser(data);
    } catch (error) {
      console.error('加载用户信息失败', error);
    }
  };

  const handleLogout = async () => {
    const result = await Dialog.confirm({
      content: '确定要退出登录吗？',
    });

    if (result) {
      removeToken();
      removeStorage(STORAGE_KEYS.USER_INFO);
      Toast.show({ content: '已退出登录' });
      history.push('/login');
    }
  };

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <Image 
          src={user?.avatar || ''} 
          width={64} 
          height={64} 
          fit="cover" 
          style={{ borderRadius: '50%', background: 'rgba(255,255,255,0.2)' }} 
        />
        <div className={styles.userInfo}>
          <div className={styles.userName}>{user?.nickname || '未设置昵称'}</div>
          <div className={styles.userPhone}>
            {user?.phone?.replace(/(\d{3})\d{4}(\d{4})/, '$1****$2') || '未登录'}
          </div>
        </div>
      </div>

      <List className={styles.list}>
        <List.Item 
          prefix={<UserOutline />} 
          onClick={() => history.push('/profile/patient')} 
          arrow
        >
          就诊人管理
        </List.Item>
        <List.Item 
          prefix={<FileOutline />} 
          onClick={() => history.push('/records')} 
          arrow
        >
          就诊记录
        </List.Item>
        <List.Item 
          prefix={<MessageOutline />} 
          arrow
        >
          消息通知
        </List.Item>
      </List>

      <List className={styles.list}>
        <List.Item prefix={<QuestionCircleOutline />} arrow>
          意见反馈
        </List.Item>
        <List.Item prefix={<SetOutline />} arrow>
          设置
        </List.Item>
      </List>

      <div className={styles.logout}>
        <Button block onClick={handleLogout}>
          退出登录
        </Button>
      </div>
    </div>
  );
};

export default ProfilePage;
