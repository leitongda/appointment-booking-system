import { View, Text, Button } from '@tarojs/components';
import Taro, { useDidShow, useShareAppMessage } from '@tarojs/taro';
import { useState, type ComponentType } from 'react';
import { userApi } from '@hospital/api';
import type { User } from '@hospital/shared';
import { PageContainer } from '../../components/PageContainer';
import { useTemplate } from '../../contexts/TemplateContext';
import { getToken, removeToken } from '../../utils/auth';
import { triggerCheckinScan } from '../../utils/checkin';
import { CalendarIcon, ScanIcon, HeadsetIcon, AddUserIcon, SettingsIcon, StarIcon, ChatIcon, ShareIcon } from '../../components/Icons';
import LoginPopup from '../../components/LoginPopup';

/** 菜单项配置 - 长辈友好版（对齐竞品：我的挂号/扫码签到/我的收藏/意见反馈/联系客服/就诊人管理/设置/我的分享）
 * contact=微信客服会话（open-type="contact"）；share=转发给朋友（open-type="share"）
 */
interface ProfileMenuItem {
  key: string;
  label: string;
  icon: ComponentType<{ size?: number; color?: string }>;
  path?: string;
  action?: string;
  needLogin?: boolean;
  contact?: boolean;
  share?: boolean;
}

const menuItems: ProfileMenuItem[] = [
  { key: 'appointments', label: '我的挂号', icon: CalendarIcon, path: '/pages/appointment/index', needLogin: true },
  { key: 'checkin', label: '扫码签到', icon: ScanIcon, action: 'checkin', needLogin: true },
  { key: 'favorite', label: '我的收藏', icon: StarIcon, path: '/packageProfile/pages/favorite/index', needLogin: true },
  { key: 'feedback', label: '意见反馈', icon: ChatIcon, path: '/packageProfile/pages/feedback/index', needLogin: true },
  { key: 'service', label: '联系客服', icon: HeadsetIcon, contact: true, needLogin: true },
  { key: 'patient', label: '就诊人管理', icon: AddUserIcon, path: '/packageProfile/pages/patient/index', needLogin: true },
  { key: 'settings', label: '设置', icon: SettingsIcon, path: '/packageProfile/pages/settings/index' },
  { key: 'share', label: '我的分享', icon: ShareIcon, share: true, needLogin: true },
];

/** 个人中心壳层 -- 长辈友好版
 * 大头像、大字号信息、大尺寸菜单项（高度 120rpx）
 */
