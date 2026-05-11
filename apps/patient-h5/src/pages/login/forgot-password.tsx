import { Form, Input, Toast, NavBar } from 'antd-mobile';
import { history } from 'umi';
import { useState } from 'react';
import { motion } from 'framer-motion';
import { authApi } from '@hospital/api';
import { Button, Card, GradientText } from '@/components/ui';
import { fadeInUp } from '@/components/ui/animations';

const ForgotPasswordPage: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [sendingCode, setSendingCode] = useState(false);
  const [countdown, setCountdown] = useState(0);
  const [form] = Form.useForm();

  const handleSendCode = async () => {
    const phone = form.getFieldValue('phone');
    if (!phone) {
      Toast.show({ content: '请先输入手机号', icon: 'fail' });
      return;
    }

    if (!/^1\d{10}$/.test(phone)) {
      Toast.show({ content: '请输入正确的手机号', icon: 'fail' });
      return;
    }

    setSendingCode(true);
    try {
      const result = await authApi.sendCode(phone, 'reset');
      Toast.show({
        content: `验证码已发送${result.code ? '：' + result.code : ''}`,
        icon: 'success',
      });

      // 开始倒计时
      setCountdown(60);
      const timer = setInterval(() => {
        setCountdown((prev) => {
          if (prev <= 1) {
            clearInterval(timer);
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

  const onFinish = async (values: { phone: string; code: string; newPassword: string; confirmPassword: string }) => {
    if (values.newPassword !== values.confirmPassword) {
      Toast.show({ content: '两次输入的新密码不一致', icon: 'fail' });
      return;
    }

    // 验证密码长度
    if (values.newPassword.length < 6 || values.newPassword.length > 20) {
      Toast.show({ content: '密码长度必须为6-20位', icon: 'fail' });
      return;
    }

    setLoading(true);
    try {
      await authApi.forgotPassword({
        phone: values.phone,
        verificationCode: values.code,
        newPassword: values.newPassword,
      });
      Toast.show({ content: '密码重置成功，请使用新密码登录', icon: 'success' });
      form.resetFields();
      setTimeout(() => {
        history.push('/login');
      }, 1500);
    } catch (error: any) {
      Toast.show({ content: error.message || '密码重置失败', icon: 'fail' });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-background">
      <NavBar onBack={() => history.back()}>忘记密码</NavBar>

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
              name="phone"
              label="手机号"
              rules={[
                { required: true, message: '请输入手机号' },
                { pattern: /^1\d{10}$/, message: '请输入正确的手机号' },
              ]}
            >
              <Input
                placeholder="请输入注册时的手机号"
                type="tel"
                maxLength={11}
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

            <Form.Item
              name="newPassword"
              label="新密码"
              rules={[
                { required: true, message: '请输入新密码' },
                { min: 6, message: '密码至少6位' },
                { max: 20, message: '密码最多20位' },
              ]}
            >
              <Input
                placeholder="请输入新密码（6-20位）"
                type="password"
                clearable
              />
            </Form.Item>

            <Form.Item
              name="confirmPassword"
              label="确认新密码"
              dependencies={['newPassword']}
              rules={[
                { required: true, message: '请确认新密码' },
                ({ getFieldValue }) => ({
                  validator(_, value) {
                    if (!value || getFieldValue('newPassword') === value) {
                      return Promise.resolve();
                    }
                    return Promise.reject(new Error('两次输入的密码不一致'));
                  },
                }),
              ]}
            >
              <Input
                placeholder="请再次输入新密码"
                type="password"
                clearable
              />
            </Form.Item>

            <div className="mt-6">
              <Button
                block
                type="submit"
                loading={loading}
              >
                重置密码
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

export default ForgotPasswordPage;
