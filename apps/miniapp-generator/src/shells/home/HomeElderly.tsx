import { View, Text } from '@tarojs/components';
import Taro, { useDidShow, usePullDownRefresh } from '@tarojs/taro';
import { useState, useEffect } from 'react';
import { doctorApi, contentApi } from '@hospital/api';
import type { Doctor } from '@hospital/shared';
import { PageContainer } from '../../components/PageContainer';
import { useTemplate } from '../../contexts/TemplateContext';
import { getToken, AUTH_EVENTS, subscribeAuthChange } from '../../utils/auth';
import { triggerCheckinScan } from '../../utils/checkin';
import LoginPopup from '../../components/LoginPopup';

/** 超大快捷按钮配置 */
const quickActions = [
  { key: 'register', label: '挂号', icon: '\ud83c\udfe5', path: '/pages/department/index', color: '#8B6F47' },
  { key: 'appointments', label: '我的预约', icon: '\ud83d\udcc5', path: '/pages/appointment/index', color: '#6B5235', needLogin: true },
  { key: 'checkin', label: '扫码签到', icon: '\ud83d\udcf7', action: 'checkin', color: '#A68B5B', needLogin: true },
  { key: 'service', label: '联系客服', icon: '\ud83d\udcde', path: '/packageProfile/pages/feedback/index', color: '#5D4E37', needLogin: true },
];

/** 首页壳层 -- 长辈友好/中医康养
 * 模块：2x2 超大按钮 -> 单条公告 -> 常看医生(2-3名)
 */
