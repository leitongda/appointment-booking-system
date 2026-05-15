import { PageContainer, ProForm, ProFormText } from '@ant-design/pro-components';
import { Card, App, Row, Col, Typography, Space, Spin, Switch, TimePicker, Divider, Modal, Form, Input, Button, Tag } from 'antd';
import { useState, useEffect, useRef } from 'react';
import { useModel } from '@umijs/max';
import { adminApi, notificationPreferenceApi } from '@hospital/api';
import type { Admin, NotificationPreference } from '@hospital/api';
import ImageUpload from '@/components/ImageUpload';
import {
  BellOutlined,
  ClockCircleOutlined,
  CustomerServiceOutlined,
  LinkOutlined,
  MailOutlined,
  MessageOutlined,
  MoonOutlined,
  NotificationOutlined,
  PauseCircleOutlined,
  SwapOutlined,
  DisconnectOutlined,
  WechatOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';

const { Title, Text } = Typography;

interface QuietHoursConfig {
  enabled: boolean;
  startTime: dayjs.Dayjs | null;
  endTime: dayjs.Dayjs | null;
}

const AccountSettingsPage: React.FC = () => {
  const { message } = App.useApp();
  const { initialState, setInitialState } = useModel('@@initialState');
  const [loading, setLoading] = useState(false);
  const [admin, setAdmin] = useState<Admin | null>(null);
  const [avatarUrl, setAvatarUrl] = useState<string | undefined>();
  const [avatarSaving, setAvatarSaving] = useState(false);

  const [notificationPreference, setNotificationPreference] = useState<NotificationPreference | null>(null);
  const [notificationLoading, setNotificationLoading] = useState(false);
  const [quietHours, setQuietHours] = useState<QuietHoursConfig>({
    enabled: false,
    startTime: null,
    endTime: null,
  });

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

  async function loadAdmin() {
    setLoading(true);
    try {
      const data = await adminApi.getCurrentAdmin();
      setAdmin(data);
      setAvatarUrl(data.avatar);
    } catch (error) {
      console.error('加载用户信息失败', error);
    } finally {
      setLoading(false);
    }
  };

  // 头像变更时自动保存
  const handleAvatarChange = async (url: string | undefined) => {
    setAvatarUrl(url);
    if (url === admin?.avatar) return; // 没有变化不需要保存
    
    setAvatarSaving(true);
    try {
      const updatedAdmin = await adminApi.updateProfile({ avatar: url });
      message.success('头像更新成功');
      setAdmin(updatedAdmin);
      // 更新全局状态
      if (initialState) {
        setInitialState({
          ...initialState,
          currentUser: updatedAdmin,
        });
      }
    } catch (error: any) {
      message.error(error.message || '头像更新失败');
      // 恢复原来的头像
      setAvatarUrl(admin?.avatar);
    } finally {
      setAvatarSaving(false);
    }
  };

  const handleSubmit = async (values: { name?: string; phone?: string; email?: string }) => {
    try {
      const updatedAdmin = await adminApi.updateProfile(values);
      message.success('保存成功');
      setAdmin(updatedAdmin);
      // 更新全局状态
      if (initialState) {
        setInitialState({
          ...initialState,
          currentUser: updatedAdmin,
        });
      }
    } catch (error: any) {
      message.error(error.message || '保存失败');
    }
  };

  async function loadNotificationPreferences() {
    try {
      setNotificationLoading(true);
      const data = await notificationPreferenceApi.get();
      setNotificationPreference(data);

      const hasQuietHours = data.quietHoursStart || data.quietHoursEnd;
      setQuietHours({
        enabled: !!hasQuietHours,
        startTime: data.quietHoursStart
          ? dayjs(data.quietHoursStart, 'HH:mm')
          : null,
        endTime: data.quietHoursEnd ? dayjs(data.quietHoursEnd, 'HH:mm') : null,
      });
    } catch (error) {
      console.error('加载通知偏好失败', error);
    } finally {
      setNotificationLoading(false);
    }
  }

  useEffect(() => {
    loadAdmin();
    loadNotificationPreferences();
    return () => {
      if (emailTimerRef.current) clearInterval(emailTimerRef.current);
      if (emailOldTimerRef.current) clearInterval(emailOldTimerRef.current);
    };
  }, []);

  const handleNotificationToggle = async (
    key: keyof NotificationPreference,
    value: boolean
  ) => {
    if (!notificationPreference) return;

    try {
      const updated = await notificationPreferenceApi.update({ [key]: value });
      setNotificationPreference(updated);
      message.success('设置已保存');
    } catch (error) {
      message.error('保存失败');
      setNotificationPreference({ ...notificationPreference });
    }
  };

  const handleQuietHoursToggle = async (enabled: boolean) => {
    if (!notificationPreference) return;

    try {
      const updates: Partial<NotificationPreference> = {
        quietHoursStart: enabled ? '22:00' : undefined,
        quietHoursEnd: enabled ? '08:00' : undefined,
      };
      const updated = await notificationPreferenceApi.update(updates);
      setNotificationPreference(updated);
      setQuietHours({
        ...quietHours,
        enabled,
        startTime: enabled ? dayjs('22:00', 'HH:mm') : null,
        endTime: enabled ? dayjs('08:00', 'HH:mm') : null,
      });
      message.success('设置已保存');
    } catch (error) {
      message.error('保存失败');
      setQuietHours({ ...quietHours, enabled: !enabled });
    }
  };

  const handleQuietHoursTimeChange = async (
    field: 'start' | 'end',
    time: dayjs.Dayjs | null
  ) => {
    if (!notificationPreference) return;

    const newQuietHours = { ...quietHours };
    if (field === 'start') {
      newQuietHours.startTime = time;
    } else {
      newQuietHours.endTime = time;
    }

    try {
      const updates: Partial<NotificationPreference> = {
        quietHoursStart: newQuietHours.startTime?.format('HH:mm'),
        quietHoursEnd: newQuietHours.endTime?.format('HH:mm'),
      };
      const updated = await notificationPreferenceApi.update(updates);
      setNotificationPreference(updated);
      setQuietHours(newQuietHours);
      message.success('设置已保存');
    } catch (error) {
      message.error('保存失败');
    }
  };

  // ========== 邮箱管理 ==========

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
        await adminApi.sendProfileEmailCode(email);
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
        // 给旧邮箱发验证码（解绑/换绑场景）
        if (!admin?.email) {
          message.error('当前未绑定邮箱');
          return;
        }
        setEmailOldCodeSending(true);
        await adminApi.sendProfileEmailCode(admin.email);
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
        await adminApi.bindEmail({ email: values.email, code: values.code });
        message.success('邮箱绑定成功');
      } else if (emailModalType === 'unbind') {
        await adminApi.unbindEmail({ code: values.code });
        message.success('邮箱解绑成功');
      } else if (emailModalType === 'change') {
        await adminApi.changeEmail({
          newEmail: values.email,
          newEmailCode: values.code,
          oldEmailCode: values.oldCode,
        });
        message.success('邮箱换绑成功');
      }

      setEmailModalVisible(false);
      // 刷新管理员信息
      const updatedAdmin = await adminApi.getCurrentAdmin();
      setAdmin(updatedAdmin);
      if (initialState) {
        setInitialState({
          ...initialState,
          currentUser: updatedAdmin,
        });
      }
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

  return (
    <PageContainer title="个人设置">
      <Spin spinning={loading}>
        <Card style={{ marginBottom: 16 }}>
          <Row gutter={24} align="middle">
            <Col>
              <Spin spinning={avatarSaving}>
                <ImageUpload
                  value={avatarUrl}
                  onChange={handleAvatarChange}
                  aspectRatio="1:1"
                  width={100}
                  height={100}
                  folder="avatars"
                  placeholder="上传头像"
                  allowUrlTransfer={false}
                  showCrop={true}
                />
              </Spin>
            </Col>
            <Col>
              <Space size={4}>
                <Title level={4} style={{ margin: 0 }}>
                  {admin?.name || admin?.username}
                </Title>
                <Text type="secondary">用户名：{admin?.username}</Text>
                <Text type="secondary">角色：{admin?.roleName || '-'}</Text>
                <Text type="secondary" style={{ fontSize: 12 }}>点击左侧可更换头像</Text>
              </Space>
            </Col>
          </Row>
        </Card>

        <Card title="基本信息">
          <ProForm
            onFinish={handleSubmit}
            initialValues={{
              name: admin?.name,
              phone: admin?.phone,
              email: admin?.email,
            }}
            submitter={{
              searchConfig: { submitText: '保存' },
              resetButtonProps: { style: { display: 'none' } },
            }}
          >
            <ProForm.Group>
              <ProFormText
                name="name"
                label="姓名"
                width="md"
                placeholder="请输入姓名"
                fieldProps={{ autoComplete: 'off' }}
              />
              <ProFormText
                name="phone"
                label="手机号"
                width="md"
                placeholder="请输入手机号"
                rules={[
                  { pattern: /^1\d{10}$/, message: '手机号格式不正确' },
                ]}
                fieldProps={{ autoComplete: 'off' }}
              />
            </ProForm.Group>
            {/* 邮箱绑定管理 */}
            <div style={{ marginBottom: 24 }}>
              <div style={{ marginBottom: 8 }}>
                <Typography.Text type="secondary" style={{ fontSize: 14 }}>邮箱</Typography.Text>
              </div>
              <Space align="center">
                {admin?.email ? (
                  <>
                    <Tag icon={<MailOutlined />} color="blue">{admin.email}</Tag>
                    <Tag color="green">已绑定</Tag>
                    <Button
                      size="small"
                      icon={<SwapOutlined />}
                      onClick={() => openEmailModal('change')}
                    >
                      更换邮箱
                    </Button>
                    <Button
                      size="small"
                      danger
                      icon={<DisconnectOutlined />}
                      onClick={() => openEmailModal('unbind')}
                    >
                      解绑邮箱
                    </Button>
                  </>
                ) : (
                  <>
                    <Tag>未绑定</Tag>
                    <Button
                      size="small"
                      type="primary"
                      icon={<LinkOutlined />}
                      onClick={() => openEmailModal('bind')}
                    >
                      绑定邮箱
                    </Button>
                  </>
                )}
              </Space>
            </div>
          </ProForm>
        </Card>

        <Card title="通知设置" loading={notificationLoading} style={{ marginTop: 16 }}>
          {notificationPreference && (
            <>
              <div style={{ marginBottom: 16 }}>
                <Typography.Title level={5} style={{ marginBottom: 12 }}>
                  <NotificationOutlined /> 通知类型
                </Typography.Title>
                <Space direction="vertical" style={{ width: '100%' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <Space>
                      <BellOutlined />
                      <span>预约通知</span>
                    </Space>
                    <Switch
                      checked={notificationPreference.appointmentEnabled}
                      onChange={(v) => handleNotificationToggle('appointmentEnabled', v)}
                    />
                  </div>
                  <Divider style={{ margin: '8px 0' }} />
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <Space>
                      <ClockCircleOutlined />
                      <span>提醒通知</span>
                    </Space>
                    <Switch
                      checked={notificationPreference.reminderEnabled}
                      onChange={(v) => handleNotificationToggle('reminderEnabled', v)}
                    />
                  </div>
                  <Divider style={{ margin: '8px 0' }} />
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <Space>
                      <CustomerServiceOutlined />
                      <span>系统通知</span>
                    </Space>
                    <Switch
                      checked={notificationPreference.systemEnabled}
                      onChange={(v) => handleNotificationToggle('systemEnabled', v)}
                    />
                  </div>
                  <Divider style={{ margin: '8px 0' }} />
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <Space>
                      <NotificationOutlined />
                      <span>叫号通知</span>
                    </Space>
                    <Switch
                      checked={notificationPreference.queueCallEnabled}
                      onChange={(v) => handleNotificationToggle('queueCallEnabled', v)}
                    />
                  </div>
                  <Divider style={{ margin: '8px 0' }} />
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <Space>
                      <PauseCircleOutlined />
                      <span>停诊通知</span>
                    </Space>
                    <Switch
                      checked={notificationPreference.stopClinicEnabled}
                      onChange={(v) => handleNotificationToggle('stopClinicEnabled', v)}
                    />
                  </div>
                </Space>
              </div>

              <Divider />

              <div style={{ marginBottom: 16 }}>
                <Typography.Title level={5} style={{ marginBottom: 12 }}>
                  <MessageOutlined /> 通知渠道
                </Typography.Title>
                <Space direction="vertical" style={{ width: '100%' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <Space>
                      <CustomerServiceOutlined />
                      <span>短信通知</span>
                    </Space>
                    <Switch
                      checked={notificationPreference.smsEnabled}
                      onChange={(v) => handleNotificationToggle('smsEnabled', v)}
                    />
                  </div>
                  <Divider style={{ margin: '8px 0' }} />
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <Space>
                      <MessageOutlined />
                      <span>站内通知</span>
                    </Space>
                    <Switch
                      checked={notificationPreference.inAppEnabled}
                      onChange={(v) => handleNotificationToggle('inAppEnabled', v)}
                    />
                  </div>
                  <Divider style={{ margin: '8px 0' }} />
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <Space>
                      <MailOutlined />
                      <span>邮件通知</span>
                    </Space>
                    <Switch
                      checked={notificationPreference.emailEnabled}
                      onChange={(v) => handleNotificationToggle('emailEnabled', v)}
                    />
                  </div>
                  <Divider style={{ margin: '8px 0' }} />
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <Space>
                      <WechatOutlined />
                      <span>微信推送</span>
                    </Space>
                    <Switch
                      checked={notificationPreference.wechatEnabled}
                      onChange={(v) => handleNotificationToggle('wechatEnabled', v)}
                    />
                  </div>
                </Space>
              </div>

              <Divider />

              <div>
                <Typography.Title level={5} style={{ marginBottom: 12 }}>
                  <MoonOutlined /> 免打扰时段
                </Typography.Title>
                <div style={{ marginBottom: 12 }}>
                  <Switch
                    checked={quietHours.enabled}
                    onChange={handleQuietHoursToggle}
                    checkedChildren="已启用"
                    unCheckedChildren="已关闭"
                  />
                  <Typography.Text type="secondary" style={{ marginLeft: 8 }}>
                    启用后在设定时间段内不接收通知
                  </Typography.Text>
                </div>

                {quietHours.enabled && (
                  <Row gutter={16}>
                    <Col span={12}>
                      <div style={{ marginBottom: 8 }}>
                        <Typography.Text strong>开始时间</Typography.Text>
                      </div>
                      <TimePicker
                        value={quietHours.startTime}
                        onChange={(time) => handleQuietHoursTimeChange('start', time)}
                        format="HH:mm"
                        style={{ width: '100%' }}
                      />
                    </Col>
                    <Col span={12}>
                      <div style={{ marginBottom: 8 }}>
                        <Typography.Text strong>结束时间</Typography.Text>
                      </div>
                      <TimePicker
                        value={quietHours.endTime}
                        onChange={(time) => handleQuietHoursTimeChange('end', time)}
                        format="HH:mm"
                        style={{ width: '100%' }}
                      />
                    </Col>
                  </Row>
                )}
              </div>
            </>
          )}
        </Card>

        {/* 邮箱管理弹窗 */}
        <Modal
          title={getEmailModalTitle()}
          open={emailModalVisible}
          onCancel={() => setEmailModalVisible(false)}
          footer={null}
          destroyOnHidden
          width={480}
        >
          <Form
            form={emailForm}
            layout="vertical"
            onFinish={handleEmailSubmit}
          >
            {/* 绑定邮箱：输入新邮箱 + 验证码 */}
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

            {/* 解绑邮箱：发送验证码到当前邮箱 + 输入验证码 */}
            {emailModalType === 'unbind' && (
              <>
                <Typography.Paragraph type="secondary">
                  验证码将发送到当前绑定的邮箱：<Typography.Text strong>{admin?.email}</Typography.Text>
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

            {/* 换绑邮箱：新邮箱 + 新邮箱验证码 + 旧邮箱验证码 */}
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
                  label={`旧邮箱验证码（${admin?.email || '当前邮箱'}）`}
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
      </Spin>
    </PageContainer>
  );
};

export default AccountSettingsPage;
