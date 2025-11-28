import { LockOutlined, UserOutlined } from '@ant-design/icons';
import { LoginForm, ProFormText } from '@ant-design/pro-components';
import { message } from 'antd';
import { history, useModel } from 'umi';
import { adminApi } from '@hospital/api';
import { setToken, STORAGE_KEYS, setStorage } from '@hospital/shared';
import styles from './index.less';

const Login: React.FC = () => {
  const { refresh } = useModel('@@initialState');

  const handleSubmit = async (values: { username: string; password: string }) => {
    try {
      const result = await adminApi.login(values);
      
      // 保存 token
      setToken(result.accessToken);
      setStorage(STORAGE_KEYS.REFRESH_TOKEN, result.refreshToken);
      
      message.success('登录成功！');
      
      // 刷新用户状态
      await refresh();
      
      // 跳转到首页
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
          subTitle="管理后台"
          onFinish={handleSubmit}
        >
          <ProFormText
            name="username"
            fieldProps={{
              size: 'large',
              prefix: <UserOutlined />,
            }}
            placeholder="请输入用户名"
            rules={[
              { required: true, message: '请输入用户名' },
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
