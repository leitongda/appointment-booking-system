import { Card, Space, Button, Typography, Form, Select, InputNumber, Input, Row, Col, Tooltip, Tabs, Empty, Popconfirm, Grid, Divider, Alert, theme } from 'antd';
import { PlusOutlined, DeleteOutlined, QuestionCircleOutlined, EyeOutlined } from '@ant-design/icons';
import { useState, useEffect } from 'react';
import dayjs from 'dayjs';

const { useBreakpoint } = Grid;
const { useToken } = theme;
import {
  WINDOW_ACTION_OPTIONS,
  WINDOW_REFERENCE_POINT_OPTIONS,
  WINDOW_FAIL_POLICY_OPTIONS,
  WINDOW_DEFAULT_VALUES,
} from '@/constants/rule-set';
import { RuleSetTimeline } from '@/components/rule-set-visualization';
import { formatOffset as formatOffsetUtil } from '@/utils/ruleSetFormatter';

const { Text } = Typography;

// ==================== 类型定义 ====================

type TimeUnit = 'second' | 'minute' | 'hour' | 'day' | 'week';

interface TimeUnitOption {
  label: string;
  value: TimeUnit;
  seconds: number;
}

// ==================== 常量定义 ====================

const TIME_UNIT_OPTIONS: TimeUnitOption[] = [
  { label: '秒', value: 'second', seconds: 1 },
  { label: '分钟', value: 'minute', seconds: 60 },
  { label: '小时', value: 'hour', seconds: 3600 },
  { label: '天', value: 'day', seconds: 86400 },
  { label: '周', value: 'week', seconds: 604800 },
];

const ACTION_LABELS: Record<string, string> = {
  BOOK: '预约',
  CHECKIN: '签到',
  CANCEL: '取消',
  HOLD_RELEASE: '释放',
};

// ==================== 工具函数 ====================

/**
 * 将秒数转换为可读格式
 */
const formatOffset = (seconds: number | null): string => {
  return formatOffsetUtil(seconds);
};

/**
 * 将秒数转换为单位值
 */
const secondsToUnit = (seconds: number | null, unit: TimeUnit): number | null => {
  if (seconds === null) return null;
  const unitOption = TIME_UNIT_OPTIONS.find(opt => opt.value === unit);
  if (!unitOption) return seconds;
  return Math.round(seconds / unitOption.seconds);
};

/**
 * 将单位值转换为秒数
 */
const unitToSeconds = (value: number | null, unit: TimeUnit): number | null => {
  if (value === null) return null;
  const unitOption = TIME_UNIT_OPTIONS.find(opt => opt.value === unit);
  if (!unitOption) return value;
  return value * unitOption.seconds;
};

/**
 * 生成默认时间窗名称
 */
const generateDefaultWindowName = (action: string, _index: number): string => {
  const actionLabel = ACTION_LABELS[action] || action || '未命名';
  return `${actionLabel}时间窗`;
};

// ==================== 子组件 ====================

/**
 * 时间偏移输入组件（带单位切换）
 */
interface OffsetInputProps {
  value?: number | null;
  onChange?: (value: number | null) => void;
  placeholder?: string;
  defaultUnit?: TimeUnit;
}

const OffsetInput: React.FC<OffsetInputProps> = ({
  value,
  onChange,
  placeholder,
  defaultUnit = 'minute'
}) => {
  const screens = useBreakpoint();
  const isMobile = !screens.md;
  const [unit, setUnit] = useState<TimeUnit>(defaultUnit);
  const [isInitialized, setIsInitialized] = useState(false);

  useEffect(() => {
    if (value != null && isInitialized) {
      const abs = Math.abs(value);
      if (abs >= 604800 && abs % 604800 === 0) {
        setUnit('week');
      } else if (abs >= 86400 && abs % 86400 === 0) {
        setUnit('day');
      } else if (abs >= 3600 && abs % 3600 === 0) {
        setUnit('hour');
      } else if (abs >= 60 && abs % 60 === 0) {
        setUnit('minute');
      } else {
        setUnit('second');
      }
    }
    if (value != null && !isInitialized) {
      setIsInitialized(true);
    }
  }, [value, isInitialized]);

  const displayValue = value != null ? secondsToUnit(value, unit) : null;

  const handleValueChange = (newValue: number | null) => {
    if (newValue === null) {
      onChange?.(null);
    } else {
      onChange?.(unitToSeconds(newValue, unit));
    }
    setIsInitialized(true);
  };

  const handleUnitChange = (newUnit: TimeUnit) => {
    setUnit(newUnit);
    if (displayValue !== null) {
      onChange?.(unitToSeconds(displayValue, newUnit));
    }
    setIsInitialized(true);
  };

  const unitOption = TIME_UNIT_OPTIONS.find(opt => opt.value === unit);

  return (
    <Space.Compact style={{ width: '100%' }}>
      <InputNumber
        value={displayValue}
        onChange={handleValueChange}
        placeholder={placeholder}
        min={unitOption ? -31536000 / unitOption.seconds : -31536000}
        max={unitOption ? 31536000 / unitOption.seconds : 31536000}
        precision={0}
        style={{ flex: 1 }}
        controls
      />
      <Select
        value={unit}
        onChange={handleUnitChange}
        options={TIME_UNIT_OPTIONS.map(opt => ({ label: opt.label, value: opt.value }))}
        style={{ width: isMobile ? 70 : 90 }}
      />
    </Space.Compact>
  );
};

