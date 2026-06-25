/**
 * 考勤规则表单页面
 *
 * 使用基础设施：
 * - FormPage 组件：统一表单页面布局
 * - useFormInitialValues hook：初始值处理
 * - useFormSubmit hook：提交处理
 */
import {
  ProFormText,
  ProFormTextArea,
  ProFormInputNumber,
  ProFormSwitch,
  ProFormSelect,
} from '@ant-design/pro-components';
import { Card, message } from 'antd';
import { useParams, history } from '@umijs/max';
import { useEffect, useState } from 'react';
import { attendanceApi } from '@hospital/api';
import type { AttendanceRule } from '@hospital/api';

// 基础设施导入
import FormPage from '@/components/FormPage';
import { useFormInitialValues } from '@/hooks/useFormInitialValues';
import { useFormSubmit } from '@/hooks/useFormSubmit';
import { requiredRules } from '@/utils/formValidators';

/** 策略选项 */
const POLICY_OPTIONS = [
  { label: '弹性', value: 'flexible', description: '在一定范围内允许迟到/早退' },
  { label: '严格', value: 'strict', description: '严格按时间打卡，超出即记为迟到/早退' },
  { label: '忽略', value: 'ignore', description: '不检查该项' },
];

const RuleFormPage: React.FC = () => {
  const { id } = useParams();
  const isEdit = !!id;
  const [rule, setRule] = useState<AttendanceRule | null>(null);
  const [loading, setLoading] = useState(false);

  // 加载考勤规则数据
  useEffect(() => {
    if (isEdit && id) {
      setLoading(true);
      attendanceApi.getRuleById(id)
        .then(setRule)
        .catch(() => {
          message.error('加载考勤规则失败');
          history.back();
        })
        .finally(() => setLoading(false));
    }
  }, [id]);

  // 使用 useFormInitialValues hook
  const { initialValues } = useFormInitialValues<AttendanceRule>(
    rule,
    {
      switchFields: ['overtimeEnabled', 'enabled'],
      defaults: {
        enabled: true,
        latePolicy: 'flexible',
        earlyPolicy: 'flexible',
        absentPolicy: 'strict',
        overtimeEnabled: false,
        overtimeMinMinutes: 30,
      },
    }
  );

  // 使用 useFormSubmit hook
  const { handleSubmit, submitting } = useFormSubmit(
    async (values: any) => {
      if (isEdit && id) {
        return attendanceApi.updateRule(id, values);
      } else {
        return attendanceApi.createRule(values);
      }
    },
    {
      switchFields: ['overtimeEnabled', 'enabled'],
      onSuccess: () => history.push('/attendance/rules'),
      successMessage: isEdit ? '更新成功' : '创建成功',
    }
  );

  return (
    <FormPage
      title={isEdit ? '编辑考勤规则' : '新增考勤规则'}
      loading={loading}
      submitting={submitting}
      initialValues={initialValues}
      onFinish={handleSubmit}
      onCancel={() => history.back()}
      saveText={isEdit ? '保存' : '创建'}
    >
      <Card title="基本信息">
        <ProFormText
          name="name"
          label="规则名称"
          width="lg"
          placeholder="如：标准考勤规则、弹性工作规则"
          rules={[requiredRules('请输入规则名称')]}
          fieldProps={{
            showCount: true,
            maxLength: 100,
          }}
        />

        <ProFormTextArea
          name="description"
          label="描述"
          width="lg"
          fieldProps={{
            rows: 3,
            showCount: true,
            maxLength: 500,
          }}
          placeholder="请输入考勤规则的详细描述"
        />
      </Card>

      <Card title="考勤策略" style={{ marginTop: 16 }}>
        <ProFormSelect
          name="latePolicy"
          label="迟到策略"
          width="md"
          options={POLICY_OPTIONS}
          rules={[requiredRules('请选择迟到策略')]}
          extra="配置迟到的处理方式"
        />

        <ProFormSelect
          name="earlyPolicy"
          label="早退策略"
          width="md"
          options={POLICY_OPTIONS}
          rules={[requiredRules('请选择早退策略')]}
          extra="配置早退的处理方式"
        />

        <ProFormSelect
          name="absentPolicy"
          label="缺勤策略"
          width="md"
          options={POLICY_OPTIONS}
          rules={[requiredRules('请选择缺勤策略')]}
          extra="配置缺勤的处理方式"
        />
      </Card>

      <Card title="加班设置" style={{ marginTop: 16 }}>
        <ProFormSwitch
          name="overtimeEnabled"
          label="启用加班计算"
          extra="开启后将根据加班时长计算加班"
        />

        <ProFormInputNumber
          name="overtimeMinMinutes"
          label="最低加班时长（分钟）"
          width="md"
          min={0}
          max={480}
          fieldProps={{
            precision: 0,
          }}
          extra="低于此时间的加班不计入加班统计"
        />
      </Card>

      <Card title="状态" style={{ marginTop: 16 }}>
        <ProFormSwitch
          name="enabled"
          label="启用状态"
          extra="禁用后该规则将无法被使用"
        />
      </Card>
    </FormPage>
  );
};

export default RuleFormPage;
