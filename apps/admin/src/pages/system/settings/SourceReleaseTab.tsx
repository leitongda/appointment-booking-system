import { ProForm, ProFormText, ProFormDigit, ProFormSwitch } from '@ant-design/pro-components';
import { Typography, Card, Row, Col } from 'antd';
import type { SourceReleaseTabProps } from './types';
import { DEFAULT_SOURCE_RELEASE_CONFIG } from './defaults';

const { Text } = Typography;

const SourceReleaseTab: React.FC<SourceReleaseTabProps> = ({
  sourceReleaseConfig,
  onSubmit,
  canEdit,
  loading,
}) => (
  <ProForm
    key={loading ? 'source-release-loading' : 'source-release-loaded'}
    onFinish={onSubmit}
    initialValues={{ ...DEFAULT_SOURCE_RELEASE_CONFIG, ...sourceReleaseConfig }}
    submitter={{ searchConfig: { submitText: '保存设置' }, resetButtonProps: { style: { display: 'none' } } }}
    disabled={!canEdit}
  >
    <Text type="secondary" style={{ display: 'block', marginBottom: 16 }}>
      配置号源锁定、自动释放、超额预约等策略参数。修改后立即生效。
    </Text>
    <Card title="号源锁定" size="small" style={{ marginBottom: 16 }}>
      <Row gutter={24}>
        <Col span={8}>
          <ProFormDigit
            name="lockTimeoutMinutes"
            label="锁定超时时间"
            min={1}
            max={60}
            fieldProps={{ precision: 0, addonAfter: '分钟' }}
            extra="患者选号后未完成支付，超时自动释放"
            rules={[{ required: true, message: '请输入超时时间' }]}
          />
        </Col>
        <Col span={8}>
          <ProFormDigit
            name="autoCancelUnpaidMinutes"
            label="未支付自动取消"
            min={5}
            max={1440}
            fieldProps={{ precision: 0, addonAfter: '分钟' }}
            extra="预约成功但未支付，超时自动取消"
          />
        </Col>
        <Col span={8}>
          <ProFormDigit
            name="noShowAutoMarkHours"
            label="爽约自动标记"
            min={1}
            max={168}
            fieldProps={{ precision: 0, addonAfter: '小时' }}
            extra="就诊时间后超过此时间自动标记为爽约"
          />
        </Col>
      </Row>
    </Card>
    <Card title="批量释放" size="small" style={{ marginBottom: 16 }}>
      <Row gutter={24}>
        <Col span={8}>
          <ProFormSwitch name="batchReleaseEnabled" label="启用批量释放" />
        </Col>
        <Col span={8}>
          <ProFormDigit
            name="batchReleaseDays"
            label="释放提前天数"
            min={1}
            max={30}
            fieldProps={{ precision: 0, addonAfter: '天' }}
            extra="提前多少天的号源自动释放"
          />
        </Col>
        <Col span={8}>
          <ProFormText
            name="batchReleaseTime"
            label="释放时间点"
            placeholder="08:00"
            extra="每天几点执行批量释放，格式 HH:mm"
          />
        </Col>
      </Row>
    </Card>
    <Card title="超额预约" size="small">
      <Row gutter={24}>
        <Col span={8}>
          <ProFormSwitch name="allowOverbooking" label="允许超额预约" />
        </Col>
        <Col span={8}>
          <ProFormDigit
            name="overbookingLimit"
            label="超额预约上限"
            min={0}
            max={50}
            fieldProps={{ precision: 0 }}
            extra="0 表示不允许超额"
          />
        </Col>
      </Row>
    </Card>
  </ProForm>
);

export default SourceReleaseTab;
