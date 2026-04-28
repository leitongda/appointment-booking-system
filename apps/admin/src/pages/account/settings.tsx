import { PageContainer, ProForm, ProFormText, ProFormSwitch } from '@ant-design/pro-components';
import { Card, App, Row, Col, Typography, Space, Spin, Switch, TimePicker, Divider } from 'antd';
import { useState, useEffect } from 'react';
import { useModel } from '@umijs/max';
import { adminApi, notificationPreferenceApi } from '@hospital/api';
import type { Admin, NotificationPreference } from '@hospital/api';
import ImageUpload from '@/components/ImageUpload';
import {
  BellOutlined,
  ClockCircleOutlined,
  CustomerServiceOutlined,
  MessageOutlined,
  MoonOutlined,
  NotificationOutlined,
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

  useEffect(() => {
    loadAdmin();
    loadNotificationPreferences();
  }, []);

  const loadAdmin = async () => {
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

  const loadNotificationPreferences = async () => {
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
  };

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
              <Space direction="vertical" size={4}>
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
            <ProFormText
              name="email"
              label="邮箱"
              width="md"
              placeholder="请输入邮箱"
              rules={[
                { type: 'email', message: '邮箱格式不正确' },
              ]}
              fieldProps={{ autoComplete: 'off' }}
            />
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
      </Spin>
    </PageContainer>
  );
};

export default AccountSettingsPage;

