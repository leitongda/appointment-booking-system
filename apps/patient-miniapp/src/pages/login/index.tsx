import { View, Text, Button as TaroButton } from '@tarojs/components';
import Taro from '@tarojs/taro';
import { Form, Input, Button, Dialog } from '@nutui/nutui-react-taro';
import { useState } from 'react';
import { authApi } from '@hospital/api';
import { setToken, setStorage, STORAGE_KEYS } from '@hospital/shared';
import './index.less';

const LoginPage = () => {
  const [loading, setLoading] = useState(false);
  const [wechatLoading, setWechatLoading] = useState(false);
  const [openid, setOpenid] = useState('');
  const [showBindPhone, setShowBindPhone] = useState(false);
  const [bindPhone, setBindPhone] = useState('');

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
      const code = loginRes.code;
      
      if (!code) {
        throw new Error('获取登录凭证失败');
      }
      
      // 2. 调用后端接口获取 openid
      const result = await authApi.wechatLogin(code);
      
      if (result.isNewUser || result.needBindPhone) {
        // 新用户，需要绑定手机号
        setOpenid(result.openid);
        setShowBindPhone(true);
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

  // 微信获取手机号
  const handleGetPhoneNumber = async (e: any) => {
    if (e.detail.errMsg !== 'getPhoneNumber:ok') {
      return;
    }

    const code = e.detail.code;
    if (!code) {
      Taro.showToast({ title: '获取手机号失败', icon: 'none' });
      return;
    }

    setWechatLoading(true);
    try {
      const result = await authApi.wechatGetPhone(code, openid);
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

  // 手动绑定手机号
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

  return (
    <View className="login-page">
      {/* 头部 */}
      <View className="header">
        <View className="logo">
          <Text>🏥</Text>
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

      {/* 绑定手机号弹窗 */}
      <Dialog 
        visible={showBindPhone}
        title="绑定手机号"
        onClose={() => setShowBindPhone(false)}
        footer={null}
      >
        <View className="bind-phone-dialog">
          <Text className="tip">首次登录，请绑定手机号以便接收预约通知</Text>
          
          <TaroButton
            openType="getPhoneNumber"
            onGetPhoneNumber={handleGetPhoneNumber}
            className="wechat-phone-btn"
          >
            微信授权手机号
          </TaroButton>

          <View className="manual-input">
            <Text className="label">或手动输入手机号：</Text>
            <Input
              placeholder="请输入手机号"
              type="tel"
              maxLength={11}
              value={bindPhone}
              onChange={(val) => setBindPhone(val)}
            />
            <Button 
              type="primary" 
              block 
              loading={loading}
              onClick={handleBindPhone}
            >
              确认绑定
            </Button>
          </View>
        </View>
      </Dialog>
    </View>
  );
};

export default LoginPage;
