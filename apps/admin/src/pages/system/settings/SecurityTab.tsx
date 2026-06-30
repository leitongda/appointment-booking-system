import { ProForm, ProFormText, ProFormDigit } from '@ant-design/pro-components';
import { Typography, Card, Row, Col } from 'antd';
import type { SecurityTabProps } from './types';
import { DEFAULT_SECURITY_CONFIG } from './defaults';

const { Text } = Typography;

const SecurityTab: React.FC<SecurityTabProps> = ({
  securityConfig,
  onSubmit,
  canEdit,
  loading,
}) => (
  <ProForm
    key={loading ? 'security-loading' : 'security-loaded'}
    onFinish={onSubmit}
    initialValues={{ ...DEFAULT_SECURITY_CONFIG, ...securityConfig }}
    submitter={{ searchConfig: { submitText: '保存设置' }, resetButtonProps: { style: { display: 'none' } } }}
    disabled={!canEdit}
  >
    <Text type="secondary" style={{ display: 'block', marginBottom: 16 }}>
      配置认证令牌、限流、登录锁定等安全相关参数。修改后立即生效（限流参数需重启服务）。
    </Text>
    <Card title="令牌配置" size="small" style={{ marginBottom: 16 }}>
      <Row gutter={24}>
        <Col span={8}>
          <ProFormDigit
            name="accessTokenExpireMinutes"
            label="AccessToken 有效期"
            min={5}
            max={1440}
            fieldProps={{ precision: 0, addonAfter: '分钟' }}
            rules={[{ required: true, message: '请输入有效期' }]}
          />
        </Col>
        <Col span={8}>
          <ProFormDigit
            name="refreshTokenExpireDays"
            label="RefreshToken 有效期"
            min={1}
            max={90}
            fieldProps={{ precision: 0, addonAfter: '天' }}
            rules={[{ required: true, message: '请输入有效期' }]}
          />
        </Col>
        <Col span={8}>
          <ProFormText
            name="defaultPassword"
            label="新建管理员默认密码"
            placeholder="请输入默认密码"
            fieldProps={{ type: 'password' }}
          />
        </Col>
      </Row>
    </Card>
    <Card title="限流配置" size="small" style={{ marginBottom: 16 }}>
      <Row gutter={24}>
        <Col span={8}>
          <ProFormDigit
            name="rateLimitPerMinute"
            label="每分钟请求上限"
            min={10}
            max={10000}
            fieldProps={{ precision: 0 }}
            extra="修改后需重启服务生效"
            rules={[{ required: true, message: '请输入限流值' }]}
          />
        </Col>
        <Col span={8}>
          <ProFormDigit
            name="rateLimitPerSecond"
            label="每秒请求上限"
            min={1}
            max={1000}
            fieldProps={{ precision: 0 }}
            extra="修改后需重启服务生效"
            rules={[{ required: true, message: '请输入限流值' }]}
          />
        </Col>
      </Row>
    </Card>
    <Card title="登录安全" size="small">
      <Row gutter={24}>
        <Col span={8}>
          <ProFormDigit
            name="loginFailureLockCount"
            label="登录失败锁定次数"
            min={0}
            max={20}
            fieldProps={{ precision: 0 }}
            extra="0 表示不锁定"
          />
        </Col>
        <Col span={8}>
          <ProFormDigit
            name="sessionTimeoutMinutes"
            label="会话超时时间"
            min={5}
            max={1440}
            fieldProps={{ precision: 0, addonAfter: '分钟' }}
          />
        </Col>
      </Row>
    </Card>
  </ProForm>
);

export default SecurityTab;
