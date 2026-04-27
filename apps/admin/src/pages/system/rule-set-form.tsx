/**
 * 规则组表单页面
 *
 * 结构：6个Tab（基础信息/时间口径/时间窗/预约策略/签到策略/容量策略）
 * + 可选的实时预览面板 + 规则效果预览弹窗 + 预设模板
 */
import { PageContainer, ProForm, ProFormText, ProFormSelect, ProFormDigit, ProFormSwitch, ProFormTextArea, ProFormDependency, FooterToolbar } from '@ant-design/pro-components';
import { Card, App, Button, Space, Row, Col, Tabs, message, Alert, Modal, Radio, Typography, Affix, Progress, Divider, Tag, Grid, Drawer, Result } from 'antd';
import { ThunderboltOutlined, CheckCircleOutlined, RightOutlined } from '@ant-design/icons';
import { useEffect, useState, useRef, useMemo } from 'react';
import { history, useParams, useAccess } from '@umijs/max';

const { useBreakpoint } = Grid;
import { ruleSetApi, shiftTypeApi } from '@hospital/api';
import type { RuleSet, ShiftType } from '@hospital/shared';
import RuleWindowConfig from '../../components/RuleWindowConfig';
import RulePreviewModal from './components/RulePreviewModal';
import { RuleSetLivePreview, RuleSetSummaryCard } from '@/components/rule-set-visualization';
import ResizableDivider from '@/components/ResizableDivider';
import {
  trackEditBeforePreview,
  trackEditAfterPreview,
  trackEditExitTab,
  trackEditSave,
  trackEditCancel,
  getTimestamp,
  getChangedFields,
  type EditBehaviorData,
  type EditTabType,
} from '@/utils/analytics';
import { SwitchGroup } from '@/components/formFields';
import {
  TIME_SOURCE_OPTIONS,
  TIMEZONE_SOURCE_OPTIONS,
  COMPARE_PRECISION_OPTIONS,
  ROUNDING_MODE_OPTIONS,
  CONFLICT_STRATEGY_OPTIONS,
  AFTER_GRACE_STATUS_OPTIONS,
  NO_CHECKIN_AFTER_CLOSE_OPTIONS,
  WAITLIST_PROMOTE_POLICY_OPTIONS,
  RULE_SET_FORM_INITIAL_VALUES,
  RULE_SET_PRESETS,
  fetchPresets,
  clearPresetsCache,
  type RuleSetPreset,
} from '@/constants/rule-set';

const { Text, Title } = Typography;

// ==================== 常量定义 ====================

// localStorage 键名
const STORAGE_KEY_FIRST_VISIT = 'rule-set-form-first-visit';

// 核心配置 Tab 列表
const CORE_CONFIG_TABS = ['basic', 'time', 'windows'];

// 高级策略 Tab 列表
const ADVANCED_STRATEGY_TABS = ['booking', 'checkin', 'capacity'];

// 核心配置必填字段列表（用于计算完成度）
interface CoreFieldConfig {
  tab: string;
  field: string | string[];
  label: string;
}

const CORE_REQUIRED_FIELDS: CoreFieldConfig[] = [
  // 基础信息 (3个)
  { tab: 'basic', field: 'name', label: '规则组名称' },
  { tab: 'basic', field: 'priority', label: '优先级' },
  { tab: 'basic', field: 'shiftTypeIds', label: '班次类型' },
  // 时间口径 (5个)
  { tab: 'time', field: 'timeSource', label: '时间来源' },
  { tab: 'time', field: 'timezoneSource', label: '时区来源' },
  { tab: 'time', field: 'comparePrecision', label: '比较精度' },
  { tab: 'time', field: 'roundingMode', label: '舍入模式' },
  { tab: 'time', field: 'clockSkewToleranceSec', label: '时钟容差' },
  // 时间窗 (至少1个)
  { tab: 'windows', field: 'windows', label: '时间窗配置' },
];

// 侧边栏预览面板默认和限制宽度
const DEFAULT_PREVIEW_WIDTH = 400;
const MIN_PREVIEW_WIDTH = 300;
const MAX_PREVIEW_WIDTH = 600;
const XXL_PREVIEW_WIDTH = 480; // xxl (>= 1440px) 默认宽度
const XXL_MAX_PREVIEW_WIDTH = 700; // xxl 最大宽度

// ==================== 辅助组件 ====================

/**
 * 引导卡片组件
 */
interface OnboardingCardProps {
  visible: boolean;
  onClose: () => void;
  onSelectPreset: () => void;
}

const OnboardingCard: React.FC<OnboardingCardProps> = ({ visible, onClose, onSelectPreset }) => {
  if (!visible) return null;

  return (
    <Card
      style={{
        marginBottom: 16,
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        border: 'none',
      }}
      bodyStyle={{ color: 'white' }}
    >
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        <div>
          <Title level={4} style={{ color: 'white', marginBottom: 8 }}>
            欢迎使用规则组配置
          </Title>
          <Text style={{ color: 'rgba(255,255,255,0.9)' }}>
            规则组是控制预约、签到等业务逻辑的核心配置。让我们快速完成基础配置。
          </Text>
        </div>

        <Row gutter={16}>
          <Col xs={12} sm={8} md={4}>
            <Card
              size="small"
              style={{ background: 'rgba(255,255,255,0.15)', border: 'none' }}
              bodyStyle={{ color: 'white', textAlign: 'center' }}
            >
              <Text strong style={{ color: 'white', display: 'block', marginBottom: 8 }}>
                1. 基础信息
              </Text>
              <Text style={{ color: 'rgba(255,255,255,0.8)', fontSize: 12 }}>
                名称、优先级、班次类型
              </Text>
            </Card>
          </Col>
          <Col xs={12} sm={8} md={4}>
            <Card
              size="small"
              style={{ background: 'rgba(255,255,255,0.15)', border: 'none' }}
              bodyStyle={{ color: 'white', textAlign: 'center' }}
            >
              <Text strong style={{ color: 'white', display: 'block', marginBottom: 8 }}>
                2. 时间口径
              </Text>
              <Text style={{ color: 'rgba(255,255,255,0.8)', fontSize: 12 }}>
                时间来源、时区、精度
              </Text>
            </Card>
          </Col>
          <Col xs={12} sm={8} md={4}>
            <Card
              size="small"
              style={{ background: 'rgba(255,255,255,0.15)', border: 'none' }}
              bodyStyle={{ color: 'white', textAlign: 'center' }}
            >
              <Text strong style={{ color: 'white', display: 'block', marginBottom: 8 }}>
                3. 时间窗
              </Text>
              <Text style={{ color: 'rgba(255,255,255,0.8)', fontSize: 12 }}>
                预约开放/截止时间
              </Text>
            </Card>
          </Col>
          <Col xs={12} sm={8} md={4}>
            <Card
              size="small"
              style={{ background: 'rgba(255,255,255,0.15)', border: 'none' }}
              bodyStyle={{ color: 'white', textAlign: 'center' }}
            >
              <Text strong style={{ color: 'white', display: 'block', marginBottom: 8 }}>
                4. 预约策略
              </Text>
              <Text style={{ color: 'rgba(255,255,255,0.8)', fontSize: 12 }}>
                限约规则、冲突处理
              </Text>
            </Card>
          </Col>
          <Col xs={12} sm={8} md={4}>
            <Card
              size="small"
              style={{ background: 'rgba(255,255,255,0.15)', border: 'none' }}
              bodyStyle={{ color: 'white', textAlign: 'center' }}
            >
              <Text strong style={{ color: 'white', display: 'block', marginBottom: 8 }}>
                5. 预设模板
              </Text>
              <Text style={{ color: 'rgba(255,255,255,0.8)', fontSize: 12 }}>
                一键应用完整配置
              </Text>
            </Card>
          </Col>
        </Row>

        <Space>
          <Button
            type="primary"
            size="large"
            icon={<ThunderboltOutlined />}
            onClick={() => {
              onSelectPreset();
              onClose();
            }}
            style={{ background: 'white', color: '#667eea', border: 'none' }}
          >
            使用预设模板快速开始
          </Button>
          <Button
            size="large"
            onClick={onClose}
            style={{ background: 'transparent', color: 'white', border: '1px solid white' }}
          >
            手动配置
          </Button>
        </Space>
      </Space>
    </Card>
  );
};

