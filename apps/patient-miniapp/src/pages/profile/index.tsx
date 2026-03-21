import { View, Text, Image, Button as TaroButton, Input as TaroInput } from '@tarojs/components';
import Taro, { useDidShow } from '@tarojs/taro';
import { Button } from '@nutui/nutui-react-taro';
import { useState, useEffect } from 'react';
import { userApi, appointmentApi, authApi, storeApi } from '@hospital/api';
import { STORAGE_KEYS } from '@hospital/shared';
import { clearAuthSession, getToken, setStorage, subscribeAuthChange } from '../../utils/auth';
import { getStoreId } from '../../utils/store';
import { applyWechatLoginResult, finalizeWechatUserBinding } from '../../utils/wechatAuth';
import type { User } from '@hospital/shared';
import {
  TeamIcon,
  RecordIcon,
  BellIcon,
  ChatIcon,
  InfoIcon,
  UserIcon,
  HeartIcon,
  PhoneIcon,
} from '../../components/Icons';
import { PageContainer } from '../../components/PageContainer';
import { getImageUrl } from '../../utils/url';
import { useThemePrimaryColor } from '../../utils/theme';
import './index.less';

// 图标组件类型
type IconComponent = typeof TeamIcon;

// 菜单项类型
interface MenuItem {
  icon: IconComponent;
  title: string;
  desc: string;
  path?: string;
  badge?: string;
  action?: string; // 特殊操作标识
}

