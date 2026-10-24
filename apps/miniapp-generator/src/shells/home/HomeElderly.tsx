import { View, Text, Button } from '@tarojs/components';
import Taro, { useDidShow, usePullDownRefresh } from '@tarojs/taro';
import { useState, type ReactNode } from 'react';
import { doctorApi, contentApi } from '@hospital/api';
import type { Doctor } from '@hospital/shared';
import { PageContainer } from '../../components/PageContainer';
import { useTemplate } from '../../contexts/TemplateContext';
import { getToken } from '../../utils/auth';
import { SpeakerIcon, HospitalIcon, CalendarIcon, CardIcon, HeadsetIcon, DoctorIcon } from '../../components/Icons';
import LoginPopup from '../../components/LoginPopup';
import PrivacyPopup, { hasAgreedPrivacy } from '../../components/PrivacyPopup';

/** 首页快捷按钮（文案取自模板 tone，对齐竞品四宫格：预约挂号/预约记录/我的就诊卡/在线客服） */
interface HomeQuickAction {
  key: string;
  label: string;
  icon: ReactNode;
  color: string;
  path?: string;
  needLogin?: boolean;
  /** 微信客服会话（open-type="contact"），由按钮原生处理，不走页面跳转 */
  contact?: boolean;
}

/** 首页壳层 -- 长辈友好/中医康养
 * 模块：单条公告(白底圆角横条) -> 2x2 四宫格 -> 添加健康卡 -> 常看医生(2-3名)
 */