/**
 * 核心配置完成度卡片组件
 */
interface CoreCompletionCardProps {
  completed: number;
  total: number;
  percentage: number;
  incompleteFields: string[];
}

const CoreCompletionCard: React.FC<CoreCompletionCardProps> = ({
  completed,
  total,
  percentage,
  incompleteFields,
}) => {
  const isCoreCompleted = completed === total;

  return (
    <Card
      size="small"
      style={{
        marginBottom: 16,
        background: isCoreCompleted ? '#f6ffed' : '#fff7e6',
        borderColor: isCoreCompleted ? '#b7eb8f' : '#ffd591',
      }}
    >
      <Space direction="vertical" size="small" style={{ width: '100%' }}>
        <Space>
          {isCoreCompleted ? (
            <CheckCircleOutlined style={{ color: '#52c41a', fontSize: 16 }} />
          ) : (
            <ThunderboltOutlined style={{ color: '#fa8c16', fontSize: 16 }} />
          )}
          <Text strong style={{ fontSize: 14 }}>
            {isCoreCompleted ? '核心配置已完成' : `核心配置进度：${completed}/${total} 项`}
          </Text>
        </Space>
        {!isCoreCompleted && (
          <>
            <Progress
              percent={percentage}
              strokeColor="#667eea"
              showInfo={false}
              size="small"
            />
            {incompleteFields.length > 0 && (
              <Text type="secondary" style={{ fontSize: 12 }}>
                待完善：{incompleteFields.join('、')}
              </Text>
            )}
          </>
        )}
      </Space>
    </Card>
  );
};

/** 将后端 snake_case 预设配置转为前端 camelCase */
function transformToCamelCase(obj: Record<string, any>): Record<string, any> {
  if (!obj || typeof obj !== 'object') return obj;
  const result: Record<string, any> = {};
  for (const key of Object.keys(obj)) {
    const camelKey = key.replace(/_([a-z])/g, (_, c) => c.toUpperCase());
    const value = obj[key];
    if (Array.isArray(value)) {
      result[camelKey] = value.map(v => typeof v === 'object' && v !== null ? transformToCamelCase(v) : v);
    } else if (typeof value === 'object' && value !== null) {
      result[camelKey] = transformToCamelCase(value);
    } else {
      result[camelKey] = value;
    }
  }
  return result;
}

/**
 * 预设模板选择弹窗组件
 */
interface PresetModalProps {
  open: boolean;
  onClose: () => void;
  onApply: (presetId: string) => void;
  selectedPreset: string | null;
  onSelectPreset: (presetId: string) => void;
  isMobile: boolean;
  isTablet: boolean;
}

const PresetModal: React.FC<PresetModalProps> = ({
  open,
  onClose,
  onApply,
  selectedPreset,
  onSelectPreset,
  isMobile,
  isTablet,
}) => {
  const [presets, setPresets] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (open) {
      setLoading(true);
      fetchPresets()
        .then(setPresets)
        .finally(() => setLoading(false));
    }
  }, [open]);

  return (
    <Modal
      title="选择预设模板"
      open={open}
      onCancel={() => {
        onClose();
        onSelectPreset(null);
      }}
      onOk={() => {
        if (selectedPreset) {
          onApply(selectedPreset);
        } else {
          message.warning('请选择一个预设模板');
        }
      }}
      okText="应用模板"
      cancelText="取消"
      width={isMobile ? '95%' : isTablet ? '80%' : 600}
    >
      <div style={{ marginBottom: 16 }}>
        <Text type="secondary">
          选择一个预设模板，系统将自动填充规则配置。您仍可在应用后进行调整。
        </Text>
      </div>
      <Spin spinning={loading}>
        <Radio.Group
          value={selectedPreset}
          onChange={(e) => onSelectPreset(e.target.value)}
          style={{ width: '100%' }}
        >
          <Space direction="vertical" style={{ width: '100%' }}>
            {presets.map((preset) => {
              const config = preset.config || {};
              const bookingPolicy = config.booking_policy || config.bookingPolicy || {};
              const capacityPolicy = config.capacity_policy || config.capacityPolicy || {};
              return (
                <Card
                  key={preset.id}
                  size="small"
                  hoverable
                  style={{
                    border: selectedPreset === preset.id ? '2px solid #1890ff' : '1px solid #d9d9d9',
                    backgroundColor: selectedPreset === preset.id ? '#e6f7ff' : undefined,
                  }}
                  onClick={() => onSelectPreset(preset.id)}
                >
                  <Radio value={preset.id}>
                    <Space direction="vertical" size={0}>
                      <Space>
                        <Text strong>{preset.name}</Text>
                        {preset.isSystem && <Tag color="blue" style={{ fontSize: 10 }}>系统</Tag>}
                      </Space>
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        {preset.description}
                      </Text>
                      <Space style={{ marginTop: 4 }}>
                        <Text type="secondary" style={{ fontSize: 11 }}>
                          优先级: {config.priority}
                        </Text>
                        <Text type="secondary" style={{ fontSize: 11 }}>
                          每日限约: {bookingPolicy.per_user_per_day ?? bookingPolicy.perUserPerDay ?? '不限'}
                        </Text>
                        <Text type="secondary" style={{ fontSize: 11 }}>
                          容量: {capacityPolicy.total_capacity ?? capacityPolicy.totalCapacity ?? '不限'}
                        </Text>
                      </Space>
                    </Space>
                  </Radio>
                </Card>
              );
            })}
          </Space>
        </Radio.Group>
      </Spin>
    </Modal>
  );
};

