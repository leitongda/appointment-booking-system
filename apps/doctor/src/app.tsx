import { message, Dropdown, Avatar, Space, Modal, Form, Input, Button, Typography } from 'antd';
import type { RequestConfig, RunTimeLayoutConfig } from 'umi';
import { history } from 'umi';
import { useState, useCallback, useRef } from 'react';
import { getToken, removeToken, initCrossTabSync, destroyCrossTabSync } from '@hospital/shared';
import type { CrossTabEvent } from '@hospital/shared';
import { doctorApi, authApi, setBaseURL } from '@hospital/api';
import {
  UserOutlined, LogoutOutlined, SettingOutlined, LockOutlined, MailOutlined,
} from '@ant-design/icons';
import { initApiConfig } from '@/utils/request';

// 设置 API 基础路径（从环境变量读取，支持动态配置）
const apiBaseUrl = process.env.API_BASE_URL || '/api/v1';
setBaseURL(apiBaseUrl);

// 初始化 API 请求配置（拦截器）
initApiConfig();

// 初始化跨 Tab 状态同步（医生端只关心认证变更）
initCrossTabSync((event: CrossTabEvent) => {
  if (event.type !== 'auth-change') return;

  // 登录页不弹框
  if (window.location.pathname === '/login') return;

  if (event.action === 'logout') {
    Modal.confirm({
      title: '登录状态变更',
      content: '您已在其他页面退出登录，请重新登录。',
      okText: '重新登录',
      cancelButtonProps: { style: { display: 'none' } },
      closable: false,
      maskClosable: false,
      onOk: () => { window.location.href = '/login'; },
    });
  } else if (event.action === 'switch-user') {
    Modal.confirm({
      title: '登录账号已变更',
      content: '检测到您在其他页面切换了登录账号，当前页面需要刷新。',
      okText: '刷新页面',
      cancelButtonProps: { style: { display: 'none' } },
      closable: false,
      maskClosable: false,
      onOk: () => { window.location.reload(); },
    });
  }
});

interface CurrentDoctor {
  id: string;
  name: string;
  phone?: string;
  email?: string;
  avatar?: string;
  title?: string;
  departmentId?: string;
  departmentName?: string;
  storeId?: string;
  storeName?: string;
  // 统一账号字段（兼容后端 AccountInfo.to_dict() 返回格式）
  roleType?: 'admin' | 'doctor' | 'user';
  permissions?: string[];
}

export async function getInitialState(): Promise<{ currentDoctor?: CurrentDoctor }> {
  const token = getToken();
  if (!token) {
    return {};
  }
  
  // 登录页不需要获取用户信息
  if (history.location.pathname === '/login') {
    return {};
  }
  
  try {
    // 使用医生专用 API 获取当前登录医生信息
    const doctor = await doctorApi.getMe();
    return {
      currentDoctor: {
        id: doctor.id,
        name: doctor.name,
        phone: doctor.phone,
        email: doctor.email,
        avatar: doctor.avatar,
        title: doctor.title,
        departmentId: doctor.departmentId,
        departmentName: doctor.departmentName,
        storeId: doctor.storeId,
        storeName: doctor.storeName,
        // 兼容统一账号格式：默认 roleType 为 doctor，permissions 为空数组
        // 后端切换到统一 AccountInfo 后会直接返回这些字段
        roleType: (doctor as any).roleType || 'doctor',
        permissions: (doctor as any).permissions || [],
      }
    };
  } catch (error) {
    removeToken();
    return {};
  }
}

