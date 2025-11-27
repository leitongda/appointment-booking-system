import { LockOutlined, MobileOutlined } from '@ant-design/icons';
import { LoginForm, ProFormText } from '@ant-design/pro-components';
import { message } from 'antd';
import { history } from 'umi';
import { authApi } from '@hospital/api';
import { setToken, setStorage, STORAGE_KEYS } from '@hospital/shared';
import styles from './index.less';

const Login: React.FC = () => {
  const handleSubmit = async (values: { phone: string; password: string }) => {
    try {
      const result = await authApi.login(values);
      setToken(result.accessToken);
      setStorage(STORAGE_KEYS.USER_INFO, result.user);
      message.success('登录成功');
      history.push('/dashboard');
    } catch (error: any) {
      message.error(error.message || '登录失败');
    }
  };

  return (
    <div className={styles.container}>
      <LoginForm logo="/logo.svg" title="医生工作台" subTitle="医院挂号系统" onFinish={handleSubmit}>
        <ProFormText name="phone" fieldProps={{ size: 'large', prefix: <MobileOutlined /> }} placeholder="手机号" rules={[{ required: true }]} />
        <ProFormText.Password name="password" fieldProps={{ size: 'large', prefix: <LockOutlined /> }} placeholder="密码" rules={[{ required: true }]} />
      </LoginForm>
    </div>
  );
};

export default Login;

