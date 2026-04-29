import {
  Card,
  Form,
  Switch,
  TimePicker,
  Button,
  message,
  Spin,
  Space,
  Typography,
  Divider,
} from 'antd';
import { useState, useEffect } from 'react';
import {
  BellOutlined,
  ClockCircleOutlined,
  CustomerServiceOutlined,
  MessageOutlined,
  MoonOutlined,
  NotificationOutlined,
  SaveOutlined,
} from '@ant-design/icons';
import { notificationPreferenceApi } from '@hospital/api';
import type { NotificationPreference } from '@hospital/api';
import dayjs from 'dayjs';

const { Title, Text } = Typography;

interface QuietHoursConfig {
  enabled: boolean;
  startTime: dayjs.Dayjs | null;
  endTime: dayjs.Dayjs | null;
}

const NotificationSettingsPage: React.FC = () => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [preference, setPreference] = useState<NotificationPreference | null>(
    null
  );
  const [quietHours, setQuietHours] = useState<QuietHoursConfig>({
    enabled: false,
    startTime: null,
    endTime: null,
  });

  useEffect(() => {
    loadPreferences();
  }, []);

  const loadPreferences = async () => {
    try {
      setLoading(true);
      const data = await notificationPreferenceApi.get();
      setPreference(data);
      form.setFieldsValue({
        appointmentEnabled: data.appointmentEnabled,
        systemEnabled: data.systemEnabled,
        smsEnabled: data.smsEnabled,
        inAppEnabled: data.inAppEnabled,
      });

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
      message.error('加载通知偏好失败，请重试');
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      setSaving(true);

      const updates: Partial<NotificationPreference> = {
        appointmentEnabled: values.appointmentEnabled,
        systemEnabled: values.systemEnabled,
        smsEnabled: values.smsEnabled,
        inAppEnabled: values.inAppEnabled,
      };

      if (quietHours.enabled) {
        updates.quietHoursStart = quietHours.startTime?.format('HH:mm');
        updates.quietHoursEnd = quietHours.endTime?.format('HH:mm');
      } else {
        updates.quietHoursStart = undefined;
        updates.quietHoursEnd = undefined;
      }

      await notificationPreferenceApi.update(updates);
      message.success('保存成功');
    } catch (error) {
      console.error('保存通知偏好失败', error);
      message.error('保存失败，请重试');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <Spin size="large" tip="加载中..." />
      </div>
    );
  }

  return (
    <div className="p-6 bg-gray-50 min-h-screen">
      <div className="max-w-3xl mx-auto">
        <div className="mb-6">
          <Title level={3}>通知设置</Title>
          <Text type="secondary">管理您的通知偏好和免打扰时段</Text>
        </div>

        <Form form={form} layout="vertical">
          {/* Notification Types */}
          <Card
            title={
              <Space>
                <BellOutlined />
                <span>通知类型</span>
              </Space>
            }
            className="mb-4"
          >
            <Form.Item
              name="appointmentEnabled"
              label="预约通知"
              valuePropName="checked"
            >
              <Switch
                checkedChildren="开启"
                unCheckedChildren="关闭"
                onChange={(checked) =>
                  form.setFieldValue('appointmentEnabled', checked)
                }
              />
            </Form.Item>
            <Text type="secondary" className="text-sm">
              接收新预约、预约变更等通知
            </Text>

            <Divider className="my-4" />

            <Form.Item
              name="systemEnabled"
              label="系统通知"
              valuePropName="checked"
            >
              <Switch
                checkedChildren="开启"
                unCheckedChildren="关闭"
                onChange={(checked) =>
                  form.setFieldValue('systemEnabled', checked)
                }
              />
            </Form.Item>
            <Text type="secondary" className="text-sm">
              接收系统公告、维护通知等
            </Text>
          </Card>

          {/* Notification Channels */}
          <Card
            title={
              <Space>
                <NotificationOutlined />
                <span>通知渠道</span>
              </Space>
            }
            className="mb-4"
          >
            <Form.Item
              name="smsEnabled"
              label="短信通知"
              valuePropName="checked"
            >
              <Switch
                checkedChildren="开启"
                unCheckedChildren="关闭"
                onChange={(checked) =>
                  form.setFieldValue('smsEnabled', checked)
                }
              />
            </Form.Item>
            <Text type="secondary" className="text-sm">
              通过手机短信接收通知
            </Text>

            <Divider className="my-4" />

            <Form.Item
              name="inAppEnabled"
              label="站内通知"
              valuePropName="checked"
            >
              <Switch
                checkedChildren="开启"
                unCheckedChildren="关闭"
                onChange={(checked) =>
                  form.setFieldValue('inAppEnabled', checked)
                }
              />
            </Form.Item>
            <Text type="secondary" className="text-sm">
              在医生工作台内接收通知
            </Text>
          </Card>

          {/* Quiet Hours */}
          <Card
            title={
              <Space>
                <MoonOutlined />
                <span>免打扰时段</span>
              </Space>
            }
            className="mb-4"
          >
            <div className="mb-4">
              <Switch
                checked={quietHours.enabled}
                onChange={(checked) =>
                  setQuietHours({ ...quietHours, enabled: checked })
                }
                checkedChildren="已启用"
                unCheckedChildren="已关闭"
              />
              <Text type="secondary" className="ml-2 text-sm">
                启用后在设定时间段内不接收通知
              </Text>
            </div>

            {quietHours.enabled && (
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <div className="mb-2">
                    <Text strong>开始时间</Text>
                  </div>
                  <TimePicker
                    value={quietHours.startTime}
                    onChange={(time) =>
                      setQuietHours({ ...quietHours, startTime: time })
                    }
                    format="HH:mm"
                    className="w-full"
                    placeholder="选择开始时间"
                  />
                </div>
                <div>
                  <div className="mb-2">
                    <Text strong>结束时间</Text>
                  </div>
                  <TimePicker
                    value={quietHours.endTime}
                    onChange={(time) =>
                      setQuietHours({ ...quietHours, endTime: time })
                    }
                    format="HH:mm"
                    className="w-full"
                    placeholder="选择结束时间"
                  />
                </div>
              </div>
            )}
          </Card>

          {/* Actions */}
          <div className="flex justify-end gap-3">
            <Button onClick={loadPreferences} disabled={saving}>
              重置
            </Button>
            <Button
              type="primary"
              icon={<SaveOutlined />}
              onClick={handleSave}
              loading={saving}
            >
              保存设置
            </Button>
          </div>
        </Form>
      </div>
    </div>
  );
};

export default NotificationSettingsPage;
