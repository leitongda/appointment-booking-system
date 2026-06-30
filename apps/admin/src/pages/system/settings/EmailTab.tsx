import { ProForm, ProFormText, ProFormDigit, ProFormSwitch } from '@ant-design/pro-components';
import { Typography } from 'antd';
import type { EmailTabProps } from './types';
import { DEFAULT_EMAIL_CONFIG } from './defaults';

const { Text } = Typography;

const EmailTab: React.FC<EmailTabProps> = ({
  emailConfig,
  onSubmit,
  canEdit,
  loading,
}) => (
  <ProForm
    key={loading ? 'email-loading' : 'email-loaded'}
    onFinish={onSubmit}
    initialValues={{ ...DEFAULT_EMAIL_CONFIG, ...emailConfig }}
    submitter={{ searchConfig: { submitText: '保存设置' }, resetButtonProps: { style: { display: 'none' } } }}
    disabled={!canEdit}
  >
    <Text type="secondary" style={{ display: 'block', marginBottom: 16 }}>
      配置SMTP服务器信息，用于发送邮件通知（如预约确认、就诊提醒等）。常见邮箱SMTP设置：QQ邮箱(smtp.qq.com:465)、163邮箱(smtp.163.com:465)、Gmail(smtp.gmail.com:587)
    </Text>
    <ProFormText
      name="smtpHost"
      label="SMTP服务器"
      placeholder="如：smtp.qq.com"
      rules={[{ required: true, message: '请输入SMTP服务器地址' }]}
    />
    <ProFormDigit
      name="smtpPort"
      label="SMTP端口"
      placeholder="如：465 或 587"
      min={1}
      max={65535}
      fieldProps={{ precision: 0 }}
      rules={[{ required: true, message: '请输入SMTP端口' }]}
    />
    <ProFormText
      name="smtpUser"
      label="SMTP用户名"
      placeholder="通常为邮箱地址"
      rules={[{ required: true, message: '请输入SMTP用户名' }]}
    />
    <ProFormText.Password
      name="smtpPassword"
      label="SMTP密码"
      placeholder="邮箱密码或授权码"
      rules={[{ required: true, message: '请输入SMTP密码' }]}
      extra="部分邮箱需要使用授权码而非登录密码"
      fieldProps={{ autoComplete: 'new-password' }}
    />
    <ProFormSwitch
      name="smtpSsl"
      label="使用SSL"
      extra="大多数邮箱服务器需要启用SSL"
    />
    <ProFormText
      name="senderName"
      label="发件人名称"
      placeholder="如：XX医院"
      rules={[{ required: true, message: '请输入发件人名称' }]}
    />
    <ProFormText
      name="senderEmail"
      label="发件人邮箱"
      placeholder="如：noreply@hospital.com"
      rules={[
        { required: true, message: '请输入发件人邮箱' },
        { type: 'email', message: '请输入正确的邮箱格式' },
      ]}
    />
  </ProForm>
);

export default EmailTab;
