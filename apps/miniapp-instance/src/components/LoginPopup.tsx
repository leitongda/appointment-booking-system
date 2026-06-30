import { View, Text } from '@tarojs/components';
import Taro from '@tarojs/taro';
import { useState } from 'react';
import { authApi } from '@hospital/api';
import { setAuthSession } from '../utils/auth';

export interface LoginPopupProps {
  visible: boolean;
  onClose: () => void;
  onSuccess?: () => void;
  onError?: (error: Error) => void;
}

/**
 * 登录弹窗组件 -- 简化版
 * 长辈友好模板使用，提供微信一键登录
 */
const LoginPopup: React.FC<LoginPopupProps> = ({ visible, onClose, onSuccess, onError }) => {
  const [loading, setLoading] = useState(false);

  if (!visible) return null;

  const handleWechatLogin = async () => {
    setLoading(true);
    try {
      const loginRes = await Taro.login();
      if (!loginRes.code) {
        throw new Error('微信登录失败');
      }
      const authResult = await authApi.wechatLogin(loginRes.code);
      if (authResult.accessToken) {
        const loginUser = (authResult as { user?: Parameters<typeof setAuthSession>[0]['user'] }).user;
        setAuthSession({
          accessToken: authResult.accessToken,
          refreshToken: authResult.refreshToken,
          user: loginUser,
        });
        onSuccess?.();
      }
    } catch (err: any) {
      onError?.(err instanceof Error ? err : new Error(err?.message || '登录失败'));
      Taro.showToast({ title: '登录失败，请重试', icon: 'none' });
    } finally {
      setLoading(false);
    }
  };

  return (
    <View style={{
      position: 'fixed',
      bottom: 0,
      left: 0,
      right: 0,
      backgroundColor: '#FFFFFF',
      borderTopLeftRadius: '32rpx',
      borderTopRightRadius: '32rpx',
      padding: '48rpx 32rpx calc(env(safe-area-inset-bottom) + 32rpx)',
      zIndex: 1000,
      boxShadow: '0 -4rpx 24rpx rgba(0,0,0,0.1)',
    }}>
      <View style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '40rpx' }}>
        <Text style={{ fontSize: '40rpx', fontWeight: 700, color: '#3D2B1F' }}>登录</Text>
        <Text onClick={onClose} style={{ fontSize: '40rpx', color: '#9CA3AF', padding: '16rpx' }}>X</Text>
      </View>

      <View
        onClick={loading ? undefined : handleWechatLogin}
        style={{
          height: '120rpx',
          borderRadius: '9999rpx',
          backgroundColor: '#07C160',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          opacity: loading ? 0.6 : 1,
        }}
      >
        <Text style={{ fontSize: '40rpx', fontWeight: 600, color: '#FFFFFF' }}>
          {loading ? '登录中...' : '微信一键登录'}
        </Text>
      </View>

      <Text style={{
        fontSize: '28rpx',
        color: '#9CA3AF',
        textAlign: 'center',
        marginTop: '24rpx',
        display: 'block',
      }}>
        登录即表示同意用户协议和隐私政策
      </Text>
    </View>
  );
};

export default LoginPopup;
