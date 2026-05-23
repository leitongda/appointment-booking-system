import { View, Text, Textarea, Input } from '@tarojs/components';
import Taro, { useRouter } from '@tarojs/taro';
import { Button, Loading } from '@nutui/nutui-react-taro';
import { useState, useCallback } from 'react';
import { followUpApi, selfReportApi } from '@hospital/api';
import { useProtectedPage } from '../../../hooks/useProtectedPage';
import { useApplyThemeNavigationBar } from '../../../utils/theme';
import LoginPopup from '../../../components/LoginPopup';
import type { FollowUpTask } from '@hospital/api';
import './report.less';

const SYMPTOM_OPTIONS = ['头痛', '头晕', '恶心', '乏力', '胸闷', '失眠', '心悸', '咳嗽'];

const CONDITION_OPTIONS = [
  { value: 'improved', label: '好转' },
  { value: 'stable', label: '稳定' },
  { value: 'worsened', label: '加重' },
];

const SelfReportPage = () => {
  useApplyThemeNavigationBar();
  const router = useRouter();
  const { taskId } = router.params;

  const [task, setTask] = useState<FollowUpTask | null>(null);
  const [loading, setLoading] = useState(!!taskId);
  const [submitting, setSubmitting] = useState(false);

  // 表单数据
  const [systolicBp, setSystolicBp] = useState('');
  const [diastolicBp, setDiastolicBp] = useState('');
  const [bloodGlucose, setBloodGlucose] = useState('');
  const [heartRate, setHeartRate] = useState('');
  const [temperature, setTemperature] = useState('');
  const [selectedSymptoms, setSelectedSymptoms] = useState<string[]>([]);
  const [symptomDetail, setSymptomDetail] = useState('');
  const [patientCondition, setPatientCondition] = useState('');
  const [notes, setNotes] = useState('');

  const loadData = useCallback(async () => {
    if (!taskId) {
      setLoading(false);
      return;
    }
    try {
      const taskData = await followUpApi.getTaskDetail(taskId);
      setTask(taskData);
    } catch (error: any) {
      console.error('加载任务失败', error);
      Taro.showToast({ title: error.message || '加载失败', icon: 'none' });
    } finally {
      setLoading(false);
    }
  }, [taskId]);

  const { showLoginPopup, handleLoginSuccess, handleLoginClose } = useProtectedPage({
    load: loadData,
    clear: () => {
      setTask(null);
      setLoading(false);
    },
    deps: [taskId],
  });

  const toggleSymptom = (symptom: string) => {
    setSelectedSymptoms(prev =>
      prev.includes(symptom) ? prev.filter(s => s !== symptom) : [...prev, symptom]
    );
  };

  const handleSubmit = async () => {
    const hasVitals = systolicBp || diastolicBp || bloodGlucose || heartRate || temperature;
    const hasSymptoms = selectedSymptoms.length > 0 || symptomDetail.trim();
    const hasCondition = !!patientCondition;

    if (!hasVitals && !hasSymptoms && !hasCondition) {
      Taro.showToast({ title: '请至少填写一项数据', icon: 'none' });
      return;
    }

    if ((systolicBp && !diastolicBp) || (!systolicBp && diastolicBp)) {
      Taro.showToast({ title: '收缩压和舒张压需同时填写', icon: 'none' });
      return;
    }

    setSubmitting(true);
    try {
      const symptoms = [...selectedSymptoms, symptomDetail.trim()].filter(Boolean).join('；');

      await selfReportApi.create({
        taskId: taskId || undefined,
        systolicBp: systolicBp ? Number(systolicBp) : undefined,
        diastolicBp: diastolicBp ? Number(diastolicBp) : undefined,
        bloodGlucose: bloodGlucose ? Number(bloodGlucose) : undefined,
        heartRate: heartRate ? Number(heartRate) : undefined,
        temperature: temperature ? Number(temperature) : undefined,
        symptoms: symptoms || undefined,
        patientCondition: (patientCondition as any) || undefined,
        notes: notes.trim() || undefined,
      });

      Taro.showToast({ title: '提交成功', icon: 'success' });
      setTimeout(() => Taro.navigateBack(), 1000);
    } catch (error: any) {
      Taro.showToast({ title: error.message || '提交失败', icon: 'none' });
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <View className="self-report-page loading-container">
        <Loading type="spinner">加载中...</Loading>
      </View>
    );
  }

  return (
    <View className="self-report-page">
      {/* 任务信息 */}
      {task && (
        <View className="task-info-card">
          <Text className="task-title">
            {task.planName || '随访任务'}
            {task.stepOrder != null ? ` · 第${task.stepOrder}步` : ''}
          </Text>
          <Text className="task-meta">
            {task.doctorName || ''} · {task.departmentName || ''}
          </Text>
        </View>
      )}

      {/* 体征数据 */}
      <View className="section">
        <Text className="section-title">体征数据</Text>
        <View className="form-card">
          <View className="form-row">
            <Text className="form-label">血压</Text>
            <View className="bp-inputs">
              <Input
                className="form-input bp-input"
                type="number"
                placeholder="收缩压"
                value={systolicBp}
                onInput={(e) => setSystolicBp(e.detail.value)}
              />
              <Text className="bp-separator">/</Text>
              <Input
                className="form-input bp-input"
                type="number"
                placeholder="舒张压"
                value={diastolicBp}
                onInput={(e) => setDiastolicBp(e.detail.value)}
              />
              <Text className="form-unit">mmHg</Text>
            </View>
          </View>
          <View className="form-row">
            <Text className="form-label">血糖</Text>
            <View className="input-with-unit">
              <Input
                className="form-input"
                type="digit"
                placeholder="空腹血糖"
                value={bloodGlucose}
                onInput={(e) => setBloodGlucose(e.detail.value)}
              />
              <Text className="form-unit">mmol/L</Text>
            </View>
          </View>
          <View className="form-row">
            <Text className="form-label">心率</Text>
            <View className="input-with-unit">
              <Input
                className="form-input"
                type="number"
                placeholder="心率"
                value={heartRate}
                onInput={(e) => setHeartRate(e.detail.value)}
              />
              <Text className="form-unit">次/分</Text>
            </View>
          </View>
          <View className="form-row last">
            <Text className="form-label">体温</Text>
            <View className="input-with-unit">
              <Input
                className="form-input"
                type="digit"
                placeholder="体温"
                value={temperature}
                onInput={(e) => setTemperature(e.detail.value)}
              />
              <Text className="form-unit">°C</Text>
            </View>
          </View>
        </View>
      </View>

      {/* 症状 */}
      <View className="section">
        <Text className="section-title">症状描述</Text>
        <View className="form-card">
          <View className="symptom-tags">
            {SYMPTOM_OPTIONS.map(symptom => (
              <View
                key={symptom}
                className={`symptom-tag ${selectedSymptoms.includes(symptom) ? 'active' : ''}`}
                onClick={() => toggleSymptom(symptom)}
              >
                <Text>{symptom}</Text>
              </View>
            ))}
          </View>
          <View className="textarea-wrap">
            <Textarea
              className="form-textarea"
              placeholder="补充描述症状（选填）"
              value={symptomDetail}
              onInput={(e) => setSymptomDetail(e.detail.value)}
              maxlength={300}
            />
            <Text className="char-count">{symptomDetail.length}/300</Text>
          </View>
        </View>
      </View>

      {/* 自我感受 */}
      <View className="section">
        <Text className="section-title">自我感受</Text>
        <View className="form-card">
          <View className="condition-options">
            {CONDITION_OPTIONS.map(option => (
              <View
                key={option.value}
                className={`condition-option ${patientCondition === option.value ? 'active' : ''}`}
                onClick={() => setPatientCondition(option.value === patientCondition ? '' : option.value)}
              >
                <Text>{option.label}</Text>
              </View>
            ))}
          </View>
        </View>
      </View>

      {/* 备注 */}
      <View className="section">
        <Text className="section-title">备注</Text>
        <View className="form-card">
          <View className="textarea-wrap">
            <Textarea
              className="form-textarea"
              placeholder="其他需要说明的情况（选填）"
              value={notes}
              onInput={(e) => setNotes(e.detail.value)}
              maxlength={500}
            />
            <Text className="char-count">{notes.length}/500</Text>
          </View>
        </View>
      </View>

      {/* 提交按钮 */}
      <View className="submit-bar">
        <Button
          type="primary"
          block
          loading={submitting}
          onClick={handleSubmit}
        >
          提交报告
        </Button>
      </View>

      <LoginPopup
        visible={showLoginPopup}
        onClose={handleLoginClose}
        onSuccess={handleLoginSuccess}
      />
    </View>
  );
};

export default SelfReportPage;