/**
 * 单个时间窗配置表单内容
 */
interface WindowFormContentProps {
  field: any;
  remove: (name: number) => void;
}

const WindowFormContent: React.FC<WindowFormContentProps> = ({ field, remove }) => {
  const screens = useBreakpoint();
  const { token } = useToken();
  const _isMobile = !screens.md;
  const _action = Form.useWatch(['windows', field.name, 'action']);
  const openOffsetSec = Form.useWatch(['windows', field.name, 'openOffsetSec']);
  const closeOffsetSec = Form.useWatch(['windows', field.name, 'closeOffsetSec']);
  const failPolicy = Form.useWatch(['windows', field.name, 'failPolicy']);

  return (
    <div style={{ padding: '16px 0' }}>
      <Space style={{ width: '100%' }} size="middle">
        {/* 自定义名称 */}
        <Row gutter={16}>
          <Col span={24}>
            <Form.Item
              name={[field.name, 'name']}
              label="时间窗名称"
              rules={[{ required: true, message: '请输入时间窗名称' }]}
              extra="自定义名称，用于识别此时间窗"
            >
              <Input placeholder="如：提前预约窗口、签到时间窗" maxLength={50} />
            </Form.Item>
          </Col>
        </Row>

        {/* 动作类型与参考点 */}
        <Row gutter={16}>
          <Col xs={24} sm={12}>
            <Form.Item
              name={[field.name, 'action']}
              label={
                <Space>
                  动作类型
                  <Tooltip title="选择要限制的操作类型：预约-创建新预约，签到-签到操作，取消-取消预约，释放-释放占位号">
                    <QuestionCircleOutlined style={{ color: token.colorPrimary }} />
                  </Tooltip>
                </Space>
              }
              rules={[{ required: true, message: '请选择动作类型' }]}
            >
              <Select options={[...WINDOW_ACTION_OPTIONS]} placeholder="请选择动作类型" />
            </Form.Item>
          </Col>
          <Col xs={24} sm={12}>
            <Form.Item
              name={[field.name, 'referencePoint']}
              label={
                <Space>
                  参考点
                  <Tooltip title="时间窗口的计算基准：班次开始/结束时间基于班次时间表，预约创建时间基于用户操作时间">
                    <QuestionCircleOutlined style={{ color: token.colorPrimary }} />
                  </Tooltip>
                </Space>
              }
              rules={[{ required: true, message: '请选择参考点' }]}
            >
              <Select options={[...WINDOW_REFERENCE_POINT_OPTIONS]} placeholder="请选择参考点" />
            </Form.Item>
          </Col>
        </Row>

        {/* 开放与截止偏移 */}
        <Row gutter={16}>
          <Col xs={24} sm={12}>
            <Form.Item
              name={[field.name, 'openOffsetSec']}
              label="开放偏移"
              extra="留空表示不限制最早时间"
            >
              <OffsetInput placeholder="留空=不限制" defaultUnit="minute" />
            </Form.Item>
            <Text type="secondary" style={{ fontSize: 12 }}>
              当前值: {formatOffset(openOffsetSec ?? null)}
            </Text>
          </Col>
          <Col xs={24} sm={12}>
            <Form.Item
              name={[field.name, 'closeOffsetSec']}
              label="截止偏移"
              extra="留空表示不限制最晚时间"
            >
              <OffsetInput placeholder="留空=不限制" defaultUnit="minute" />
            </Form.Item>
            <Text type="secondary" style={{ fontSize: 12 }}>
              当前值: {formatOffset(closeOffsetSec ?? null)}
            </Text>
          </Col>
        </Row>

        {/* 边界与失败策略 */}
        <Row gutter={16}>
          <Col xs={24} sm={8}>
            <Form.Item
              name={[field.name, 'openInclusive']}
              label={
                <Space>
                  包含开放边界
                  <Tooltip title="是否包含开放时刻：包含表示到达开放时刻即可操作，不包含表示必须过开放时刻才能操作">
                    <QuestionCircleOutlined style={{ color: token.colorPrimary }} />
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
          <Col xs={24} sm={8}>
            <Form.Item
              name={[field.name, 'closeInclusive']}
              label={
                <Space>
                  包含截止边界
                  <Tooltip title="是否包含截止时刻：包含表示截止时刻仍可操作，不包含表示必须在截止时刻前完成操作">
                    <QuestionCircleOutlined style={{ color: token.colorPrimary }} />
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
          <Col xs={24} sm={8}>
            <Form.Item
              name={[field.name, 'failPolicy']}
              label={
                <Space>
                  失败策略
                  <Tooltip title="操作不在时间窗内的处理方式：拒绝-禁止操作并提示错误，允许并打标签-允许操作但标记特殊状态，自动候补-添加到候补队列">
                    <QuestionCircleOutlined style={{ color: token.colorPrimary }} />
                  </Tooltip>
                </Space>
              }
              rules={[{ required: true, message: '请选择失败策略' }]}
              initialValue="REJECT"
            >
              <Select options={[...WINDOW_FAIL_POLICY_OPTIONS]} placeholder="请选择失败策略" />
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
              label="备注说明"
            >
              <Input.TextArea placeholder="可选，描述该时间窗的用途" rows={2} />
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

        {/* 删除按钮 */}
        <div style={{ borderTop: '1px solid #f0f0f0', paddingTop: 16, marginTop: 8 }}>
          <Popconfirm
            title="确定删除此时间窗？"
            onConfirm={() => remove(field.name)}
            okText="删除"
            cancelText="取消"
            okButtonProps={{ danger: true }}
          >
            <Button danger icon={<DeleteOutlined />}>
              删除此时间窗
            </Button>
          </Popconfirm>
        </div>
      </Space>
    </div>
  );
};

/**
 * 时间窗 Tabs 内容组件 - 使用 Form.useWatch 获取实时数据
 */
interface WindowTabsContentProps {
  fields: any[];
  add: (defaultValue?: any) => void;
  remove: (index: number) => void;
  activeKey: string;
  setActiveKey: (key: string) => void;
}

const WindowTabsContent: React.FC<WindowTabsContentProps> = ({
  fields,
  add,
  remove,
  activeKey,
  setActiveKey,
}) => {
  const screens = useBreakpoint();
  const { token } = useToken();
  const isMobile = !screens.md;
  const isTablet = screens.md && !screens.lg;

  // 使用 useWatch 获取所有 windows 的数据
  const windows = Form.useWatch('windows') || [];

  // 生成 tab 项
  const tabItems = fields.map((field, index) => {
    const windowData = windows[index] || {};
    const name = windowData.name || generateDefaultWindowName(windowData.action, index);
    const action = windowData.action;
    const actionLabel = ACTION_LABELS[action] || '';

    return {
      key: String(index),
      label: (
        <div style={{
          maxWidth: isMobile ? 100 : isTablet ? 120 : 150,
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          whiteSpace: 'nowrap',
          textAlign: 'left',
        }}>
          <div style={{ fontWeight: 500, fontSize: isMobile ? 12 : 14 }}>{name}</div>
          {actionLabel && (
            <div style={{ fontSize: isMobile ? 10 : 11, color: token.colorTextSecondary }}>{actionLabel}</div>
          )}
        </div>
      ),
      children: (
        <WindowFormContent
          key={field.key}
          field={field}
          remove={(name) => {
            remove(name);
            // 删除后调整 activeKey
            if (fields.length > 1) {
              const newIndex = Math.min(index, fields.length - 2);
              setActiveKey(String(newIndex));
            }
          }}
        />
      ),
    };
  });

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <Tabs
        activeKey={activeKey}
        onChange={setActiveKey}
        tabPlacement={(isMobile ? 'top' : 'left') as any}
        items={tabItems}
        style={{ minHeight: isMobile ? 300 : 400 }}
        tabBarStyle={{ width: isMobile ? 'auto' : isTablet ? 120 : 180 }}
        tabBarExtraContent={{
          left: !isMobile && (
            <div style={{ padding: '8px 0', marginBottom: 8 }}>
              <Text type="secondary" style={{ fontSize: 12 }}>
                共 {fields.length} 个时间窗
              </Text>
            </div>
          ),
        }}
      />
      <Button
        type="dashed"
        onClick={() => {
          add({ ...WINDOW_DEFAULT_VALUES, name: `时间窗 ${fields.length + 1}` });
          setActiveKey(String(fields.length));
        }}
        block
        icon={<PlusOutlined />}
        style={{ height: isMobile ? 44 : 40 }}
      >
        添加时间窗
      </Button>
    </div>
  );
};

/**
 * 时间轴可视化组件 - 显示时间窗的时间关系
 */
interface WindowTimelineVisualizationProps {
  fields: any[];
}

const WindowTimelineVisualization: React.FC<WindowTimelineVisualizationProps> = ({ fields: _fields }) => {
  const screens = useBreakpoint();
  const { token } = useToken();
  const isMobile = !screens.md;

  // 使用 useWatch 获取所有 windows 的数据
  const windows = Form.useWatch('windows') || [];

  // 示例班次时间（默认 8:00 - 12:00）
  const baseDate = dayjs().startOf('day').toDate();
  const shiftStart = dayjs(baseDate).hour(8).minute(0).second(0).toDate();
  const shiftEnd = dayjs(baseDate).hour(12).minute(0).second(0).toDate();

  // 过滤启用的时间窗
  const enabledWindows = windows.filter((w: any) => w.enabled !== false);

  if (enabledWindows.length === 0) {
    return (
      <Alert
        title="暂无已启用的时间窗"
        description="启用时间窗后，此处将显示时间轴可视化"
        type="info"
        showIcon
      />
    );
  }

  return (
    <div>
      <Text strong style={{ fontSize: 14, marginBottom: 12, display: 'block' }}>
        时间轴预览（以班次开始时间 8:00 为基准）
      </Text>

      {/* 垂直时间轴展示 */}
      <div style={{
        padding: isMobile ? '12px' : '16px',
        backgroundColor: '#fafafa',
        borderRadius: '6px',
        marginTop: 12,
      }}>
        <RuleSetTimeline
          windows={enabledWindows}
          direction="vertical"
          compact={isMobile}
          shiftStart={shiftStart}
          shiftEnd={shiftEnd}
        />
      </div>

      {/* 时间关系说明 */}
      <div style={{ marginTop: 16, padding: 12, backgroundColor: token.colorInfoBg, borderRadius: 6, borderLeft: `3px solid ${token.colorInfo}` }}>
        <Text type="secondary" style={{ fontSize: 12 }}>
          提示：时间轴显示各时间窗相对于班次开始时间（8:00）的开放和截止时间。
          绿色表示开放时间偏移，红色表示截止时间偏移。多个时间窗组合时，系统会取最严格的限制。
        </Text>
      </div>
    </div>
  );
};

/**
 * 时间窗配置组件 - 使用竖向 Tabs 展示
 */
const RuleWindowConfig: React.FC = () => {
  const [activeKey, setActiveKey] = useState<string>('0');
  const [showTimeline, setShowTimeline] = useState(false);

  return (
    <Card
      title="时间窗配置"
      style={{ marginBottom: 16 }}
      extra={
        <Button
          icon={<EyeOutlined />}
          onClick={() => setShowTimeline(!showTimeline)}
          type={showTimeline ? 'primary' : 'default'}
          size="small"
        >
          {showTimeline ? '隐藏时间轴' : '显示时间轴'}
        </Button>
      }
    >
      <Form.List name="windows">
        {(fields, { add, remove }) => {
          // 当没有时间窗时显示空状态
          if (fields.length === 0) {
            return (
              <div style={{ textAlign: 'center', padding: '48px 0' }}>
                <Empty
                  description="暂无时间窗配置"
                  image={Empty.PRESENTED_IMAGE_SIMPLE}
                >
                  <Button
                    type="primary"
                    icon={<PlusOutlined />}
                    onClick={() => {
                      add({ ...WINDOW_DEFAULT_VALUES, name: '新时间窗' });
                      setActiveKey('0');
                    }}
                  >
                    添加时间窗
                  </Button>
                </Empty>
              </div>
            );
          }

          // 使用 Form.useWatch 获取 windows 数据用于显示 tab 标签
          return (
            <>
              <WindowTabsContent
                fields={fields}
                add={add}
                remove={remove}
                activeKey={activeKey}
                setActiveKey={setActiveKey}
              />

              {/* 时间轴可视化 */}
              {showTimeline && (
                <>
                  <Divider />
                  <WindowTimelineVisualization fields={fields} />
                </>
              )}
            </>
          );
        }}
      </Form.List>
    </Card>
  );
};

export default RuleWindowConfig;
