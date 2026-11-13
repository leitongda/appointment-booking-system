import { useState } from 'react';
import {
  CalendarOutlined,
  FileTextOutlined,
  HeartOutlined,
  LockOutlined,
  UserOutlined,
} from '@ant-design/icons';
import { Button, ConfigProvider, Form, Input, message } from 'antd';
import { authApi } from '@hospital/api';
import {
  setToken,
  setStorage,
  STORAGE_KEYS,
  resetTokenExpiredState,
} from '@hospital/shared';
import { hardNavigate } from '@/utils/hardNavigate';
import styles from './index.less';

const FEATURES = [
  { icon: <CalendarOutlined />, text: '今日预约与排班，一屏掌握' },
  { icon: <FileTextOutlined />, text: '病历模板化录入，快速归档' },
  { icon: <HeartOutlined />, text: '复诊随访自动提醒，不漏一人' },
];

const BrandMark = () => (
  <>
    <span className={styles.brandLogo}>
      <img src="/logo.svg" alt="" />
    </span>
    <span>
      <span className={styles.brandName}>医生工作台</span>
      <span className={styles.brandSub}>Doctor Workspace</span>
    </span>
  </>
);

const Login: React.FC = () => {
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (values: { phone: string; password: string }) => {
    if (submitting) return;
    setSubmitting(true);
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
      setSubmitting(false);
    }
  };

  return (
    <ConfigProvider
      theme={{
        token: {
          colorPrimary: '#2563eb',
          colorInfo: '#2563eb',
          borderRadius: 8,
          controlHeightLG: 46,
          fontSize: 14,
        },
      }}
    >
      <div className={styles.page}>
        <div className={styles.shell}>
          <aside className={styles.aside}>
            <div className={styles.brand}>
              <BrandMark />
            </div>

            <div className={styles.hero}>
              <p className={styles.eyebrow}>医院挂号系统 · 医生端</p>
              <h1 className={styles.title}>
                把时间留给患者，
                <br />
                把琐事交给系统。
              </h1>
              <p className={styles.lead}>
                排班、预约、病历与随访，集中在同一个工作台。
              </p>

              <ul className={styles.features}>
                {FEATURES.map((item) => (
                  <li key={item.text} className={styles.feature}>
                    <span className={styles.featureIcon}>{item.icon}</span>
                    {item.text}
                  </li>
                ))}
              </ul>
            </div>
          </aside>

          <main className={styles.main}>
            <div className={styles.card}>
              <div className={styles.mobileBrand}>
                <BrandMark />
              </div>

              <header className={styles.cardHeader}>
                <h2 className={styles.greeting}>欢迎回来</h2>
                <p className={styles.cardSub}>
                  登录后查看今日排班与预约，开始今天的接诊。
                </p>
              </header>

              <Form
                layout="vertical"
                size="large"
                requiredMark={false}
                className={styles.form}
                onFinish={handleSubmit}
              >
                <Form.Item
                  name="phone"
                  label="手机号 / 账号"
                  rules={[{ required: true, message: '请输入手机号或账号' }]}
                >
                  <Input
                    prefix={<UserOutlined />}
                    placeholder="请输入手机号或账号"
                    autoComplete="username"
                  />
                </Form.Item>

                <Form.Item
                  name="password"
                  label="密码"
                  rules={[{ required: true, message: '请输入密码' }]}
                >
                  <Input.Password
                    prefix={<LockOutlined />}
                    placeholder="请输入密码"
                    autoComplete="current-password"
                  />
                </Form.Item>

                <Button
                  type="primary"
                  htmlType="submit"
                  block
                  loading={submitting}
                  autoInsertSpace={false}
                  className={styles.submit}
                >
                  登录
                </Button>
              </Form>

              <p className={styles.help}>
                忘记密码或账号异常，请联系医院信息科重置。
              </p>
            </div>

            <p className={styles.copyright}>
              © {new Date().getFullYear()} 医院挂号系统 · 医生端
            </p>
          </main>
        </div>
      </div>
    </ConfigProvider>
  );
};

export default Login;
