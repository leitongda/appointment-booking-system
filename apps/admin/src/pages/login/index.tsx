import { LockOutlined, MobileOutlined } from '@ant-design/icons';
import { LoginForm, ProFormText } from '@ant-design/pro-components';
import { message } from 'antd';
import { history } from 'umi';
import { authApi } from '@hospital/api';
import { setToken, STORAGE_KEYS, setStorage } from '@hospital/shared';
import styles from './index.less';

const Login: React.FC = () => {
  const handleSubmit = async (values: { phone: string; password: string }) => {
    try {
      const result = await authApi.login(values);
      setToken(result.accessToken);
      setStorage(STORAGE_KEYS.REFRESH_TOKEN, result.refreshToken);
      setStorage(STORAGE_KEYS.USER_INFO, result.user);
      
      message.success('登录成功！');
      history.push('/dashboard');
    } catch (error: any) {
      message.error(error.message || '登录失败');
    }
  };

  return (
    <div className={styles.container}>
      <div className={styles.content}>
        <LoginForm
          logo="/logo.svg"
          title="医院挂号管理系统"
          subTitle="机构端后台管理"
          onFinish={handleSubmit}
        >
          <ProFormText
            name="phone"
            fieldProps={{
              size: 'large',
              prefix: <MobileOutlined />,
            }}
            placeholder="请输入手机号"
            rules={[
              { required: true, message: '请输入手机号' },
              { pattern: /^1[3-9]\d{9}$/, message: '手机号格式错误' },
            ]}
          />
          <ProFormText.Password
            name="password"
            fieldProps={{
              size: 'large',
              prefix: <LockOutlined />,
            }}
            placeholder="请输入密码"
            rules={[{ required: true, message: '请输入密码' }]}
          />
        </LoginForm>
      </div>
    </div>
  );
};

export default Login;

