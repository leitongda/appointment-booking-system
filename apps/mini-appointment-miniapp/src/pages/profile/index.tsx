import { View, Image, Text } from '@tarojs/components';
import { useState, useEffect } from 'react';
import Taro, { useDidShow } from '@tarojs/taro';
import { getUserProfile } from '@/services/user';
import { checkLogin, getCachedUser, setCachedUser } from '@/utils/auth';
import type { User } from '@/types/api';
import './index.scss';

export default function Profile() {
  const [user, setUser] = useState<User | null>(null);
  const [isLoggedIn, setIsLoggedIn] = useState(false);

  useEffect(() => {
    setUser(getCachedUser());
  }, []);

  useDidShow(() => {
    checkLoginAndLoadData();
  });

  const checkLoginAndLoadData = async () => {
    const loggedIn = checkLogin();
    setIsLoggedIn(loggedIn);

    if (!loggedIn) {
      setUser(null);
      setCachedUser(null);
      return;
    }

    const cachedUser = getCachedUser();
    if (cachedUser) {
      setUser(cachedUser);
    }

    try {
      const userData = await getUserProfile();
      setUser(userData);
      setCachedUser(userData);
    } catch (error) {
      console.error('Load user profile failed:', error);
    }
  };

  const handleLogin = () => {
    Taro.navigateTo({
      url: '/pages/login/index'
    });
  };

  const menuItems = [
    {
      title: '就诊服务',
      items: [
        { icon: '📋', title: '预约记录', url: '/pages/profile/appointments/index' },
        { icon: '👤', title: '就诊人管理', url: '/pages/profile/patients/index' },
        { icon: '⭐', title: '我的收藏', url: '/pages/profile/favorites/index' }
      ]
    },
    {
      title: '其他',
      items: [
        { icon: '💬', title: '意见反馈', url: '/pages/profile/feedback/index' },
        { icon: '⚙️', title: '设置', url: '/pages/profile/settings/index' }
      ]
    }
  ];

  const handleMenuClick = (url: string) => {
    if (!isLoggedIn) {
      Taro.showModal({
        title: '提示',
        content: '请先登录',
        success: (res) => {
          if (res.confirm) {
            handleLogin();
          }
        }
      });
      return;
    }

    Taro.navigateTo({ url });
  };

  return (
    <View className='profile-page'>
      {/* 用户信息区域 */}
      <View className='user-section'>
        {isLoggedIn && user ? (
          <View className='user-info'>
            <Image
              className='user-avatar'
              src={user.avatar || '/assets/images/default-avatar.png'}
              mode='aspectFill'
            />
            <View className='user-details'>
              <Text className='user-name'>{user.nickname || '用户'}</Text>
              {user.phone && (
                <Text className='user-phone'>{user.phone}</Text>
              )}
            </View>
          </View>
        ) : (
          <View className='login-prompt' onClick={handleLogin}>
            <Image
              className='user-avatar'
              src='/assets/images/default-avatar.png'
              mode='aspectFill'
            />
            <View className='user-details'>
              <Text className='login-text'>点击登录</Text>
            </View>
          </View>
        )}
      </View>

      {/* 菜单列表 */}
      {menuItems.map((section, sectionIndex) => (
        <View key={sectionIndex} className='menu-section'>
          {section.title && (
            <View className='section-title'>{section.title}</View>
          )}
          <View className='menu-list'>
            {section.items.map((item, itemIndex) => (
              <View
                key={itemIndex}
                className='menu-item'
                onClick={() => handleMenuClick(item.url)}
              >
                <View className='menu-icon'>{item.icon}</View>
                <Text className='menu-title'>{item.title}</Text>
                <Text className='menu-arrow'>›</Text>
              </View>
            ))}
          </View>
        </View>
      ))}
    </View>
  );
}
