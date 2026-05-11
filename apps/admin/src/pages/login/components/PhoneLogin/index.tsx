import { useState, useEffect } from 'react';
import { MobileOutlined, SafetyOutlined, MailOutlined } from '@ant-design/icons';
import { App, Form, Input, Button, Segmented } from 'antd';
import { adminApi } from '@hospital/api';
import styles from './index.less';

type VerifyType = 'phone' | 'email';

interface PhoneLoginProps {
  onSuccess: (result: any) => void;
}

const PhoneLogin: React.FC<PhoneLoginProps> = ({ onSuccess }) => {
  const { message } = App.useApp();
  const [form] = Form.useForm();

  const [loading, setLoading] = useState(false);
  const [smsLoading, setSmsLoading] = useState(false);
  const [countdown, setCountdown] = useState(0);
  const [verifyType, setVerifyType] = useState<VerifyType>('phone');

  // 切换类型时重置表单
  useEffect(() => {
    form.resetFields();
    setCountdown(0);
  }, [verifyType, form]);

  // 登录
  const handleLogin = async (values: { account: string; code: string }) => {
    setLoading(true);
    try {
      let result: any;
      if (verifyType === 'phone') {
        result = await adminApi.smsLogin({ phone: values.account, code: values.code });
      } else {
        result = await adminApi.emailLogin({ email: values.account, code: values.code });
      }
      onSuccess(result);
    } catch (error: any) {
      // ApiError 已由响应拦截器显示错误提示，此处仅处理未被拦截器捕获的错误
      if (typeof error?.code !== 'number') {
        message.error(error.message || '登录失败');
      }
    } finally {
      setLoading(false);
    }
  };

  // 发送验证码
  const handleSendCode = async () => {
    try {
      const account = form.getFieldValue('account');
      if (!account) {
        message.error(verifyType === 'phone' ? '请输入手机号' : '请输入邮箱');
        return;
      }

      if (verifyType === 'phone' && !/^1\d{10}$/.test(account)) {
        message.error('手机号格式不正确');
        return;
      }

      if (verifyType === 'email' && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(account)) {
        message.error('邮箱格式不正确');
        return;
      }

      setSmsLoading(true);
      if (verifyType === 'phone') {
        await adminApi.sendSmsCode(account);
      } else {
        await adminApi.sendEmailCode(account);
      }
      message.success('验证码已发送');
      setCountdown(60);
    } catch (error: any) {
      // ApiError 已由响应拦截器显示错误提示，此处仅处理未被拦截器捕获的错误
      if (typeof error?.code !== 'number') {
        message.error(error.message || '发送失败');
      }
    } finally {
      setSmsLoading(false);
    }
  };

  // 倒计时
  useEffect(() => {
    if (countdown > 0) {
      const timer = setTimeout(() => setCountdown(countdown - 1), 1000);
      return () => clearTimeout(timer);
    }
  }, [countdown]);

  return (
    <div className={styles.phoneLogin}>
      <div className={styles.phoneLoginTypeSwitch}>
        <Segmented
          options={[
            { label: '手机号', value: 'phone' },
            { label: '邮箱', value: 'email' },
          ]}
          value={verifyType}
          onChange={(val) => setVerifyType(val as VerifyType)}
        />
      </div>

      <Form
        form={form}
        onFinish={handleLogin}
        size="large"
        className={styles.loginForm}
      >
        <Form.Item
          name="account"
          rules={
            verifyType === 'phone'
              ? [
                  { required: true, message: '请输入手机号' },
                  { pattern: /^1\d{10}$/, message: '手机号格式不正确' },
                ]
              : [
                  { required: true, message: '请输入邮箱' },
                  { type: 'email', message: '邮箱格式不正确' },
                ]
          }
        >
          <Input
            prefix={verifyType === 'phone' ? <MobileOutlined /> : <MailOutlined />}
            placeholder={verifyType === 'phone' ? '请输入手机号' : '请输入邮箱'}
            maxLength={verifyType === 'phone' ? 11 : undefined}
          />
        </Form.Item>

        <Form.Item
          name="code"
          rules={[{ required: true, message: '请输入验证码' }]}
        >
          <Input
            prefix={<SafetyOutlined />}
            placeholder="请输入验证码"
            maxLength={6}
            suffix={
              <Button
                type="link"
                size="small"
                disabled={countdown > 0}
                loading={smsLoading}
                onClick={handleSendCode}
                style={{ padding: 0 }}
              >
                {countdown > 0 ? `${countdown}s` : '获取验证码'}
              </Button>
            }
          />
        </Form.Item>

        <Form.Item>
          <Button type="primary" htmlType="submit" block loading={loading}>
            登 录
          </Button>
        </Form.Item>
      </Form>
    </div>
  );
};

export { PhoneLogin, MobileOutlined };
export default PhoneLogin;
