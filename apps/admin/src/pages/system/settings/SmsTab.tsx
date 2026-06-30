import { ProForm, ProFormDigit } from '@ant-design/pro-components';
import { Typography } from 'antd';
import type { SmsTabProps } from './types';
import { DEFAULT_SMS_POLICY } from './defaults';

const { Text } = Typography;

const SmsTab: React.FC<SmsTabProps> = ({
  smsConfig,
  onSubmit,
  canEdit,
  loading,
}) => (
  <ProForm
    key={loading ? 'sms-loading' : 'sms-loaded'}
    onFinish={onSubmit}
    initialValues={{ ...DEFAULT_SMS_POLICY, ...smsConfig }}
    submitter={{ searchConfig: { submitText: '保存设置' }, resetButtonProps: { style: { display: 'none' } } }}
    disabled={!canEdit}
  >
    <Text type="secondary" style={{ display: 'block', marginBottom: 16 }}>
      配置短信验证码和发送频率的相关参数。修改后立即生效。
    </Text>
    <ProFormDigit
      name="codeExpireSeconds"
      label="验证码有效期"
      min={60}
      max={600}
      fieldProps={{ precision: 0, addonAfter: '秒' }}
      extra="用户收到的短信验证码的有效时长，范围 60-600 秒"
      rules={[{ required: true, message: '请输入验证码有效期' }]}
    />
    <ProFormDigit
      name="sendIntervalSeconds"
      label="短信发送间隔"
      min={30}
      max={300}
      fieldProps={{ precision: 0, addonAfter: '秒' }}
      extra="同一手机号两次发送短信的最短间隔，范围 30-300 秒"
      rules={[{ required: true, message: '请输入短信发送间隔' }]}
    />
  </ProForm>
);

export default SmsTab;
