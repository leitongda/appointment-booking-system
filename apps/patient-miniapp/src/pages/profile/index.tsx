import { View, Text, Image } from '@tarojs/components';
import Taro from '@tarojs/taro';
import { Button } from '@nutui/nutui-react-taro';
import { useState, useEffect } from 'react';
import { userApi, appointmentApi } from '@hospital/api';
import { STORAGE_KEYS } from '@hospital/shared';
import { getToken, removeToken, removeStorage } from '../../utils/auth';
import type { User } from '@hospital/shared';
import {
  TeamIcon,
  RecordIcon,
  BellIcon,
  ChatIcon,
  InfoIcon,
  SettingsIcon,
  UserIcon,
} from '../../components/Icons';
import './index.less';

// 图标组件类型
type IconComponent = typeof TeamIcon;

// 菜单配置
const menuGroups: { items: { icon: IconComponent; title: string; desc: string; path?: string; badge?: string }[] }[] = [
  {
    items: [
      { icon: TeamIcon, title: '就诊人管理', desc: '管理就诊人信息', path: '/packageProfile/pages/patient/index' },
      { icon: RecordIcon, title: '就诊记录', desc: '查看历史就诊记录', path: '/packageProfile/pages/records/index' },
      { icon: BellIcon, title: '消息通知', desc: '预约提醒、系统通知', path: '/packageProfile/pages/message/index' },
    ],
  },
  {
    items: [
      { icon: ChatIcon, title: '意见反馈', desc: '帮助我们做得更好', path: '/packageProfile/pages/feedback/index' },
      { icon: InfoIcon, title: '关于我们', desc: '了解更多', path: '/packageOther/pages/about/index' },
      { icon: SettingsIcon, title: '设置', desc: '账号与安全', path: '/packageProfile/pages/settings/index' },
    ],
  },
];

// 统计数据类型
interface Stats {
  appointmentCount: number;
  patientCount: number;
  messageCount: number;
}

const ProfilePage = () => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [stats, setStats] = useState<Stats>({ appointmentCount: 0, patientCount: 0, messageCount: 0 });

  useEffect(() => {
    checkLoginStatus();
  }, []);

  // 页面显示时刷新数据
  Taro.useDidShow(() => {
    if (isLoggedIn) {
      loadStats();
    }
  });

  const checkLoginStatus = () => {
    const token = getToken();
    if (token) {
      setIsLoggedIn(true);
      loadProfile();
      loadStats();
    } else {
      setIsLoggedIn(false);
      setUser(null);
      setStats({ appointmentCount: 0, patientCount: 0, messageCount: 0 });
    }
  };

  const loadProfile = async () => {
    try {
      const data = await userApi.getProfile();
      setUser(data);
    } catch (error) {
      console.error('加载用户信息失败', error);
      // 如果获取用户信息失败（可能 token 过期），重置登录状态
      setIsLoggedIn(false);
      setUser(null);
    }
  };

  const loadStats = async () => {
    try {
      const [appointmentsResult, patients] = await Promise.all([
        appointmentApi.getList({ pageSize: 1 }).catch(() => ({ total: 0, data: [] })),
        userApi.getPatients().catch(() => []),
      ]);
      
      setStats({
        appointmentCount: appointmentsResult.total || 0,
        patientCount: patients.length,
        messageCount: 0, // 消息模块待实现
      });
    } catch (error) {
      console.error('加载统计数据失败', error);
    }
  };

  // 点击头像/用户信息区域，未登录时跳转登录
  const handleHeaderClick = () => {
    if (!isLoggedIn) {
      Taro.navigateTo({ url: '/pages/login/index' });
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
    // 需要登录的菜单项
    const requireLoginPaths = [
      '/packageProfile/pages/patient/index',
      '/packageProfile/pages/records/index',
      '/packageProfile/pages/message/index',
      '/packageProfile/pages/feedback/index',
      '/packageProfile/pages/settings/index',
    ];

    if (item.path) {
      // 检查是否需要登录
      if (requireLoginPaths.includes(item.path) && !isLoggedIn) {
        Taro.showToast({ title: '请先登录', icon: 'none' });
        Taro.navigateTo({ url: '/pages/login/index' });
        return;
      }
      Taro.navigateTo({ url: item.path });
    } else {
      Taro.showToast({ title: '功能开发中', icon: 'none' });
    }
  };

  const handleStatClick = (type: 'appointment' | 'patient' | 'message') => {
    if (!isLoggedIn) {
      Taro.navigateTo({ url: '/pages/login/index' });
      return;
    }
    
    switch (type) {
      case 'appointment':
        Taro.switchTab({ url: '/pages/appointment/index' });
        break;
      case 'patient':
        Taro.navigateTo({ url: '/packageProfile/pages/patient/index' });
        break;
      case 'message':
        Taro.navigateTo({ url: '/packageProfile/pages/message/index' });
        break;
    }
  };

  return (
    <View className="profile-page">
      {/* 头部区域 */}
      <View className="header">
        <View className="header-content" onClick={handleHeaderClick}>
          <View className="avatar">
            {user?.avatar ? (
              <Image src={user.avatar} mode="aspectFill" />
            ) : (
              <UserIcon size={40} color="#fff" />
            )}
          </View>
          <View className="user-info">
            <Text className="nickname">
              {isLoggedIn ? (user?.nickname || '未设置昵称') : '点击登录'}
            </Text>
            <Text className="phone">
              {isLoggedIn
                ? (user?.phone?.replace(/(\d{3})\d{4}(\d{4})/, '$1****$2') || '')
                : '登录后享受更多服务'}
            </Text>
          </View>
          {!isLoggedIn && <Text className="login-arrow">›</Text>}
        </View>
      </View>

      {/* 统计卡片 */}
      <View className="stats-card">
        <View className="stat-item" onClick={() => handleStatClick('appointment')}>
          <Text className="stat-value">{stats.appointmentCount}</Text>
          <Text className="stat-label">预约次数</Text>
        </View>
        <View className="stat-item" onClick={() => handleStatClick('patient')}>
          <Text className="stat-value">{stats.patientCount}</Text>
          <Text className="stat-label">就诊人</Text>
        </View>
        <View className="stat-item" onClick={() => handleStatClick('message')}>
          <Text className="stat-value">{stats.messageCount}</Text>
          <Text className="stat-label">消息</Text>
        </View>
      </View>

      {/* 菜单列表 */}
      {menuGroups.map((group, groupIndex) => (
        <View key={groupIndex} className="menu-section">
          <View className="menu-card">
            {group.items.map((item, itemIndex) => {
              const IconComponent = item.icon;
              return (
                <View
                  key={itemIndex}
                  className="menu-item"
                  onClick={() => handleMenuClick(item)}
                >
                  <View className="menu-icon">
                    <IconComponent size={22} color="#4F46E5" />
                  </View>
                  <View className="menu-content">
                    <Text className="menu-title">{item.title}</Text>
                    <Text className="menu-desc">{item.desc}</Text>
                  </View>
                  {item.badge && <Text className="menu-badge">{item.badge}</Text>}
                  <Text className="menu-arrow">›</Text>
                </View>
              );
            })}
          </View>
        </View>
      ))}

      {/* 退出登录 - 仅登录状态显示 */}
      {isLoggedIn && (
        <View className="logout-wrap">
          <Button className="logout-btn" onClick={handleLogout}>
            退出登录
          </Button>
        </View>
      )}

      {/* 版本信息 */}
      <View className="version-info">
        <Text>版本 1.0.0</Text>
      </View>
    </View>
  );
};

export default ProfilePage;
