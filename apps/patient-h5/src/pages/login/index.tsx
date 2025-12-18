import { Form, Input, Button, Toast, Dialog } from 'antd-mobile';
import { history } from 'umi';
import { useState } from 'react';
import { authApi } from '@hospital/api';
import { setToken, setStorage, STORAGE_KEYS, resetTokenExpiredState } from '@hospital/shared';
import styles from './index.less';

const LoginPage: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [form] = Form.useForm();

  const onFinish = async (values: { phone: string; password: string }) => {
    setLoading(true);
    try {
      const result = await authApi.login({
        phone: values.phone,
        password: values.password,
      });
      
      // 保存 Token
      setToken(result.accessToken);
      if (result.refreshToken) {
        setStorage(STORAGE_KEYS.REFRESH_TOKEN, result.refreshToken);
      }
      
      // 保存用户信息
      if (result.user) {
        setStorage(STORAGE_KEYS.USER_INFO, JSON.stringify(result.user));
        localStorage.setItem('userId', result.user.id);
      }
      
      // 重置 token 失效处理状态
      resetTokenExpiredState();
      
      Toast.show({ content: '登录成功', icon: 'success' });
      history.push('/home');
    } catch (error: any) {
      Toast.show({ content: error.message || '登录失败，请检查手机号和密码', icon: 'fail' });
    } finally {
      setLoading(false);
    }
  };

  const handleForgotPassword = () => {
    Dialog.alert({
      content: '请联系医院客服重置密码：400-xxx-xxxx',
      confirmText: '我知道了',
    });
  };

  const handleRegister = () => {
    history.push('/register');
  };

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <div className={styles.logo}>🏥</div>
        <div className={styles.title}>医院挂号系统</div>
        <div className={styles.subtitle}>患者端</div>
      </div>
      <Form 
        form={form}
        layout="horizontal" 
        onFinish={onFinish} 
        className={styles.form}
      >
        <Form.Item 
          name="phone" 
          rules={[
            { required: true, message: '请输入手机号' },
            { pattern: /^1\d{10}$/, message: '请输入正确的手机号' },
          ]}
        >
          <Input placeholder="请输入手机号" type="tel" maxLength={11} />
        </Form.Item>
        <Form.Item 
          name="password" 
          rules={[
            { required: true, message: '请输入密码' },
            { min: 6, message: '密码至少6位' },
          ]}
        >
          <Input placeholder="请输入密码" type="password" />
        </Form.Item>
        <Button 
          block 
          color="primary" 
          type="submit" 
          size="large"
          loading={loading}
        >
          登录
        </Button>
      </Form>
      <div className={styles.footer}>
        <span onClick={handleForgotPassword}>忘记密码</span>
        <span onClick={handleRegister}>注册账号</span>
      </div>
    </div>
  );
};

export default LoginPage;

