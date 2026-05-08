import { Form, Input, Toast, NavBar } from 'antd-mobile';
import { history } from 'umi';
import { useState, useRef, useEffect } from 'react';
import { motion } from 'framer-motion';
import { authApi } from '@hospital/api';
import { setToken, setStorage, STORAGE_KEYS, resetTokenExpiredState } from '@hospital/shared';
import { Button, Card, GradientText } from '@/components/ui';
import { fadeInUp } from '@/components/ui/animations';

const EmailLoginPage: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [sendingCode, setSendingCode] = useState(false);
  const [countdown, setCountdown] = useState(0);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const [form] = Form.useForm();

  useEffect(() => {
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, []);

  const handleSendCode = async () => {
    const email = form.getFieldValue('email');
    if (!email) {
      Toast.show({ content: '请先输入邮箱', icon: 'fail' });
      return;
    }

    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      Toast.show({ content: '请输入正确的邮箱地址', icon: 'fail' });
      return;
    }

    setSendingCode(true);
    try {
      await authApi.sendEmailCode(email, 'login');
      Toast.show({ content: '验证码已发送，请查收邮箱', icon: 'success' });

      // 开始倒计时
      setCountdown(60);
      timerRef.current = setInterval(() => {
        setCountdown((prev) => {
          if (prev <= 1) {
            if (timerRef.current) {
              clearInterval(timerRef.current);
              timerRef.current = null;
            }
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
    } catch (error: any) {
      Toast.show({ content: error.message || '发送验证码失败', icon: 'fail' });
    } finally {
      setSendingCode(false);
    }
  };

  const onFinish = async (values: { email: string; code: string }) => {
    setLoading(true);
    try {
      const result = await authApi.emailLogin({
        email: values.email,
        code: values.code,
      });

      // 保存 Token（复用现有登录成功逻辑）
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
      Toast.show({ content: error.message || '登录失败，请检查邮箱和验证码', icon: 'fail' });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-background">
      <NavBar onBack={() => history.back()}>邮箱登录</NavBar>

      <motion.div
        className="px-4 py-6"
        variants={fadeInUp}
        initial="hidden"
        animate="visible"
      >
        <Card padding="lg">
          <Form
            form={form}
            layout="vertical"
            footer={null}
            onFinish={onFinish}
          >
            <Form.Item
              name="email"
              label="邮箱"
              rules={[
                { required: true, message: '请输入邮箱' },
                { type: 'email', message: '请输入正确的邮箱地址' },
              ]}
            >
              <Input
                placeholder="请输入邮箱地址"
                clearable
              />
            </Form.Item>

            <Form.Item
              name="code"
              label="验证码"
              rules={[
                { required: true, message: '请输入验证码' },
              ]}
              extra={
                <Button
                  variant="outline"
                  size="sm"
                  disabled={countdown > 0 || sendingCode}
                  onClick={handleSendCode}
                  className="mt-2"
                  style={{ width: '100%' }}
                >
                  {sendingCode ? '发送中...' : countdown > 0 ? `${countdown}秒后重试` : '获取验证码'}
                </Button>
              }
            >
              <Input
                placeholder="请输入验证码"
                type="tel"
                maxLength={6}
                clearable
              />
            </Form.Item>

            <div className="mt-6">
              <Button
                block
                type="submit"
                loading={loading}
              >
                登录
              </Button>
            </div>
          </Form>
        </Card>

        <motion.div
          className="mt-6 text-center"
          variants={fadeInUp}
        >
          <p className="text-sm text-muted-foreground">
            验证码5分钟内有效，请及时输入
          </p>
        </motion.div>
      </motion.div>
    </div>
  );
};

export default EmailLoginPage;
