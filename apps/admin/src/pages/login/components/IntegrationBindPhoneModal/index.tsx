import { useState } from 'react';
import { Modal, App, Form, Input, Button } from 'antd';
import { adminApi, type IntegrationLoginProvider } from '@hospital/api';

export interface BindPhoneInfo {
  provider: IntegrationLoginProvider;
  externalId?: string;
  unionId?: string;
  name?: string;
}

interface IntegrationBindPhoneModalProps {
  open: boolean;
  info: BindPhoneInfo | null;
  label: string;
  onSuccess: (result: any) => void;
  onCancel: () => void;
}

/**
 * 第三方登录绑定手机号弹窗。
 *
 * 用于扫码登录后未绑定本地 Admin 的场景：
 * 用户输入手机号 → 后端按手机号匹配当前租户的 Admin 并建立绑定 → 签发登录态。
 * （管理员账号由系统预先创建，此处仅做关联，不需要短信验证码。）
 */
const IntegrationBindPhoneModal: React.FC<IntegrationBindPhoneModalProps> = ({
  open,
  info,
  label,
  onSuccess,
  onCancel,
}) => {
  const { message } = App.useApp();
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);

  const handleOk = async () => {
    if (!info) return;
    try {
      const values = await form.validateFields();
      setLoading(true);
      const result = await adminApi.integrationBindPhone({
        provider: info.provider,
        externalId: info.externalId || '',
        unionId: info.unionId,
        name: info.name,
        phone: values.phone,
      });
      message.success(`${label}账号绑定成功`);
      onSuccess(result);
      form.resetFields();
    } catch (error: any) {
      if (typeof error?.code !== 'number') {
        message.error(error?.message || '绑定失败');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal
      title={`绑定手机号以完成${label}登录`}
      open={open}
      onCancel={() => {
        form.resetFields();
        onCancel();
      }}
      footer={[
        <Button
          key="cancel"
          onClick={() => {
            form.resetFields();
            onCancel();
          }}
        >
          取消
        </Button>,
        <Button key="ok" type="primary" loading={loading} onClick={handleOk}>
          确认绑定
        </Button>,
      ]}
    >
      <p style={{ color: 'var(--color-text-secondary)', marginBottom: 16 }}>
        检测到您的{label}账号尚未绑定本系统管理员，请输入您在系统中登记的手机号以完成关联。
      </p>
      <Form form={form} layout="vertical">
        <Form.Item
          label="手机号"
          name="phone"
          rules={[
            { required: true, message: '请输入手机号' },
            { pattern: /^1\d{10}$/, message: '请输入正确的手机号' },
          ]}
        >
          <Input placeholder="请输入管理员手机号" maxLength={11} />
        </Form.Item>
      </Form>
    </Modal>
  );
};

export default IntegrationBindPhoneModal;
