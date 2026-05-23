import { NavBar, Form, Input, TextArea, Selector, DatePicker, Toast, Skeleton } from 'antd-mobile';
import { history, useParams } from 'umi';
import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { followUpApi, selfReportApi } from '@hospital/api';
import type { FollowUpTask } from '@hospital/api';
import { Card, Button, SectionLabel } from '@/components/ui';
import { fadeInUp, stagger } from '@/components/ui/animations';

const CONDITION_OPTIONS = [
  { label: '好转', value: 'improved' },
  { label: '稳定', value: 'stable' },
  { label: '加重', value: 'worsened' },
];

const SYMPTOM_PRESETS = [
  { label: '头痛', value: '头痛' },
  { label: '头晕', value: '头晕' },
  { label: '恶心', value: '恶心' },
  { label: '乏力', value: '乏力' },
  { label: '胸闷', value: '胸闷' },
  { label: '失眠', value: '失眠' },
  { label: '心悸', value: '心悸' },
  { label: '咳嗽', value: '咳嗽' },
];

const SelfReportPage: React.FC = () => {
  const { taskId } = useParams() as { taskId?: string };
  const [form] = Form.useForm();
  const [submitting, setSubmitting] = useState(false);
  const [task, setTask] = useState<FollowUpTask | null>(null);
  const [loading, setLoading] = useState(!!taskId);
  const [selectedSymptoms, setSelectedSymptoms] = useState<string[]>([]);
  const [reportDate, setReportDate] = useState<Date>(new Date());
  const [datePickerVisible, setDatePickerVisible] = useState(false);

  useEffect(() => {
    if (taskId) loadTask();
  }, [taskId]);

  const loadTask = async () => {
    try {
      const data = await followUpApi.getTaskDetail(taskId!);
      setTask(data);
    } catch (error: any) {
      Toast.show({ content: error.message || '加载任务失败', icon: 'fail' });
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async () => {
    try {
      const values = form.getFieldsValue();
      const hasVitals = values.systolicBp || values.diastolicBp || values.bloodGlucose || values.heartRate || values.temperature;
      const hasSymptoms = selectedSymptoms.length > 0 || values.symptomDetail;
      const hasCondition = values.patientCondition?.length > 0;

      if (!hasVitals && !hasSymptoms && !hasCondition) {
        Toast.show({ content: '请至少填写一项数据', icon: 'fail' });
        return;
      }

      // 验证血压成对
      if ((values.systolicBp && !values.diastolicBp) || (!values.systolicBp && values.diastolicBp)) {
        Toast.show({ content: '收缩压和舒张压需同时填写', icon: 'fail' });
        return;
      }

      setSubmitting(true);

      // 组合症状文本
      const symptoms = [...selectedSymptoms, values.symptomDetail].filter(Boolean).join('；');

      await selfReportApi.create({
        taskId: taskId || undefined,
        reportDate: reportDate.toISOString(),
        systolicBp: values.systolicBp ? Number(values.systolicBp) : undefined,
        diastolicBp: values.diastolicBp ? Number(values.diastolicBp) : undefined,
        bloodGlucose: values.bloodGlucose ? Number(values.bloodGlucose) : undefined,
        heartRate: values.heartRate ? Number(values.heartRate) : undefined,
        temperature: values.temperature ? Number(values.temperature) : undefined,
        symptoms: symptoms || undefined,
        patientCondition: values.patientCondition?.[0] || undefined,
        notes: values.notes || undefined,
      });

      Toast.show({ content: '提交成功', icon: 'success' });
      setTimeout(() => history.back(), 1000);
    } catch (error: any) {
      Toast.show({ content: error.message || '提交失败', icon: 'fail' });
    } finally {
      setSubmitting(false);
    }
  };

  const formatDisplayDate = (d: Date) => {
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-background">
        <NavBar onBack={() => history.back()} className="!bg-card border-b border-border">
          提交自报告
        </NavBar>
        <div className="p-4">
          <Skeleton.Paragraph lineCount={8} animated />
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background pb-24">
      <NavBar onBack={() => history.back()} className="!bg-card border-b border-border">
        提交自报告
      </NavBar>

      <motion.div className="p-4 space-y-4" variants={stagger} initial="hidden" animate="visible">
        {/* 任务信息（如果有） */}
        {task && (
          <motion.div variants={fadeInUp}>
            <Card variant="default" padding="md" animated={false}>
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-foreground">
                    {task.planName || '随访任务'}
                    {task.stepOrder != null && ` · 第${task.stepOrder}步`}
                  </p>
                  <p className="text-xs text-muted-foreground mt-1">
                    {task.doctorName || ''} · {task.departmentName || ''}
                  </p>
                </div>
              </div>
            </Card>
          </motion.div>
        )}

        <Form form={form} layout="horizontal">
          {/* 测量时间 */}
          <motion.div variants={fadeInUp}>
            <SectionLabel>测量时间</SectionLabel>
            <Card variant="default" padding="none" animated={false}>
              <div
                className="px-4 py-3 flex justify-between items-center cursor-pointer"
                onClick={() => setDatePickerVisible(true)}
              >
                <span className="text-sm text-muted-foreground">测量时间</span>
                <span className="text-sm text-foreground">{formatDisplayDate(reportDate)}</span>
              </div>
            </Card>
            <DatePicker
              visible={datePickerVisible}
              onClose={() => setDatePickerVisible(false)}
              precision="minute"
              value={reportDate}
              onConfirm={(val) => setReportDate(val)}
              max={new Date()}
            />
          </motion.div>

          {/* 体征数据 */}
          <motion.div variants={fadeInUp}>
            <SectionLabel>体征数据</SectionLabel>
            <Card variant="default" padding="none" animated={false}>
              <div className="px-4 py-3">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-sm text-muted-foreground w-16">血压</span>
                  <Form.Item name="systolicBp" noStyle>
                    <Input type="number" placeholder="收缩压" className="flex-1" />
                  </Form.Item>
                  <span className="text-muted-foreground">/</span>
                  <Form.Item name="diastolicBp" noStyle>
                    <Input type="number" placeholder="舒张压" className="flex-1" />
                  </Form.Item>
                  <span className="text-xs text-muted-foreground">mmHg</span>
                </div>
              </div>
              <div className="px-4 py-3 border-t border-border">
                <div className="flex items-center gap-2">
                  <span className="text-sm text-muted-foreground w-16">血糖</span>
                  <Form.Item name="bloodGlucose" noStyle>
                    <Input type="digit" placeholder="空腹血糖" className="flex-1" />
                  </Form.Item>
                  <span className="text-xs text-muted-foreground">mmol/L</span>
                </div>
              </div>
              <div className="px-4 py-3 border-t border-border">
                <div className="flex items-center gap-2">
                  <span className="text-sm text-muted-foreground w-16">心率</span>
                  <Form.Item name="heartRate" noStyle>
                    <Input type="number" placeholder="心率" className="flex-1" />
                  </Form.Item>
                  <span className="text-xs text-muted-foreground">次/分</span>
                </div>
              </div>
              <div className="px-4 py-3 border-t border-border">
                <div className="flex items-center gap-2">
                  <span className="text-sm text-muted-foreground w-16">体温</span>
                  <Form.Item name="temperature" noStyle>
                    <Input type="digit" placeholder="体温" className="flex-1" />
                  </Form.Item>
                  <span className="text-xs text-muted-foreground">°C</span>
                </div>
              </div>
            </Card>
          </motion.div>

          {/* 症状 */}
          <motion.div variants={fadeInUp}>
            <SectionLabel>症状描述</SectionLabel>
            <Card variant="default" padding="md" animated={false}>
              <p className="text-sm text-muted-foreground mb-3">选择症状（可多选）</p>
              <Selector
                multiple
                options={SYMPTOM_PRESETS}
                value={selectedSymptoms}
                onChange={setSelectedSymptoms}
                style={{
                  '--border-radius': '16px',
                  '--border': '1px solid #e5e7eb',
                  '--checked-border': '1px solid #0052FF',
                  '--checked-color': '#EBF1FF',
                  '--checked-text-color': '#0052FF',
                } as React.CSSProperties}
              />
              <Form.Item name="symptomDetail" className="mt-3">
                <TextArea placeholder="补充描述症状（选填）" rows={3} maxLength={300} showCount />
              </Form.Item>
            </Card>
          </motion.div>

          {/* 自我感受 */}
          <motion.div variants={fadeInUp}>
            <SectionLabel>自我感受</SectionLabel>
            <Card variant="default" padding="md" animated={false}>
              <Form.Item name="patientCondition">
                <Selector
                  options={CONDITION_OPTIONS}
                  style={{
                    '--border-radius': '16px',
                    '--border': '1px solid #e5e7eb',
                    '--checked-border': '1px solid #0052FF',
                    '--checked-color': '#EBF1FF',
                    '--checked-text-color': '#0052FF',
                  } as React.CSSProperties}
                />
              </Form.Item>
            </Card>
          </motion.div>

          {/* 备注 */}
          <motion.div variants={fadeInUp}>
            <SectionLabel>备注</SectionLabel>
            <Card variant="default" padding="md" animated={false}>
              <Form.Item name="notes">
                <TextArea placeholder="其他需要说明的情况（选填）" rows={3} maxLength={500} showCount />
              </Form.Item>
            </Card>
          </motion.div>
        </Form>
      </motion.div>

      {/* 底部提交按钮 */}
      <div className="fixed bottom-0 left-0 right-0 p-4 bg-card border-t border-border">
        <Button
          variant="primary"
          size="lg"
          block
          loading={submitting}
          onClick={handleSubmit}
        >
          提交报告
        </Button>
      </div>
    </div>
  );
};

export default SelfReportPage;
