import { Modal, Form, Select, DatePicker, TimePicker, Button, Card, Tag, Statistic, Alert, Space, Row, Col, message, Spin } from 'antd';
import type { RulePreviewResponse, WindowCheckResult, ShiftType, RuleSet } from '@hospital/shared';
import { ruleSetApi } from '@hospital/api';
import { useState, useEffect, useRef } from 'react';
import dayjs from 'dayjs';
import {
  trackModalPreviewOpen,
  trackModalPreviewStart,
  trackModalPreviewSuccess,
  trackModalPreviewFail,
  getTimestamp,
  type ModalPreviewData,
} from '@/utils/analytics';

const { RangePicker } = DatePicker;

interface RulePreviewModalProps {
  open: boolean;
  onClose: () => void;
  shiftTypes: ShiftType[];
  ruleSetData?: Partial<RuleSet>; // 新增：接收当前编辑的规则数据
}

interface PreviewFormData {
  shiftTypeId: string;
  scheduleDate: string;
  startTime: string;
  endTime: string;
  currentTime?: string;
}

/**
 * 窗口结果卡片组件
 */
const WindowResultCard: React.FC<{
  title: string;
  result: WindowCheckResult;
}> = ({ title, result }) => {
  const formatTime = (timeStr: string) => dayjs(timeStr).format('YYYY-MM-DD HH:mm:ss');

  return (
    <Card
      title={
        <Space>
          <span>{title}</span>
          {result.allowed ? (
            <Tag color="success">允许操作</Tag>
          ) : (
            <Tag color="error">不允许操作</Tag>
          )}
        </Space>
      }
      size="small"
    >
      {result.allowed ? (
        <Space direction="vertical" style={{ width: '100%' }}>
          <Row gutter={16}>
            <Col span={12}>
              <Statistic title="开放时间" value={formatTime(result.openAt)} valueStyle={{ fontSize: 14 }} />
            </Col>
            <Col span={12}>
              <Statistic title="截止时间" value={formatTime(result.closeAt)} valueStyle={{ fontSize: 14 }} />
            </Col>
          </Row>
          <Statistic
            title="当前时间"
            value={formatTime(result.currentTime)}
            valueStyle={{ fontSize: 14 }}
          />
        </Space>
      ) : (
        <Alert
          type="error"
          message={result.message}
          description={
            <div style={{ marginTop: 8 }}>
              <p>开放时间: {formatTime(result.openAt)}</p>
              <p>截止时间: {formatTime(result.closeAt)}</p>
              <p>当前时间: {formatTime(result.currentTime)}</p>
              {result.failTag && (
                <p>
                  标签: <Tag color="warning">{result.failTag}</Tag>
                </p>
              )}
              {result.fail_policy && <p>失败策略: {result.fail_policy}</p>}
            </div>
          }
        />
      )}
    </Card>
  );
};

/**
 * 规则预览Modal组件
 */