/**
 * 基础信息 Tab 组件
 */
interface BasicInfoTabProps {
  shiftTypes: ShiftType[];
  loading?: boolean;
}

const BasicInfoTab: React.FC<BasicInfoTabProps> = ({ shiftTypes, loading }) => {
  return (
    <Card style={{ marginBottom: 16 }} loading={loading}>
      <Row gutter={16}>
        <Col xs={24} sm={12}>
          <ProFormText
            name="name"
            label="规则组名称"
            width="lg"
            placeholder="如：门诊预约规则"
            rules={[{ required: true, message: '请输入规则组名称' }]}
          />
        </Col>
        <Col xs={24} sm={12}>
          <ProFormDigit
            name="priority"
            label="优先级"
            width="md"
            min={1}
            max={1000}
            fieldProps={{ precision: 0 }}
            rules={[{ required: true, message: '请输入优先级' }]}
            extra="数值越小优先级越高，系统按优先级顺序匹配规则"
          />
        </Col>
      </Row>

      <ProFormSelect
        name="shiftTypeIds"
        label="关联班次类型"
        width="lg"
        mode="multiple"
        options={shiftTypes.map((st) => ({ label: st.name, value: st.id }))}
        rules={[{ required: true, message: '请选择班次类型' }]}
        extra="规则将应用于选中的班次类型"
      />

      <ProFormSwitch
        name="enabled"
        label="启用状态"
        extra="禁用后规则不会生效"
      />

      <ProFormTextArea
        name="description"
        label="描述"
        width="lg"
        fieldProps={{ rows: 3 }}
        placeholder="请输入规则组描述"
      />
    </Card>
  );
};

/**
 * 时间口径 Tab 组件
 */
interface TimeConfigTabProps {
  loading?: boolean;
}

const TimeConfigTab: React.FC<TimeConfigTabProps> = ({ loading }) => {
  return (
    <>
      <Alert
        message="时间口径配置说明"
        description="时间口径定义规则组计算时间窗时的基准设置。通常使用默认值即可，仅在特殊业务场景下需要调整。"
        type="info"
        showIcon
        style={{ marginBottom: 16 }}
      />
      <Card style={{ marginBottom: 16 }} loading={loading}>
        {/* 时间与精度配置 */}
        <Row gutter={[24, 16]} style={{ marginBottom: 16 }}>
          <Col xs={12} sm={6}>
            <ProFormSelect
              name="timeSource"
              label="时间来源"
              width="xl"
              options={TIME_SOURCE_OPTIONS}
              rules={[{ required: true, message: '请选择时间来源' }]}
              extra="决定用服务器时间还是客户端时间来判断预约窗口"
            />
          </Col>
          <Col xs={12} sm={6}>
            <ProFormSelect
              name="timezoneSource"
              label="时区来源"
              width="xl"
              options={TIMEZONE_SOURCE_OPTIONS}
              rules={[{ required: true, message: '请选择时区来源' }]}
              extra="统一使用医院时区、班次时区还是用户所在时区"
            />
          </Col>
          <Col xs={12} sm={6}>
            <ProFormSelect
              name="comparePrecision"
              label="比较精度"
              width="xl"
              options={COMPARE_PRECISION_OPTIONS}
              rules={[{ required: true, message: '请选择比较精度' }]}
              extra="精确到秒、毫秒或分钟"
            />
          </Col>
          <Col xs={12} sm={6}>
            <ProFormSelect
              name="roundingMode"
              label="舍入模式"
              width="xl"
              options={ROUNDING_MODE_OPTIONS}
              rules={[{ required: true, message: '请选择舍入模式' }]}
              extra="精确时间、向下取整到分钟、向上取整到分钟"
            />
          </Col>
        </Row>

        {/* 容差与边界配置 */}
        <Row gutter={[24, 16]}>
          <Col xs={24} sm={8}>
            <ProFormDigit
              name="clockSkewToleranceSec"
              label="时钟容差(秒)"
              width="xl"
              min={0}
              max={300}
              fieldProps={{ precision: 0 }}
              rules={[{ required: true, message: '请输入时钟容差' }]}
              extra="超过此偏差视为无效请求"
            />
          </Col>
          <Col xs={12} sm={8}>
            <ProFormSwitch
              name="defaultOpenInclusive"
              label="默认包含开放边界"
              extra="边界时刻本身是否算在窗口内"
            />
          </Col>
          <Col xs={12} sm={8}>
            <ProFormSwitch
              name="defaultCloseInclusive"
              label="默认包含截止边界"
              extra="边界时刻本身是否算在窗口内"
            />
          </Col>
        </Row>
      </Card>
    </>
  );
};

/**
 * 预约策略 Tab 组件
 */
interface BookingPolicyTabProps {
  loading?: boolean;
}