export function HomeElderly() {
  const { template, tokens, tone } = useTemplate();
  const [notice, setNotice] = useState<string>('');
  const [recentDoctors, setRecentDoctors] = useState<Doctor[]>([]);
  const [loading, setLoading] = useState(true);
  const [showLoginPopup, setShowLoginPopup] = useState(false);
  // 首次使用弹隐私保护提示（竞品同流程）；同意一次后不再弹
  const [showPrivacy, setShowPrivacy] = useState(() => !hasAgreedPrivacy());

  // 公告栏模块配置：文本优先取模块配置，缺省回落到首条 Banner 标题；linkUrl 未配置则整条不可点击
  const noticeModule = template.homeSchema.find(m => m.type === 'notice' && m.visible);
  const noticeLink = noticeModule?.config?.linkUrl as string | undefined;
  const noticeText = (noticeModule?.config?.text as string | undefined) || notice;

  // 健康卡模块文案：模块 config 优先，缺省回落到模板 tone 与竞品口径
  const healthCardModule = template.homeSchema.find(m => m.type === 'patient_card' && m.visible);
  const healthCardTitle = (healthCardModule?.config?.title as string | undefined)
    || tone.custom?.healthCardTitle || '添加健康卡';
  const healthCardSubtitle = (healthCardModule?.config?.subtitle as string | undefined)
    || tone.custom?.healthCardSubtitle || '记录您的健康';

  // 四宫格贴片色：取模板 designTokens.customColors（竞品绿色主题），缺省回落绿色系
  const tiles = tokens.customColors || {};
  const quickActions: HomeQuickAction[] = [
    { key: 'register', label: tone.bookingLabel, icon: <HospitalIcon size={28} color="#FFFFFF" />, path: '/pages/department/index', color: tiles.tilePrimary || '#5F8F74' },
    { key: 'appointments', label: tone.custom?.appointmentRecordsLabel || '预约记录', icon: <CalendarIcon size={28} color="#FFFFFF" />, path: '/pages/appointment/index', color: tiles.tileSecondary || '#4E8064', needLogin: true },
    { key: 'patient_card', label: tone.patientLabel || '我的就诊卡', icon: <CardIcon size={28} color="#FFFFFF" />, path: '/packageProfile/pages/patient/index', color: tiles.tileTertiary || '#7CA98B', needLogin: true },
    { key: 'service', label: tone.custom?.onlineServiceLabel || '在线客服', icon: <HeadsetIcon size={28} color="#FFFFFF" />, color: tiles.tileQuaternary || '#3E6B52', contact: true },
  ];

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

  const handleAction = (action: HomeQuickAction) => {
    if (action.needLogin && !getToken()) {
      setShowLoginPopup(true);
      return;
    }
    if (action.contact) return; // 客服会话由 Button open-type="contact" 原生处理
    if (action.path) {
      const isTab = action.path === '/pages/appointment/index' || action.path === '/pages/profile/index';
      if (isTab) {
        Taro.switchTab({ url: action.path });
      } else {
        Taro.navigateTo({ url: action.path });
      }
    }
  };

  const handleHealthCardClick = () => {
    if (!getToken()) {
      setShowLoginPopup(true);
      return;
    }
    Taro.navigateTo({ url: '/packageProfile/pages/patient/index' });
  };

  const handleDoctorClick = (doctorId: string) => {
    Taro.navigateTo({ url: `/packageBooking/pages/doctor/detail?id=${doctorId}` });
  };

  const handleNoticeClick = () => {
    if (!noticeLink) return;
    if (/^https?:\/\//.test(noticeLink)) {
      Taro.navigateTo({ url: `/packageOther/pages/webview/index?url=${encodeURIComponent(noticeLink)}` });
      return;
    }
    const isTab = noticeLink === '/pages/appointment/index' || noticeLink === '/pages/profile/index';
    if (isTab) {
      Taro.switchTab({ url: noticeLink });
    } else {
      Taro.navigateTo({ url: noticeLink });
    }
  };

  const handleLoginSuccess = async () => {
    setShowLoginPopup(false);
  };

  return (
    <PageContainer>
      <View style={{ padding: '32rpx' }}>
        {/* 模块 1: 单条公告（白底圆角横条，整条可点击跳转 config.linkUrl） */}
        {noticeText ? (
          <View
            onClick={handleNoticeClick}
            aria-label={`公告：${noticeText}`}
            role={noticeLink ? 'button' : undefined}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '16rpx',
              marginBottom: '32rpx',
              padding: '24rpx 28rpx',
              backgroundColor: '#FFFFFF',
              borderRadius: '24rpx',
              boxShadow: '0 2rpx 12rpx rgba(0,0,0,0.06)',
            }}
          >
            <View style={{ display: 'flex', alignItems: 'center', flexShrink: 0 }}>
              <SpeakerIcon size={36} color={tokens.primary} />
            </View>
            <Text
              numberOfLines={1}
              style={{
                flex: 1,
                minWidth: 0,
                fontSize: '32rpx',
                color: '#22332B',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
              }}
            >
              {noticeText}
            </Text>
          </View>
        ) : null}

        {/* 模块 2: 2x2 四宫格（在线客服为微信客服会话按钮） */}
        <View style={{
          display: 'grid',
          gridTemplateColumns: '1fr 1fr',
          gap: '24rpx',
          marginBottom: '32rpx',
        }}>
          {quickActions.map((action) => action.contact ? (
            <Button
              key={action.key}
              className="weapp-contact-tile"
              openType="contact"
              aria-label={action.label}
              style={{
                height: '160rpx',
                borderRadius: '32rpx',
                backgroundColor: action.color,
                boxShadow: '0 4rpx 16rpx rgba(95, 143, 116, 0.25)',
              }}
            >
              <View style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
              }}>
                <View style={{ marginBottom: '8rpx', height: '56rpx', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  {action.icon}
                </View>
                <Text style={{ fontSize: '36rpx', color: '#FFFFFF', fontWeight: 600 }}>{action.label}</Text>
              </View>
            </Button>
          ) : (
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
                boxShadow: '0 4rpx 16rpx rgba(95, 143, 116, 0.25)',
              }}
            >
              <View style={{ marginBottom: '8rpx', height: '56rpx', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                {action.icon}
              </View>
              <Text style={{ fontSize: '36rpx', color: '#FFFFFF', fontWeight: 600 }}>{action.label}</Text>
            </View>
          ))}
        </View>

        {/* 模块 3: 添加健康卡（竞品同款色块卡，点击进入就诊人管理） */}
        <View
          onClick={handleHealthCardClick}
          aria-label={healthCardTitle}
          role="button"
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '24rpx',
            marginBottom: '32rpx',
            padding: '36rpx 32rpx',
            backgroundColor: tokens.primarySoft,
            borderRadius: '32rpx',
          }}
        >
          <View style={{
            width: '88rpx',
            height: '88rpx',
            borderRadius: '44rpx',
            border: `4rpx solid ${tokens.primary}`,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexShrink: 0,
          }}>
            <Text style={{ fontSize: '52rpx', lineHeight: '52rpx', color: tokens.primary }}>+</Text>
          </View>
          <View style={{ flex: 1 }}>
            <Text style={{ fontSize: '38rpx', fontWeight: 700, color: tokens.accent, display: 'block' }}>
              {healthCardTitle}
            </Text>
            <Text style={{ fontSize: '30rpx', color: tokens.accent, opacity: 0.8, marginTop: '6rpx', display: 'block' }}>
              {healthCardSubtitle}
            </Text>
          </View>
          <Text style={{ fontSize: '40rpx', color: tokens.primary, flexShrink: 0 }}>{'\u203A'}</Text>
        </View>

        {/* 模块 4: 常看医生 */}
        <View style={{ marginBottom: '32rpx' }}>
          <Text style={{
            fontSize: '40rpx',
            fontWeight: 700,
            color: '#22332B',
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
                <DoctorIcon size={24} color={tokens.primary} />
              </View>
              <View style={{ flex: 1, minWidth: 0 }}>
                <View style={{ display: 'flex', alignItems: 'baseline', marginBottom: '8rpx' }}>
                  <Text style={{ fontSize: '40rpx', fontWeight: 700, color: '#22332B', marginRight: '16rpx' }}>
                    {doctor.name}
                  </Text>
                  {doctor.title && (
                    <Text style={{ fontSize: '32rpx', color: tokens.primary }}>{doctor.title}</Text>
                  )}
                  {/* 号源角标（竞品「有号」绿标）：后端返回未来7天号源情况 */}
                  <Text
                    style={{
                      marginLeft: 'auto',
                      paddingLeft: '20rpx',
                      paddingRight: '20rpx',
                      paddingTop: '4rpx',
                      paddingBottom: '4rpx',
                      borderRadius: '9999rpx',
                      fontSize: '28rpx',
                      color: '#FFFFFF',
                      backgroundColor: doctor.hasAvailableSlots ? tokens.primary : '#D1D5DB',
                    }}
                  >
                    {doctor.hasAvailableSlots ? '有号' : '无号'}
                  </Text>
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

      <PrivacyPopup
        visible={showPrivacy}
        onAgree={() => setShowPrivacy(false)}
        orgName={tone.custom?.orgName}
      />
    </PageContainer>
  );
}
