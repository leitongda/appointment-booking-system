import { View, Text, Image } from '@tarojs/components';
import Taro from '@tarojs/taro';
import { Button } from '@nutui/nutui-react-taro';
import { useState, useEffect } from 'react';
import { userApi } from '@hospital/api';
import { removeToken, removeStorage, STORAGE_KEYS } from '@hospital/shared';
import type { User } from '@hospital/shared';
import './index.less';

// 菜单配置
const menuGroups = [
  {
    items: [
      { icon: '👥', title: '就诊人管理', desc: '管理就诊人信息', path: '/pages/profile/patient/index' },
      { icon: '📋', title: '就诊记录', desc: '查看历史就诊记录', path: '/pages/records/index' },
      { icon: '🔔', title: '消息通知', desc: '预约提醒、系统通知', badge: '' },
    ],
  },
  {
    items: [
      { icon: '💬', title: '意见反馈', desc: '帮助我们做得更好' },
      { icon: 'ℹ️', title: '关于我们', desc: '了解更多' },
      { icon: '⚙️', title: '设置', desc: '账号与安全' },
    ],
  },
];

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

  const handleMenuClick = (item: typeof menuGroups[0]['items'][0]) => {
    if (item.path) {
      Taro.navigateTo({ url: item.path });
    } else {
      Taro.showToast({ title: '功能开发中', icon: 'none' });
    }
  };

  return (
    <View className="profile-page">
      {/* 头部区域 */}
      <View className="header">
        <View className="header-content">
          <View className="avatar">
            {user?.avatar ? (
              <Image src={user.avatar} mode="aspectFill" />
            ) : (
              <Text>👤</Text>
            )}
          </View>
          <View className="user-info">
            <Text className="nickname">{user?.nickname || '未设置昵称'}</Text>
            <Text className="phone">
              {user?.phone?.replace(/(\d{3})\d{4}(\d{4})/, '$1****$2') || '未登录'}
            </Text>
          </View>
        </View>
      </View>

      {/* 统计卡片 */}
      <View className="stats-card">
        <View className="stat-item">
          <Text className="stat-value">0</Text>
          <Text className="stat-label">预约次数</Text>
        </View>
        <View className="stat-item">
          <Text className="stat-value">0</Text>
          <Text className="stat-label">就诊人</Text>
        </View>
        <View className="stat-item">
          <Text className="stat-value">0</Text>
          <Text className="stat-label">消息</Text>
        </View>
      </View>

      {/* 菜单列表 */}
      {menuGroups.map((group, groupIndex) => (
        <View key={groupIndex} className="menu-section">
          <View className="menu-card">
            {group.items.map((item, itemIndex) => (
              <View
                key={itemIndex}
                className="menu-item"
                onClick={() => handleMenuClick(item)}
              >
                <View className="menu-icon">
                  <Text>{item.icon}</Text>
                </View>
                <View className="menu-content">
                  <Text className="menu-title">{item.title}</Text>
                  <Text className="menu-desc">{item.desc}</Text>
                </View>
                {item.badge && <Text className="menu-badge">{item.badge}</Text>}
                <Text className="menu-arrow">›</Text>
              </View>
            ))}
          </View>
        </View>
      ))}

      {/* 退出登录 */}
      <View className="logout-wrap">
        <Button className="logout-btn" onClick={handleLogout}>
          退出登录
        </Button>
      </View>

      {/* 版本信息 */}
      <View className="version-info">
        <Text>版本 1.0.0</Text>
      </View>
    </View>
  );
};

export default ProfilePage;