export function ProfileElderly() {
  const { tokens, tone } = useTemplate();
  const [userInfo, setUserInfo] = useState<User | null>(null);
  const [showLoginPopup, setShowLoginPopup] = useState(false);

  // 转发卡片：分享项经 Button open-type="share" 触发
  useShareAppMessage(() => ({
    title: tone.custom?.orgName || '医馆预约挂号',
    path: '/pages/index/index',
  }));

  useDidShow(() => {
    Taro.eventCenter.trigger('tabbar:change', 2);
    const token = getToken();
    if (token) {
      void loadUserInfo();
    }
  });

  const loadUserInfo = async () => {
    try {
      const data = await userApi.getProfile();
      setUserInfo(data);
    } catch {
      // 静默处理
    }
  };

  const handleLoginSuccess = () => {
    setShowLoginPopup(false);
    void loadUserInfo();
  };

  const handleMenuClick = (item: ProfileMenuItem) => {
    if (item.needLogin && !getToken()) {
      setShowLoginPopup(true);
      return;
    }
    if (item.contact) return; // 客服会话由 Button open-type="contact" 原生处理
    if (item.share) return; // 转发由 Button open-type="share" 原生处理
    // 扫码签到特殊处理
    if (item.action === 'checkin') {
      triggerCheckinScan();
      return;
    }
    if (item.path) {
      // Tab页面使用switchTab
      if (item.path === '/pages/appointment/index') {
        Taro.switchTab({ url: item.path });
      } else {
        Taro.navigateTo({ url: item.path });
      }
    }
  };

  const handleLogout = () => {
    Taro.showModal({
      title: '确认退出',
      content: '确定要退出登录吗？',
      confirmText: '确认',
      cancelText: '再想想',
      confirmColor: tokens.primary,
      success: (res) => {
        if (res.confirm) {
          removeToken();
          setUserInfo(null);
          Taro.showToast({ title: '已退出', icon: 'success' });
        }
      },
    });
  };

  const isLoggedIn = !!getToken();

  return (
    <PageContainer>
      <View style={{ padding: '32rpx' }}>
        {/* 用户信息区 */}
        <View style={{
          backgroundColor: '#FFFFFF',
          borderRadius: '32rpx',
          padding: '48rpx 40rpx',
          marginBottom: '32rpx',
          boxShadow: '0 2rpx 12rpx rgba(0,0,0,0.06)',
          display: 'flex',
          alignItems: 'center',
        }}>
          <View style={{
            width: '120rpx',
            height: '120rpx',
            borderRadius: '60rpx',
            backgroundColor: tokens.primarySoft,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            marginRight: '32rpx',
            flexShrink: 0,
          }}>
            <Text style={{ fontSize: '64rpx' }}>
              {isLoggedIn && userInfo?.avatar ? '' : '\u{1F464}'}
            </Text>
          </View>
          <View style={{ flex: 1 }}>
            {isLoggedIn && userInfo ? (
              <>
                <Text style={{ fontSize: '44rpx', fontWeight: 700, color: '#3D2B1F', display: 'block', marginBottom: '8rpx' }}>
                  {userInfo.nickname || userInfo.phone || '用户'}
                </Text>
                <Text style={{ fontSize: '36rpx', color: '#6B7280' }}>
                  {userInfo.phone || ''}
                </Text>
              </>
            ) : (
              <>
                <Text
	                  onClick={() => setShowLoginPopup(true)}
	                  style={{ fontSize: '44rpx', fontWeight: 700, color: tokens.primary, display: 'block' }}
                >
                  点击登录
                </Text>
                <Text style={{ fontSize: '36rpx', color: '#9CA3AF', marginTop: '8rpx', display: 'block' }}>
                  登录后可以管理预约
                </Text>
              </>
            )}
          </View>
        </View>

        {/* 菜单列表 */}
        <View style={{
          backgroundColor: '#FFFFFF',
          borderRadius: '24rpx',
          overflow: 'hidden',
          boxShadow: '0 2rpx 12rpx rgba(0,0,0,0.06)',
        }}>
          {menuItems.map((item, idx) => {
            const MenuIcon = item.icon;
            const rowStyle = {
              height: '120rpx',
              padding: '0 32rpx',
              display: 'flex',
              alignItems: 'center',
              width: '100%',
              backgroundColor: 'transparent',
              borderRadius: 0,
              margin: 0,
              border: 'none',
              lineHeight: 'normal',
              fontSize: 'inherit',
              textAlign: 'left',
              justifyContent: 'flex-start',
              borderBottom: 'none',
            } as const;
            const content = (
              <>
                <View style={{ marginRight: '24rpx', width: '48rpx', height: '48rpx', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <MenuIcon size={24} color={tokens.primary} />
                </View>
                <Text style={{ flex: 1, fontSize: '36rpx', color: '#3D2B1F' }}>{item.label}</Text>
                <Text style={{ fontSize: '36rpx', color: '#9CA3AF' }}>{'\u203A'}</Text>
              </>
            );
            if (item.contact) {
              return (
                <Button
                  key={item.key}
                  className="weapp-contact-tile"
                  openType="contact"
                  aria-label={item.label}
                  style={rowStyle}
                >
                  {content}
                </Button>
              );
            }
            if (item.share) {
              return (
                <Button
                  key={item.key}
                  openType="share"
                  aria-label={item.label}
                  style={rowStyle}
                >
                  {content}
                </Button>
              );
            }
            return (
              <View
                key={item.key}
                onClick={() => handleMenuClick(item)}
                aria-label={item.label}
                role="button"
                style={{
                  height: '120rpx',
                  padding: '0 32rpx',
                  display: 'flex',
                  alignItems: 'center',
                  borderBottom: idx < menuItems.length - 1 ? '2rpx solid #F3F4F6' : 'none',
                }}
              >
                {content}
              </View>
            );
          })}
        </View>

        {/* 退出登录 */}
        {isLoggedIn && (
          <View
            onClick={handleLogout}
            aria-label="退出登录"
            role="button"
            style={{
              marginTop: '48rpx',
              height: '120rpx',
              borderRadius: '24rpx',
              backgroundColor: '#FFFFFF',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 2rpx 12rpx rgba(0,0,0,0.06)',
            }}
          >
            <Text style={{ fontSize: '36rpx', color: '#D32F2F' }}>退出登录</Text>
          </View>
        )}
      </View>

      <LoginPopup
        visible={showLoginPopup}
        onClose={() => setShowLoginPopup(false)}
        onSuccess={handleLoginSuccess}
      />
    </PageContainer>
  );
}
