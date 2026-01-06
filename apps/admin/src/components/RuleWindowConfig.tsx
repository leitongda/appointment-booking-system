import { Card, Space, Button, Typography, Form, Select, InputNumber, Input, Row, Col, Tooltip } from 'antd';
import { PlusOutlined, DeleteOutlined, QuestionCircleOutlined } from '@ant-design/icons';
import {
  WINDOW_ACTION_OPTIONS,
  WINDOW_REFERENCE_POINT_OPTIONS,
  WINDOW_FAIL_POLICY_OPTIONS,
  WINDOW_DEFAULT_VALUES,
} from '@/constants/rule-set';

const { Text } = Typography;

/**
 * 将秒数转换为可读格式
 * @param seconds 秒数，null 表示不限制
 * @param referencePoint 参考点类型
 */
const formatOffset = (seconds: number | null, referencePoint?: string): string => {
  if (seconds === null) return '不限制';

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
 * 获取时间窗描述
 */
const getWindowDescription = (action: string, referencePoint: string): string => {
  const actionLabels: Record<string, string> = {
    BOOK: '预约',
    CHECKIN: '签到',
    CANCEL: '取消',
    HOLD_RELEASE: '释放',
  };
  const refLabels: Record<string, string> = {
    SHIFT_START: '班次开始时间',
    SHIFT_END: '班次结束时间',
    BOOKING_CREATED_AT: '预约创建时间',
  };
  return `${actionLabels[action] || action} - 基于${refLabels[referencePoint] || referencePoint}`;
};

/**
 * 单个时间窗配置项组件
 */
interface WindowFormItemProps {
  field: any;
  remove: (name: number) => void;
}

const WindowFormItem: React.FC<WindowFormItemProps> = ({ field, remove }) => {
  const action = Form.useWatch(['windows', field.name, 'action']);
  const referencePoint = Form.useWatch(['windows', field.name, 'referencePoint']);
  const openOffsetSec = Form.useWatch(['windows', field.name, 'openOffsetSec']);
  const closeOffsetSec = Form.useWatch(['windows', field.name, 'closeOffsetSec']);
  const failPolicy = Form.useWatch(['windows', field.name, 'failPolicy']);

  // 自动生成描述
  const autoDescription = action && referencePoint ? getWindowDescription(action, referencePoint) : '';

  return (
    <Card
      key={field.key}
      type="inner"
      title={`时间窗 ${field.name + 1}`}
      extra={
        <Button
          type="text"
          danger
          size="small"
          icon={<DeleteOutlined />}
          onClick={() => remove(field.name)}
          title="删除此时间窗"
        />
      }
    >
      <Space direction="vertical" style={{ width: '100%' }} size="middle">
        {/* 动作类型与参考点 */}
        <Row gutter={16}>
          <Col span={12}>
            <Form.Item
              name={[field.name, 'action']}
              label={
                <Space>
                  动作类型
                  <Tooltip title="选择要限制的操作类型：预约-创建新预约，签到-签到操作，取消-取消预约，释放-释放占位号">
                    <QuestionCircleOutlined style={{ color: '#1890ff' }} />
                  </Tooltip>
                </Space>
              }
              rules={[{ required: true, message: '请选择动作类型' }]}
            >
              <Select options={WINDOW_ACTION_OPTIONS} placeholder="请选择动作类型" />
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item
              name={[field.name, 'referencePoint']}
              label={
                <Space>
                  参考点
                  <Tooltip title="时间窗口的计算基准：班次开始/结束时间基于班次时间表，预约创建时间基于用户操作时间">
                    <QuestionCircleOutlined style={{ color: '#1890ff' }} />
                  </Tooltip>
                </Space>
              }
              rules={[{ required: true, message: '请选择参考点' }]}
            >
              <Select options={WINDOW_REFERENCE_POINT_OPTIONS} placeholder="请选择参考点" />
            </Form.Item>
          </Col>
        </Row>

        {/* 开放与截止偏移 */}
        <Row gutter={16}>
          <Col span={12}>
            <Form.Item
              name={[field.name, 'openOffsetSec']}
              label="开放偏移(秒)"
              extra="留空表示不限制最早时间"
            >
              <InputNumber
                min={-31536000}
                max={31536000}
                precision={0}
                style={{ width: '100%' }}
                placeholder="留空=不限制"
              />
            </Form.Item>
            <Text type="secondary" style={{ fontSize: 12 }}>
              {formatOffset(openOffsetSec ?? null)}
            </Text>
          </Col>
          <Col span={12}>
            <Form.Item
              name={[field.name, 'closeOffsetSec']}
              label="截止偏移(秒)"
              extra="留空表示不限制最晚时间"
            >
              <InputNumber
                min={-31536000}
                max={31536000}
                precision={0}
                style={{ width: '100%' }}
                placeholder="留空=不限制"
              />
            </Form.Item>
            <Text type="secondary" style={{ fontSize: 12 }}>
              {formatOffset(closeOffsetSec ?? null)}
            </Text>
          </Col>
        </Row>

        {/* 边界与失败策略 */}
        <Row gutter={16}>
          <Col span={8}>
            <Form.Item
              name={[field.name, 'openInclusive']}
              label={
                <Space>
                  包含开放边界
                  <Tooltip title="是否包含开放时刻：包含表示到达开放时刻即可操作，不包含表示必须过开放时刻才能操作">
                    <QuestionCircleOutlined style={{ color: '#1890ff' }} />
                  </Tooltip>
                </Space>
              }
              initialValue={true}
            >
              <Select
                options={[
                  { label: '是', value: true },
                  { label: '否', value: false },
                ]}
              />
            </Form.Item>
          </Col>
          <Col span={8}>
            <Form.Item
              name={[field.name, 'closeInclusive']}
              label={
                <Space>
                  包含截止边界
                  <Tooltip title="是否包含截止时刻：包含表示截止时刻仍可操作，不包含表示必须在截止时刻前完成操作">
                    <QuestionCircleOutlined style={{ color: '#1890ff' }} />
                  </Tooltip>
                </Space>
              }
              initialValue={false}
            >
              <Select
                options={[
                  { label: '是', value: true },
                  { label: '否', value: false },
                ]}
              />
            </Form.Item>
          </Col>
          <Col span={8}>
            <Form.Item
              name={[field.name, 'failPolicy']}
              label={
                <Space>
                  失败策略
                  <Tooltip title="操作不在时间窗内的处理方式：拒绝-禁止操作并提示错误，允许并打标签-允许操作但标记特殊状态，自动候补-添加到候补队列">
                    <QuestionCircleOutlined style={{ color: '#1890ff' }} />
                  </Tooltip>
                </Space>
              }
              rules={[{ required: true, message: '请选择失败策略' }]}
              initialValue="REJECT"
            >
              <Select options={WINDOW_FAIL_POLICY_OPTIONS} placeholder="请选择失败策略" />
            </Form.Item>
          </Col>
        </Row>

        {/* 条件渲染：失败标签 */}
        {failPolicy === 'ALLOW_WITH_TAG' && (
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name={[field.name, 'failTag']}
                label="失败标签"
                rules={[{ required: true, message: '请输入失败标签' }]}
                extra="用于标记和统计特殊预约，如'迟到预约'、'超额预约'等，方便后续数据分析"
              >
                <Input placeholder="如：迟到预约" />
              </Form.Item>
            </Col>
          </Row>
        )}

        {/* 描述 */}
        <Row gutter={16}>
          <Col span={24}>
            <Form.Item
              name={[field.name, 'description']}
              label="描述"
              initialValue={autoDescription}
            >
              <Input placeholder="可选，描述该时间窗的用途" />
            </Form.Item>
          </Col>
        </Row>

        {/* 启用状态 - 隐藏字段 */}
        <Form.Item
          name={[field.name, 'enabled']}
          initialValue={true}
          noStyle
        >
          <input type="hidden" />
        </Form.Item>
      </Space>
    </Card>
  );
};

/**
 * 时间窗配置组件 - 使用 Form.List 集成到主表单
 */
const RuleWindowConfig: React.FC = () => {
  return (
    <Card title="时间窗配置" style={{ marginBottom: 16 }}>
      <Form.List name="windows">
        {(fields, { add, remove }) => (
          <>
            {fields.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '32px 0' }}>
                <Text type="secondary" style={{ fontSize: 14 }}>暂无时间窗配置，点击下方按钮添加</Text>
              </div>
            ) : (
              <Space direction="vertical" style={{ width: '100%' }} size="large">
                {fields.map((field) => (
                  <WindowFormItem key={field.key} field={field} remove={remove} />
                ))}
              </Space>
            )}

            <Button
              type="dashed"
              onClick={() => add(WINDOW_DEFAULT_VALUES)}
              block
              icon={<PlusOutlined />}
              style={{ marginTop: 16, height: 40 }}
              size="large"
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
