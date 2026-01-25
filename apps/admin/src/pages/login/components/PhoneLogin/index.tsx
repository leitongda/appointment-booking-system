import { useState, useEffect } from 'react';
import { MobileOutlined, SafetyOutlined } from '@ant-design/icons';
import { App, Form, Input, Button } from 'antd';
import { adminApi } from '@hospital/api';
import styles from './index.less';

interface PhoneLoginProps {
  onSuccess: (result: any) => void;
}

const PhoneLogin: React.FC<PhoneLoginProps> = ({ onSuccess }) => {
  const { message } = App.useApp();
  const [form] = Form.useForm();

  const [loading, setLoading] = useState(false);
  const [smsLoading, setSmsLoading] = useState(false);
  const [countdown, setCountdown] = useState(0);

  // 手机号+验证码登录
  const handlePhoneSmsLogin = async (values: { phone: string; code: string }) => {
    setLoading(true);
    try {
      const result = await adminApi.smsLogin(values);
      onSuccess(result);
    } catch (error: any) {
      message.error(error.message || '登录失败');
    } finally {
      setLoading(false);
    }
  };

  // 发送验证码
  const handleSendSms = async () => {
    try {
      const phone = form.getFieldValue('phone');
      if (!phone || !/^1\d{10}$/.test(phone)) {
        message.error('请输入正确的手机号');
        return;
      }

      setSmsLoading(true);
      await adminApi.sendSmsCode(phone);
      message.success('验证码已发送');
      setCountdown(60);
    } catch (error: any) {
      message.error(error.message || '发送失败');
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
      <Form
        form={form}
        onFinish={handlePhoneSmsLogin}
        size="large"
        className={styles.loginForm}
      >
        <Form.Item
          name="phone"
          rules={[
            { required: true, message: '请输入手机号' },
            { pattern: /^1\d{10}$/, message: '手机号格式不正确' }
          ]}
        >
          <Input
            prefix={<MobileOutlined />}
            placeholder="请输入手机号"
            maxLength={11}
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
                onClick={handleSendSms}
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
