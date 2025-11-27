import { View, Text, Image } from '@tarojs/components';
import Taro from '@tarojs/taro';
import { Cell, CellGroup, Button } from '@nutui/nutui-react-taro';
import { useState, useEffect } from 'react';
import { userApi } from '@hospital/api';
import { removeToken, removeStorage, STORAGE_KEYS } from '@hospital/shared';
import type { User } from '@hospital/shared';
import './index.less';

const ProfilePage = () => {
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
    const result = await Taro.showModal({
      title: '退出登录',
      content: '确定要退出登录吗？',
    });

    if (result.confirm) {
      removeToken();
      removeStorage(STORAGE_KEYS.USER_INFO);
      Taro.showToast({ title: '已退出登录', icon: 'success' });
      Taro.reLaunch({ url: '/pages/login/index' });
    }
  };

  return (
    <View className="profile-page">
      <View className="header">
        <Image 
          className="avatar" 
          src={user?.avatar || ''} 
          mode="aspectFill"
        />
        <View className="user-info">
          <Text className="nickname">{user?.nickname || '未设置昵称'}</Text>
          <Text className="phone">
            {user?.phone?.replace(/(\d{3})\d{4}(\d{4})/, '$1****$2') || '未登录'}
          </Text>
        </View>
      </View>

      <CellGroup className="menu-group">
        <Cell
          title="就诊人管理"
          isLink
          onClick={() => Taro.navigateTo({ url: '/pages/profile/patient/index' })}
        />
        <Cell
          title="就诊记录"
          isLink
          onClick={() => Taro.navigateTo({ url: '/pages/records/index' })}
        />
        <Cell
          title="消息通知"
          isLink
        />
      </CellGroup>

      <CellGroup className="menu-group">
        <Cell title="意见反馈" isLink />
        <Cell title="关于我们" isLink />
        <Cell title="设置" isLink />
      </CellGroup>

      <View className="logout-wrap">
        <Button block onClick={handleLogout}>退出登录</Button>
      </View>
    </View>
  );
};

export default ProfilePage;