export const layout: RunTimeLayoutConfig = ({ initialState, setInitialState }) => {
  const [passwordModalVisible, setPasswordModalVisible] = useState(false);
  const [passwordLoading, setPasswordLoading] = useState(false);
  const [form] = Form.useForm();

  // 邮箱管理状态
  const [emailModalVisible, setEmailModalVisible] = useState(false);
  const [emailModalType, setEmailModalType] = useState<'bind' | 'unbind' | 'change'>('bind');
  const [emailForm] = Form.useForm();
  const [emailCodeSending, setEmailCodeSending] = useState(false);
  const [emailCodeCountdown, setEmailCodeCountdown] = useState(0);
  const [emailOldCodeSending, setEmailOldCodeSending] = useState(false);
  const [emailOldCodeCountdown, setEmailOldCodeCountdown] = useState(0);
  const [emailSubmitting, setEmailSubmitting] = useState(false);
  const emailTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const emailOldTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const handleLogout = () => {
    removeToken();
    localStorage.removeItem('doctor');
    setInitialState({ currentDoctor: undefined });
    history.push('/login');
    message.success('已退出登录');
  };

  const handleChangePassword = useCallback(async (values: { oldPassword: string; newPassword: string; confirmPassword: string }) => {
    if (values.newPassword !== values.confirmPassword) {
      message.error('两次输入的新密码不一致');
      return;
    }

    // 验证密码长度
    if (!values.oldPassword || values.newPassword.length < 6 || values.newPassword.length > 20) {
      message.error('密码长度必须为6-20位');
      return;
    }

    // 验证新旧密码不能相同
    if (values.oldPassword === values.newPassword) {
      message.error('新密码不能与原密码相同');
      return;
    }

    setPasswordLoading(true);
    try {
      await doctorApi.changePassword({
        oldPassword: values.oldPassword,
        newPassword: values.newPassword,
      });
      message.success('密码修改成功');
      setPasswordModalVisible(false);
      form.resetFields();
    } catch (error: any) {
      message.error(error.message || '密码修改失败');
    } finally {
      setPasswordLoading(false);
    }
  }, [form]);

  // ========== 邮箱管理 ==========

  const refreshDoctorInfo = async () => {
    try {
      const doctor = await doctorApi.getMe();
      setInitialState({
        currentDoctor: {
          id: doctor.id,
          name: doctor.name,
          phone: doctor.phone,
          email: doctor.email,
          avatar: doctor.avatar,
          title: doctor.title,
          departmentId: doctor.departmentId,
          departmentName: doctor.departmentName,
          storeId: doctor.storeId,
          storeName: doctor.storeName,
          roleType: (doctor as any).roleType || 'doctor',
          permissions: (doctor as any).permissions || [],
        },
      } as any);
    } catch {}
  };

  const openEmailModal = (type: 'bind' | 'unbind' | 'change') => {
    setEmailModalType(type);
    setEmailModalVisible(true);
    emailForm.resetFields();
    setEmailCodeCountdown(0);
    setEmailOldCodeCountdown(0);
    if (emailTimerRef.current) {
      clearInterval(emailTimerRef.current);
      emailTimerRef.current = null;
    }
    if (emailOldTimerRef.current) {
      clearInterval(emailOldTimerRef.current);
      emailOldTimerRef.current = null;
    }
  };

  const handleSendEmailCode = async (target: 'new' | 'old' = 'new') => {
    try {
      if (target === 'new') {
        const email = emailForm.getFieldValue('email');
        if (!email) {
          message.error('请先输入邮箱');
          return;
        }
        if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
          message.error('邮箱格式不正确');
          return;
        }
        setEmailCodeSending(true);
        await authApi.sendEmailCode(email, 'bind');
        message.success('验证码已发送');
        setEmailCodeCountdown(60);
        emailTimerRef.current = setInterval(() => {
          setEmailCodeCountdown((prev) => {
            if (prev <= 1) {
              if (emailTimerRef.current) {
                clearInterval(emailTimerRef.current);
                emailTimerRef.current = null;
              }
              return 0;
            }
            return prev - 1;
          });
        }, 1000);
      } else {
        if (!initialState?.currentDoctor?.email) {
          message.error('当前未绑定邮箱');
          return;
        }
        setEmailOldCodeSending(true);
        await authApi.sendEmailCode(initialState.currentDoctor.email, 'bind');
        message.success('验证码已发送到当前邮箱');
        setEmailOldCodeCountdown(60);
        emailOldTimerRef.current = setInterval(() => {
          setEmailOldCodeCountdown((prev) => {
            if (prev <= 1) {
              if (emailOldTimerRef.current) {
                clearInterval(emailOldTimerRef.current);
                emailOldTimerRef.current = null;
              }
              return 0;
            }
            return prev - 1;
          });
        }, 1000);
      }
    } catch (error: any) {
      message.error(error.message || '发送验证码失败');
    } finally {
      setEmailCodeSending(false);
      setEmailOldCodeSending(false);
    }
  };

  const handleEmailSubmit = async () => {
    try {
      const values = await emailForm.validateFields();
      setEmailSubmitting(true);

      if (emailModalType === 'bind') {
        await authApi.emailBind({ email: values.email, code: values.code });
        message.success('邮箱绑定成功');
      } else if (emailModalType === 'unbind') {
        await authApi.emailUnbind({ code: values.code });
        message.success('邮箱解绑成功');
      } else if (emailModalType === 'change') {
        await authApi.emailChange({
          newEmail: values.email,
          newEmailCode: values.code,
          oldEmailCode: values.oldCode,
        });
        message.success('邮箱换绑成功');
      }

      setEmailModalVisible(false);
      await refreshDoctorInfo();
    } catch (error: any) {
      if (error.message) {
        message.error(error.message);
      }
    } finally {
      setEmailSubmitting(false);
    }
  };

  const getEmailModalTitle = () => {
    switch (emailModalType) {
      case 'bind': return '绑定邮箱';
      case 'unbind': return '解绑邮箱';
      case 'change': return '更换邮箱';
    }
  };

  return {
    logo: '/logo.svg',
    title: '医生工作站',
    menu: { locale: false },
    rightContentRender: () => {
      if (!initialState?.currentDoctor) {
        return null;
      }

      const menuItems = [
        {
          key: 'notification-settings',
          icon: <SettingOutlined />,
          label: '通知设置',
          onClick: () => history.push('/settings/notification'),
        },
        {
          key: 'email-management',
          icon: <MailOutlined />,
          label: '邮箱管理',
          onClick: () => {
            if (initialState.currentDoctor.email) {
              // 已绑定：显示操作选择
              Modal.confirm({
                title: '邮箱管理',
                content: (
                  <div style={{ textAlign: 'center', padding: '8px 0' }}>
                    <div style={{ fontSize: 14, color: '#999', marginBottom: 4 }}>当前绑定邮箱</div>
                    <div style={{ fontSize: 16, fontWeight: 500 }}>{initialState.currentDoctor.email}</div>
                  </div>
                ),
                okText: '更换邮箱',
                cancelText: '解绑邮箱',
                cancelButtonProps: { danger: true },
                onOk: () => openEmailModal('change'),
                onCancel: () => openEmailModal('unbind'),
              });
            } else {
              openEmailModal('bind');
            }
          },
        },
        {
          key: 'change-password',
          icon: <LockOutlined />,
          label: '修改密码',
          onClick: () => setPasswordModalVisible(true),
        },
        {
          type: 'divider' as const,
        },
        {
          key: 'logout',
          icon: <LogoutOutlined />,
          label: '退出登录',
          onClick: handleLogout,
        },
      ];

      return (
        <>
          <Dropdown menu={{ items: menuItems }} placement="bottomRight">
            <Space style={{ cursor: 'pointer', padding: '0 12px' }}>
              <Avatar
                size="small"
                icon={<UserOutlined />}
                src={initialState.currentDoctor.avatar}
              />
              <span>{initialState.currentDoctor.name}</span>
              {initialState.currentDoctor.title && (
                <span style={{ color: '#999', fontSize: 12 }}>
                  ({initialState.currentDoctor.title})
                </span>
              )}
            </Space>
          </Dropdown>

          {/* 修改密码弹窗 */}
          <Modal
            title="修改密码"
            open={passwordModalVisible}
            onCancel={() => {
              setPasswordModalVisible(false);
              form.resetFields();
            }}
            onOk={() => form.submit()}
            confirmLoading={passwordLoading}
            destroyOnClose
          >
            <Form
              form={form}
              layout="vertical"
              onFinish={handleChangePassword}
            >
              <Form.Item
                name="oldPassword"
                label="原密码"
                rules={[
                  { required: true, message: '请输入原密码' },
                  { min: 6, message: '密码至少6位' },
                ]}
              >
                <Input.Password placeholder="请输入原密码" />
              </Form.Item>
              <Form.Item
                name="newPassword"
                label="新密码"
                rules={[
                  { required: true, message: '请输入新密码' },
                  { min: 6, message: '密码至少6位' },
                  { max: 20, message: '密码最多20位' },
                ]}
              >
                <Input.Password placeholder="请输入新密码" />
              </Form.Item>
              <Form.Item
                name="confirmPassword"
                label="确认新密码"
                dependencies={['newPassword']}
                rules={[
                  { required: true, message: '请确认新密码' },
                  ({ getFieldValue }) => ({
                    validator(_, value) {
                      if (!value || getFieldValue('newPassword') === value) {
                        return Promise.resolve();
                      }
                      return Promise.reject(new Error('两次输入的密码不一致'));
                    },
                  }),
                ]}
              >
                <Input.Password placeholder="请再次输入新密码" />
              </Form.Item>
            </Form>
          </Modal>

          {/* 邮箱管理弹窗 */}
          <Modal
            title={getEmailModalTitle()}
            open={emailModalVisible}
            onCancel={() => setEmailModalVisible(false)}
            footer={null}
            destroyOnClose
            width={480}
          >
            <Form
              form={emailForm}
              layout="vertical"
              onFinish={handleEmailSubmit}
            >
              {emailModalType === 'bind' && (
                <>
                  <Form.Item
                    name="email"
                    label="邮箱地址"
                    rules={[
                      { required: true, message: '请输入邮箱' },
                      { type: 'email', message: '邮箱格式不正确' },
                    ]}
                  >
                    <Input placeholder="请输入邮箱地址" prefix={<MailOutlined />} />
                  </Form.Item>
                  <Form.Item
                    name="code"
                    label="验证码"
                    rules={[{ required: true, message: '请输入验证码' }]}
                  >
                    <Input
                      placeholder="请输入验证码"
                      maxLength={6}
                      suffix={
                        <Button
                          type="link"
                          size="small"
                          disabled={emailCodeCountdown > 0}
                          loading={emailCodeSending}
                          onClick={() => handleSendEmailCode('new')}
                          style={{ padding: 0 }}
                        >
                          {emailCodeCountdown > 0 ? `${emailCodeCountdown}s` : '获取验证码'}
                        </Button>
                      }
                    />
                  </Form.Item>
                </>
              )}

              {emailModalType === 'unbind' && (
                <>
                  <Typography.Paragraph type="secondary">
                    验证码将发送到当前绑定的邮箱：<Typography.Text strong>{initialState?.currentDoctor?.email}</Typography.Text>
                  </Typography.Paragraph>
                  <Form.Item
                    name="code"
                    label="验证码"
                    rules={[{ required: true, message: '请输入验证码' }]}
                  >
                    <Input
                      placeholder="请输入验证码"
                      maxLength={6}
                      suffix={
                        <Button
                          type="link"
                          size="small"
                          disabled={emailCodeCountdown > 0}
                          loading={emailCodeSending}
                          onClick={() => handleSendEmailCode('new')}
                          style={{ padding: 0 }}
                        >
                          {emailCodeCountdown > 0 ? `${emailCodeCountdown}s` : '获取验证码'}
                        </Button>
                      }
                    />
                  </Form.Item>
                </>
              )}

              {emailModalType === 'change' && (
                <>
                  <Form.Item
                    name="email"
                    label="新邮箱地址"
                    rules={[
                      { required: true, message: '请输入新邮箱' },
                      { type: 'email', message: '邮箱格式不正确' },
                    ]}
                  >
                    <Input placeholder="请输入新邮箱地址" prefix={<MailOutlined />} />
                  </Form.Item>
                  <Form.Item
                    name="code"
                    label="新邮箱验证码"
                    rules={[{ required: true, message: '请输入新邮箱验证码' }]}
                  >
                    <Input
                      placeholder="请输入新邮箱验证码"
                      maxLength={6}
                      suffix={
                        <Button
                          type="link"
                          size="small"
                          disabled={emailCodeCountdown > 0}
                          loading={emailCodeSending}
                          onClick={() => handleSendEmailCode('new')}
                          style={{ padding: 0 }}
                        >
                          {emailCodeCountdown > 0 ? `${emailCodeCountdown}s` : '获取验证码'}
                        </Button>
                      }
                    />
                  </Form.Item>
                  <Form.Item
                    name="oldCode"
                    label={`旧邮箱验证码（${initialState?.currentDoctor?.email || '当前邮箱'}）`}
                    rules={[{ required: true, message: '请输入旧邮箱验证码' }]}
                  >
                    <Input
                      placeholder="请输入旧邮箱验证码"
                      maxLength={6}
                      suffix={
                        <Button
                          type="link"
                          size="small"
                          disabled={emailOldCodeCountdown > 0}
                          loading={emailOldCodeSending}
                          onClick={() => handleSendEmailCode('old')}
                          style={{ padding: 0 }}
                        >
                          {emailOldCodeCountdown > 0 ? `${emailOldCodeCountdown}s` : '获取验证码'}
                        </Button>
                      }
                    />
                  </Form.Item>
                </>
              )}

              <Form.Item style={{ marginBottom: 0, textAlign: 'right' }}>
                <Space>
                  <Button onClick={() => setEmailModalVisible(false)}>取消</Button>
                  <Button type="primary" htmlType="submit" loading={emailSubmitting}>
                    确认
                  </Button>
                </Space>
              </Form.Item>
            </Form>
          </Modal>
        </>
      );
    },
    onPageChange: () => {
      if (!initialState?.currentDoctor && location.pathname !== '/login') {
        history.push('/login');
      }
    },
  };
};

export const request: RequestConfig = {
  timeout: 30000,
  errorConfig: {
    errorHandler: (error: any) => {
      if (error.response?.status !== 401) {
        message.error(error.message || '请求失败');
      }
    },
  },
  requestInterceptors: [
    (config: any) => {
      const token = getToken();
      if (token) {
        config.headers = { ...config.headers, Authorization: `Bearer ${token}` };
      }
      return config;
    },
  ],
  responseInterceptors: [
    (response: any) => {
      const { data, status } = response;
      
      if (status === 401 || data?.code === 401) {
        // 登录页不弹框
        if (window.location.pathname === '/login') return response;

        removeToken();
        Modal.confirm({
          title: '登录已过期',
          content: data?.message || '您的登录已失效，请重新登录。',
          okText: '重新登录',
          cancelButtonProps: { style: { display: 'none' } },
          closable: false,
          maskClosable: false,
          onOk: () => { window.location.href = '/login'; },
        });
        return response;
      }
      
      if (data?.code && data.code !== 200 && data.code !== 0) {
        message.error(data?.message || '请求失败');
      }
      
      return response;
    },
  ],
};
