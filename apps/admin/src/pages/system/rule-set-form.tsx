import { PageContainer, ProForm, ProFormText, ProFormSelect, ProFormDigit, ProFormSwitch, ProFormTextArea, FooterToolbar, ProFormDependency } from '@ant-design/pro-components';
import { Card, App, Button, Space, Row, Col, Tabs, message, Form, Alert, Modal, Radio, Typography, Affix } from 'antd';
import { ThunderboltOutlined } from '@ant-design/icons';

// 侧边栏预览面板宽度
const PREVIEW_SIDEBAR_WIDTH = 400;
import { useEffect, useState, useRef, useMemo } from 'react';
import { history, useParams, useAccess } from '@umijs/max';
import { ruleSetApi, shiftTypeApi } from '@hospital/api';
import type { RuleSet, ShiftType } from '@hospital/shared';
import RuleWindowConfig from '../../components/RuleWindowConfig';
import RulePreviewModal from './components/RulePreviewModal';
import { RuleSetLivePreview, RuleSetSummaryCard } from '@/components/rule-set-visualization';
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
  type RuleSetPreset,
} from '@/constants/rule-set';

const { Text } = Typography;

const RuleSetFormPage: React.FC = () => {
  const { message: antMessage } = App.useApp();
  const { id } = useParams();
  const access = useAccess();
  const isEdit = !!id;
  const [loading, setLoading] = useState(false);
  const [ruleSet, setRuleSet] = useState<RuleSet | null>(null);
  const [shiftTypes, setShiftTypes] = useState<ShiftType[]>([]);
  const [previewModalOpen, setPreviewModalOpen] = useState(false);
  const [currentFormData, setCurrentFormData] = useState<any>(null);
  const [formValues, setFormValues] = useState<Partial<RuleSet>>({});
  const formRef = useRef<any>();

  // 预设模板相关状态
  const [presetModalOpen, setPresetModalOpen] = useState(false);
  const [selectedPreset, setSelectedPreset] = useState<string | null>(null);

  // 应用预设模板
  const handleApplyPreset = (presetId: string) => {
    const preset = RULE_SET_PRESETS.find(p => p.id === presetId);
    if (preset) {
      // 保留用户已选择的班次类型
      const currentShiftTypeIds = formRef.current?.getFieldValue('shiftTypeIds') || [];
      // 深拷贝预设配置以转换为可变类型
      const newValues = JSON.parse(JSON.stringify({
        ...preset.config,
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
    loadShiftTypes();
    if (isEdit) {
      loadRuleSet();
    }
  }, [id]);

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
      antMessage.error('加载规则组失败');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (values: any) => {
    try {
      // 直接使用表单值，不再需要手动合并独立状态
      const data = {
        ...values,
        shiftTypeIds: values.shiftTypeIds || [],
      };

      if (isEdit && id) {
        await ruleSetApi.update(id, data);
        antMessage.success('更新成功');
      } else {
        await ruleSetApi.create(data);
        antMessage.success('创建成功');
      }
      history.push('/system/rule-sets');
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
      setFormValues({
        ...ruleSet,
        shiftTypeIds: ruleSet.shiftTypes?.map((st) => st.id) || [],
      });
    } else {
      setFormValues(RULE_SET_FORM_INITIAL_VALUES);
    }
  }, [ruleSet]);

  // 等待数据加载完成再渲染表单（编辑模式下）
  if (isEdit && loading) {
    return (
      <PageContainer title={isEdit ? '编辑规则组' : '新增规则组'}>
        <Card loading />
      </PageContainer>
    );
  }

  return (
    <PageContainer title={isEdit ? '编辑规则组' : '新增规则组'}>
      {/* 快速配置预设提示（仅新增时显示） */}
      {!isEdit && (
        <Alert
          message="快速开始"
          description={
            <Space>
              <span>选择预设模板可快速配置规则组，节省配置时间</span>
              <Button
                type="primary"
                size="small"
                icon={<ThunderboltOutlined />}
                onClick={() => setPresetModalOpen(true)}
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

      {/* 左右分栏布局：左侧表单，右侧固定预览 */}
      <div style={{ display: 'flex', gap: 24 }}>
        {/* 左侧：表单区域 */}
        <div style={{ flex: 1, minWidth: 0 }}>
          <ProForm
            formRef={formRef}
            onFinish={handleSubmit}
            initialValues={initialValues}
            onValuesChange={(changedValues, allValues) => {
              // 实时更新表单值用于预览
              setFormValues(allValues);
            }}
            submitter={{
              render: (props, dom) => (
                <FooterToolbar>
                  <Space>
                    <Button onClick={() => {
                      // 传入当前表单数据
                      const values = formRef.current?.getFieldsValue();
                      setCurrentFormData(values);
                      setPreviewModalOpen(true);
                    }}>
                      预览规则效果
                    </Button>
                    <Button onClick={() => history.back()}>取消</Button>
                    <Button type="primary" onClick={() => props.form?.submit()}>
                      {isEdit ? '保存' : '创建'}
                    </Button>
                  </Space>
                </FooterToolbar>
              ),
            }}
          >
            <Tabs
              defaultActiveKey="basic"
              items={[
            {
              key: 'basic',
              label: '基础信息',
              children: (
                <Card style={{ marginBottom: 16 }} loading={loading}>
                  <Row gutter={16}>
                    <Col span={12}>
                      <ProFormText
                        name="name"
                        label="规则组名称"
                        width="lg"
                        placeholder="如：门诊预约规则"
                        rules={[{ required: true, message: '请输入规则组名称' }]}
                      />
                    </Col>
                    <Col span={12}>
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
              ),
            },
            {
              key: 'time',
              label: '时间口径',
              children: (
                <Card style={{ marginBottom: 16 }} loading={loading}>
                  {/* 时间与精度配置 */}
                  <Row gutter={[24, 16]} style={{ marginBottom: 16 }}>
                    <Col span={6}>
                      <ProFormSelect
                        name="timeSource"
                        label="时间来源"
                        width="xl"
                        options={TIME_SOURCE_OPTIONS}
                        rules={[{ required: true, message: '请选择时间来源' }]}
                        tooltip="用于判断时间窗的基准时间来源"
                      />
                    </Col>
                    <Col span={6}>
                      <ProFormSelect
                        name="timezoneSource"
                        label="时区来源"
                        width="xl"
                        options={TIMEZONE_SOURCE_OPTIONS}
                        rules={[{ required: true, message: '请选择时区来源' }]}
                        tooltip="用于时间判断的时区基准：医院配置时区使用统一标准时区，班次时区使用班次特定时区，用户时区使用用户所在地时区"
                      />
                    </Col>
                    <Col span={6}>
                      <ProFormSelect
                        name="comparePrecision"
                        label="比较精度"
                        width="xl"
                        options={COMPARE_PRECISION_OPTIONS}
                        rules={[{ required: true, message: '请选择比较精度' }]}
                        tooltip="时间比较的最小单位"
                      />
                    </Col>
                    <Col span={6}>
                      <ProFormSelect
                        name="roundingMode"
                        label="舍入模式"
                        width="xl"
                        options={ROUNDING_MODE_OPTIONS}
                        rules={[{ required: true, message: '请选择舍入模式' }]}
                        tooltip="时间比较时的舍入规则：不舍入使用精确时间，向下/向上取整到分钟可提高比较效率并减少时钟偏差影响"
                      />
                    </Col>
                  </Row>

                  {/* 容差与边界配置 */}
                  <Row gutter={[24, 16]}>
                    <Col span={8}>
                      <ProFormDigit
                        name="clockSkewToleranceSec"
                        label="时钟容差(秒)"
                        width="xl"
                        min={0}
                        max={300}
                        fieldProps={{ precision: 0 }}
                        rules={[{ required: true, message: '请输入时钟容差' }]}
                        tooltip="允许客户端与服务端时间的最大偏差"
                      />
                    </Col>
                    <Col span={8}>
                      <ProFormSwitch
                        name="defaultOpenInclusive"
                        label="默认包含开放边界"
                        tooltip="默认情况下时间窗开放时间是否包含边界"
                      />
                    </Col>
                    <Col span={8}>
                      <ProFormSwitch
                        name="defaultCloseInclusive"
                        label="默认包含截止边界"
                        tooltip="默认情况下时间窗截止时间是否包含边界"
                      />
                    </Col>
                  </Row>
                </Card>
              ),
            },
            {
              key: 'windows',
              label: '时间窗配置',
              children: <RuleWindowConfig />,
            },
            {
              key: 'booking',
              label: '预约策略',
              children: (
                <Card style={{ marginBottom: 16 }} loading={loading}>
                  {/* 预约前置条件 */}
                  <Row gutter={[24, 16]} style={{ marginBottom: 16 }}>
                    <Col span={8}>
                      <ProFormSwitch
                        name={['bookingPolicy', 'requireAuth']}
                        label="需要登录"
                        tooltip="未登录用户无法预约"
                      />
                    </Col>
                    <Col span={8}>
                      <ProFormSwitch
                        name={['bookingPolicy', 'requirePatientProfileComplete']}
                        label="需要完整档案"
                        tooltip="预约前需完善就诊人信息"
                      />
                    </Col>
                  </Row>

                  {/* 限约配置 */}
                  <Row gutter={[24, 16]} style={{ marginBottom: 16 }}>
                    <Col span={8}>
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
                    <Col span={8}>
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
                    <Col span={8}>
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
                    <Col span={8}>
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
                    <Col span={8}>
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
                    <Col span={8}>
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
              ),
            },
            {
              key: 'checkin',
              label: '签到策略',
              children: (
                <Card style={{ marginBottom: 16 }} loading={loading}>
                  {/* 签到前置条件 */}
                  <Row gutter={[24, 16]} style={{ marginBottom: 16 }}>
                    <Col span={8}>
                      <ProFormSwitch
                        name={['checkinPolicy', 'requireBooking']}
                        label="需要预约"
                        tooltip="是否必须先预约才能签到"
                      />
                    </Col>
                    <Col span={8}>
                      <ProFormSwitch
                        name={['checkinPolicy', 'allowOnsiteBooking']}
                        label="允许现场预约"
                        tooltip="允许在签到时现场创建预约"
                      />
                    </Col>
                    <Col span={8}>
                      <ProFormSwitch
                        name={['checkinPolicy', 'auditLog']}
                        label="记录签到日志"
                        tooltip="记录每次签到的详细信息"
                      />
                    </Col>
                  </Row>

                  {/* 签到限制配置 */}
                  <Row gutter={[24, 16]} style={{ marginBottom: 16 }}>
                    <Col span={8}>
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
                    <Col span={8}>
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
                    <Col span={8}>
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
              ),
            },
            {
              key: 'capacity',
              label: '容量策略',
              children: (
                <Card style={{ marginBottom: 16 }} loading={loading}>
                  {/* 基础容量配置 */}
                  <Row gutter={[24, 16]} style={{ marginBottom: 16 }}>
                    <Col span={8}>
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
                    <Col span={8}>
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
                    <Col span={8}>
                      <ProFormSwitch
                        name={['capacityPolicy', 'overbookingEnabled']}
                        label="允许超额预约"
                        tooltip="允许预约数超过总容量"
                      />
                    </Col>
                  </Row>

                  {/* 候补配置 */}
                  <Row gutter={[24, 16]} style={{ marginBottom: 16 }}>
                    <Col span={8}>
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
                            <Col span={8}>
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
                            <Col span={8}>
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
                          <Col span={12}>
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
              ),
            },
          ]}
        />
          </ProForm>
        </div>

        {/* 右侧：固定预览面板 */}
        <div style={{ width: PREVIEW_SIDEBAR_WIDTH, flexShrink: 0 }}>
          <Affix offsetTop={80}>
            <div style={{ maxHeight: 'calc(100vh - 160px)', overflowY: 'auto' }}>
              <RuleSetLivePreview
                formData={formValues}
                shiftTypes={shiftTypes}
              />
            </div>
          </Affix>
        </div>
      </div>

      <RulePreviewModal
        open={previewModalOpen}
        onClose={() => setPreviewModalOpen(false)}
        shiftTypes={shiftTypes}
        ruleSetData={currentFormData}
      />

      {/* 预设模板选择弹窗 */}
      <Modal
        title="选择预设模板"
        open={presetModalOpen}
        onCancel={() => {
          setPresetModalOpen(false);
          setSelectedPreset(null);
        }}
        onOk={() => {
          if (selectedPreset) {
            handleApplyPreset(selectedPreset);
          } else {
            antMessage.warning('请选择一个预设模板');
          }
        }}
        okText="应用模板"
        cancelText="取消"
        width={600}
      >
        <div style={{ marginBottom: 16 }}>
          <Text type="secondary">
            选择一个预设模板，系统将自动填充规则配置。您仍可在应用后进行调整。
          </Text>
        </div>
        <Radio.Group
          value={selectedPreset}
          onChange={(e) => setSelectedPreset(e.target.value)}
          style={{ width: '100%' }}
        >
          <Space direction="vertical" style={{ width: '100%' }}>
            {RULE_SET_PRESETS.map((preset) => (
              <Card
                key={preset.id}
                size="small"
                hoverable
                style={{
                  border: selectedPreset === preset.id ? '2px solid #1890ff' : '1px solid #d9d9d9',
                  backgroundColor: selectedPreset === preset.id ? '#e6f7ff' : undefined,
                }}
                onClick={() => setSelectedPreset(preset.id)}
              >
                <Radio value={preset.id}>
                  <Space direction="vertical" size={0}>
                    <Text strong>{preset.name}</Text>
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      {preset.description}
                    </Text>
                    <Space style={{ marginTop: 4 }}>
                      <Text type="secondary" style={{ fontSize: 11 }}>
                        优先级: {preset.config.priority}
                      </Text>
                      <Text type="secondary" style={{ fontSize: 11 }}>
                        每日限约: {preset.config.bookingPolicy.perUserPerDay || '不限'}
                      </Text>
                      <Text type="secondary" style={{ fontSize: 11 }}>
                        容量: {preset.config.capacityPolicy.totalCapacity || '不限'}
                      </Text>
                    </Space>
                  </Space>
                </Radio>
              </Card>
            ))}
          </Space>
        </Radio.Group>
      </Modal>
    </PageContainer>
  );
};

export default RuleSetFormPage;
