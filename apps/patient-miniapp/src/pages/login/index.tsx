import { View, Text } from '@tarojs/components';
import Taro from '@tarojs/taro';
import { Form, Input, Button } from '@nutui/nutui-react-taro';
import { useState } from 'react';
import { authApi } from '@hospital/api';
import { setToken, setStorage, STORAGE_KEYS } from '@hospital/shared';
import './index.less';

const LoginPage = () => {
  const [loading, setLoading] = useState(false);

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

  return (
    <View className="login-page">
      <View className="header">
        <Text className="logo">🏥</Text>
        <Text className="title">医院挂号系统</Text>
        <Text className="subtitle">便捷预约，健康生活</Text>
      </View>

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

      <View className="footer">
        <Text className="link">忘记密码</Text>
        <Text className="divider">|</Text>
        <Text className="link">注册账号</Text>
      </View>
    </View>
  );
};

export default LoginPage;