const BookingPolicyTab: React.FC<BookingPolicyTabProps> = ({ loading }) => {
  return (
    <Card style={{ marginBottom: 16 }} loading={loading}>
      {/* 预约前置条件 */}
      <Row gutter={[24, 16]} style={{ marginBottom: 16 }}>
        <Col xs={24} sm={12}>
          <ProFormSwitch
            name={['bookingPolicy', 'requireAuth']}
            label="需要登录"
            tooltip="未登录用户无法预约"
          />
        </Col>
        <Col xs={24} sm={12}>
          <ProFormSwitch
            name={['bookingPolicy', 'requirePatientProfileComplete']}
            label="需要完整档案"
            tooltip="预约前需完善就诊人信息"
          />
        </Col>
      </Row>

      {/* 限约配置 */}
      <Row gutter={[24, 16]} style={{ marginBottom: 16 }}>
        <Col xs={24} sm={8}>
          <ProFormDigit
            name={['bookingPolicy', 'perUserPerShift']}
            label="每班次限约数"
            width="xl"
            min={1}
            max={100}
            fieldProps={{ precision: 0 }}
            rules={[{ required: true, message: '请输入限约数' }]}
            tooltip="同一用户在同一班次的预约上限"
          />
        </Col>
        <Col xs={24} sm={8}>
          <ProFormDigit
            name={['bookingPolicy', 'perUserPerDay']}
            label="每日限约数"
            width="xl"
            min={0}
            max={100}
            fieldProps={{ precision: 0 }}
            tooltip="0表示不限制"
          />
        </Col>
        <Col xs={24} sm={8}>
          <ProFormDigit
            name={['bookingPolicy', 'perUserPerWeek']}
            label="每周限约数"
            width="xl"
            min={0}
            max={500}
            fieldProps={{ precision: 0 }}
            tooltip="0表示不限制"
          />
        </Col>
      </Row>

      {/* 冲突处理策略 */}
      <Row gutter={[24, 16]}>
        <Col xs={24} sm={8}>
          <ProFormSelect
            name={['bookingPolicy', 'conflictSameShift']}
            label="同班次冲突策略"
            width="xl"
            options={CONFLICT_STRATEGY_OPTIONS.filter(opt =>
              opt.value === 'REJECT' || opt.value === 'REPLACE'
            )}
            rules={[{ required: true, message: '请选择冲突策略' }]}
            tooltip="同一用户在同一班次多次预约时的处理方式：拒绝表示不允许重复预约，替换表示新预约替换旧预约"
          />
        </Col>
        <Col xs={24} sm={8}>
          <ProFormSelect
            name={['bookingPolicy', 'conflictOverlapTime']}
            label="时间重叠策略"
            width="xl"
            options={CONFLICT_STRATEGY_OPTIONS.filter(opt =>
              opt.value === 'REJECT' || opt.value === 'ALLOW'
            )}
            rules={[{ required: true, message: '请选择重叠策略' }]}
            tooltip="同一用户预约时间重叠的班次时的处理方式：拒绝表示不允许时间重叠的预约，允许表示可以同时预约多个时间重叠的班次"
          />
        </Col>
        <Col xs={24} sm={8}>
          <ProFormSelect
            name={['bookingPolicy', 'conflictSameTypeSameDay']}
            label="同类型同日策略"
            width="xl"
            options={CONFLICT_STRATEGY_OPTIONS.filter(opt =>
              opt.value === 'REJECT' || opt.value === 'ALLOW'
            )}
            rules={[{ required: true, message: '请选择策略' }]}
            tooltip="同一类型预约在同一天的限制"
          />
        </Col>
      </Row>
    </Card>
  );
};

/**
 * 签到策略 Tab 组件
 */
interface CheckinPolicyTabProps {
  loading?: boolean;
}

const CheckinPolicyTab: React.FC<CheckinPolicyTabProps> = ({ loading }) => {
  return (
    <Card style={{ marginBottom: 16 }} loading={loading}>
      {/* 签到前置条件 */}
      <Row gutter={[24, 16]} style={{ marginBottom: 16 }}>
        <Col xs={24} sm={8}>
          <ProFormSwitch
            name={['checkinPolicy', 'requireBooking']}
            label="需要预约"
            tooltip="是否必须先预约才能签到"
          />
        </Col>
        <Col xs={24} sm={8}>
          <ProFormSwitch
            name={['checkinPolicy', 'allowOnsiteBooking']}
            label="允许现场预约"
            tooltip="允许在签到时现场创建预约"
          />
        </Col>
        <Col xs={24} sm={8}>
          <ProFormSwitch
            name={['checkinPolicy', 'auditLog']}
            label="记录签到日志"
            tooltip="记录每次签到的详细信息"
          />
        </Col>
      </Row>

      {/* 签到限制配置 */}
      <Row gutter={[24, 16]} style={{ marginBottom: 16 }}>
        <Col xs={24} sm={8}>
          <ProFormDigit
            name={['checkinPolicy', 'maxTimes']}
            label="最大签到次数"
            width="xl"
            min={1}
            max={10}
            fieldProps={{ precision: 0 }}
            rules={[{ required: true, message: '请输入最大次数' }]}
            tooltip="同一预约最多允许签到的次数"
          />
        </Col>
        <Col xs={24} sm={8}>
          <ProFormDigit
            name={['checkinPolicy', 'gracePeriodSec']}
            label="宽限期(秒)"
            width="xl"
            min={0}
            max={3600}
            fieldProps={{ precision: 0 }}
            rules={[{ required: true, message: '请输入宽限期' }]}
            tooltip="迟到后的宽限时间，默认15分钟"
          />
        </Col>
        <Col xs={24} sm={8}>
          <ProFormSelect
            name={['checkinPolicy', 'afterGraceStatus']}
            label="宽限期后状态"
            width="xl"
            options={AFTER_GRACE_STATUS_OPTIONS}
            tooltip="宽限期结束后的状态标记"
          />
        </Col>
      </Row>

      {/* 超时处理 */}
      <Row gutter={[24, 16]}>
        <Col span={24}>
          <ProFormSelect
            name={['checkinPolicy', 'noCheckinAfterClose']}
            label="超时未签到处理"
            width="xl"
            options={NO_CHECKIN_AFTER_CLOSE_OPTIONS}
            rules={[{ required: true, message: '请选择处理方式' }]}
            tooltip="签到窗口关闭后仍未签到的处理方式"
          />
        </Col>
      </Row>
    </Card>
  );
};

/**
 * 容量策略 Tab 组件
 */
interface CapacityPolicyTabProps {
  loading?: boolean;
}

