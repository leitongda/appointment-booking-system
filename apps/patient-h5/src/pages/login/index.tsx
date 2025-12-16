import { Form, Input, Button, Toast } from 'antd-mobile';
import { history } from 'umi';
import { resetTokenExpiredState } from '@hospital/shared';
import styles from './index.less';

const LoginPage: React.FC = () => {
  const onFinish = (values: any) => {
    console.log(values);
    // 重置 token 失效处理状态
    resetTokenExpiredState();
    Toast.show('登录成功');
    history.push('/home');
  };

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <div className={styles.logo}>🏥</div>
        <div className={styles.title}>医院挂号系统</div>
        <div className={styles.subtitle}>患者端</div>
      </div>
      <Form layout="horizontal" onFinish={onFinish} className={styles.form}>
        <Form.Item name="phone" rules={[{ required: true, message: '请输入手机号' }]}>
          <Input placeholder="请输入手机号" type="tel" />
        </Form.Item>
        <Form.Item name="password" rules={[{ required: true, message: '请输入密码' }]}>
          <Input placeholder="请输入密码" type="password" />
        </Form.Item>
        <Button block color="primary" type="submit" size="large">登录</Button>
      </Form>
      <div className={styles.footer}>
        <span onClick={() => {}}>忘记密码</span>
        <span onClick={() => {}}>注册账号</span>
      </div>
    </div>
  );
};

export default LoginPage;

