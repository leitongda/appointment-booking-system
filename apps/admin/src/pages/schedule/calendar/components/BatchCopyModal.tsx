import { Modal, Button, Steps, Form, DatePicker, Select, Checkbox, Radio, Alert, Space, Tag, App } from 'antd';
import { useState, useEffect, useMemo } from 'react';
import type { Dayjs } from 'dayjs';
import { scheduleApi, doctorApi } from '@hospital/api';
import { fetchAllData } from '@/utils/fetchAllData';
import type { Doctor } from '@hospital/shared';

interface BatchCopyModalProps {
  open: boolean;
  onClose: () => void;
  onSuccess: () => void;
  doctorId?: string;
}

interface FormValues {
  sourceRange: [Dayjs, Dayjs];
  targetRange: [Dayjs, Dayjs];
  doctorIds?: string[];
  copyContent: string[];
  conflictStrategy: 'skip' | 'overwrite' | 'manual';
  skipHolidays: boolean;
}

const { RangePicker } = DatePicker;

const COPY_CONTENT_OPTIONS = [
  { label: '号源配置', value: 'quota' },
  { label: '诊室', value: 'room' },
  { label: '挂号费', value: 'fee' },
];

const CONFLICT_STRATEGY_OPTIONS = [
  { label: '跳过', value: 'skip' },
  { label: '覆盖', value: 'overwrite' },
  { label: '手动处理', value: 'manual' },
];

const STEPS = [
  { title: '源周期' },
  { title: '目标周期' },
  { title: '复制对象' },
  { title: '复制内容' },
  { title: '冲突策略' },
  { title: '确认' },
];