export function HomeElderly() {
  const { tokens, tone } = useTemplate();
  const [notice, setNotice] = useState<string>('');
  const [recentDoctors, setRecentDoctors] = useState<Doctor[]>([]);
  const [loading, setLoading] = useState(true);
  const [showLoginPopup, setShowLoginPopup] = useState(false);
  const [pendingCheckin, setPendingCheckin] = useState(false);

  useDidShow(() => {
    Taro.eventCenter.trigger('tabbar:change', 0);
    void loadData();
  });

  usePullDownRefresh(() => {
    loadData().finally(() => Taro.stopPullDownRefresh());
  });

  const loadData = async () => {
    try {
      const [banners, doctors] = await Promise.all([
        contentApi.getActiveBanners('home').catch(() => []),
        doctorApi.getRecommended(3).catch(() => []),
      ]);
      if (banners.length > 0 && banners[0].title) {
        setNotice(banners[0].title);
      }
      setRecentDoctors(doctors.slice(0, 3));
    } catch {
      // 静默失败
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    return subscribeAuthChange((payload) => {
      if (payload.type === AUTH_EVENTS.LOGIN && pendingCheckin) {
        setPendingCheckin(false);
        setShowLoginPopup(false);
        triggerCheckinScan();
      }
      if (payload.type === AUTH_EVENTS.LOGOUT || payload.type === AUTH_EVENTS.EXPIRED) {
        setPendingCheckin(false);
      }
    });
  }, [pendingCheckin]);

  const handleAction = (action: typeof quickActions[0]) => {
    if (action.needLogin && !getToken()) {
      if (action.action === 'checkin') setPendingCheckin(true);
      setShowLoginPopup(true);
      return;
    }
    if (action.action === 'checkin') {
      triggerCheckinScan();
      return;
    }
    if (action.path) {
      const isTab = action.path === '/pages/appointment/index' || action.path === '/pages/profile/index';
      if (isTab) {
        Taro.switchTab({ url: action.path });
      } else {
        Taro.navigateTo({ url: action.path });
      }
    }
  };

  const handleDoctorClick = (doctorId: string) => {
    Taro.navigateTo({ url: `/packageBooking/pages/doctor/detail?id=${doctorId}` });
  };

  const handleLoginSuccess = async () => {
    setShowLoginPopup(false);
  };

  return (
    <PageContainer>
      <View style={{ padding: '32rpx' }}>
        {/* 模块 1: 2x2 超大快捷按钮 */}
        <View style={{
          display: 'grid',
          gridTemplateColumns: '1fr 1fr',
          gap: '24rpx',
          marginBottom: '32rpx',
        }}>
          {quickActions.map((action) => (
            <View
              key={action.key}
              onClick={() => handleAction(action)}
              aria-label={action.label}
              role="button"
              style={{
                height: '160rpx',
                borderRadius: '32rpx',
                backgroundColor: action.color,
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                boxShadow: '0 4rpx 16rpx rgba(139, 111, 71, 0.2)',
              }}
            >
              <Text style={{ fontSize: '56rpx', marginBottom: '8rpx' }}>{action.icon}</Text>
              <Text style={{ fontSize: '36rpx', color: '#FFFFFF', fontWeight: 600 }}>{action.label}</Text>
            </View>
          ))}
        </View>

        {/* 模块 2: 单条公告 */}
        {notice && (
          <View style={{
            marginBottom: '32rpx',
            padding: '32rpx',
            backgroundColor: '#F5EDE0',
            borderRadius: '24rpx',
            borderLeft: `8rpx solid ${tokens.primary}`,
          }}>
            <Text style={{ fontSize: '28rpx', color: '#6B5235', fontWeight: 600 }}>
              {'\ud83d\udce2'} 公告
            </Text>
            <Text style={{ fontSize: '36rpx', color: '#3D2B1F', marginTop: '12rpx', display: 'block', lineHeight: 1.6 }}>
              {notice}
            </Text>
          </View>
        )}

        {/* 模块 3: 常看医生 */}
        <View style={{ marginBottom: '32rpx' }}>
          <Text style={{
            fontSize: '40rpx',
            fontWeight: 700,
            color: '#3D2B1F',
            marginBottom: '24rpx',
            display: 'block',
          }}>
            常看医生
          </Text>

          {!loading && recentDoctors.length === 0 && (
            <View style={{
              padding: '48rpx',
              backgroundColor: '#FFFFFF',
              borderRadius: '24rpx',
              textAlign: 'center',
            }}>
              <Text style={{ fontSize: '36rpx', color: '#9CA3AF' }}>
                {tone.emptyBookingText}
              </Text>
            </View>
          )}

          {recentDoctors.map((doctor) => (
            <View
              key={doctor.id}
              onClick={() => handleDoctorClick(doctor.id)}
              aria-label={`查看医生${doctor.name}的详情`}
              role="button"
              style={{
                marginBottom: '24rpx',
                padding: '32rpx',
                backgroundColor: '#FFFFFF',
                borderRadius: '24rpx',
                display: 'flex',
                alignItems: 'center',
                boxShadow: '0 2rpx 12rpx rgba(0,0,0,0.06)',
              }}
            >
              <View style={{
                width: '96rpx',
                height: '96rpx',
                borderRadius: '48rpx',
                backgroundColor: tokens.primarySoft,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                marginRight: '28rpx',
                flexShrink: 0,
              }}>
                <Text style={{ fontSize: '48rpx' }}>{'\ud83e\ude7a'}</Text>
              </View>
              <View style={{ flex: 1, minWidth: 0 }}>
                <View style={{ display: 'flex', alignItems: 'baseline', marginBottom: '8rpx' }}>
                  <Text style={{ fontSize: '40rpx', fontWeight: 700, color: '#3D2B1F', marginRight: '16rpx' }}>
                    {doctor.name}
                  </Text>
                  {doctor.title && (
                    <Text style={{ fontSize: '32rpx', color: '#8B6F47' }}>{doctor.title}</Text>
                  )}
                </View>
                <Text style={{ fontSize: '32rpx', color: '#6B7280' }}>
                  {doctor.departmentName}
                </Text>
                {doctor.specialty && (
                  <Text style={{ fontSize: '32rpx', color: '#9CA3AF', marginTop: '4rpx' }} numberOfLines={1}>
                    擅长：{doctor.specialty}
                  </Text>
                )}
              </View>
              <Text style={{ fontSize: '36rpx', color: tokens.primary, flexShrink: 0 }}>{'\u203A'}</Text>
            </View>
          ))}
        </View>
      </View>

      <LoginPopup
        visible={showLoginPopup}
        onClose={() => setShowLoginPopup(false)}
        onSuccess={handleLoginSuccess}
      />
    </PageContainer>
  );
}
