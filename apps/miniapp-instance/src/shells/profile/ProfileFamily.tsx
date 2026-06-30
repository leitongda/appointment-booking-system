import { View, Text, Image, Button as TaroButton, Input as TaroInput } from '@tarojs/components';
import Taro, { useDidShow } from '@tarojs/taro';
import { Button } from '@nutui/nutui-react-taro';
import { useState, useEffect } from 'react';
import { userApi, appointmentApi, authApi, storeApi, favoriteApi } from '@hospital/api';
import { STORAGE_KEYS } from '@hospital/shared';
import { clearAuthSession, getToken, setStorage, subscribeAuthChange } from '../../utils/auth';
import { getStoreId } from '../../utils/store';
import { applyWechatLoginResult, finalizeWechatUserBinding } from '../../utils/wechatAuth';
import type { User, Patient } from '@hospital/shared';
import {
  TeamIcon,
  RecordIcon,
  BellIcon,
  ChatIcon,
  InfoIcon,
  UserIcon,
  HeartIcon,
  PhoneIcon,
  BabyIcon,
  CalendarIcon,
} from '../../components/Icons';
import { PageContainer } from '../../components/PageContainer';
import { useTemplate } from '../../contexts/TemplateContext';
import { getImageUrl } from '../../utils/url';
import { useThemePrimaryColor } from '../../utils/theme';
import './ProfileFamily.less';

// 图标组件类型
type IconComponent = typeof TeamIcon;

// 菜单项类型
interface MenuItem {
  icon: IconComponent;
  title: string;
  desc: string;
  path?: string;
  action?: string;
}

// 菜单配置 - 亲子儿科版
const menuGroups: { items: MenuItem[] }[] = [
  {
    items: [
      { icon: CalendarIcon, title: '我的预约', desc: '查看预约记录', path: '/pages/appointment/index' },
      { icon: RecordIcon, title: '就诊记录', desc: '查看历史就诊记录', path: '/packageProfile/pages/records/index' },
      { icon: TeamIcon, title: '就诊人管理', desc: '管理家庭成员', path: '/packageProfile/pages/patient/index' },
    ],
  },
  {
    items: [
      { icon: BabyIcon, title: '疫苗记录', desc: '查看疫苗接种记录', action: 'vaccine-record' },
      { icon: BabyIcon, title: '成长记录', desc: '记录宝贝成长', action: 'growth-reserved' },
    ],
  },
  {
    items: [
      { icon: HeartIcon, title: '我的收藏', desc: '收藏的医生', path: '/packageProfile/pages/favorite/index' },
      { icon: BellIcon, title: '消息通知', desc: '预约提醒、系统通知', path: '/packageProfile/pages/message/index' },
      { icon: ChatIcon, title: '意见反馈', desc: '帮助我们做得更好', path: '/packageProfile/pages/feedback/index' },
      { icon: PhoneIcon, title: '联系我们', desc: '拨打门店电话', action: 'contact' },
      { icon: InfoIcon, title: '关于我们', desc: '了解更多', path: '/packageOther/pages/about/index' },
    ],
  },
];

// 统计数据类型
interface Stats {
  appointmentCount: number;
  visitCount: number;
  favoriteCount: number;
}

/**
 * 个人中心壳层 -- 亲子儿科版
 * 顶部家庭头像组 + 统计卡片 + 分组菜单列表
 */
