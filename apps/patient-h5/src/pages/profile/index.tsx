import { List, Image, Button, Dialog, Toast, Badge } from 'antd-mobile';
import { history } from 'umi';
import { UserOutline, FileOutline, MessageOutline, QuestionCircleOutline, SetOutline, EditSOutline } from 'antd-mobile-icons';
import { useState, useEffect } from 'react';
import { userApi, messageApi } from '@hospital/api';
import { removeToken, removeStorage, STORAGE_KEYS } from '@hospital/shared';
import type { User, UnreadCount } from '@hospital/shared';
import styles from './index.less';

const ProfilePage: React.FC = () => {
  const [user, setUser] = useState<User | null>(null);
  const [unreadCount, setUnreadCount] = useState(0);
  const userId = localStorage.getItem('userId') || '';

  useEffect(() => {
    loadProfile();
    loadUnreadCount();
  }, []);

  const loadProfile = async () => {
    try {
      const data = await userApi.getProfile();
      setUser(data);
    } catch (error) {
      console.error('加载用户信息失败', error);
    }
  };

  const loadUnreadCount = async () => {
    if (!userId) return;
    try {
      const count = await messageApi.getUnreadCount(userId, 'patient');
      setUnreadCount(count.total || 0);
    } catch (error) {
      console.error('获取未读消息数失败', error);
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

  const handleEditProfile = () => {
    history.push('/profile/edit');
  };

  return (
    <div className={styles.container}>
      <div className={styles.header} onClick={handleEditProfile}>
        <Image 
          src={user?.avatar || ''} 
          width={64} 
          height={64} 
          fit="cover" 
          style={{ borderRadius: '50%', background: 'rgba(255,255,255,0.2)' }} 
        />
        <div className={styles.userInfo}>
          <div className={styles.userName}>
            {user?.nickname || user?.name || '未设置昵称'}
            <EditSOutline className={styles.editIcon} />
          </div>
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
          onClick={() => history.push('/message')}
          arrow
          extra={unreadCount > 0 ? <Badge content={unreadCount} /> : null}
        >
          消息通知
        </List.Item>
      </List>

      <List className={styles.list}>
        <List.Item 
          prefix={<QuestionCircleOutline />} 
          onClick={() => history.push('/feedback')}
          arrow
        >
          意见反馈
        </List.Item>
        <List.Item 
          prefix={<SetOutline />} 
          onClick={() => history.push('/settings')}
          arrow
        >
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
