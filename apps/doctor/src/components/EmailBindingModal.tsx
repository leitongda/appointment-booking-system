import { Modal, Form, Input, Button, Typography, Space } from 'antd';
import { MailOutlined } from '@ant-design/icons';
import { useEffect } from 'react';
import type { UseEmailBindingResult } from '@hospital/api';

interface EmailBindingModalProps {
  binding: UseEmailBindingResult;
  /** 当前已绑定邮箱（用于解绑/换绑场景展示） */
  currentEmail?: string | null;
}

/**
 * 把完整邮箱遮罩成 `a***b@example.com` 形式。
 * 短邮箱（用户名 < 2 位）退化为 `*@example.com`。
 */
function maskEmail(email?: string | null): string {
  if (!email) return '';
  const at = email.indexOf('@');
  if (at <= 0) return email;
  const user = email.slice(0, at);
  const domain = email.slice(at);
  if (user.length <= 1) return `*${domain}`;
  if (user.length === 2) return `${user[0]}*${domain}`;
  const middleStars = '*'.repeat(Math.min(user.length - 2, 4));
  return `${user[0]}${middleStars}${user[user.length - 1]}${domain}`;
}

const EmailBindingModal: React.FC<EmailBindingModalProps> = ({ binding, currentEmail }) => {
  const [emailForm] = Form.useForm();
  const {
    mode,
    open,
    submitting,
    newCodeCountdown,
    oldCodeCountdown,
    newCodeSending,
    oldCodeSending,
    closeModal,
    sendNewCode,
    sendOldCode,
    submitBind,
    submitUnbind,
    submitChange,
  } = binding;

  useEffect(() => {
    if (!open) {
      emailForm.resetFields();
    }
  }, [open, emailForm]);

  const title = mode === 'bind' ? '绑定邮箱' : mode === 'unbind' ? '解绑邮箱' : '更换邮箱';

  const handleSendNewCode = async () => {
    const email = emailForm.getFieldValue('email');
    await sendNewCode(email || '');
  };

  const handleEmailBlur = () => {
    const value = emailForm.getFieldValue('email');
    if (typeof value === 'string') {
      emailForm.setFieldsValue({ email: value.trim().toLowerCase() });
    }
  };

  const handleSubmit = async () => {
    let values: any;
    try {
      values = await emailForm.validateFields();
    } catch {
      return;
    }
    if (mode === 'bind') {
      await submitBind({ email: values.email, code: values.code });
    } else if (mode === 'unbind') {
      await submitUnbind({ code: values.code });
    } else {
      await submitChange({
        newEmail: values.email,
        newEmailCode: values.code,
        oldEmailCode: values.oldCode,
      });
    }
  };

  const newCountdownLabel =
    newCodeCountdown > 0 ? `重新发送(${newCodeCountdown}s)` : '获取验证码';
  const oldCountdownLabel =
    oldCodeCountdown > 0 ? `重新发送(${oldCodeCountdown}s)` : '获取验证码';

  return (
    <Modal
      title={title}
      open={open}
      onCancel={closeModal}
      footer={null}
      destroyOnClose
      width={480}
    >
      <Form form={emailForm} layout="vertical" onFinish={handleSubmit}>
        {mode === 'bind' && (
          <>
            <Form.Item
              name="email"
              label="邮箱地址"
              rules={[
                { required: true, message: '请输入邮箱' },
                { type: 'email', message: '邮箱格式不正确' },
              ]}
            >
              <Input
                placeholder="请输入邮箱地址"
                prefix={<MailOutlined />}
                autoComplete="email"
                inputMode="email"
                onBlur={handleEmailBlur}
              />
            </Form.Item>
            <Form.Item
              name="code"
              label="验证码"
              rules={[{ required: true, message: '请输入验证码' }]}
            >
              <Input
                placeholder="请输入验证码"
                maxLength={6}
                autoComplete="one-time-code"
                inputMode="numeric"
                suffix={
                  <Button
                    type="link"
                    size="small"
                    disabled={newCodeCountdown > 0}
                    loading={newCodeSending}
                    onClick={handleSendNewCode}
                    style={{ padding: 0 }}
                    aria-label={
                      newCodeCountdown > 0
                        ? `${newCodeCountdown}秒后可重新发送验证码`
                        : '获取验证码'
                    }
                  >
                    {newCountdownLabel}
                  </Button>
                }
              />
            </Form.Item>
          </>
        )}

        {mode === 'unbind' && (
          <>
            <Typography.Paragraph type="secondary">
              验证码将发送到当前绑定的邮箱：
              <Typography.Text strong>{maskEmail(currentEmail)}</Typography.Text>
            </Typography.Paragraph>
            <Form.Item
              name="code"
              label="验证码"
              rules={[{ required: true, message: '请输入验证码' }]}
            >
              <Input
                placeholder="请输入验证码"
                maxLength={6}
                autoComplete="one-time-code"
                inputMode="numeric"
                suffix={
                  <Button
                    type="link"
                    size="small"
                    disabled={oldCodeCountdown > 0}
                    loading={oldCodeSending}
                    onClick={() => sendOldCode()}
                    style={{ padding: 0 }}
                    aria-label={
                      oldCodeCountdown > 0
                        ? `${oldCodeCountdown}秒后可重新发送验证码`
                        : '获取验证码'
                    }
                  >
                    {oldCountdownLabel}
                  </Button>
                }
              />
            </Form.Item>
          </>
        )}

        {mode === 'change' && (
          <>
            <Form.Item
              name="email"
              label="新邮箱地址"
              rules={[
                { required: true, message: '请输入新邮箱' },
                { type: 'email', message: '邮箱格式不正确' },
              ]}
            >
              <Input
                placeholder="请输入新邮箱地址"
                prefix={<MailOutlined />}
                autoComplete="email"
                inputMode="email"
                onBlur={handleEmailBlur}
              />
            </Form.Item>
            <Form.Item
              name="code"
              label="新邮箱验证码"
              rules={[{ required: true, message: '请输入新邮箱验证码' }]}
            >
              <Input
                placeholder="请输入新邮箱验证码"
                maxLength={6}
                autoComplete="one-time-code"
                inputMode="numeric"
                suffix={
                  <Button
                    type="link"
                    size="small"
                    disabled={newCodeCountdown > 0}
                    loading={newCodeSending}
                    onClick={handleSendNewCode}
                    style={{ padding: 0 }}
                    aria-label={
                      newCodeCountdown > 0
                        ? `${newCodeCountdown}秒后可重新发送`
                        : '获取新邮箱验证码'
                    }
                  >
                    {newCountdownLabel}
                  </Button>
                }
              />
            </Form.Item>
            <Form.Item
              name="oldCode"
              label={`旧邮箱验证码（${maskEmail(currentEmail) || '当前邮箱'}）`}
              rules={[{ required: true, message: '请输入旧邮箱验证码' }]}
            >
              <Input
                placeholder="请输入旧邮箱验证码"
                maxLength={6}
                autoComplete="one-time-code"
                inputMode="numeric"
                suffix={
                  <Button
                    type="link"
                    size="small"
                    disabled={oldCodeCountdown > 0}
                    loading={oldCodeSending}
                    onClick={() => sendOldCode()}
                    style={{ padding: 0 }}
                    aria-label={
                      oldCodeCountdown > 0
                        ? `${oldCodeCountdown}秒后可重新发送`
                        : '获取旧邮箱验证码'
                    }
                  >
                    {oldCountdownLabel}
                  </Button>
                }
              />
            </Form.Item>
          </>
        )}

        <Form.Item style={{ marginBottom: 0, textAlign: 'right' }}>
          <Space>
            <Button onClick={closeModal}>取消</Button>
            <Button type="primary" htmlType="submit" loading={submitting}>
              确认
            </Button>
          </Space>
        </Form.Item>
      </Form>
    </Modal>
  );
};

export default EmailBindingModal;
export { maskEmail };