export function ProfileFamily() {
  const primaryColor = useThemePrimaryColor();
  const { tone } = useTemplate();

  const [user, setUser] = useState<User | null>(null);
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [isInitializing, setIsInitializing] = useState(true);
  const [stats, setStats] = useState<Stats>({ appointmentCount: 0, visitCount: 0, favoriteCount: 0 });
  const [patients, setPatients] = useState<Patient[]>([]);

  // 微信登录相关状态
  const [wechatLoading, setWechatLoading] = useState(false);
  const [openid, setOpenid] = useState('');
  const [bindLoading, setBindLoading] = useState(false);

  // 用户信息设置弹窗
  const [showUserInfo, setShowUserInfo] = useState(false);
  const [avatar, setAvatar] = useState('');
  const [nickname, setNickname] = useState('');

  // 门店电话
  const [storePhone, setStorePhone] = useState('');

  useDidShow(() => {
    Taro.eventCenter.trigger('tabbar:change', 2);
  });

  useEffect(() => {
    checkLoginStatus();
    loadStoreInfo();
  }, []);

  useEffect(
    () =>
      subscribeAuthChange(payload => {
        if (payload.type === 'auth:logout' || payload.type === 'auth:expired') {
          setIsLoggedIn(false);
          setUser(null);
          setStats({ appointmentCount: 0, visitCount: 0, favoriteCount: 0 });
          setPatients([]);
        }
      }),
    []
  );

  const loadStoreInfo = async () => {
    const storeId = getStoreId();
    if (!storeId) return;
    try {
      const store = await storeApi.getDetail(storeId);
      if (store?.phone) setStorePhone(store.phone);
    } catch {
      // 忽略
    }
  };

  Taro.useDidShow(() => {
    if (isInitializing) return;
    const token = getToken();
    if (token && isLoggedIn) {
      loadProfile();
      loadStats();
      loadPatients();
    } else if (!token) {
      setIsLoggedIn(false);
      setUser(null);
      setStats({ appointmentCount: 0, visitCount: 0, favoriteCount: 0 });
      setPatients([]);
    }
  });

  const checkLoginStatus = async () => {
    setIsInitializing(true);
    const token = getToken();
    if (token) {
      const isValid = await loadProfile();
      if (isValid) {
        setIsLoggedIn(true);
        loadStats();
        loadPatients();
      } else {
        clearAuthSession('expired');
        setIsLoggedIn(false);
        setUser(null);
        setStats({ appointmentCount: 0, visitCount: 0, favoriteCount: 0 });
        setPatients([]);
      }
    } else {
      setIsLoggedIn(false);
      setUser(null);
      setStats({ appointmentCount: 0, visitCount: 0, favoriteCount: 0 });
      setPatients([]);
    }
    setIsInitializing(false);
  };

  const loadProfile = async (): Promise<boolean> => {
    try {
      const data = await userApi.getProfile();
      setUser(data);
      setStorage(STORAGE_KEYS.USER_INFO, data);
      return true;
    } catch {
      setIsLoggedIn(false);
      setUser(null);
      return false;
    }
  };

  const loadStats = async () => {
    if (!getToken()) return;
    try {
      const [appointmentsResult, favoritesResult] = await Promise.all([
        appointmentApi.getList({ pageSize: 1 }).catch(() => ({ total: 0, data: [] })),
        favoriteApi.getList({ targetType: 'doctor', pageSize: 1 }).catch(() => ({ total: 0, data: [] })),
      ]);
      setStats({
        appointmentCount: appointmentsResult.total || 0,
        visitCount: patients.length || 0, // 使用就诊人数作为宝宝数
        favoriteCount: favoritesResult.total || 0, // 收藏医生数量
      });
    } catch {
      // 忽略
    }
  };

  const loadPatients = async () => {
    if (!getToken()) return;
    try {
      const patientList = await userApi.getPatients();
      setPatients(patientList);
    } catch {
      // 忽略
    }
  };

  const handleHeaderClick = async () => {
    if (isInitializing || wechatLoading) return;
    if (isLoggedIn) {
      Taro.navigateTo({ url: '/packageProfile/pages/profile/edit' });
      return;
    }

    setWechatLoading(true);
    try {
      const loginRes = await Taro.login();
      const code = loginRes.code;
      if (!code) throw new Error('获取登录凭证失败');

      const storeId = getStoreId();
      const result = await authApi.wechatLogin(code, storeId || undefined);
      const resolution = await applyWechatLoginResult(result);
      if (resolution.status === 'needs-profile') {
        setOpenid(resolution.openid);
        setShowUserInfo(true);
      } else {
        Taro.showToast({ title: '登录成功', icon: 'success' });
        setIsLoggedIn(true);
        loadProfile();
        loadStats();
        loadPatients();
      }
    } catch (error: any) {
      Taro.showToast({ title: error.message || '微信登录失败', icon: 'none' });
    } finally {
      setWechatLoading(false);
    }
  };

  const handleChooseAvatar = (e: any) => {
    const avatarUrl = e.detail.avatarUrl;
    if (avatarUrl) setAvatar(avatarUrl);
  };

  const handleNicknameBlur = (e: any) => {
    const value = e.detail.value;
    if (value) setNickname(value);
  };

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
      loadPatients();
    } catch (error: any) {
      Taro.showToast({ title: error.message || '登录失败', icon: 'none' });
    } finally {
      setBindLoading(false);
    }
  };

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
      loadPatients();
    } catch (error: any) {
      Taro.showToast({ title: error.message || '登录失败', icon: 'none' });
    } finally {
      setBindLoading(false);
    }
  };

  const handleLogout = async () => {
    const result = await Taro.showModal({
      title: '退出登录',
      content: '确定要退出登录吗？',
    });
    if (result.confirm) {
      clearAuthSession('logout');
      setIsLoggedIn(false);
      setUser(null);
      setStats({ appointmentCount: 0, visitCount: 0, favoriteCount: 0 });
      setPatients([]);
      Taro.showToast({ title: '已退出登录', icon: 'success' });
    }
  };

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
        Taro.makePhoneCall({ phoneNumber: storePhone });
      }
    } catch (error: any) {
      if (error.errMsg !== 'showActionSheet:fail cancel') {
        console.error('操作失败', error);
      }
    }
  };

  const handleMenuClick = (item: MenuItem) => {
    if (item.action === 'contact') {
      handleContactUs();
      return;
    }
    if (item.action === 'growth-reserved' || item.action === 'vaccine-reserved') {
      Taro.showToast({ title: '功能开发中', icon: 'none' });
      return;
    }
    if (item.action === 'vaccine-record') {
      // TODO: 后端需要新增疫苗记录 API
      // 目前跳转到就诊记录页面作为占位
      Taro.showToast({ title: '疫苗记录功能开发中', icon: 'none' });
      return;
    }

    const requireLoginPaths = [
      '/packageProfile/pages/patient/index',
      '/packageProfile/pages/favorite/index',
      '/packageProfile/pages/records/index',
      '/packageProfile/pages/message/index',
      '/packageProfile/pages/feedback/index',
      '/packageProfile/pages/vaccine/index',
    ];

    if (item.path) {
      if (requireLoginPaths.includes(item.path) && !isLoggedIn) {
        handleHeaderClick();
        return;
      }
      if (item.path === '/pages/appointment/index') {
        Taro.switchTab({ url: item.path });
      } else {
        Taro.navigateTo({ url: item.path });
      }
    } else {
      Taro.showToast({ title: '功能开发中', icon: 'none' });
    }
  };

  const handleStatClick = (type: 'appointment' | 'visit' | 'favorite') => {
    if (!isLoggedIn) {
      handleHeaderClick();
      return;
    }
    switch (type) {
      case 'appointment':
        Taro.switchTab({ url: '/pages/appointment/index' });
        break;
      case 'visit':
        Taro.navigateTo({ url: '/packageProfile/pages/records/index' });
        break;
      case 'favorite':
        Taro.navigateTo({ url: '/packageProfile/pages/favorite/index' });
        break;
    }
  };

  const handleAddPatient = () => {
    if (!isLoggedIn) {
      handleHeaderClick();
      return;
    }
    Taro.navigateTo({ url: '/packageProfile/pages/patient/edit' });
  };

  return (
    <PageContainer className="profile-page profile-family">
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
          {!wechatLoading && !isInitializing && <Text className="login-arrow">{'>'}</Text>}
        </View>
      </View>

      {/* 家庭头像组 */}
      <View className="family-avatars-section">
        <View className="family-avatars">
          {patients.slice(0, 4).map(patient => (
            <View key={patient.id} className="family-avatar-item">
              {patient.avatar ? (
                <Image className="family-avatar-img" src={getImageUrl(patient.avatar)} mode="aspectFill" />
              ) : (
                <View className="family-avatar-placeholder">
                  <BabyIcon size={20} color={primaryColor} />
                </View>
              )}
            </View>
          ))}
          {patients.length === 0 && isLoggedIn && (
            <View className="family-avatar-item" onClick={handleAddPatient}>
              <View className="family-avatar-placeholder add">
                <Text className="add-icon">+</Text>
              </View>
            </View>
          )}
          {patients.length >= 4 && (
            <View className="family-avatar-item" onClick={() => Taro.navigateTo({ url: '/packageProfile/pages/patient/index' })}>
              <View className="family-avatar-placeholder more">
                <Text className="more-text">...</Text>
              </View>
            </View>
          )}
          {patients.length > 0 && patients.length < 4 && (
            <View className="family-avatar-item" onClick={handleAddPatient}>
              <View className="family-avatar-placeholder add">
                <Text className="add-icon">+</Text>
              </View>
            </View>
          )}
        </View>
        {!isLoggedIn && (
          <View className="family-tip">
            <Text>登录后管理家庭成员</Text>
          </View>
        )}
      </View>

      {/* 统计卡片 */}
      <View className="stats-card">
        <View className="stat-item" onClick={() => handleStatClick('appointment')}>
          <Text className="stat-value">{stats.appointmentCount}</Text>
          <Text className="stat-label">预约数</Text>
        </View>
        <View className="stat-item" onClick={() => handleStatClick('visit')}>
          <Text className="stat-value">{stats.visitCount}</Text>
          <Text className="stat-label">宝宝数</Text>
        </View>
        <View className="stat-item" onClick={() => handleStatClick('favorite')}>
          <Text className="stat-value">{stats.favoriteCount}</Text>
          <Text className="stat-label">待提醒</Text>
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
                    <Text className="menu-desc">{item.desc}</Text>
                  </View>
                  <Text className="menu-arrow">{'>'}</Text>
                </View>
              );
            })}
          </View>
        </View>
      ))}

      {/* 退出登录 */}
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

      {/* 用户信息弹窗 */}
      {showUserInfo && (
        <View className="user-info-mask" onClick={() => setShowUserInfo(false)}>
          <View className="user-info-sheet" onClick={e => e.stopPropagation()}>
            <View className="sheet-header">
              <Text className="sheet-title">完善个人信息</Text>
              <Text className="sheet-close" onClick={() => setShowUserInfo(false)}>x</Text>
            </View>
            <View className="sheet-content">
              <Text className="tip">请设置您的头像和昵称</Text>

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

              <View className="nickname-section">
                <Text className="label">昵称</Text>
                <TaroInput
                  type="nickname"
                  className="nickname-input"
                  placeholder="请输入昵称"
                  value={nickname}
                  onBlur={handleNicknameBlur}
                  onInput={e => setNickname(e.detail.value)}
                />
              </View>

              <Button
                type="primary"
                block
                loading={bindLoading}
                onClick={handleConfirmUserInfo}
                className="confirm-btn"
              >
                确认并登录
              </Button>

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
}
