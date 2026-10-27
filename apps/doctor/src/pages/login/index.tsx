import { LockOutlined, UserOutlined } from '@ant-design/icons';
import { LoginForm, ProFormText } from '@ant-design/pro-components';
import { message } from 'antd';
import { authApi } from '@hospital/api';
import { setToken, setStorage, STORAGE_KEYS, resetTokenExpiredState } from '@hospital/shared';
import { hardNavigate } from '@/utils/hardNavigate';
import styles from './index.less';

const Login: React.FC = () => {
  const handleSubmit = async (values: { phone: string; password: string }) => {
    try {
      const result = await authApi.doctorLogin(values);

      // 重置 token 失效处理状态
      resetTokenExpiredState();

      setToken(result.accessToken);
      setStorage(STORAGE_KEYS.REFRESH_TOKEN, result.refreshToken);
      setStorage('doctor', JSON.stringify(result.doctor));

      message.success('登录成功');

      // 整页跳转而非 refresh() + history.push：
      // refresh() 重跑 getInitialState 时路由仍在 /login，会命中其「登录页直接返回 {}」
      // 的早退分支，currentDoctor 不会被填充；随后 push('/dashboard') 触发 layout 的
      // onPageChange 守卫（无 currentDoctor → 弹回 /login），表现为「登录成功却留在登录页」。
      // 整页跳转让 getInitialState 在 /dashboard 上带 token 重跑，与 admin 端同一策略。
      setTimeout(() => {
        hardNavigate('/dashboard');
      }, 0);
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
