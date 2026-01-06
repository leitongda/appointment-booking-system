import { PageContainer, ProForm, ProFormText, ProFormSelect, ProFormDigit, ProFormSwitch, ProFormTextArea, FooterToolbar } from '@ant-design/pro-components';
import { Card, App, Button, Space, Row, Col, Tabs, message } from 'antd';
import { useEffect, useState, useRef } from 'react';
import { history, useParams, useAccess } from '@umijs/max';
import { ruleSetApi, shiftTypeApi } from '@hospital/api';
import type { RuleSet, ShiftType } from '@hospital/shared';
import RuleWindowConfig from '../../components/RuleWindowConfig';
import RulePreviewModal from './components/RulePreviewModal';
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
} from '@/constants/rule-set';

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
  const formRef = useRef<any>();

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

  return (
    <PageContainer title={isEdit ? '编辑规则组' : '新增规则组'}>
      <ProForm
        formRef={formRef}
        onFinish={handleSubmit}
        initialValues={initialValues}
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
                  <Row gutter={16}>
                    <Col span={12}>
                      <ProFormSelect
                        name="timeSource"
                        label="时间来源"
                        width="md"
                        options={TIME_SOURCE_OPTIONS}
                        rules={[{ required: true, message: '请选择时间来源' }]}
                        extra="用于判断时间窗的基准时间来源"
                      />
                    </Col>
                    <Col span={12}>
                      <ProFormSelect
                        name="timezoneSource"
                        label="时区来源"
                        width="md"
                        options={TIMEZONE_SOURCE_OPTIONS}
                        rules={[{ required: true, message: '请选择时区来源' }]}
                      />
                    </Col>
                  </Row>

                  <Row gutter={16}>
                    <Col span={8}>
                      <ProFormSelect
                        name="comparePrecision"
                        label="比较精度"
                        width="md"
                        options={COMPARE_PRECISION_OPTIONS}
                        rules={[{ required: true, message: '请选择比较精度' }]}
                      />
                    </Col>
                    <Col span={8}>
                      <ProFormSelect
                        name="roundingMode"
                        label="舍入模式"
                        width="md"
                        options={ROUNDING_MODE_OPTIONS}
                        rules={[{ required: true, message: '请选择舍入模式' }]}
                      />
                    </Col>
                    <Col span={8}>
                      <ProFormDigit
                        name="clockSkewToleranceSec"
                        label="时钟容差(秒)"
                        width="md"
                        min={0}
                        max={300}
                        fieldProps={{ precision: 0 }}
                        rules={[{ required: true, message: '请输入时钟容差' }]}
                        extra="允许客户端与服务端时间的最大偏差"
                      />
                    </Col>
                  </Row>

                  <Row gutter={16}>
                    <Col span={12}>
                      <ProFormSwitch
                        name="defaultOpenInclusive"
                        label="默认包含开放边界"
                        extra="默认情况下时间窗开放时间是否包含边界"
                      />
                    </Col>
                    <Col span={12}>
                      <ProFormSwitch
                        name="defaultCloseInclusive"
                        label="默认包含截止边界"
                        extra="默认情况下时间窗截止时间是否包含边界"
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
                  <Row gutter={16}>
                    <Col span={8}>
                      <ProFormSwitch
                        name={['bookingPolicy', 'requireAuth']}
                        label="需要登录"
                        extra="未登录用户无法预约"
                      />
                    </Col>
                    <Col span={8}>
                      <ProFormSwitch
                        name={['bookingPolicy', 'requirePatientProfileComplete']}
                        label="需要完整档案"
                        extra="预约前需完善就诊人信息"
                      />
                    </Col>
                    <Col span={8}>
                      {/* 占位，保持布局对齐 */}
                    </Col>
                  </Row>

                  <Row gutter={16}>
                    <Col span={8}>
                      <ProFormDigit
                        name={['bookingPolicy', 'perUserPerShift']}
                        label="每班次限约数"
                        min={1}
                        max={100}
                        fieldProps={{ precision: 0 }}
                        rules={[{ required: true, message: '请输入限约数' }]}
                        extra="同一用户在同一班次的预约上限"
                      />
                    </Col>
                    <Col span={8}>
                      <ProFormDigit
                        name={['bookingPolicy', 'perUserPerDay']}
                        label="每日限约数"
                        min={0}
                        max={100}
                        fieldProps={{ precision: 0 }}
                        extra="0表示不限制"
                      />
                    </Col>
                    <Col span={8}>
                      <ProFormDigit
                        name={['bookingPolicy', 'perUserPerWeek']}
                        label="每周限约数"
                        min={0}
                        max={500}
                        fieldProps={{ precision: 0 }}
                        extra="0表示不限制"
                      />
                    </Col>
                  </Row>

                  <Row gutter={16}>
                    <Col span={8}>
                      <ProFormSelect
                        name={['bookingPolicy', 'conflictSameShift']}
                        label="同班次冲突策略"
                        options={CONFLICT_STRATEGY_OPTIONS.filter(opt =>
                          opt.value === 'REJECT' || opt.value === 'REPLACE'
                        )}
                        rules={[{ required: true, message: '请选择冲突策略' }]}
                      />
                    </Col>
                    <Col span={8}>
                      <ProFormSelect
                        name={['bookingPolicy', 'conflictOverlapTime']}
                        label="时间重叠策略"
                        options={CONFLICT_STRATEGY_OPTIONS.filter(opt =>
                          opt.value === 'REJECT' || opt.value === 'ALLOW'
                        )}
                        rules={[{ required: true, message: '请选择重叠策略' }]}
                      />
                    </Col>
                    <Col span={8}>
                      <ProFormSelect
                        name={['bookingPolicy', 'conflictSameTypeSameDay']}
                        label="同类型同日策略"
                        options={CONFLICT_STRATEGY_OPTIONS.filter(opt =>
                          opt.value === 'REJECT' || opt.value === 'ALLOW'
                        )}
                        rules={[{ required: true, message: '请选择策略' }]}
                        extra="同一类型预约在同一天的限制"
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
                  <Row gutter={16}>
                    <Col span={8}>
                      <ProFormSwitch
                        name={['checkinPolicy', 'requireBooking']}
                        label="需要预约"
                        extra="是否必须先预约才能签到"
                      />
                    </Col>
                    <Col span={8}>
                      <ProFormSwitch
                        name={['checkinPolicy', 'allowOnsiteBooking']}
                        label="允许现场预约"
                      />
                    </Col>
                    <Col span={8}>
                      <ProFormSwitch
                        name={['checkinPolicy', 'auditLog']}
                        label="记录签到日志"
                      />
                    </Col>
                  </Row>

                  <Row gutter={16}>
                    <Col span={8}>
                      <ProFormDigit
                        name={['checkinPolicy', 'maxTimes']}
                        label="最大签到次数"
                        min={1}
                        max={10}
                        fieldProps={{ precision: 0 }}
                        rules={[{ required: true, message: '请输入最大次数' }]}
                        extra="同一预约最多允许签到的次数"
                      />
                    </Col>
                    <Col span={8}>
                      <ProFormDigit
                        name={['checkinPolicy', 'gracePeriodSec']}
                        label="宽限期(秒)"
                        min={0}
                        max={3600}
                        fieldProps={{ precision: 0 }}
                        rules={[{ required: true, message: '请输入宽限期' }]}
                        extra="迟到后的宽限时间，默认15分钟"
                      />
                    </Col>
                    <Col span={8}>
                      <ProFormSelect
                        name={['checkinPolicy', 'afterGraceStatus']}
                        label="宽限期后状态"
                        options={AFTER_GRACE_STATUS_OPTIONS}
                        extra="宽限期结束后的状态标记"
                      />
                    </Col>
                  </Row>

                  <ProFormSelect
                    name={['checkinPolicy', 'noCheckinAfterClose']}
                    label="超时未签到处理"
                    options={NO_CHECKIN_AFTER_CLOSE_OPTIONS}
                    rules={[{ required: true, message: '请选择处理方式' }]}
                    extra="签到窗口关闭后仍未签到的处理方式"
                  />
                </Card>
              ),
            },
            {
              key: 'capacity',
              label: '容量策略',
              children: (
                <Card style={{ marginBottom: 16 }} loading={loading}>
                  <Row gutter={16}>
                    <Col span={12}>
                      <ProFormDigit
                        name={['capacityPolicy', 'totalCapacity']}
                        label="总容量"
                        min={1}
                        max={1000}
                        fieldProps={{ precision: 0 }}
                        rules={[{ required: true, message: '请输入总容量' }]}
                        extra="班次的总预约容量"
                      />
                    </Col>
                    <Col span={12}>
                      <ProFormDigit
                        name={['capacityPolicy', 'perUserCapacity']}
                        label="每人限约数"
                        min={1}
                        max={50}
                        fieldProps={{ precision: 0 }}
                        rules={[{ required: true, message: '请输入限约数' }]}
                        extra="每个用户最多可预约的数量"
                      />
                    </Col>
                  </Row>

                  <Row gutter={16}>
                    <Col span={8}>
                      <ProFormSwitch
                        name={['capacityPolicy', 'waitlistEnabled']}
                        label="启用候补"
                      />
                    </Col>
                    <Col span={8}>
                      <ProFormDigit
                        name={['capacityPolicy', 'waitlistMaxSize']}
                        label="候补队列大小"
                        min={1}
                        max={100}
                        fieldProps={{ precision: 0 }}
                        rules={[{ required: true, message: '请输入队列大小' }]}
                        tooltip={{
                          title: '仅在启用候补时生效',
                          placement: 'top',
                        }}
                      />
                    </Col>
                    <Col span={8}>
                      <ProFormSelect
                        name={['capacityPolicy', 'waitlistPromotePolicy']}
                        label="候补递补策略"
                        options={WAITLIST_PROMOTE_POLICY_OPTIONS}
                        tooltip={{
                          title: '仅在启用候补时生效',
                          placement: 'top',
                        }}
                      />
                    </Col>
                  </Row>

                  <Row gutter={16}>
                    <Col span={12}>
                      <ProFormSwitch
                        name={['capacityPolicy', 'overbookingEnabled']}
                        label="允许超额预约"
                      />
                    </Col>
                    <Col span={12}>
                      <ProFormDigit
                        name={['capacityPolicy', 'overbookingMax']}
                        label="最大超额数"
                        min={1}
                        max={100}
                        fieldProps={{ precision: 0 }}
                        rules={[{ required: true, message: '请输入超额数' }]}
                        extra="允许超过总容量的最大数量"
                        tooltip={{
                          title: '仅在允许超额预约时生效',
                          placement: 'top',
                        }}
                      />
                    </Col>
                  </Row>
                </Card>
              ),
            },
          ]}
        />
      </ProForm>

      <RulePreviewModal
        open={previewModalOpen}
        onClose={() => setPreviewModalOpen(false)}
        shiftTypes={shiftTypes}
        ruleSetData={currentFormData}
      />
    </PageContainer>
  );
};

export default RuleSetFormPage;
