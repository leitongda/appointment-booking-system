import { Form, Input, Button, Toast, NavBar } from 'antd-mobile';
import { history } from 'umi';
import { useState, useRef } from 'react';
import { authApi } from '@hospital/api';
import styles from './index.less';

const RegisterPage: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [sendingCode, setSendingCode] = useState(false);
  const [countdown, setCountdown] = useState(0);
  const [form] = Form.useForm();
  const timerRef = useRef<NodeJS.Timeout>();

  const startCountdown = () => {
    setCountdown(60);
    timerRef.current = setInterval(() => {
      setCountdown((prev) => {
        if (prev <= 1) {
          clearInterval(timerRef.current);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
  };

  const handleSendCode = async () => {
    const phone = form.getFieldValue('phone');
    if (!phone || !/^1\d{10}$/.test(phone)) {
      Toast.show({ content: '请输入正确的手机号' });
      return;
    }

    setSendingCode(true);
    try {
      await authApi.sendCode(phone, 'register');
      Toast.show({ content: '验证码已发送', icon: 'success' });
      startCountdown();
    } catch (error: any) {
      Toast.show({ content: error.message || '发送失败', icon: 'fail' });
    } finally {
      setSendingCode(false);
    }
  };

  const onFinish = async (values: { phone: string; password: string; code: string; name: string }) => {
    if (values.password !== form.getFieldValue('confirmPassword')) {
      Toast.show({ content: '两次密码输入不一致' });
      return;
    }

    setLoading(true);
    try {
      await authApi.register({
        phone: values.phone,
        password: values.password,
        code: values.code,
        name: values.name,
      });

      Toast.show({ content: '注册成功，请登录', icon: 'success' });
      history.replace('/login');
    } catch (error: any) {
      Toast.show({ content: error.message || '注册失败', icon: 'fail' });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={styles.container}>
      <NavBar onBack={() => history.back()}>注册账号</NavBar>
      
      <div className={styles.formWrapper}>
        <Form 
          form={form}
          layout="vertical" 
          onFinish={onFinish}
          footer={
            <Button 
              block 
              color="primary" 
              type="submit" 
              size="large"
              loading={loading}
            >
              注册
            </Button>
          }
        >
          <Form.Item 
            name="name" 
            label="姓名"
            rules={[{ required: true, message: '请输入姓名' }]}
          >
            <Input placeholder="请输入真实姓名" />
          </Form.Item>
          
          <Form.Item 
            name="phone" 
            label="手机号"
            rules={[
              { required: true, message: '请输入手机号' },
              { pattern: /^1\d{10}$/, message: '请输入正确的手机号' },
            ]}
          >
            <Input placeholder="请输入手机号" type="tel" maxLength={11} />
          </Form.Item>
          
          <Form.Item 
            name="code" 
            label="验证码"
            rules={[{ required: true, message: '请输入验证码' }]}
            extra={
              <Button 
                size="small" 
                onClick={handleSendCode}
                disabled={countdown > 0}
                loading={sendingCode}
              >
                {countdown > 0 ? `${countdown}s后重试` : '获取验证码'}
              </Button>
            }
          >
            <Input placeholder="请输入验证码" maxLength={6} />
          </Form.Item>
          
          <Form.Item 
            name="password" 
            label="密码"
            rules={[
              { required: true, message: '请输入密码' },
              { min: 6, message: '密码至少6位' },
            ]}
          >
            <Input placeholder="请输入密码（至少6位）" type="password" />
          </Form.Item>
          
          <Form.Item 
            name="confirmPassword" 
            label="确认密码"
            rules={[{ required: true, message: '请再次输入密码' }]}
          >
            <Input placeholder="请再次输入密码" type="password" />
          </Form.Item>
        </Form>
      </div>
      
      <div className={styles.loginLink}>
        已有账号？<span onClick={() => history.push('/login')}>立即登录</span>
      </div>
    </div>
  );
};

export default RegisterPage;

