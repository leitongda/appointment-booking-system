import { useState, useEffect, useRef, useCallback } from 'react';
import { 
  LockOutlined, 
  UserOutlined, 
  MedicineBoxOutlined, 
  MobileOutlined,
  WechatOutlined,
  SafetyOutlined,
} from '@ant-design/icons';
import { App, Tabs, Button, Form, Input, QRCode, Spin, Space } from 'antd';
import { adminApi } from '@hospital/api';
import { setToken, STORAGE_KEYS, setStorage, getStorage, removeStorage, resetTokenExpiredState } from '@hospital/shared';
import styles from './index.less';

type LoginType = 'wechat' | 'phone' | 'account';
type PhoneLoginType = 'sms' | 'password';

const Login: React.FC = () => {
  const { message } = App.useApp();
  
  // 登录方式（从 localStorage 读取，实现刷新后保持选中状态）
  const [loginType, setLoginType] = useState<LoginType>(
    () => getStorage<LoginType>(STORAGE_KEYS.LOGIN_TYPE) || 'wechat'
  );
  const [phoneLoginType, setPhoneLoginType] = useState<PhoneLoginType>(
    () => getStorage<PhoneLoginType>(STORAGE_KEYS.PHONE_LOGIN_TYPE) || 'sms'
  );

  // 延迟启用动画，避免初始化时的切换效果
  const [enableAnimation, setEnableAnimation] = useState(false);
  
  // 加载状态
  const [loading, setLoading] = useState(false);
  const [smsLoading, setSmsLoading] = useState(false);
  const [countdown, setCountdown] = useState(0);
  
  // 微信扫码相关
  const [qrcodeUrl, setQrcodeUrl] = useState('');
  const [qrcodeTicket, setQrcodeTicket] = useState('');
  const [qrcodeStatus, setQrcodeStatus] = useState<'loading' | 'active' | 'expired'>('loading');
  const pollTimerRef = useRef<NodeJS.Timeout | null>(null);
  
  // 表单
  const [accountForm] = Form.useForm();
  const [phoneForm] = Form.useForm();

  // 登录成功后的处理
  const handleLoginSuccess = useCallback(async (result: any) => {
    // 重置 token 失效处理状态
    resetTokenExpiredState();
    
    setToken(result.accessToken);
    setStorage(STORAGE_KEYS.REFRESH_TOKEN, result.refreshToken);
    
    // 保存门店信息到 localStorage（如果有）
    if (result.store) {
      localStorage.setItem('currentStore', JSON.stringify(result.store));
    } else {
      localStorage.removeItem('currentStore');
    }
    
    message.success('登录成功！');
    
    // 获取上次访问的页面路径
    const lastPath = getStorage<string>(STORAGE_KEYS.LAST_PATH);
    // 清除存储的路径（只使用一次）
    removeStorage(STORAGE_KEYS.LAST_PATH);
    
    // 使用 window.location.href 而不是 history.push
    // 这样会触发页面刷新，重新执行 getInitialState，确保权限正确加载
    // 如果有上次访问的路径则跳转到该路径，否则跳转到 dashboard
    // 权限检查由 layout 的 onUnAccessible 处理，无权限时会自动重定向到 dashboard
    const targetPath = lastPath && lastPath !== '/' ? lastPath : '/dashboard';
    window.location.href = targetPath;
  }, [message]);

  // 账号密码登录
  const handleAccountLogin = async (values: { username: string; password: string }) => {
    setLoading(true);
    try {
      const result = await adminApi.login(values);
      await handleLoginSuccess(result);
    } catch (error: any) {
      message.error(error.message || '登录失败');
    } finally {
      setLoading(false);
    }
  };

  // 手机号+密码登录
  const handlePhonePasswordLogin = async (values: { phone: string; password: string }) => {
    setLoading(true);
    try {
      const result = await adminApi.phoneLogin(values);
      await handleLoginSuccess(result);
    } catch (error: any) {
      message.error(error.message || '登录失败');
    } finally {
      setLoading(false);
    }
  };

  // 手机号+验证码登录
  const handlePhoneSmsLogin = async (values: { phone: string; code: string }) => {
    setLoading(true);
    try {
      const result = await adminApi.smsLogin(values);
      await handleLoginSuccess(result);
    } catch (error: any) {
      message.error(error.message || '登录失败');
    } finally {
      setLoading(false);
    }
  };

  // 发送验证码
  const handleSendSms = async () => {
    try {
      const phone = phoneForm.getFieldValue('phone');
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

  // 组件挂载后启用动画
  useEffect(() => {
    const timer = setTimeout(() => setEnableAnimation(true), 50);
    return () => clearTimeout(timer);
  }, []);

  // 获取微信二维码
  const fetchWechatQrcode = useCallback(async () => {
    setQrcodeStatus('loading');
    try {
      const result = await adminApi.getWechatQrcode();
      setQrcodeUrl(result.qrcodeUrl);
      setQrcodeTicket(result.ticket);
      setQrcodeStatus('active');
    } catch (error: any) {
      message.error('获取二维码失败');
      setQrcodeStatus('expired');
    }
  }, [message]);

  // 轮询检查扫码状态
  const pollWechatStatus = useCallback(async () => {
    if (!qrcodeTicket || qrcodeStatus !== 'active') return;
    
    try {
      const result = await adminApi.checkWechatScan(qrcodeTicket);
      
      if (result.status === 'confirmed' && result.accessToken) {
        // 登录成功
        if (pollTimerRef.current) {
          clearInterval(pollTimerRef.current);
          pollTimerRef.current = null;
        }
        await handleLoginSuccess(result);
      } else if (result.status === 'expired') {
        setQrcodeStatus('expired');
        if (pollTimerRef.current) {
          clearInterval(pollTimerRef.current);
          pollTimerRef.current = null;
        }
      }
    } catch (error) {
      // 忽略轮询错误
    }
  }, [qrcodeTicket, qrcodeStatus, handleLoginSuccess]);

  // 当切换到微信登录时获取二维码
  useEffect(() => {
    if (loginType === 'wechat') {
      fetchWechatQrcode();
    }
    
    return () => {
      if (pollTimerRef.current) {
        clearInterval(pollTimerRef.current);
        pollTimerRef.current = null;
      }
    };
  }, [loginType, fetchWechatQrcode]);

  // 开始轮询
  useEffect(() => {
    if (qrcodeStatus === 'active' && qrcodeTicket) {
      pollTimerRef.current = setInterval(pollWechatStatus, 2000);
    }
    
    return () => {
      if (pollTimerRef.current) {
        clearInterval(pollTimerRef.current);
        pollTimerRef.current = null;
      }
    };
  }, [qrcodeStatus, qrcodeTicket, pollWechatStatus]);

  // 手机号登录表单提交
  const handlePhoneFormSubmit = (values: any) => {
    if (phoneLoginType === 'sms') {
      handlePhoneSmsLogin(values);
    } else {
      handlePhonePasswordLogin(values);
    }
  };

  // 处理忘记密码
  const handleForgotPassword = () => {
    message.info('请联系系统管理员重置密码');
  };

  // 渲染微信扫码登录
  const renderWechatLogin = () => (
    <div className={styles.wechatLogin}>
      <div className={styles.qrcodeWrapper}>
        {qrcodeStatus === 'loading' && (
          <div className={styles.qrcodeLoading}>
            <Spin size="large" />
            <p>加载中...</p>
          </div>
        )}
        {qrcodeStatus === 'active' && (
          <>
            <QRCode 
              value={qrcodeUrl || '-'} 
              size={180}
              status="active"
              bordered={false}
            />
            <p className={styles.qrcodeTip}>请使用微信扫描二维码登录</p>
          </>
        )}
        {qrcodeStatus === 'expired' && (
          <div className={styles.qrcodeExpired}>
            <QRCode 
              value="-" 
              size={180}
              status="expired"
              bordered={false}
              onRefresh={fetchWechatQrcode}
            />
            <p>二维码已过期，请刷新</p>
          </div>
        )}
      </div>
    </div>
  );

  // 渲染手机号登录
  const renderPhoneLogin = () => (
    <div className={styles.phoneLogin}>
      <div className={styles.phoneLoginTypeSwitch}>
        <Space>
          <Button
            type={phoneLoginType === 'sms' ? 'primary' : 'default'}
            size="small"
            onClick={() => {
              setPhoneLoginType('sms');
              setStorage(STORAGE_KEYS.PHONE_LOGIN_TYPE, 'sms');
            }}
          >
            验证码登录
          </Button>
          <Button
            type={phoneLoginType === 'password' ? 'primary' : 'default'}
            size="small"
            onClick={() => {
              setPhoneLoginType('password');
              setStorage(STORAGE_KEYS.PHONE_LOGIN_TYPE, 'password');
            }}
          >
            密码登录
          </Button>
        </Space>
      </div>
      
      <Form
        form={phoneForm}
        onFinish={handlePhoneFormSubmit}
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
        
        {phoneLoginType === 'sms' ? (
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
        ) : (
          <Form.Item
            name="password"
            rules={[{ required: true, message: '请输入密码' }]}
          >
            <Input.Password 
              prefix={<LockOutlined />} 
              placeholder="请输入密码" 
            />
          </Form.Item>
        )}
        
        <Form.Item>
          <Button type="primary" htmlType="submit" block loading={loading}>
            登 录
          </Button>
        </Form.Item>
      </Form>
      
      {phoneLoginType === 'password' && (
        <div className={styles.forgotPassword}>
          <a onClick={handleForgotPassword}>忘记密码？</a>
        </div>
      )}
    </div>
  );

  // 渲染账号密码登录
  const renderAccountLogin = () => (
    <div className={styles.accountLogin}>
      <Form
        form={accountForm}
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

  const tabItems = [
    {
      key: 'wechat',
      label: (
        <span>
          <WechatOutlined />
          微信登录
        </span>
      ),
      children: renderWechatLogin(),
    },
    {
      key: 'phone',
      label: (
        <span>
          <MobileOutlined />
          手机号登录
        </span>
      ),
      children: renderPhoneLogin(),
    },
    {
      key: 'account',
      label: (
        <span>
          <UserOutlined />
          账号登录
        </span>
      ),
      children: renderAccountLogin(),
    },
  ];

  return (
    <div className={styles.container}>
      <div className={styles.background} />
      <div className={styles.content}>
        <div className={styles.card}>
          <div className={styles.header}>
            <div className={styles.logo}><MedicineBoxOutlined /></div>
            <h1 className={styles.title}>医院挂号管理系统</h1>
          </div>
          
          <Tabs
            activeKey={loginType}
            onChange={(key) => {
              const newType = key as LoginType;
              setLoginType(newType);
              setStorage(STORAGE_KEYS.LOGIN_TYPE, newType);
            }}
            items={tabItems}
            centered
            className={styles.loginTabs}
            animated={enableAnimation}
          />
        </div>
      </div>
      <div className={styles.footer}>
        <a 
          href="https://beian.miit.gov.cn/" 
          target="_blank" 
          rel="noopener noreferrer"
        >
          蜀ICP备2022022726号-2
        </a>
      </div>
    </div>
  );
};

export default Login;