// 菜单配置
const menuGroups: { items: MenuItem[] }[] = [
  {
    items: [
      { icon: TeamIcon, title: '就诊人管理', desc: '管理就诊人信息', path: '/packageProfile/pages/patient/index' },
      { icon: HeartIcon, title: '我的收藏', desc: '收藏的医生', path: '/packageProfile/pages/favorite/index' },
      { icon: RecordIcon, title: '就诊记录', desc: '查看历史就诊记录', path: '/packageProfile/pages/records/index' },
      { icon: BellIcon, title: '消息通知', desc: '预约提醒、系统通知', path: '/packageProfile/pages/message/index' },
    ],
  },
  {
    items: [
      { icon: ChatIcon, title: '意见反馈', desc: '帮助我们做得更好', path: '/packageProfile/pages/feedback/index' },
      { icon: PhoneIcon, title: '联系我们', desc: '拨打门店电话', action: 'contact' },
      { icon: InfoIcon, title: '关于我们', desc: '了解更多', path: '/packageOther/pages/about/index' },
      { icon: RecordIcon, title: '用户协议', desc: '服务条款', action: 'agreement-user' },
      { icon: RecordIcon, title: '隐私政策', desc: '隐私保护说明', action: 'agreement-privacy' },
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
  const primaryColor = useThemePrimaryColor();
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
  
  // 门店电话
  const [storePhone, setStorePhone] = useState('');

  // 页面显示时更新 TabBar 选中状态
  useDidShow(() => {
    Taro.eventCenter.trigger('tabbar:change', 2);
  });

  useEffect(() => {
    checkLoginStatus();
    loadStoreInfo();
  }, []);

  useEffect(
    () =>
      subscribeAuthChange((payload) => {
        if (payload.type === 'auth:logout' || payload.type === 'auth:expired') {
          setIsLoggedIn(false);
          setUser(null);
          setStats({ appointmentCount: 0, patientCount: 0, messageCount: 0 });
        }
      }),
    []
  );
  
  // 加载门店信息（获取电话号码）
  const loadStoreInfo = async () => {
    const storeId = getStoreId();
    if (!storeId) return;
    
    try {
      const store = await storeApi.getDetail(storeId);
      if (store?.phone) {
        setStorePhone(store.phone);
      }
    } catch (error) {
      console.error('获取门店信息失败', error);
    }
  };

  // 页面显示时刷新数据
  Taro.useDidShow(() => {
    // 如果正在初始化，跳过
    if (isInitializing) return;
    
    // 重新检查登录状态，确保 token 仍然有效
    const token = getToken();
    if (token && isLoggedIn) {
      // 重新加载用户信息（可能从编辑页返回，头像或昵称已更新）
      loadProfile();
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
        clearAuthSession('expired');
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
    try {
      const data = await userApi.getProfile();
      setUser(data);
      setStorage(STORAGE_KEYS.USER_INFO, data);
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

  // 点击头像/用户信息区域
  // 已登录：跳转到个人信息编辑页面
  // 未登录：发起微信登录
  const handleHeaderClick = async () => {
    // 初始化中、正在登录中，不处理点击
    if (isInitializing || wechatLoading) return;
    
    // 已登录用户点击头像，跳转到个人信息编辑页面
    if (isLoggedIn) {
      Taro.navigateTo({ url: '/packageProfile/pages/profile/edit' });
      return;
    }
    
    setWechatLoading(true);
    
    try {
      // 1. 获取微信登录 code
      const loginRes = await Taro.login();
      const code = loginRes.code;
      
      if (!code) {
        throw new Error('获取登录凭证失败');
      }
      
      // 2. 调用后端接口获取 openid
      const storeId = getStoreId();
      const result = await authApi.wechatLogin(code, storeId || undefined);

      const resolution = await applyWechatLoginResult(result);
      if (resolution.status === 'needs-profile') {
        // 新用户，显示设置头像昵称弹窗
        setOpenid(resolution.openid);
        setShowUserInfo(true);
        // 已注释：原来需要绑定手机号
        // setShowBindPhone(true);
      } else {
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
    const avatarUrl = e.detail.avatarUrl;
    if (avatarUrl) {
      setAvatar(avatarUrl);
    }
  };

  // 昵称输入完成回调
  const handleNicknameBlur = (e: any) => {
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
      await finalizeWechatUserBinding(result);
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

  // 跳过设置，使用默认信息登录
  const handleSkipUserInfo = async () => {
    setBindLoading(true);
    try {
      const result = await authApi.wechatBindUserInfo(openid, '微信用户', '');
      await finalizeWechatUserBinding(result);
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
      clearAuthSession('logout');
      setIsLoggedIn(false);
      setUser(null);
      setStats({ appointmentCount: 0, patientCount: 0, messageCount: 0 });
      Taro.showToast({ title: '已退出登录', icon: 'success' });
    }
  };

  // 联系我们 - 显示 ActionSheet 选择拨打电话
  const handleContactUs = async () => {
    if (!storePhone) {
      Taro.showToast({ title: '暂无联系电话', icon: 'none' });
      return;
    }
    
    try {
      const result = await Taro.showActionSheet({
        itemList: [`拨打电话 ${storePhone}`],
      });
      
      if (result.tapIndex === 0) {
        Taro.makePhoneCall({
          phoneNumber: storePhone,
        });
      }
    } catch (error: any) {
      // 用户取消选择时会抛出错误，无需处理
      if (error.errMsg !== 'showActionSheet:fail cancel') {
        console.error('操作失败', error);
      }
    }
  };

  const handleMenuClick = (item: MenuItem) => {
    // 处理特殊操作
    if (item.action === 'contact') {
      handleContactUs();
      return;
    }
    
    // 处理协议页面跳转
    if (item.action === 'agreement-user') {
      Taro.navigateTo({ url: '/packageOther/pages/agreement/index?type=user' });
      return;
    }
    if (item.action === 'agreement-privacy') {
      Taro.navigateTo({ url: '/packageOther/pages/agreement/index?type=privacy' });
      return;
    }
    
    // 需要登录的菜单项
    const requireLoginPaths = [
      '/packageProfile/pages/patient/index',
      '/packageProfile/pages/favorite/index',
      '/packageProfile/pages/records/index',
      '/packageProfile/pages/message/index',
      '/packageProfile/pages/feedback/index',
    ];

    if (item.path) {
      // 检查是否需要登录
      if (requireLoginPaths.includes(item.path) && !isLoggedIn) {
        // 触发登录流程（点击头像区域）
        handleHeaderClick();
        return;
      }
      Taro.navigateTo({ url: item.path });
    } else {
      Taro.showToast({ title: '功能开发中', icon: 'none' });
    }
  };

  const handleStatClick = (type: 'appointment' | 'patient' | 'message') => {
    if (!isLoggedIn) {
      // 触发登录流程
      handleHeaderClick();
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
    <PageContainer className="profile-page">
      {/* 头部区域 */}
      <View className="header">
        <View className="header-content" onClick={handleHeaderClick}>
          <View className="avatar">
            {user?.avatar ? (
              <Image src={getImageUrl(user.avatar)} mode="aspectFill" />
            ) : (
              <UserIcon size={40} color={primaryColor} />
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
          {/* 显示箭头：未登录时或已登录时（可编辑资料） */}
          {!wechatLoading && !isInitializing && <Text className="login-arrow">›</Text>}
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
                    <IconComponent size={22} color={primaryColor} />
                  </View>
                  <View className="menu-content">
                    <Text className="menu-title">{item.title}</Text>
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
          <Button type="danger" className="logout-btn" onClick={handleLogout}>
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
    </PageContainer>
  );
};

export default ProfilePage;
