import { PageContainer, ProForm, ProFormText } from '@ant-design/pro-components';
import { Card, App, Row, Col, Typography, Space, Spin, Switch, TimePicker, Divider, Skeleton, Button, Tag, Tabs, Timeline, Statistic } from 'antd';
import { useState, useEffect } from 'react';
import { useModel, useRequest } from '@umijs/max';
import { adminApi, notificationPreferenceApi, useEmailBinding } from '@hospital/api';
import type { Admin, NotificationPreference, LoginHistory, DeviceDistribution } from '@hospital/api';
import ImageUpload from '@/components/ImageUpload';
import EmailBindingModal from '@/components/EmailBindingModal';
import IntegrationBindingsSection from './IntegrationBindingsSection';
import { phoneRules } from '@/utils/formValidators';
import {
  BellOutlined,
  ClockCircleOutlined,
  CustomerServiceOutlined,
  DesktopOutlined,
  HistoryOutlined,
  LinkOutlined,
  LogoutOutlined,
  MailOutlined,
  MessageOutlined,
  MobileOutlined,
  MoonOutlined,
  NotificationOutlined,
  PauseCircleOutlined,
  StopOutlined,
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

/** 格式化时间间隔为可读字符串（复用 online-users.tsx 逻辑） */
const formatDuration = (seconds: number | undefined | null): string => {
  if (seconds === undefined || seconds === null) return '-';
  if (seconds < 60) return `${seconds}秒`;
  if (seconds < 3600) {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}分${secs > 0 ? secs + '秒' : ''}`;
  }
  const hours = Math.floor(seconds / 3600);
  const mins = Math.floor((seconds % 3600) / 60);
  return `${hours}小时${mins > 0 ? mins + '分' : ''}`;
};

/** 格式化时间 */
const formatTime = (time: string | undefined | null): string => {
  if (!time) return '-';
  return new Date(time).toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
};

/** 获取设备类型图标 */
const getDeviceIcon = (deviceType: string | undefined) => {
  switch (deviceType) {
    case 'mobile':
      return <MobileOutlined style={{ fontSize: 16, color: '#52c41a' }} />;
    case 'tablet':
      return <MobileOutlined style={{ fontSize: 16, color: '#1890ff' }} />;
    default:
      return <DesktopOutlined style={{ fontSize: 16, color: '#722ed1' }} />;
  }
};

/** 获取退出类型标签 */
const getLogoutTypeTag = (logoutType: string | undefined) => {
  switch (logoutType) {
    case 'manual':
      return <Tag icon={<LogoutOutlined />} color="blue">主动退出</Tag>;
    case 'kicked':
      return <Tag icon={<StopOutlined />} color="red">强制下线</Tag>;
    case 'timeout':
      return <Tag icon={<ClockCircleOutlined />} color="orange">超时退出</Tag>;
    default:
      return <Tag color="default">未知</Tag>;
  }
};

// ========== 使用概览 Tab 组件 ==========

interface UsageOverviewProps {
  adminId: string | undefined;
}

const UsageOverviewTab: React.FC<UsageOverviewProps> = ({ adminId }) => {
  const { data: stats, loading: statsLoading } = useRequest(
    () => adminApi.getAccountStats({ adminId }),
    { refreshDeps: [adminId], ready: !!adminId },
  );

  const { data: historyData, loading: historyLoading } = useRequest(
    () => adminApi.getLoginHistory(adminId!, { page: 1, pageSize: 10 }),
    { refreshDeps: [adminId], ready: !!adminId },
  );

  const loginHistory: LoginHistory[] = historyData?.list ?? [];

  // 设备分布用 Tag 展示
  const renderDeviceDistribution = (devices: DeviceDistribution[]) => {
    if (!devices || devices.length === 0) {
      return <Text type="secondary">暂无数据</Text>;
    }
    return (
      <Space wrap>
        {devices.map((d) => (
          <Tag key={d.deviceType} icon={getDeviceIcon(d.deviceType)} color="blue">
            {d.deviceType === 'desktop' ? '桌面端' : d.deviceType === 'mobile' ? '移动端' : d.deviceType === 'tablet' ? '平板' : d.deviceType}
            {' '}{d.count}次 ({d.percentage}%)
          </Tag>
        ))}
      </Space>
    );
  };

  // 浏览器分布用 Tag 展示
  const renderBrowserDistribution = (browsers: DeviceDistribution[]) => {
    if (!browsers || browsers.length === 0) {
      return <Text type="secondary">暂无数据</Text>;
    }
    return (
      <Space wrap>
        {browsers.map((b) => (
          <Tag key={b.deviceType} color="cyan">
            {b.deviceType} {b.count}次 ({b.percentage}%)
          </Tag>
        ))}
      </Space>
    );
  };

  return (
    <>
      {/* 顶部统计卡片 */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Card loading={statsLoading}>
            <Statistic
              title="总登录次数"
              value={stats?.summary?.totalLogins ?? 0}
              suffix="次"
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card loading={statsLoading}>
            <Statistic
              title="总使用时长"
              value={stats?.summary?.totalDurationHours ?? 0}
              precision={1}
              suffix="小时"
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card loading={statsLoading}>
            <Statistic
              title="平均使用时长"
              value={stats?.summary?.avgDurationMinutes ?? 0}
              precision={1}
              suffix="分钟/次"
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card loading={statsLoading}>
            <Statistic
              title="活跃账号数"
              value={stats?.summary?.activeAccounts ?? 0}
              suffix="个"
            />
          </Card>
        </Col>
      </Row>

      {/* 设备分布 */}
      <Card title="设备分布" style={{ marginBottom: 16 }}>
        <Row gutter={24}>
          <Col span={12}>
            <Typography.Title level={5}>设备类型</Typography.Title>
            {renderDeviceDistribution(stats?.deviceDistribution ?? [])}
          </Col>
          <Col span={12}>
            <Typography.Title level={5}>浏览器</Typography.Title>
            {renderBrowserDistribution(stats?.browserDistribution ?? [])}
          </Col>
        </Row>
      </Card>

      {/* 最近登录记录 */}
      <Card title={<Space><HistoryOutlined /><span>最近登录记录</span></Space>}>
        {historyLoading ? (
          <div style={{ textAlign: 'center', padding: 40 }}>加载中...</div>
        ) : loginHistory.length === 0 ? (
          <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>暂无登录记录</div>
        ) : (
          <Timeline
            items={loginHistory.map((item) => ({
              color: item.logoutTime ? 'gray' : 'green',
              children: (
                <div style={{ marginBottom: 16 }}>
                  <div style={{ marginBottom: 8 }}>
                    <Space>
                      <Text strong>登录时间:</Text>
                      <Text>{formatTime(item.loginTime)}</Text>
                    </Space>
                  </div>
                  {item.logoutTime && (
                    <div style={{ marginBottom: 8 }}>
                      <Space>
                        <Text strong>退出时间:</Text>
                        <Text>{formatTime(item.logoutTime)}</Text>
                        {getLogoutTypeTag(item.logoutType)}
                      </Space>
                    </div>
                  )}
                  {!item.logoutTime && (
                    <div style={{ marginBottom: 8 }}>
                      <Tag color="green">当前会话</Tag>
                    </div>
                  )}
                  <div style={{ marginBottom: 8 }}>
                    <Space>
                      <Text strong>在线时长:</Text>
                      <Text>{formatDuration(item.duration)}</Text>
                    </Space>
                  </div>
                  <div style={{ marginBottom: 8 }}>
                    <Space>
                      {getDeviceIcon(item.deviceType)}
                      <Text type="secondary">
                        {item.browser || 'Unknown'} / {item.os || 'Unknown'}
                      </Text>
                    </Space>
                  </div>
                  <div>
                    <Space>
                      <Text strong>IP:</Text>
                      <Text code>{item.loginIp || '-'}</Text>
                    </Space>
                  </div>
                </div>
              ),
            }))}
          />
        )}
      </Card>
    </>
  );
};

// ========== 主页面 ==========

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

  // 邮箱管理：统一使用共享 hook（默认走 accountApi）
  const emailBinding = useEmailBinding({
    currentEmail: admin?.email,
    onSuccess: async (mode) => {
      if (mode === 'bind') message.success('邮箱绑定成功');
      else if (mode === 'unbind') message.success('邮箱解绑成功');
      else message.success('邮箱换绑成功');
      // 刷新管理员信息 + 全局状态
      try {
        const updatedAdmin = await adminApi.getCurrentAdmin();
        setAdmin(updatedAdmin);
        if (initialState) {
          setInitialState({ ...initialState, currentUser: updatedAdmin });
        }
      } catch {
        /* 静默 */
      }
    },
    onError: (error) => {
      const msg = (error as any)?.message || '操作失败';
      message.error(msg);
    },
  });

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
  }

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

        <Tabs
          defaultActiveKey="profile"
          items={[
            {
              key: 'profile',
              label: '个人资料',
              children: (
                <>
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
                            phoneRules.pattern,
                          ]}
                          fieldProps={{ autoComplete: 'off' }}
                        />
                      </ProForm.Group>
                      {/* 邮箱绑定管理 */}
                      <div style={{ marginBottom: 24 }}>
                        <div style={{ marginBottom: 8 }}>
                          <Typography.Text type="secondary" style={{ fontSize: 14 }}>邮箱</Typography.Text>
                        </div>
                        {loading ? (
                          <Skeleton.Input active size="small" style={{ width: 320 }} />
                        ) : (
                          <Space align="center" wrap>
                            {admin?.email ? (
                              <>
                                <Tag icon={<MailOutlined />} color="blue">{admin.email}</Tag>
                                <Tag color="green">已绑定</Tag>
                                <Button
                                  size="small"
                                  icon={<SwapOutlined />}
                                  onClick={() => emailBinding.openModal('change')}
                                >
                                  更换邮箱
                                </Button>
                                <Button
                                  size="small"
                                  danger
                                  icon={<DisconnectOutlined />}
                                  onClick={() => emailBinding.openModal('unbind')}
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
                                  onClick={() => emailBinding.openModal('bind')}
                                >
                                  绑定邮箱
                                </Button>
                              </>
                            )}
                          </Space>
                        )}
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
                </>
              ),
            },
            {
              key: 'usage',
              label: '使用概览',
              children: <UsageOverviewTab adminId={admin?.id} />,
            },
            {
              key: 'integrations',
              label: '第三方账号',
              children: <IntegrationBindingsSection />,
            },
          ]}
        />

        {/* 邮箱管理弹窗 */}
        <EmailBindingModal binding={emailBinding} currentEmail={admin?.email} />
      </Spin>
    </PageContainer>
  );
};

export default AccountSettingsPage;