const RulePreviewModal: React.FC<RulePreviewModalProps> = ({
  open,
  onClose,
  shiftTypes,
  ruleSetData // 新增参数
}) => {
  const [form] = Form.useForm<PreviewFormData>();
  const [loading, setLoading] = useState(false);
  const [previewResult, setPreviewResult] = useState<RulePreviewResponse | null>(null);

  // 埋点：记录预览开始时间
  const previewStartTimeRef = useRef<number>(0);

  // 当打开 Modal 时，智能设置默认值并埋点
  useEffect(() => {
    if (open) {
      form.setFieldsValue({
        scheduleDate: dayjs(),
        // 如果传入了规则数据，尝试设置第一个班次类型
        shiftTypeId: ruleSetData?.shiftTypeIds?.[0] || undefined,
        startTime: dayjs('08:00:00', 'HH:mm:ss'),
        endTime: dayjs('12:00:00', 'HH:mm:ss'),
      });

      // 埋点：追踪 Modal 打开
      const data: ModalPreviewData = {
        ruleSetId: ruleSetData?.id,
        ruleSetName: ruleSetData?.name,
        timestamp: getTimestamp(),
      };
      trackModalPreviewOpen(data);
    }
  }, [open, ruleSetData, form]);

  const handlePreview = async () => {
    try {
      const values = await form.validateFields();
      setLoading(true);
      previewStartTimeRef.current = Date.now();

      // 埋点：追踪预览开始
      const startData: ModalPreviewData = {
        ruleSetId: ruleSetData?.id,
        ruleSetName: ruleSetData?.name,
        shiftTypeId: values.shiftTypeId,
        scheduleDate: dayjs(values.scheduleDate).format('YYYY-MM-DD'),
        hasCurrentTime: !!values.currentTime,
        timestamp: getTimestamp(),
      };
      trackModalPreviewStart(startData);

      const result = await ruleSetApi.preview({
        shiftTypeId: values.shiftTypeId,
        scheduleDate: dayjs(values.scheduleDate).format('YYYY-MM-DD'),
        startTime: dayjs(values.startTime).format('HH:mm:ss'),
        endTime: dayjs(values.endTime).format('HH:mm:ss'),
        currentTime: values.currentTime ? dayjs(values.currentTime).toISOString() : undefined,
      });

      setPreviewResult(result);
      message.success('预览成功');

      // 埋点：追踪预览成功
      const previewDuration = Date.now() - previewStartTimeRef.current;
      const successData: ModalPreviewData = {
        ruleSetId: ruleSetData?.id,
        ruleSetName: ruleSetData?.name,
        previewDuration,
        timestamp: getTimestamp(),
      };
      trackModalPreviewSuccess(successData);
    } catch (error: any) {
      message.error(error.message || '预览失败');

      // 埋点：追踪预览失败
      const failData: ModalPreviewData & { error?: string } = {
        ruleSetId: ruleSetData?.id,
        ruleSetName: ruleSetData?.name,
        error: error.message || '未知错误',
        timestamp: getTimestamp(),
      };
      trackModalPreviewFail(failData);
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    setPreviewResult(null);
    form.resetFields();
    onClose();
  };

  return (
    <Modal
      title="规则效果预览"
      open={open}
      onCancel={handleClose}
      footer={null}
      width={800}
      destroyOnHidden
    >
      <Form
        form={form}
        layout="vertical"
        initialValues={{
          scheduleDate: dayjs(),
        }}
      >
        <Form.Item
          label="班次类型"
          name="shiftTypeId"
          rules={[{ required: true, message: '请选择班次类型' }]}
        >
          <Select
            placeholder="请选择班次类型"
            options={shiftTypes.map((st) => ({ label: st.name, value: st.id }))}
          />
        </Form.Item>

        <Row gutter={16}>
          <Col span={24}>
            <Form.Item
              label="排班日期"
              name="scheduleDate"
              rules={[{ required: true, message: '请选择排班日期' }]}
            >
              <DatePicker style={{ width: '100%' }} />
            </Form.Item>
          </Col>
        </Row>

        <Row gutter={16}>
          <Col span={12}>
            <Form.Item
              label="开始时间"
              name="startTime"
              rules={[{ required: true, message: '请选择开始时间' }]}
            >
              <TimePicker style={{ width: '100%' }} format="HH:mm:ss" />
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item
              label="结束时间"
              name="endTime"
              rules={[{ required: true, message: '请选择结束时间' }]}
            >
              <TimePicker style={{ width: '100%' }} format="HH:mm:ss" />
            </Form.Item>
          </Col>
        </Row>

        <Form.Item label="当前时间（可选，默认使用服务端时间）" name="currentTime">
          <DatePicker
            showTime
            format="YYYY-MM-DD HH:mm:ss"
            style={{ width: '100%' }}
          />
        </Form.Item>

        <Form.Item>
          <Button type="primary" onClick={handlePreview} loading={loading} block>
            开始预览
          </Button>
        </Form.Item>
      </Form>

      {previewResult && (
        <Spin spinning={loading}>
          <Space direction="vertical" style={{ width: '100%', marginTop: 16 }} size="middle">
            <WindowResultCard title="预约窗口" result={previewResult.bookWindow} />
            <WindowResultCard title="签到窗口" result={previewResult.checkinWindow} />
            <WindowResultCard title="取消窗口" result={previewResult.cancelWindow} />
          </Space>
        </Spin>
      )}
    </Modal>
  );
};

export default RulePreviewModal;
