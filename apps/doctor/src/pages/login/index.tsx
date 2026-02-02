import { LockOutlined, UserOutlined } from '@ant-design/icons';
import { LoginForm, ProFormText } from '@ant-design/pro-components';
import { message } from 'antd';
import { history, useModel } from 'umi';
import { authApi } from '@hospital/api';
import { setToken, setStorage, STORAGE_KEYS, resetTokenExpiredState } from '@hospital/shared';
import styles from './index.less';

const Login: React.FC = () => {
  const { refresh } = useModel('@@initialState');

  const handleSubmit = async (values: { phone: string; password: string }) => {
    try {
      const result = await authApi.doctorLogin(values);

      // 重置 token 失效处理状态
      resetTokenExpiredState();

      setToken(result.accessToken);
      setStorage(STORAGE_KEYS.REFRESH_TOKEN, result.refreshToken);
      setStorage('doctor', JSON.stringify(result.doctor));

      message.success('登录成功');

      // 刷新医生状态
      await refresh();

      history.push('/dashboard');
    } catch (error: any) {
      message.error(error.message || '登录失败');
    }
  };

  return (
    <div className={styles.container}>
      <LoginForm
        logo="/logo.svg"
        title="医生工作台"
        subTitle="医院挂号系统"
        onFinish={handleSubmit}
      >
        <ProFormText
          name="phone"
          fieldProps={{ size: 'large', prefix: <UserOutlined /> }}
          placeholder="请输入手机号或账号"
          rules={[
            { required: true, message: '请输入手机号或账号' },
          ]}
        />
        <ProFormText.Password
          name="password"
          fieldProps={{ size: 'large', prefix: <LockOutlined /> }}
          placeholder="请输入密码"
          rules={[{ required: true, message: '请输入密码' }]}
        />
      </LoginForm>
    </div>
  );
};

export default Login;
