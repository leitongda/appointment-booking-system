import { useState } from 'react';
import { LockOutlined, UserOutlined, MedicineBoxOutlined } from '@ant-design/icons';
import { LoginForm, ProFormText } from '@ant-design/pro-components';
import { useModel, history } from '@umijs/max';
import { App } from 'antd';
import { adminApi } from '@hospital/api';
import { setToken, STORAGE_KEYS, setStorage } from '@hospital/shared';
import styles from './index.less';

const Login: React.FC = () => {
  const { message } = App.useApp();
  const { initialState, setInitialState } = useModel('@@initialState');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (values: API.LoginParams) => {
    setLoading(true);
    try {
      // adminApi.login 内部会自动获取公钥并加密密码
      const result = await adminApi.login(values);
      setToken(result.accessToken);
      setStorage(STORAGE_KEYS.REFRESH_TOKEN, result.refreshToken);
      message.success('登录成功！');
      const userInfo = await initialState?.fetchUserInfo?.();
      await setInitialState((s) => ({ ...s, currentUser: userInfo }));
      history.push('/dashboard');
    } catch (error: any) {
      message.error(error.message || '登录失败');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={styles.container}>
      <div className={styles.background} />
      <div className={styles.content}>
        <div className={styles.card}>
          <div className={styles.header}>
            <div className={styles.logo}><MedicineBoxOutlined /></div>
            <h1 className={styles.title}>医院挂号管理系统</h1>
          </div>
          <LoginForm
            contentStyle={{ minWidth: 320 }}
            submitter={{
              searchConfig: { submitText: '登 录' },
              submitButtonProps: { size: 'large', style: { width: '100%' }, loading },
            }}
            onFinish={handleSubmit}
          >
            <ProFormText
              name="username"
              fieldProps={{ size: 'large', prefix: <UserOutlined /> }}
              placeholder="用户名"
              rules={[{ required: true, message: '请输入用户名' }]}
            />
            <ProFormText.Password
              name="password"
              fieldProps={{ size: 'large', prefix: <LockOutlined /> }}
              placeholder="密码"
              rules={[{ required: true, message: '请输入密码' }]}
            />
          </LoginForm>
        </div>
      </div>
    </div>
  );
};

export default Login;

