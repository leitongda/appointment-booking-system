import { Form, Input, Toast, Dialog } from 'antd-mobile';
import { history } from 'umi';
import { useState } from 'react';
import { motion } from 'framer-motion';
import { authApi } from '@hospital/api';
import { setToken, setStorage, STORAGE_KEYS, resetTokenExpiredState } from '@hospital/shared';
import { Button, Card, GradientText, RadialGlow } from '@/components/ui';
import { fadeInUp, stagger, viewportOptions } from '@/components/ui/animations';

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
    history.push('/login/forgot-password');
  };

  const handleRegister = () => {
    history.push('/register');
  };

  return (
    <div className="min-h-screen bg-background relative overflow-hidden flex flex-col justify-center px-6 py-12">
      {/* Background decorative elements */}
      <RadialGlow 
        size="xl" 
        position="top-right" 
        opacity={0.08}
      />
      <RadialGlow 
        size="lg" 
        position="bottom-left" 
        color="secondary"
        opacity={0.05}
      />

      {/* Content */}
      <motion.div
        className="relative z-10 w-full max-w-md mx-auto"
        variants={stagger}
        initial="hidden"
        animate="visible"
      >
        {/* Header / Logo */}
        <motion.div 
          className="text-center mb-10"
          variants={fadeInUp}
        >
          {/* Logo Icon with gradient background */}
          <div className="inline-flex items-center justify-center w-20 h-20 rounded-2xl bg-gradient-to-br from-accent to-accent-secondary shadow-accent-lg mb-6">
            <svg 
              className="w-10 h-10 text-white" 
              fill="none" 
              stroke="currentColor" 
              viewBox="0 0 24 24"
            >
              <path 
                strokeLinecap="round" 
                strokeLinejoin="round" 
                strokeWidth={2} 
                d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" 
              />
            </svg>
          </div>

          {/* Title with gradient text */}
          <h1 className="font-display text-3xl text-foreground mb-2">
            医院<GradientText>挂号</GradientText>系统
          </h1>
          <p className="text-muted-foreground">
            便捷预约，健康生活
          </p>
        </motion.div>

        {/* Login Card */}
        <Card 
          variant="elevated" 
          padding="lg"
          className="shadow-xl"
          animated={true}
        >
          <Form 
            form={form}
            layout="vertical" 
            onFinish={onFinish}
            footer={null}
          >
            <Form.Item 
              name="phone" 
              rules={[
                { required: true, message: '请输入手机号' },
                { pattern: /^1\d{10}$/, message: '请输入正确的手机号' },
              ]}
            >
              <Input 
                placeholder="请输入手机号" 
                type="tel" 
                maxLength={11}
                className="!h-12 !rounded-xl !border-border focus:!border-accent"
              />
            </Form.Item>
            <Form.Item 
              name="password" 
              rules={[
                { required: true, message: '请输入密码' },
                { min: 6, message: '密码至少6位' },
              ]}
            >
              <Input 
                placeholder="请输入密码" 
                type="password"
                className="!h-12 !rounded-xl !border-border focus:!border-accent"
              />
            </Form.Item>

            <div className="mt-6">
              <Button 
                block 
                type="submit"
                size="lg"
                loading={loading}
              >
                登录
              </Button>
            </div>
          </Form>

          {/* Footer Links */}
          <motion.div 
            className="flex justify-between mt-6 pt-6 border-t border-border"
            variants={fadeInUp}
          >
            <button 
              onClick={handleForgotPassword}
              className="text-sm text-muted-foreground hover:text-accent transition-colors"
            >
              忘记密码
            </button>
            <button 
              onClick={handleRegister}
              className="text-sm text-accent hover:text-accent-secondary transition-colors font-medium"
            >
              注册账号
            </button>
          </motion.div>
        </Card>

        {/* Bottom decoration */}
        <motion.p 
          className="text-center text-xs text-muted-foreground mt-8"
          variants={fadeInUp}
        >
          登录即表示您同意我们的服务条款和隐私政策
        </motion.p>
      </motion.div>
    </div>
  );
};

export default LoginPage;
