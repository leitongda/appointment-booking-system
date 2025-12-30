import { View, Text, Button as TaroButton, Image, Input as TaroInput } from '@tarojs/components';
import Taro from '@tarojs/taro';
import { Form, Input, Button } from '@nutui/nutui-react-taro';
import { useState } from 'react';
import { authApi } from '@hospital/api';
import { STORAGE_KEYS } from '@hospital/shared';
import { setToken, setStorage } from '../../utils/auth';
import { HospitalIcon } from '../../components/Icons';
import { getStoreId } from '../../utils/store';
import './index.less';

const LoginPage = () => {
  const [loading, setLoading] = useState(false);
  const [wechatLoading, setWechatLoading] = useState(false);
  const [openid, setOpenid] = useState('');
  
  // 用户信息设置弹窗状态
  const [showUserInfo, setShowUserInfo] = useState(false);
  const [avatar, setAvatar] = useState('');
  const [nickname, setNickname] = useState('');
  
  // 已注释：绑定手机号相关状态
  // const [showBindPhone, setShowBindPhone] = useState(false);
  // const [bindPhone, setBindPhone] = useState('');

  // 普通手机号登录
  const handleSubmit = async (values: { phone: string; password: string }) => {
    if (!values.phone || !values.password) {
      Taro.showToast({ title: '请填写完整信息', icon: 'none' });
      return;
    }

    setLoading(true);
    try {
      const result = await authApi.login(values);
      setToken(result.accessToken);
      setStorage(STORAGE_KEYS.USER_INFO, result.user);
      Taro.showToast({ title: '登录成功', icon: 'success' });
      Taro.switchTab({ url: '/pages/index/index' });
    } catch (error: any) {
      Taro.showToast({ title: error.message || '登录失败', icon: 'none' });
    } finally {
      setLoading(false);
    }
  };

  // 微信一键登录
  const handleWechatLogin = async () => {
    setWechatLoading(true);
    
    try {
      // 1. 获取微信登录 code
      const loginRes = await Taro.login();
      console.log("🚀 ~ handleWechatLogin ~ loginRes:", loginRes)
      const code = loginRes.code;
      console.log("🚀 ~ handleWechatLogin ~ code:", code)
      
      if (!code) {
        throw new Error('获取登录凭证失败');
      }
      
      // 2. 调用后端接口获取 openid（传递门店ID以使用对应的微信配置）
      const storeId = getStoreId();
      console.log("🚀 ~ handleWechatLogin ~ storeId:", storeId)
      const result = await authApi.wechatLogin(code, storeId || undefined);
      console.log("🚀 ~ handleWechatLogin ~ result:", result)
      
      if (result.isNewUser || result.needBindPhone) {
        // 新用户，显示设置头像昵称弹窗
        setOpenid(result.openid);
        setShowUserInfo(true);
        // 已注释：原来需要绑定手机号
        // setShowBindPhone(true);
      } else {
        // 已有用户，直接登录成功
        setToken(result.accessToken!);
        Taro.showToast({ title: '登录成功', icon: 'success' });
        Taro.switchTab({ url: '/pages/index/index' });
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

    setLoading(true);
    try {
      // 调用后端接口保存用户信息并完成登录
      const result = await authApi.wechatBindUserInfo(openid, nickname, avatar);
      setToken(result.accessToken);
      setStorage(STORAGE_KEYS.USER_INFO, result.user);
      setShowUserInfo(false);
      Taro.showToast({ title: '登录成功', icon: 'success' });
      Taro.switchTab({ url: '/pages/index/index' });
    } catch (error: any) {
      console.log("🚀 ~ handleConfirmUserInfo ~ error:", error);
      Taro.showToast({ title: error.message || '登录失败', icon: 'none' });
    } finally {
      setLoading(false);
    }
  };

  /* 已注释：微信获取手机号相关代码
  const handleGetPhoneNumber = async (e: any) => {
    console.log("🚀 ~ handleGetPhoneNumber ~ e:", e);
    console.log("🚀 ~ handleGetPhoneNumber ~ e.detail:", e.detail);
    
    if (e.detail.errMsg !== 'getPhoneNumber:ok') {
      console.log("🚀 ~ 用户取消或授权失败:", e.detail.errMsg);
      if (e.detail.errMsg?.includes('deny') || e.detail.errMsg?.includes('cancel')) {
        Taro.showToast({ title: '您取消了授权', icon: 'none' });
      } else {
        Taro.showToast({ title: `授权失败: ${e.detail.errMsg || '未知错误'}`, icon: 'none' });
      }
      return;
    }

    const code = e.detail.code;
    if (!code) {
      Taro.showToast({ title: '获取手机号失败，请重试', icon: 'none' });
      return;
    }

    setWechatLoading(true);
    try {
      const storeId = getStoreId();
      const result = await authApi.wechatGetPhone(code, openid, storeId || undefined);
      setToken(result.accessToken);
      setStorage(STORAGE_KEYS.USER_INFO, result.user);
      setShowBindPhone(false);
      Taro.showToast({ title: '登录成功', icon: 'success' });
      Taro.switchTab({ url: '/pages/index/index' });
    } catch (error: any) {
      Taro.showToast({ title: error.message || '获取手机号失败', icon: 'none' });
    } finally {
      setWechatLoading(false);
    }
  };

  const handleBindPhone = async () => {
    if (!bindPhone || !/^1\d{10}$/.test(bindPhone)) {
      Taro.showToast({ title: '请输入正确的手机号', icon: 'none' });
      return;
    }

    setLoading(true);
    try {
      const result = await authApi.wechatBindPhone(openid, bindPhone);
      setToken(result.accessToken);
      setStorage(STORAGE_KEYS.USER_INFO, result.user);
      setShowBindPhone(false);
      Taro.showToast({ title: '绑定成功', icon: 'success' });
      Taro.switchTab({ url: '/pages/index/index' });
    } catch (error: any) {
      Taro.showToast({ title: error.message || '绑定失败', icon: 'none' });
    } finally {
      setLoading(false);
    }
  };
  */

  return (
    <View className="login-page">
      {/* 头部 */}
      <View className="header">
        <View className="logo">
          <HospitalIcon size={48} color="#4F46E5" />
        </View>
        <Text className="title">医院挂号系统</Text>
        <Text className="subtitle">便捷预约，健康生活</Text>
      </View>

      {/* 微信一键登录 */}
      <View className="wechat-login">
        <Button 
          type="primary" 
          block 
          loading={wechatLoading}
          onClick={handleWechatLogin}
        >
          微信一键登录
        </Button>
      </View>

      {/* 分隔线 */}
      <View className="divider">
        <View className="line" />
        <Text className="text">或使用手机号登录</Text>
        <View className="line" />
      </View>

      {/* 表单 */}
      <View className="form-wrap">
        <Form onFinish={handleSubmit}>
          <Form.Item name="phone" rules={[{ required: true, message: '请输入手机号' }]}>
            <Input placeholder="请输入手机号" type="tel" maxLength={11} />
          </Form.Item>
          <Form.Item name="password" rules={[{ required: true, message: '请输入密码' }]}>
            <Input placeholder="请输入密码" type="password" />
          </Form.Item>
          <Button type="primary" block formType="submit" loading={loading}>
            登录
          </Button>
        </Form>
      </View>

      {/* 底部 */}
      <View className="footer">
        <Text className="tip">首次登录将自动创建账号</Text>
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
                loading={loading}
                onClick={handleConfirmUserInfo}
                className="confirm-btn"
              >
                确认并登录
              </Button>

              {/* 跳过按钮 */}
              <View className="skip-section">
                <Text 
                  className="skip-btn"
                  onClick={async () => {
                    // 跳过设置，使用默认信息登录
                    setLoading(true);
                    try {
                      const result = await authApi.wechatBindUserInfo(openid, '微信用户', '');
                      setToken(result.accessToken);
                      setStorage(STORAGE_KEYS.USER_INFO, result.user);
                      setShowUserInfo(false);
                      Taro.showToast({ title: '登录成功', icon: 'success' });
                      Taro.switchTab({ url: '/pages/index/index' });
                    } catch (error: any) {
                      Taro.showToast({ title: error.message || '登录失败', icon: 'none' });
                    } finally {
                      setLoading(false);
                    }
                  }}
                >
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

export default LoginPage;
