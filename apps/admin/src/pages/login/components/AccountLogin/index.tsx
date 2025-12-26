import { useState } from 'react';
import { UserOutlined, LockOutlined } from '@ant-design/icons';
import { App, Form, Input, Button } from 'antd';
import { adminApi } from '@hospital/api';
import styles from './index.less';

interface AccountLoginProps {
  onSuccess: (result: any) => void;
}

const AccountLogin: React.FC<AccountLoginProps> = ({ onSuccess }) => {
  const { message } = App.useApp();
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);

  // 账号密码登录
  const handleAccountLogin = async (values: { username: string; password: string }) => {
    setLoading(true);
    try {
      const result = await adminApi.login(values);
      onSuccess(result);
    } catch (error: any) {
      message.error(error.message || '登录失败');
    } finally {
      setLoading(false);
    }
  };

  // 忘记密码
  const handleForgotPassword = () => {
    message.info('请联系系统管理员重置密码');
  };

  return (
    <div className={styles.accountLogin}>
      <Form
        form={form}
        onFinish={handleAccountLogin}
        size="large"
        className={styles.loginForm}
      >
        <Form.Item
          name="username"
          rules={[{ required: true, message: '请输入用户名' }]}
        >
          <Input 
            prefix={<UserOutlined />} 
            placeholder="请输入用户名" 
          />
        </Form.Item>
        
        <Form.Item
          name="password"
          rules={[{ required: true, message: '请输入密码' }]}
        >
          <Input.Password 
            prefix={<LockOutlined />} 
            placeholder="请输入密码" 
          />
        </Form.Item>
        
        <Form.Item>
          <Button type="primary" htmlType="submit" block loading={loading}>
            登 录
          </Button>
        </Form.Item>
      </Form>
      
      <div className={styles.forgotPassword}>
        <a onClick={handleForgotPassword}>忘记密码？</a>
      </div>
    </div>
  );
};

export { AccountLogin, UserOutlined };
export default AccountLogin;
