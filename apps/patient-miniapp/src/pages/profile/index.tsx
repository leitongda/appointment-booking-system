import { View, Text, Image, Button as TaroButton, Input as TaroInput } from '@tarojs/components';
import Taro from '@tarojs/taro';
import { Button } from '@nutui/nutui-react-taro';
import { useState, useEffect } from 'react';
import { userApi, appointmentApi, authApi } from '@hospital/api';
import { STORAGE_KEYS } from '@hospital/shared';
import { getToken, removeToken, removeStorage, setToken, setStorage } from '../../utils/auth';
import { getStoreId } from '../../utils/store';
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
  const [isInitializing, setIsInitializing] = useState(true); // 初始化状态
  const [stats, setStats] = useState<Stats>({ appointmentCount: 0, patientCount: 0, messageCount: 0 });
  
  // 微信登录相关状态
  const [wechatLoading, setWechatLoading] = useState(false);
  const [openid, setOpenid] = useState('');
  const [bindLoading, setBindLoading] = useState(false);
  
  // 用户信息设置弹窗状态
  const [showUserInfo, setShowUserInfo] = useState(false);
  const [avatar, setAvatar] = useState('');
  const [nickname, setNickname] = useState('');
  
  // 已注释：绑定手机号相关状态
  // const [showBindPhone, setShowBindPhone] = useState(false);
  // const [bindPhone, setBindPhone] = useState('');

  useEffect(() => {
    checkLoginStatus();
  }, []);

  // 页面显示时刷新数据
  Taro.useDidShow(() => {
    // 如果正在初始化，跳过
    if (isInitializing) return;
    
    // 重新检查登录状态，确保 token 仍然有效
    const token = getToken();
    if (token && isLoggedIn) {
      loadStats();
    } else if (!token) {
      // token 已被清除，重置状态
      setIsLoggedIn(false);
      setUser(null);
      setStats({ appointmentCount: 0, patientCount: 0, messageCount: 0 });
    }
  });

  // 检查登录状态，先验证 token 有效性
  const checkLoginStatus = async () => {
    setIsInitializing(true);
    const token = getToken();
    if (token) {
      // 先验证 token 是否有效
      const isValid = await loadProfile();
      if (isValid) {
        setIsLoggedIn(true);
        loadStats();
      } else {
        // token 无效，清除并重置状态
        removeToken();
        removeStorage(STORAGE_KEYS.USER_INFO);
        setIsLoggedIn(false);
        setUser(null);
        setStats({ appointmentCount: 0, patientCount: 0, messageCount: 0 });
      }
    } else {
      setIsLoggedIn(false);
      setUser(null);
      setStats({ appointmentCount: 0, patientCount: 0, messageCount: 0 });
    }
    setIsInitializing(false);
  };

  // 加载用户资料，返回是否成功
  const loadProfile = async (): Promise<boolean> => {
    console.log("🚀 ~ loadProfile 开始调用");
    try {
      const data = await userApi.getProfile();
      console.log("🚀 ~ loadProfile 成功:", data);
      setUser(data);
      return true;
    } catch (error: any) {
      console.error('❌ loadProfile 失败:', error?.message || error);
      console.error('❌ 错误详情:', JSON.stringify(error, null, 2));
      // 如果获取用户信息失败（可能 token 过期），重置登录状态
      setIsLoggedIn(false);
      setUser(null);
      return false;
    }
  };

  const loadStats = async () => {
    // 再次检查 token，避免无效请求
    if (!getToken()) return;
    
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

  // 点击头像/用户信息区域，未登录时直接发起微信登录
  const handleHeaderClick = async () => {
    // 初始化中、已登录、正在登录中，都不处理点击
    if (isInitializing || isLoggedIn || wechatLoading) return;
    
    setWechatLoading(true);
    
    try {
      // 1. 获取微信登录 code
      const loginRes = await Taro.login();
      console.log("🚀 ~ handleHeaderClick ~ loginRes:", loginRes)
      const code = loginRes.code;
      console.log("🚀 ~ handleHeaderClick ~ code:", code)
      
      if (!code) {
        throw new Error('获取登录凭证失败');
      }
      
      // 2. 调用后端接口获取 openid
      const storeId = getStoreId();
      console.log("🚀 ~ handleHeaderClick ~ storeId:", storeId)
      const result = await authApi.wechatLogin(code, storeId || undefined);
      console.log("🚀 ~ handleHeaderClick ~ result:", result);
      console.log("🚀 ~ result 类型:", typeof result);
      console.log("🚀 ~ result.isNewUser:", result.isNewUser);
      console.log("🚀 ~ result.needBindPhone:", result.needBindPhone);
      console.log("🚀 ~ result.openid:", result.openid);
      console.log("🚀 ~ 条件判断:", result.isNewUser || result.needBindPhone);
      
      if (result.isNewUser || result.needBindPhone) {
        // 新用户，显示设置头像昵称弹窗
        console.log("🚀 ~ 进入新用户分支，准备显示设置用户信息弹窗");
        setOpenid(result.openid);
        setShowUserInfo(true);
        console.log("🚀 ~ setShowUserInfo(true) 已调用");
        // 已注释：原来需要绑定手机号
        // setShowBindPhone(true);
      } else {
        // 已有用户，直接登录成功
        console.log("🚀 ~ 登录成功，准备保存 Token:", result.accessToken);
        
        if (!result.accessToken) {
          console.error("❌ accessToken 为空！检查后端返回的数据结构");
          Taro.showToast({ title: '登录失败：Token 为空', icon: 'none' });
          return;
        }
        
        setToken(result.accessToken);
        
        // 验证 Token 是否保存成功
        const savedToken = Taro.getStorageSync('hospital_token');
        console.log("🚀 ~ 验证保存的 Token:", savedToken ? `${savedToken.substring(0, 20)}...` : '空');
        
        Taro.showToast({ title: '登录成功', icon: 'success' });
        setIsLoggedIn(true);
        // 加载用户信息和统计数据
        loadProfile();
        loadStats();
      }
    } catch (error: any) {
      Taro.showToast({ title: error.message || '微信登录失败', icon: 'none' });
    } finally {
      setWechatLoading(false);
    }
  };

  // 选择头像回调
  const handleChooseAvatar = (e: any) => {
    console.log("🚀 ~ handleChooseAvatar ~ e:", e);
    const avatarUrl = e.detail.avatarUrl;
    if (avatarUrl) {
      setAvatar(avatarUrl);
    }
  };

  // 昵称输入完成回调
  const handleNicknameBlur = (e: any) => {
    console.log("🚀 ~ handleNicknameBlur ~ e:", e);
    const value = e.detail.value;
    if (value) {
      setNickname(value);
    }
  };

  // 确认用户信息并完成登录
  const handleConfirmUserInfo = async () => {
    if (!nickname.trim()) {
      Taro.showToast({ title: '请输入昵称', icon: 'none' });
      return;
    }

    setBindLoading(true);
    try {
      const result = await authApi.wechatBindUserInfo(openid, nickname, avatar);
      setToken(result.accessToken);
      if (result.user) {
        setStorage(STORAGE_KEYS.USER_INFO, result.user);
      }
      setShowUserInfo(false);
      Taro.showToast({ title: '登录成功', icon: 'success' });
      setIsLoggedIn(true);
      loadProfile();
      loadStats();
    } catch (error: any) {
      console.log("🚀 ~ handleConfirmUserInfo ~ error:", error);
      Taro.showToast({ title: error.message || '登录失败', icon: 'none' });
    } finally {
      setBindLoading(false);
    }
  };

  // 跳过设置，使用默认信息登录
  const handleSkipUserInfo = async () => {
    setBindLoading(true);
    try {
      const result = await authApi.wechatBindUserInfo(openid, '微信用户', '');
      setToken(result.accessToken);
      if (result.user) {
        setStorage(STORAGE_KEYS.USER_INFO, result.user);
      }
      setShowUserInfo(false);
      Taro.showToast({ title: '登录成功', icon: 'success' });
      setIsLoggedIn(true);
      loadProfile();
      loadStats();
    } catch (error: any) {
      Taro.showToast({ title: error.message || '登录失败', icon: 'none' });
    } finally {
      setBindLoading(false);
    }
  };

  /* 已注释：微信获取手机号相关代码
  const handleGetPhoneNumber = async (e: any) => {
    if (e.detail.errMsg !== 'getPhoneNumber:ok') {
      return;
    }

    const code = e.detail.code;
    if (!code) {
      Taro.showToast({ title: '获取手机号失败', icon: 'none' });
      return;
    }

    setBindLoading(true);
    try {
      const storeId = getStoreId();
      const result = await authApi.wechatGetPhone(code, openid, storeId || undefined);
      setToken(result.accessToken);
      if (result.user) {
        setStorage(STORAGE_KEYS.USER_INFO, result.user);
      }
      setShowBindPhone(false);
      Taro.showToast({ title: '登录成功', icon: 'success' });
      setIsLoggedIn(true);
      loadProfile();
      loadStats();
    } catch (error: any) {
      Taro.showToast({ title: error.message || '获取手机号失败', icon: 'none' });
    } finally {
      setBindLoading(false);
    }
  };

  const handleBindPhone = async () => {
    if (!bindPhone || !/^1\d{10}$/.test(bindPhone)) {
      Taro.showToast({ title: '请输入正确的手机号', icon: 'none' });
      return;
    }

    setBindLoading(true);
    try {
      const result = await authApi.wechatBindPhone(openid, bindPhone);
      setToken(result.accessToken);
      if (result.user) {
        setStorage(STORAGE_KEYS.USER_INFO, result.user);
      }
      setShowBindPhone(false);
      setBindPhone('');
      Taro.showToast({ title: '绑定成功', icon: 'success' });
      setIsLoggedIn(true);
      loadProfile();
      loadStats();
    } catch (error: any) {
      Taro.showToast({ title: error.message || '绑定失败', icon: 'none' });
    } finally {
      setBindLoading(false);
    }
  };
  */

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
              {isInitializing ? '加载中...' : (wechatLoading ? '登录中...' : (isLoggedIn ? (user?.nickname || '未设置昵称') : '点击登录'))}
            </Text>
            <Text className="phone">
              {isLoggedIn
                ? (user?.phone?.replace(/(\d{3})\d{4}(\d{4})/, '$1****$2') || '')
                : '登录后享受更多服务'}
            </Text>
          </View>
          {!isLoggedIn && !wechatLoading && !isInitializing && <Text className="login-arrow">›</Text>}
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

      {/* 设置用户信息弹窗 - 获取头像昵称 */}
      {showUserInfo && (
        <View className="user-info-mask" onClick={() => setShowUserInfo(false)}>
          <View className="user-info-sheet" onClick={(e) => e.stopPropagation()}>
            <View className="sheet-header">
              <Text className="sheet-title">完善个人信息</Text>
              <Text className="sheet-close" onClick={() => setShowUserInfo(false)}>×</Text>
            </View>
            <View className="sheet-content">
              <Text className="tip">请设置您的头像和昵称</Text>
              
              {/* 头像选择 */}
              <View className="avatar-section">
                <TaroButton
                  openType="chooseAvatar"
                  onChooseAvatar={handleChooseAvatar}
                  className="avatar-btn"
                >
                  {avatar ? (
                    <Image src={avatar} className="avatar-img" mode="aspectFill" />
                  ) : (
                    <View className="avatar-placeholder">
                      <Text className="avatar-icon">+</Text>
                      <Text className="avatar-text">选择头像</Text>
                    </View>
                  )}
                </TaroButton>
              </View>

              {/* 昵称输入 */}
              <View className="nickname-section">
                <Text className="label">昵称</Text>
                <TaroInput
                  type="nickname"
                  className="nickname-input"
                  placeholder="请输入昵称"
                  value={nickname}
                  onBlur={handleNicknameBlur}
                  onInput={(e) => setNickname(e.detail.value)}
                />
              </View>

              {/* 确认按钮 */}
              <Button 
                type="primary" 
                block 
                loading={bindLoading}
                onClick={handleConfirmUserInfo}
                className="confirm-btn"
              >
                确认并登录
              </Button>

              {/* 跳过按钮 */}
              <View className="skip-section">
                <Text className="skip-btn" onClick={handleSkipUserInfo}>
                  跳过，稍后设置
                </Text>
              </View>
            </View>
          </View>
        </View>
      )}
    </View>
  );
};

export default ProfilePage;
