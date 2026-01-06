import { ProFormDependency } from '@ant-design/pro-components';
import { Card, Space, Button, Tag, Typography, Form, Select, InputNumber, Input } from 'antd';
import { PlusOutlined, DeleteOutlined } from '@ant-design/icons';
import {
  WINDOW_ACTION_OPTIONS,
  WINDOW_REFERENCE_POINT_OPTIONS,
  WINDOW_FAIL_POLICY_OPTIONS,
  WINDOW_DEFAULT_VALUES,
} from '@/constants/rule-set';

const { Text } = Typography;

/**
 * 将秒数转换为可读格式
 */
const formatOffset = (seconds: number): string => {
  const abs = Math.abs(seconds);
  const hours = Math.floor(abs / 3600);
  const minutes = Math.floor((abs % 3600) / 60);
  const secs = abs % 60;

  const parts: string[] = [];
  if (hours > 0) parts.push(`${hours}小时`);
  if (minutes > 0) parts.push(`${minutes}分钟`);
  if (secs > 0) parts.push(`${secs}秒`);

  const str = parts.join('');
  return seconds >= 0 ? `延后${str}` : `提前${str}`;
};

/**
 * 时间窗配置组件 - 使用 Form.List 集成到主表单
 */
const RuleWindowConfig: React.FC = () => {
  return (
    <Card title="时间窗配置" style={{ marginBottom: 16 }}>
      <Form.List name="windows" initialValue={[]}>
        {(fields, { add, remove }) => (
          <>
            {fields.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '20px 0' }}>
                <Tag>暂无时间窗配置，点击下方按钮添加</Tag>
              </div>
            ) : (
              <Space direction="vertical" style={{ width: '100%' }} size="middle">
                {fields.map((field) => (
                  <Card
                    key={field.key}
                    size="small"
                    type="inner"
                    title={
                      <Form.Item noStyle shouldUpdate>
                        {() => {
                          const actionType = Form.useWatch([field.name, 'action']);
                          const enabled = Form.useWatch([field.name, 'enabled']);
                          const actionLabel = WINDOW_ACTION_OPTIONS.find(o => o.value === actionType)?.label || '未配置';
                          return (
                            <Space>
                              <span>{actionLabel}</span>
                              {enabled ? <Tag color="green">启用</Tag> : <Tag>禁用</Tag>}
                            </Space>
                          );
                        }}
                      </Form.Item>
                    }
                    extra={
                      <Button
                        type="text"
                        danger
                        size="small"
                        icon={<DeleteOutlined />}
                        onClick={() => remove(field.name)}
                      />
                    }
                  >
                    <Space direction="vertical" style={{ width: '100%' }} size="small">
                      <Space.Compact style={{ width: '100%' }}>
                        <Form.Item
                          name={[field.name, 'action']}
                          label="动作类型"
                          rules={[{ required: true, message: '请选择动作类型' }]}
                          style={{ flex: 1 }}
                        >
                          <Select options={WINDOW_ACTION_OPTIONS} placeholder="请选择动作类型" />
                        </Form.Item>
                        <Form.Item
                          name={[field.name, 'referencePoint']}
                          label="参考点"
                          rules={[{ required: true, message: '请选择参考点' }]}
                          style={{ flex: 1 }}
                        >
                          <Select options={WINDOW_REFERENCE_POINT_OPTIONS} placeholder="请选择参考点" />
                        </Form.Item>
                      </Space.Compact>

                      <Space.Compact style={{ width: '100%' }}>
                        <Form.Item
                          name={[field.name, 'openOffsetSec']}
                          label="开放偏移(秒)"
                          rules={[{ required: true, message: '请输入开放偏移' }]}
                          style={{ flex: 1 }}
                          initialValue={-86400}
                        >
                          <InputNumber
                            min={-31536000}
                            max={31536000}
                            precision={0}
                            style={{ width: '100%' }}
                            placeholder="请输入开放偏移"
                          />
                        </Form.Item>
                        <Form.Item
                          name={[field.name, 'closeOffsetSec']}
                          label="截止偏移(秒)"
                          rules={[{ required: true, message: '请输入截止偏移' }]}
                          style={{ flex: 1 }}
                          initialValue={0}
                        >
                          <InputNumber
                            min={-31536000}
                            max={31536000}
                            precision={0}
                            style={{ width: '100%' }}
                            placeholder="请输入截止偏移"
                          />
                        </Form.Item>
                      </Space.Compact>

                      <Space.Compact style={{ width: '100%' }}>
                        <Form.Item
                          name={[field.name, 'openInclusive']}
                          label="包含开放边界"
                          initialValue={true}
                          style={{ flex: 1 }}
                        >
                          <Select
                            options={[
                              { label: '是', value: true },
                              { label: '否', value: false },
                            ]}
                          />
                        </Form.Item>
                        <Form.Item
                          name={[field.name, 'closeInclusive']}
                          label="包含截止边界"
                          initialValue={false}
                          style={{ flex: 1 }}
                        >
                          <Select
                            options={[
                              { label: '是', value: true },
                              { label: '否', value: false },
                            ]}
                          />
                        </Form.Item>
                        <Form.Item
                          name={[field.name, 'failPolicy']}
                          label="失败策略"
                          rules={[{ required: true, message: '请选择失败策略' }]}
                          style={{ flex: 1 }}
                          initialValue="REJECT"
                        >
                          <Select options={WINDOW_FAIL_POLICY_OPTIONS} placeholder="请选择失败策略" />
                        </Form.Item>
                      </Space.Compact>

                      <Form.Item noStyle shouldUpdate>
                        {() => {
                          const failPolicy = Form.useWatch([field.name, 'failPolicy']);
                          if (failPolicy === 'ALLOW_WITH_TAG') {
                            return (
                              <Form.Item
                                name={[field.name, 'failTag']}
                                label="失败标签"
                                rules={[{ required: true, message: '请输入失败标签' }]}
                              >
                                <Input placeholder="如：迟到预约" />
                              </Form.Item>
                            );
                          }
                          return null;
                        }}
                      </Form.Item>

                      <Form.Item
                        name={[field.name, 'description']}
                        label="描述"
                      >
                        <Input placeholder="可选，描述该时间窗的用途" />
                      </Form.Item>

                      <Form.Item
                        name={[field.name, 'enabled']}
                        initialValue={true}
                        noStyle
                      >
                        <input type="hidden" />
                      </Form.Item>
                    </Space>
                  </Card>
                ))}
              </Space>
            )}

            <Button
              type="dashed"
              onClick={() => add(WINDOW_DEFAULT_VALUES)}
              block
              icon={<PlusOutlined />}
              style={{ marginTop: 16 }}
            >
              添加时间窗
            </Button>
          </>
        )}
      </Form.List>
    </Card>
  );
};

export default RuleWindowConfig;