const CapacityPolicyTab: React.FC<CapacityPolicyTabProps> = ({ loading }) => {
  return (
    <Card style={{ marginBottom: 16 }} loading={loading}>
      {/* 基础容量配置 */}
      <Row gutter={[24, 16]} style={{ marginBottom: 16 }}>
        <Col xs={24} sm={8}>
          <ProFormDigit
            name={['capacityPolicy', 'totalCapacity']}
            label="总容量"
            width="xl"
            min={1}
            max={1000}
            fieldProps={{ precision: 0 }}
            rules={[{ required: true, message: '请输入总容量' }]}
            tooltip="班次的总预约容量"
          />
        </Col>
        <Col xs={24} sm={8}>
          <ProFormDigit
            name={['capacityPolicy', 'perUserCapacity']}
            label="每人限约数"
            width="xl"
            min={1}
            max={50}
            fieldProps={{ precision: 0 }}
            rules={[{ required: true, message: '请输入限约数' }]}
            tooltip="每个用户最多可预约的数量"
          />
        </Col>
        <Col xs={24} sm={8}>
          <ProFormSwitch
            name={['capacityPolicy', 'overbookingEnabled']}
            label="允许超额预约"
            tooltip="允许预约数超过总容量"
          />
        </Col>
      </Row>

      {/* 候补配置 */}
      <Row gutter={[24, 16]} style={{ marginBottom: 16 }}>
        <Col xs={24} sm={8}>
          <ProFormSwitch
            name={['capacityPolicy', 'waitlistEnabled']}
            label="启用候补"
            tooltip="启用候补队列功能"
          />
        </Col>
        <ProFormDependency name={[['capacityPolicy', 'waitlistEnabled']]}>
          {({ capacityPolicy }) => {
            if (!capacityPolicy?.waitlistEnabled) return null;
            return (
              <>
                <Col xs={24} sm={8}>
                  <ProFormDigit
                    name={['capacityPolicy', 'waitlistMaxSize']}
                    label="候补队列大小"
                    width="xl"
                    min={1}
                    max={100}
                    fieldProps={{ precision: 0 }}
                    rules={[{ required: true, message: '请输入队列大小' }]}
                    tooltip="候补队列的最大长度"
                  />
                </Col>
                <Col xs={24} sm={8}>
                  <ProFormSelect
                    name={['capacityPolicy', 'waitlistPromotePolicy']}
                    label="候补递补策略"
                    width="xl"
                    options={[...WAITLIST_PROMOTE_POLICY_OPTIONS]}
                    tooltip="当有空位时如何递补候补用户"
                  />
                </Col>
              </>
            );
          }}
        </ProFormDependency>
      </Row>

      {/* 超额预约配置 - 仅在启用超额时显示 */}
      <ProFormDependency name={[['capacityPolicy', 'overbookingEnabled']]}>
        {({ capacityPolicy }) => {
          if (!capacityPolicy?.overbookingEnabled) return null;
          return (
            <Row gutter={[24, 16]}>
              <Col span={24}>
                <ProFormDigit
                  name={['capacityPolicy', 'overbookingMax']}
                  label="最大超额数"
                  width="xl"
                  min={1}
                  max={100}
                  fieldProps={{ precision: 0 }}
                  rules={[{ required: true, message: '请输入超额数' }]}
                  tooltip="允许超过总容量的最大预约数量"
                />
              </Col>
            </Row>
          );
        }}
      </ProFormDependency>
    </Card>
  );
};

// ==================== 主组件 ====================