const BatchCopyModal: React.FC<BatchCopyModalProps> = ({
  open,
  onClose,
  onSuccess,
  doctorId,
}) => {
  const { message } = App.useApp();
  const [form] = Form.useForm<FormValues>();
  const [currentStep, setCurrentStep] = useState(0);
  const [loading, setLoading] = useState(false);
  const [doctors, setDoctors] = useState<Doctor[]>([]);
  const [doctorsLoading, setDoctorsLoading] = useState(false);

  // 加载医生列表
  useEffect(() => {
    if (!open) return;
    setDoctorsLoading(true);
    fetchAllData((page, pageSize) =>
      doctorApi.getList({ page, pageSize, status: 1 })
    )
      .then(setDoctors)
      .catch(() => {
        console.error('加载医生列表失败');
      })
      .finally(() => setDoctorsLoading(false));
  }, [open]);

  // 初始化表单默认值
  useEffect(() => {
    if (open) {
      setCurrentStep(0);
      form.setFieldsValue({
        copyContent: ['quota', 'room', 'fee'],
        conflictStrategy: 'skip',
        skipHolidays: true,
        ...(doctorId ? { doctorIds: [doctorId] } : {}),
      });
    }
  }, [open, doctorId, form]);

  // 源周期变化时自动计算默认目标周期
  const handleSourceRangeChange = (dates: [Dayjs | null, Dayjs | null] | null) => {
    if (dates && dates[0] && dates[1]) {
      const days = dates[1].diff(dates[0], 'day') + 1;
      const targetStart = dates[1].add(1, 'day');
      const targetEnd = targetStart.add(days - 1, 'day');
      form.setFieldsValue({
        targetRange: [targetStart, targetEnd],
      });
    } else {
      form.setFieldsValue({ targetRange: undefined });
    }
  };

  // 获取当前步骤的表单字段名
  const stepFields: string[][] = [
    ['sourceRange'],
    ['targetRange'],
    ['doctorIds'],
    ['copyContent'],
    ['conflictStrategy', 'skipHolidays'],
    [],
  ];

  // 步骤导航
  const handleNext = async () => {
    try {
      await form.validateFields(stepFields[currentStep]);
      setCurrentStep((prev) => Math.min(prev + 1, STEPS.length - 1));
    } catch {
      // 验证失败，不跳转
    }
  };

  const handlePrev = () => {
    setCurrentStep((prev) => Math.max(prev - 1, 0));
  };

  // 计算天数和排班数摘要
  const summary = useMemo(() => {
    const values = form.getFieldsValue(true);
    const sourceRange = values.sourceRange;
    const targetRange = values.targetRange;
    const days = sourceRange && sourceRange[0] && sourceRange[1]
      ? sourceRange[1].diff(sourceRange[0], 'day') + 1
      : 0;
    const targetDays = targetRange && targetRange[0] && targetRange[1]
      ? targetRange[1].diff(targetRange[0], 'day') + 1
      : 0;
    return { days, targetDays };
  }, [form, currentStep]);

  // 提交
  const handleSubmit = async () => {
    const values = form.getFieldsValue(true);
    setLoading(true);
    try {
      await scheduleApi.copySchedules({
        sourceStartDate: values.sourceRange[0].format('YYYY-MM-DD'),
        sourceEndDate: values.sourceRange[1].format('YYYY-MM-DD'),
        targetStartDate: values.targetRange[0].format('YYYY-MM-DD'),
        targetEndDate: values.targetRange[1].format('YYYY-MM-DD'),
        doctorIds: values.doctorIds?.length ? values.doctorIds : undefined,
        copyQuota: values.copyContent.includes('quota'),
        copyRoom: values.copyContent.includes('room'),
        copyFee: values.copyContent.includes('fee'),
        skipHolidays: values.skipHolidays,
        conflictStrategy: values.conflictStrategy,
      });
      message.success('批量复制排班成功');
      onSuccess();
      onClose();
    } catch (error: any) {
      message.error(error?.message || '批量复制排班失败');
    } finally {
      setLoading(false);
    }
  };

  // 渲染步骤内容
  const renderStepContent = () => {
    const values = form.getFieldsValue(true);

    switch (currentStep) {
      case 0:
        return (
          <Form.Item
            name="sourceRange"
            label="源排班周期"
            rules={[{ required: true, message: '请选择源排班周期' }]}
          >
            <RangePicker
              style={{ width: '100%' }}
              placeholder={['开始日期', '结束日期']}
              onChange={handleSourceRangeChange}
            />
          </Form.Item>
        );

      case 1:
        return (
          <Form.Item
            name="targetRange"
            label="目标排班周期"
            rules={[{ required: true, message: '请选择目标排班周期' }]}
          >
            <RangePicker
              style={{ width: '100%' }}
              placeholder={['开始日期', '结束日期']}
            />
          </Form.Item>
        );

      case 2:
        return (
          <Form.Item name="doctorIds" label="选择医生（留空则复制全部）">
            <Select
              mode="multiple"
              placeholder="请选择医生"
              allowClear
              showSearch
              optionFilterProp="label"
              loading={doctorsLoading}
              maxTagCount="responsive"
              options={doctors.map((d) => ({
                label: `${d.name} - ${d.title || ''} - ${d.departmentName || ''}`,
                value: d.id,
              }))}
            />
          </Form.Item>
        );

      case 3:
        return (
          <Form.Item
            name="copyContent"
            label="复制内容"
            rules={[{ required: true, message: '请选择至少一项复制内容' }]}
          >
            <Checkbox.Group options={COPY_CONTENT_OPTIONS} />
          </Form.Item>
        );

      case 4:
        return (
          <>
            <Form.Item
              name="conflictStrategy"
              label="冲突处理策略"
              rules={[{ required: true, message: '请选择冲突处理策略' }]}
            >
              <Radio.Group options={CONFLICT_STRATEGY_OPTIONS} />
            </Form.Item>
            <Form.Item name="skipHolidays" valuePropName="checked">
              <Checkbox>跳过法定节假日</Checkbox>
            </Form.Item>
          </>
        );

      case 5:
        return (
          <div className="batch-copy-summary">
            <div className="summary-item">
              <span className="summary-label">源周期：</span>
              <span>
                {values.sourceRange?.[0]?.format('YYYY-MM-DD')} ~ {values.sourceRange?.[1]?.format('YYYY-MM-DD')}
                <Tag style={{ marginLeft: 8 }}>{summary.days} 天</Tag>
              </span>
            </div>
            <div className="summary-item">
              <span className="summary-label">目标周期：</span>
              <span>
                {values.targetRange?.[0]?.format('YYYY-MM-DD')} ~ {values.targetRange?.[1]?.format('YYYY-MM-DD')}
                <Tag style={{ marginLeft: 8 }}>{summary.targetDays} 天</Tag>
              </span>
            </div>
            <div className="summary-item">
              <span className="summary-label">医生：</span>
              <span>
                {values.doctorIds?.length
                  ? doctors
                      .filter((d) => values.doctorIds.includes(d.id))
                      .map((d) => d.name)
                      .join('、')
                  : '全部医生'}
              </span>
            </div>
            <div className="summary-item">
              <span className="summary-label">复制内容：</span>
              <span>
                {values.copyContent
                  ?.map((v: string) => COPY_CONTENT_OPTIONS.find((o) => o.value === v)?.label)
                  .filter(Boolean)
                  .join('、') || '-'}
              </span>
            </div>
            <div className="summary-item">
              <span className="summary-label">冲突策略：</span>
              <span>
                {CONFLICT_STRATEGY_OPTIONS.find((o) => o.value === values.conflictStrategy)?.label || '-'}
              </span>
            </div>
            <div className="summary-item">
              <span className="summary-label">跳过节假日：</span>
              <span>{values.skipHolidays ? '是' : '否'}</span>
            </div>
            <Alert
              message="确认后将立即执行批量复制操作，请仔细核对以上信息。"
              type="warning"
              showIcon
              style={{ marginTop: 16 }}
            />
          </div>
        );

      default:
        return null;
    }
  };

  // 底部按钮
  const renderFooter = () => {
    if (currentStep === STEPS.length - 1) {
      return (
        <Space>
          <Button onClick={onClose}>取消</Button>
          <Button onClick={handlePrev}>上一步</Button>
          <Button type="primary" onClick={handleSubmit} loading={loading}>
            确认复制
          </Button>
        </Space>
      );
    }
    return (
      <Space>
        <Button onClick={onClose}>取消</Button>
        {currentStep > 0 && (
          <Button onClick={handlePrev}>上一步</Button>
        )}
        <Button type="primary" onClick={handleNext}>下一步</Button>
      </Space>
    );
  };

  return (
    <Modal
      title="批量复制排班"
      open={open}
      onCancel={onClose}
      width={640}
      footer={renderFooter()}
      destroyOnHidden
      className="batch-copy-modal"
    >
      <Steps
        current={currentStep}
        items={STEPS}
        size="small"
        style={{ marginBottom: 24 }}
      />
      <Form
        form={form}
        layout="vertical"
        style={{ minHeight: 300 }}
      >
        {renderStepContent()}
      </Form>
    </Modal>
  );
};

export default BatchCopyModal;
