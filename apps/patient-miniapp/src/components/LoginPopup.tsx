import { View, Text, Button as TaroButton, Image, Input as TaroInput } from '@tarojs/components';
import Taro from '@tarojs/taro';
import { Button } from '@nutui/nutui-react-taro';
import { useState, useEffect, useCallback } from 'react';
import { authApi, userApi } from '@hospital/api';
import { STORAGE_KEYS } from '@hospital/shared';
import { setToken, setStorage } from '../utils/auth';
import { getStoreId } from '../utils/store';
import { HospitalIcon } from './Icons';
import { getThemePrimaryColor } from '../utils/theme';
import './LoginPopup.less';

export interface LoginPopupProps {
  /** 是否显示弹窗 */
  visible: boolean;
  /** 关闭弹窗回调 */
  onClose: () => void;
  /** 登录成功回调 */
  onSuccess?: () => void;
  /** 登录失败回调 */
  onError?: (error: Error) => void;
}

/**
 * 登录弹窗组件
 * 从底部弹出，提供微信一键登录功能
 */
const LoginPopup: React.FC<LoginPopupProps> = ({
  visible,
  onClose,
  onSuccess,
  onError,
}) => {
  const [wechatLoading, setWechatLoading] = useState(false);
  const [openid, setOpenid] = useState('');
  const [bindLoading, setBindLoading] = useState(false);
  
  // 用户信息设置状态
  const [showUserInfo, setShowUserInfo] = useState(false);
  const [avatar, setAvatar] = useState('');
  const [nickname, setNickname] = useState('');

  // 重置状态
  const resetState = useCallback(() => {
    setWechatLoading(false);
    setOpenid('');
    setBindLoading(false);
    setShowUserInfo(false);
    setAvatar('');
    setNickname('');
  }, []);

  // 关闭时重置状态
  useEffect(() => {
    if (!visible) {
      resetState();
    }
  }, [visible, resetState]);

  // 微信一键登录
  const handleWechatLogin = async () => {
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
      
      if (result.isNewUser || result.needBindPhone) {
        // 新用户，显示设置头像昵称界面
        setOpenid(result.openid);
        setShowUserInfo(true);
      } else {
        // 已有用户，直接登录成功
        
        if (!result.accessToken) {
          console.error("❌ accessToken 为空！");
          throw new Error('登录失败：Token 为空');
        }
        
        setToken(result.accessToken);
        try {
          const profile = await userApi.getProfile();
          setStorage(STORAGE_KEYS.USER_INFO, profile);
        } catch (profileError) {
          console.error('登录后加载用户信息失败', profileError);
        }
        Taro.showToast({ title: '登录成功', icon: 'success' });
        onClose();
        onSuccess?.();
      }
    } catch (error: any) {
      console.error("❌ 微信登录失败:", error);
      Taro.showToast({ title: error.message || '微信登录失败', icon: 'none' });
      onError?.(error);
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

  // 昵称输入回调
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
      setToken(result.accessToken);
      if (result.user) {
        setStorage(STORAGE_KEYS.USER_INFO, result.user);
      }
      Taro.showToast({ title: '登录成功', icon: 'success' });
      onClose();
      onSuccess?.();
    } catch (error: any) {
      console.error("❌ 设置用户信息失败:", error);
      Taro.showToast({ title: error.message || '登录失败', icon: 'none' });
      onError?.(error);
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
      Taro.showToast({ title: '登录成功', icon: 'success' });
      onClose();
      onSuccess?.();
    } catch (error: any) {
      console.error("❌ 跳过设置失败:", error);
      Taro.showToast({ title: error.message || '登录失败', icon: 'none' });
      onError?.(error);
    } finally {
      setBindLoading(false);
    }
  };

  if (!visible) {
    return null;
  }

  return (
    <View className="login-popup-mask" onClick={onClose}>
      <View className="login-popup-sheet" onClick={(e) => e.stopPropagation()}>
        {/* 顶部指示条 */}
        <View className="sheet-indicator" />
        
        {!showUserInfo ? (
          // 登录界面
          <>
            <View className="sheet-header">
              <View className="logo">
                <HospitalIcon size={36} color={getThemePrimaryColor()} />
              </View>
              <Text className="sheet-title">登录医院挂号系统</Text>
              <Text className="sheet-subtitle">便捷预约，健康生活</Text>
            </View>
            
            <View className="sheet-content">
              <Button 
                type="primary" 
                block 
                loading={wechatLoading}
                onClick={handleWechatLogin}
                className="wechat-btn"
              >
                微信一键登录
              </Button>
              
              <Text className="tip">首次登录将自动创建账号</Text>
              
              <View className="agreement">
                <Text>登录即表示同意</Text>
                <Text 
                  className="link" 
                  onClick={() => Taro.navigateTo({ url: '/packageOther/pages/agreement/index?type=user' })}
                >
                  用户协议
                </Text>
                <Text>和</Text>
                <Text 
                  className="link" 
                  onClick={() => Taro.navigateTo({ url: '/packageOther/pages/agreement/index?type=privacy' })}
                >
                  隐私政策
                </Text>
              </View>
            </View>
          </>
        ) : (
          // 设置用户信息界面
          <>
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
          </>
        )}
      </View>
    </View>
  );
};

export default LoginPopup;