const RuleSetFormPage: React.FC = () => {
  const { message: antMessage } = App.useApp();
  const { id } = useParams();
  const access = useAccess();
  const screens = useBreakpoint();
  const isMobile = !screens.md; // 小于 768px
  const isTablet = screens.md && !screens.lg; // 768px - 992px
  const isXxl = screens.xxl; // >= 1600px
  const isEdit = !!id;
  const [loading, setLoading] = useState(false);
  const [ruleSet, setRuleSet] = useState<RuleSet | null>(null);
  const [shiftTypes, setShiftTypes] = useState<ShiftType[]>([]);
  const [loadError, setLoadError] = useState(false);
  const [previewModalOpen, setPreviewModalOpen] = useState(false);
  const [currentFormData, setCurrentFormData] = useState<any>(null);
  const [formValues, setFormValues] = useState<any>({});
  const formRef = useRef<any>();

  // 埋点：记录表单初始状态和当前 Tab
  const initialFormDataRef = useRef<any>(null);
  const beforePreviewFormDataRef = useRef<any>(null);
  const [activeTab, setActiveTab] = useState<string>('basic');

  // 预览面板宽度状态 - 响应式调整（包含 xxl 断点）
  const [previewWidth, setPreviewWidth] = useState(() => {
    if (typeof window !== 'undefined') {
      if (window.innerWidth < 768) return 300;
      if (window.innerWidth < 1024) return 350;
      if (window.innerWidth < 1440) return DEFAULT_PREVIEW_WIDTH;
      return 480; // xxl (>= 1440px) 使用更大的预览宽度
    }
    return DEFAULT_PREVIEW_WIDTH;
  });

  // 预览抽屉状态（小屏幕使用）
  const [previewDrawerOpen, setPreviewDrawerOpen] = useState(false);

  // 预设模板相关状态
  const [presetModalOpen, setPresetModalOpen] = useState(false);
  const [selectedPreset, setSelectedPreset] = useState<string | null>(null);

  // 渐进式引导相关状态
  const [showOnboarding, setShowOnboarding] = useState(false);

  // ==================== 辅助函数 ====================

  /**
   * 计算核心配置完成度
   */
  const calculateCoreCompletion = (values: any): { completed: number; total: number; percentage: number } => {
    let completed = 0;
    const total = CORE_REQUIRED_FIELDS.length;

    CORE_REQUIRED_FIELDS.forEach(({ field }) => {
      const value = typeof field === 'string' ? values[field] : values[field[0]]?.[field[1]];
      // 检查字段是否有值
      if (value !== undefined && value !== null && value !== '') {
        if (Array.isArray(value)) {
          if (value.length > 0) completed++;
        } else {
          completed++;
        }
      }
    });

    return {
      completed,
      total,
      percentage: Math.round((completed / total) * 100),
    };
  };

  /**
   * 获取核心配置未完成的字段列表
   */
  const getIncompleteFields = (values: any): string[] => {
    const incomplete: string[] = [];

    CORE_REQUIRED_FIELDS.forEach(({ field, label }) => {
      const value = typeof field === 'string' ? values[field] : values[field[0]]?.[field[1]];
      if (value === undefined || value === null || value === '' || (Array.isArray(value) && value.length === 0)) {
        incomplete.push(label);
      }
    });

    return incomplete;
  };

  // 应用预设模板
  const handleApplyPreset = async (presetId: string) => {
    // 先从后端预设中查找，再回退到本地硬编码
    const backendPresets = await fetchPresets();
    const preset = backendPresets.find(p => p.id === presetId);
    if (preset) {
      // 保留用户已选择的班次类型
      const currentShiftTypeIds = formRef.current?.getFieldValue('shiftTypeIds') || [];
      // 后端 config 是 snake_case，需要转为 camelCase 以匹配表单字段
      const config = transformToCamelCase(preset.config);
      const newValues = JSON.parse(JSON.stringify({
        ...config,
        shiftTypeIds: currentShiftTypeIds.length > 0 ? currentShiftTypeIds : [],
      }));
      formRef.current?.setFieldsValue(newValues);
      setFormValues(newValues);
      antMessage.success(`已应用「${preset.name}」预设模板`);
      setPresetModalOpen(false);
      setSelectedPreset(null);
    }
  };

  useEffect(() => {
    // 检查权限：只有超级管理员可以访问此页面
    if (!access.canSuperAdmin) {
      antMessage.error('只有超级管理员可以创建或编辑规则组');
      history.push('/organization/medical-config/rule-sets');
      return;
    }

    loadShiftTypes();
    if (isEdit) {
      loadRuleSet();
    } else {
      // 新增模式下检查是否首次访问
      const hasVisited = localStorage.getItem(STORAGE_KEY_FIRST_VISIT);
      if (!hasVisited) {
        setShowOnboarding(true);
        localStorage.setItem(STORAGE_KEY_FIRST_VISIT, 'true');
      }
    }
  }, [id, access.canSuperAdmin]);

  const loadShiftTypes = async () => {
    try {
      const data = await shiftTypeApi.getAll();
      setShiftTypes(data.filter((st) => st.enabled));
    } catch (error) {
      console.error('加载班次类型失败', error);
    }
  };

  const loadRuleSet = async () => {
    if (!id) return;
    setLoading(true);
    setLoadError(false);
    try {
      const data = await ruleSetApi.getById(id);
      setRuleSet(data);

      // 设置表单值 - 所有字段通过 ProForm 管理
      formRef.current?.setFieldsValue({
        ...data,
        shiftTypeIds: data.shiftTypes?.map((st) => st.id) || [],
        // 策略数据直接设置，不再需要独立状态
        bookingPolicy: data.bookingPolicy || RULE_SET_FORM_INITIAL_VALUES.bookingPolicy,
        checkinPolicy: data.checkinPolicy || RULE_SET_FORM_INITIAL_VALUES.checkinPolicy,
        capacityPolicy: data.capacityPolicy || RULE_SET_FORM_INITIAL_VALUES.capacityPolicy,
        windows: Array.isArray(data.windows) ? data.windows : [],
      });

      // 同时更新 formValues 用于预览
      setFormValues({
        ...data,
        shiftTypeIds: data.shiftTypes?.map((st) => st.id) || [],
        bookingPolicy: data.bookingPolicy || RULE_SET_FORM_INITIAL_VALUES.bookingPolicy,
        checkinPolicy: data.checkinPolicy || RULE_SET_FORM_INITIAL_VALUES.checkinPolicy,
        capacityPolicy: data.capacityPolicy || RULE_SET_FORM_INITIAL_VALUES.capacityPolicy,
        windows: Array.isArray(data.windows) ? data.windows : [],
      });
    } catch (error: any) {
      setLoadError(true);
      antMessage.error('加载规则组失败');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (values: any) => {
    // 检查权限
    if (!access.canSuperAdmin) {
      antMessage.error('只有超级管理员可以创建或编辑规则组');
      return;
    }

    // 保存前校验：如果没有配置时间窗，显示 Modal 警告
    const hasWindows = values.windows && values.windows.length > 0;
    if (!hasWindows) {
      return new Promise<void>((resolve, reject) => {
        Modal.confirm({
          title: '未配置时间窗',
          content: '您尚未配置任何时间窗规则。没有时间窗配置，用户将无法进行预约。是否继续保存？',
          okText: '继续保存',
          cancelText: '取消',
          onOk: async () => {
            try {
              await performSubmit(values);
              resolve();
            } catch (error) {
              reject(error);
            }
          },
          onCancel: () => {
            reject(new Error('用户取消操作'));
          },
        });
      });
    }

    await performSubmit(values);
  };

  const performSubmit = async (values: any) => {
    try {
      // 直接使用表单值，不再需要手动合并独立状态
      const data = {
        ...values,
        shiftTypeIds: values.shiftTypeIds || [],
      };

      if (isEdit && id) {
        // 携带乐观锁字段：期望的最后更新时间
        if (ruleSet?.updatedAt) {
          data.expectedUpdatedAt = ruleSet.updatedAt;
        }
        await ruleSetApi.update(id, data);
        antMessage.success('更新成功');
        // 编辑模式：停留在当前页面，不跳转
      } else {
        // 创建模式：创建成功后跳转到编辑页
        const result = await ruleSetApi.create(data);
        antMessage.success('创建成功');
        // 埋点：追踪保存操作
        const saveData: EditBehaviorData = {
          ruleSetId: result.id,
          ruleSetName: values.name,
          tab: activeTab as EditTabType,
          hasWindows: !!(values.windows && values.windows.length > 0),
          timestamp: getTimestamp(),
        };
        trackEditSave(saveData);
        // 使用 replace 跳转到编辑页，避免用户回退到空白创建页
        history.replace(`/organization/medical-config/rule-sets/${result.id}/edit`);
        return;
      }

      // 埋点：追踪保存操作（仅编辑模式）
      const saveData: EditBehaviorData = {
        ruleSetId: id,
        ruleSetName: values.name,
        tab: activeTab as EditTabType,
        hasWindows: !!(values.windows && values.windows.length > 0),
        timestamp: getTimestamp(),
      };
      trackEditSave(saveData);
    } catch (error: any) {
      antMessage.error(error.message || '操作失败');
      throw error;
    }
  };

  const initialValues = ruleSet ? {
    ...ruleSet,
    shiftTypeIds: ruleSet.shiftTypes?.map((st) => st.id) || [],
  } : RULE_SET_FORM_INITIAL_VALUES;

  // 初始化 formValues
  useEffect(() => {
    if (ruleSet) {
      const initialValues = {
        ...ruleSet,
        shiftTypeIds: ruleSet.shiftTypes?.map((st) => st.id) || [],
      };
      setFormValues(initialValues);
      // 保存初始表单数据用于埋点对比
      initialFormDataRef.current = initialValues;
    } else {
      setFormValues(RULE_SET_FORM_INITIAL_VALUES);
      initialFormDataRef.current = RULE_SET_FORM_INITIAL_VALUES;
    }
  }, [ruleSet]);

  // 计算核心配置完成度
  const coreCompletion = calculateCoreCompletion(formValues);
  const incompleteFields = getIncompleteFields(formValues);
  const isCoreCompleted = coreCompletion.completed === coreCompletion.total;

  /**
   * 生成 Tab 的 label，包含完成度指示器
   */
  const getTabLabel = (key: string, baseLabel: string): React.ReactNode => {
    const isCoreTab = CORE_CONFIG_TABS.includes(key);

    if (isCoreTab && !isCoreCompleted) {
      // 核心配置未完成时，显示进度指示
      const tabFields = CORE_REQUIRED_FIELDS.filter(f => f.tab === key);
      const tabCompleted = tabFields.filter(({ field }) => {
        const value = typeof field === 'string' ? formValues[field] : formValues[field[0]]?.[field[1]];
        return value !== undefined && value !== null && value !== '' && !(Array.isArray(value) && value.length === 0);
      }).length;

      if (tabCompleted < tabFields.length) {
        return (
          <Space size={4}>
            <span>{baseLabel}</span>
            <Tag color="orange" style={{ marginLeft: 4 }}>
              {tabCompleted}/{tabFields.length}
            </Tag>
          </Space>
        );
      }
    }

    if (isCoreTab && isCoreCompleted) {
      // 核心配置已完成
      return (
        <Space size={4}>
          <span>{baseLabel}</span>
          <CheckCircleOutlined style={{ color: '#52c41a', marginLeft: 4 }} />
        </Space>
      );
    }

    return baseLabel;
  };

  /**
   * 生成 Tab 列表配置
   */
  const generateTabItems = () => [
    {
      key: 'basic',
      label: getTabLabel('basic', '基础信息'),
      children: <BasicInfoTab shiftTypes={shiftTypes} loading={loading} />,
    },
    {
      key: 'time',
      label: getTabLabel('time', '时间口径'),
      children: <TimeConfigTab loading={loading} />,
    },
    {
      key: 'windows',
      label: getTabLabel('windows', '时间窗配置'),
      children: <RuleWindowConfig />,
    },
    {
      key: 'booking',
      label: '预约策略',
      children: <BookingPolicyTab loading={loading} />,
    },
    {
      key: 'checkin',
      label: '签到策略',
      children: <CheckinPolicyTab loading={loading} />,
    },
    {
      key: 'capacity',
      label: '容量策略',
      children: <CapacityPolicyTab loading={loading} />,
    },
  ];

  /**
   * 渲染表单内容
   */
  const renderFormContent = () => (
    <>
      {/* 核心配置完成度指示器 */}
      <CoreCompletionCard
        completed={coreCompletion.completed}
        total={coreCompletion.total}
        percentage={coreCompletion.percentage}
        incompleteFields={incompleteFields}
      />

      {/* Tab 分组标签 */}
      <div style={{ marginBottom: 12 }}>
        <Space size="large" split={<Divider type="vertical" />}>
          <Text strong style={{ fontSize: 13, color: '#1890ff' }}>
            基础配置
          </Text>
          <Text type="secondary" style={{ fontSize: 13 }}>
            高级策略
          </Text>
        </Space>
      </div>

      <Tabs
        defaultActiveKey="basic"
        items={generateTabItems()}
      />
    </>
  );

  return (
    <PageContainer title={isEdit ? '编辑规则组' : '新增规则组'}>
      {/* 加载失败时显示错误页面 */}
      {isEdit && loadError && (
        <Result
          status="error"
          title="加载规则组失败"
          subTitle="无法加载规则组数据，请检查网络连接或稍后重试"
          extra={[
            <Button key="retry" type="primary" onClick={() => loadRuleSet()}>
              重试
            </Button>,
            <Button key="back" onClick={() => history.back()}>
              返回
            </Button>,
          ]}
        />
      )}

      {/* 引导卡片 */}
      <OnboardingCard
        visible={showOnboarding && !isEdit}
        onClose={() => setShowOnboarding(false)}
        onSelectPreset={() => setPresetModalOpen(true)}
      />

      {/* 快速配置预设提示（新增和编辑模式都显示） */}
      {(!isEdit || !showOnboarding) && (
        <Alert
          message={isEdit ? "快速重新配置" : "快速开始"}
          description={
            <Space>
              <span>{isEdit ? "应用预设模板将覆盖当前配置，是否重新开始？" : "选择预设模板可快速配置规则组，节省配置时间"}</span>
              <Button
                type="primary"
                size="small"
                icon={<ThunderboltOutlined />}
                onClick={() => {
                  if (isEdit) {
                    // 编辑模式下需要额外确认
                    Modal.confirm({
                      title: '确认应用预设模板',
                      content: '应用预设模板将覆盖当前配置，此操作不可撤销。是否继续？',
                      okText: '继续',
                      cancelText: '取消',
                      onOk: () => setPresetModalOpen(true),
                    });
                  } else {
                    setPresetModalOpen(true);
                  }
                }}
              >
                选择预设模板
              </Button>
            </Space>
          }
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
        />
      )}

      {/* 表单内容区域：加载错误时不显示 */}
      {!loadError && (
        <>
      {/* 左右分栏布局：左侧表单，右侧可调整宽度的预览 */}
      {/* 小屏幕使用垂直布局，大屏幕使用左右分栏 */}
      {isMobile || isTablet ? (
        <>
          {/* 表单区域 */}
          <ProForm
            formRef={formRef}
            onFinish={handleSubmit}
            initialValues={initialValues}
            onValuesChange={(changedValues, allValues) => {
              // 实时更新表单值用于预览
              setFormValues(allValues);
            }}
            onTabChange={(key) => {
              // 埋点：追踪 Tab 切换
              const tabData: EditBehaviorData = {
                ruleSetId: id,
                ruleSetName: formValues.name,
                tab: key as EditTabType,
                changedFields: getChangedFields(initialFormDataRef.current, formValues),
                hasWindows: !!(formValues.windows && formValues.windows.length > 0),
                timestamp: getTimestamp(),
              };
              trackEditExitTab(tabData);
              setActiveTab(key);
            }}
            submitter={{
              render: (props, dom) => (
                <FooterToolbar>
                  <Space wrap>
                    <Button
                      icon={<RightOutlined />}
                      onClick={() => {
                        setPreviewDrawerOpen(true);
                      }}>
                      实时预览
                    </Button>
                    <Button onClick={() => {
                      // 保存预览前的表单状态
                      const values = formRef.current?.getFieldsValue();
                      beforePreviewFormDataRef.current = { ...values };

                      // 埋点：追踪预览前的编辑状态
                      const beforeData: EditBehaviorData = {
                        ruleSetId: id,
                        ruleSetName: values.name,
                        tab: activeTab as EditTabType,
                        changedFields: getChangedFields(initialFormDataRef.current, values),
                        hasWindows: !!(values.windows && values.windows.length > 0),
                        timestamp: getTimestamp(),
                      };
                      trackEditBeforePreview(beforeData);

                      setCurrentFormData(values);
                      setPreviewModalOpen(true);
                    }}>
                      预览规则效果
                    </Button>
                    <Button onClick={() => {
                      // 埋点：追踪取消操作
                      const cancelData: EditBehaviorData = {
                        ruleSetId: id,
                        ruleSetName: formValues.name,
                        tab: activeTab as EditTabType,
                        timestamp: getTimestamp(),
                      };
                      trackEditCancel(cancelData);
                      history.back();
                    }}>取消</Button>
                    <Button type="primary" onClick={() => {
                      // 埋点：追踪预览后的编辑状态
                      const currentValues = formRef.current?.getFieldsValue();
                      const afterData: EditBehaviorData = {
                        ruleSetId: id,
                        ruleSetName: currentValues.name,
                        tab: activeTab as EditTabType,
                        changedFields: beforePreviewFormDataRef.current
                          ? getChangedFields(beforePreviewFormDataRef.current, currentValues)
                          : [],
                        hasWindows: !!(currentValues.windows && currentValues.windows.length > 0),
                        timestamp: getTimestamp(),
                      };
                      trackEditAfterPreview(afterData);

                      props.form?.submit();
                    }}>
                      {isEdit ? '保存' : '创建'}
                    </Button>
                  </Space>
                </FooterToolbar>
              ),
            }}
          >
            {renderFormContent()}
          </ProForm>

          {/* 实时预览抽屉（小屏幕） */}
          <Drawer
            title="实时预览"
            placement="right"
            width={isMobile ? '90%' : '70%'}
            open={previewDrawerOpen}
            onClose={() => setPreviewDrawerOpen(false)}
            styles={{ body: { padding: 16 } }}
          >
            <RuleSetLivePreview
              formData={formValues}
              shiftTypes={shiftTypes}
            />
          </Drawer>
        </>
      ) : (
        <ResizableDivider
          initialRightWidth={previewWidth}
          minRightWidth={MIN_PREVIEW_WIDTH}
          maxRightWidth={isXxl ? XXL_MAX_PREVIEW_WIDTH : MAX_PREVIEW_WIDTH}
          onWidthChange={setPreviewWidth}
          leftContent={
            <ProForm
              formRef={formRef}
              onFinish={handleSubmit}
              initialValues={initialValues}
              onValuesChange={(changedValues, allValues) => {
                // 实时更新表单值用于预览
                setFormValues(allValues);
              }}
              onTabChange={(key) => {
                // 埋点：追踪 Tab 切换
                const tabData: EditBehaviorData = {
                  ruleSetId: id,
                  ruleSetName: formValues.name,
                  tab: key as EditTabType,
                  changedFields: getChangedFields(initialFormDataRef.current, formValues),
                  hasWindows: !!(formValues.windows && formValues.windows.length > 0),
                  timestamp: getTimestamp(),
                };
                trackEditExitTab(tabData);
                setActiveTab(key);
              }}
              submitter={{
                render: (props, dom) => (
                  <FooterToolbar>
                    <Space>
                      <Button onClick={() => {
                        // 保存预览前的表单状态
                        const values = formRef.current?.getFieldsValue();
                        beforePreviewFormDataRef.current = { ...values };

                        // 埋点：追踪预览前的编辑状态
                        const beforeData: EditBehaviorData = {
                          ruleSetId: id,
                          ruleSetName: values.name,
                          tab: activeTab as EditTabType,
                          changedFields: getChangedFields(initialFormDataRef.current, values),
                          hasWindows: !!(values.windows && values.windows.length > 0),
                          timestamp: getTimestamp(),
                        };
                        trackEditBeforePreview(beforeData);

                        setCurrentFormData(values);
                        setPreviewModalOpen(true);
                      }}>
                        预览规则效果
                      </Button>
                      <Button onClick={() => {
                        // 埋点：追踪取消操作
                        const cancelData: EditBehaviorData = {
                          ruleSetId: id,
                          ruleSetName: formValues.name,
                          tab: activeTab as EditTabType,
                          timestamp: getTimestamp(),
                        };
                        trackEditCancel(cancelData);
                        history.back();
                      }}>取消</Button>
                      <Button type="primary" onClick={() => {
                        // 埋点：追踪预览后的编辑状态
                        const currentValues = formRef.current?.getFieldsValue();
                        const afterData: EditBehaviorData = {
                          ruleSetId: id,
                          ruleSetName: currentValues.name,
                          tab: activeTab as EditTabType,
                          changedFields: beforePreviewFormDataRef.current
                            ? getChangedFields(beforePreviewFormDataRef.current, currentValues)
                            : [],
                          hasWindows: !!(currentValues.windows && currentValues.windows.length > 0),
                          timestamp: getTimestamp(),
                        };
                        trackEditAfterPreview(afterData);

                        props.form?.submit();
                      }}>
                        {isEdit ? '保存' : '创建'}
                      </Button>
                    </Space>
                  </FooterToolbar>
                ),
              }}
            >
              {renderFormContent()}
            </ProForm>
          }
          rightContent={
            <Affix offsetTop={80}>
              <div style={{ maxHeight: 'calc(100vh - 160px)', overflowY: 'auto', paddingLeft: 8 }}>
                <RuleSetLivePreview
                  formData={formValues}
                  shiftTypes={shiftTypes}
                />
              </div>
            </Affix>
          }
        />
      )}

      <RulePreviewModal
        open={previewModalOpen}
        onClose={() => setPreviewModalOpen(false)}
        shiftTypes={shiftTypes}
        ruleSetData={currentFormData}
      />
      </>
      )}

      {/* 预设模板选择弹窗 */}
      <PresetModal
        open={presetModalOpen}
        onClose={() => {
          setPresetModalOpen(false);
          setSelectedPreset(null);
        }}
        onApply={handleApplyPreset}
        selectedPreset={selectedPreset}
        onSelectPreset={setSelectedPreset}
        isMobile={isMobile}
        isTablet={isTablet}
      />
    </PageContainer>
  );
};

export default RuleSetFormPage;
