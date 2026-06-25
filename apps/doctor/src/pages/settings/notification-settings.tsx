import { PageContainer } from '@ant-design/pro-components';
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
  Row,
  Col,
} from 'antd';
import { useState, useEffect } from 'react';
import {
  BellOutlined,
  MoonOutlined,
  NotificationOutlined,
  SaveOutlined,
} from '@ant-design/icons';
import { notificationPreferenceApi } from '@hospital/api';
import type { NotificationPreference } from '@hospital/api';
import dayjs from 'dayjs';

const { Text } = Typography;

interface QuietHoursConfig {
  enabled: boolean;
  startTime: dayjs.Dayjs | null;
  endTime: dayjs.Dayjs | null;
}

const NotificationSettingsPage: React.FC = () => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
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
      form.setFieldsValue({
        appointmentEnabled: data.appointmentEnabled,
        reminderEnabled: data.reminderEnabled,
        queueCallEnabled: data.queueCallEnabled,
        stopClinicEnabled: data.stopClinicEnabled,
        wechatEnabled: data.wechatEnabled,
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
        reminderEnabled: values.reminderEnabled,
        queueCallEnabled: values.queueCallEnabled,
        stopClinicEnabled: values.stopClinicEnabled,
        wechatEnabled: values.wechatEnabled,
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
      <PageContainer>
        <div style={{ textAlign: 'center', paddingTop: 200 }}>
          <Spin size="large" tip="加载中..." />
        </div>
      </PageContainer>
    );
  }

  return (
    <PageContainer>
      <div style={{ maxWidth: 720, margin: '0 auto' }}>
        <Form form={form} layout="vertical">
          <Card
            title={
              <Space>
                <BellOutlined />
                <span>通知类型</span>
              </Space>
            }
            style={{ marginBottom: 16 }}
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
            <Text type="secondary" style={{ fontSize: 14 }}>
              接收新预约、预约变更等通知
            </Text>

            <Divider style={{ margin: '16px 0' }} />

            <Form.Item
              name="reminderEnabled"
              label="预约提醒"
              valuePropName="checked"
            >
              <Switch
                checkedChildren="开启"
                unCheckedChildren="关闭"
                onChange={(checked) =>
                  form.setFieldValue('reminderEnabled', checked)
                }
              />
            </Form.Item>
            <Text type="secondary" style={{ fontSize: 14 }}>
              接收就诊前提醒通知
            </Text>

            <Divider style={{ margin: '16px 0' }} />

            <Form.Item
              name="queueCallEnabled"
              label="排队叫号"
              valuePropName="checked"
            >
              <Switch
                checkedChildren="开启"
                unCheckedChildren="关闭"
                onChange={(checked) =>
                  form.setFieldValue('queueCallEnabled', checked)
                }
              />
            </Form.Item>
            <Text type="secondary" style={{ fontSize: 14 }}>
              接收排队叫号通知
            </Text>

            <Divider style={{ margin: '16px 0' }} />

            <Form.Item
              name="stopClinicEnabled"
              label="停诊通知"
              valuePropName="checked"
            >
              <Switch
                checkedChildren="开启"
                unCheckedChildren="关闭"
                onChange={(checked) =>
                  form.setFieldValue('stopClinicEnabled', checked)
                }
              />
            </Form.Item>
            <Text type="secondary" style={{ fontSize: 14 }}>
              接收停诊、复诊等通知
            </Text>

            <Divider style={{ margin: '16px 0' }} />

            <Form.Item
              name="wechatEnabled"
              label="微信通知"
              valuePropName="checked"
            >
              <Switch
                checkedChildren="开启"
                unCheckedChildren="关闭"
                onChange={(checked) =>
                  form.setFieldValue('wechatEnabled', checked)
                }
              />
            </Form.Item>
            <Text type="secondary" style={{ fontSize: 14 }}>
              通过微信接收通知
            </Text>

            <Divider style={{ margin: '16px 0' }} />

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
            <Text type="secondary" style={{ fontSize: 14 }}>
              接收系统公告、维护通知等
            </Text>
          </Card>

          <Card
            title={
              <Space>
                <NotificationOutlined />
                <span>通知渠道</span>
              </Space>
            }
            style={{ marginBottom: 16 }}
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
            <Text type="secondary" style={{ fontSize: 14 }}>
              通过手机短信接收通知
            </Text>

            <Divider style={{ margin: '16px 0' }} />

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
            <Text type="secondary" style={{ fontSize: 14 }}>
              在医生工作台内接收通知
            </Text>
          </Card>

          <Card
            title={
              <Space>
                <MoonOutlined />
                <span>免打扰时段</span>
              </Space>
            }
            style={{ marginBottom: 16 }}
          >
            <div style={{ marginBottom: 16 }}>
              <Switch
                checked={quietHours.enabled}
                onChange={(checked) =>
                  setQuietHours({ ...quietHours, enabled: checked })
                }
                checkedChildren="已启用"
                unCheckedChildren="已关闭"
              />
              <Text type="secondary" style={{ marginLeft: 8, fontSize: 14 }}>
                启用后在设定时间段内不接收通知
              </Text>
            </div>

            {quietHours.enabled && (
              <Row gutter={16}>
                <Col span={12}>
                  <div style={{ marginBottom: 8 }}>
                    <Text strong>开始时间</Text>
                  </div>
                  <TimePicker
                    value={quietHours.startTime}
                    onChange={(time) =>
                      setQuietHours({ ...quietHours, startTime: time })
                    }
                    format="HH:mm"
                    style={{ width: '100%' }}
                    placeholder="选择开始时间"
                  />
                </Col>
                <Col span={12}>
                  <div style={{ marginBottom: 8 }}>
                    <Text strong>结束时间</Text>
                  </div>
                  <TimePicker
                    value={quietHours.endTime}
                    onChange={(time) =>
                      setQuietHours({ ...quietHours, endTime: time })
                    }
                    format="HH:mm"
                    style={{ width: '100%' }}
                    placeholder="选择结束时间"
                  />
                </Col>
              </Row>
            )}
          </Card>

          <div style={{ textAlign: 'right' }}>
            <Space>
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
            </Space>
          </div>
        </Form>
      </div>
    </PageContainer>
  );
};

export default NotificationSettingsPage;
