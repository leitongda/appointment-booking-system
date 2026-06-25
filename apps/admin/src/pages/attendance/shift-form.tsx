/**
 * 班次表单页面
 *
 * 使用基础设施：
 * - FormPage 组件：统一表单页面布局
 * - useFormInitialValues hook：初始值处理
 * - useFormSubmit hook：提交处理
 */
import {
  ProFormText,
  ProFormTimePicker,
  ProFormInputNumber,
  ProFormSwitch,
} from '@ant-design/pro-components';
import { Card, message } from 'antd';
import { useParams, history } from '@umijs/max';
import { useEffect, useState } from 'react';
import { attendanceApi } from '@hospital/api';
import type { AttendanceShift } from '@hospital/api';

// 基础设施导入
import FormPage from '@/components/FormPage';
import { useFormInitialValues } from '@/hooks/useFormInitialValues';
import { useFormSubmit } from '@/hooks/useFormSubmit';
import { requiredRules } from '@/utils/formValidators';

const ShiftFormPage: React.FC = () => {
  const { id } = useParams();
  const isEdit = !!id;
  const [shift, setShift] = useState<AttendanceShift | null>(null);
  const [loading, setLoading] = useState(false);

  // 加载班次数据
  useEffect(() => {
    if (isEdit && id) {
      setLoading(true);
      attendanceApi.getShiftById(id)
        .then(setShift)
        .catch(() => {
          message.error('加载班次失败');
          history.back();
        })
        .finally(() => setLoading(false));
    }
  }, [id]);

  // 使用 useFormInitialValues hook
  const { initialValues } = useFormInitialValues<AttendanceShift>(
    shift,
    {
      switchFields: ['isFlexible', 'enabled'],
      defaults: { enabled: true, isFlexible: false, graceMinutes: 0, lateThresholdMinutes: 0, earlyThresholdMinutes: 0 },
    }
  );

  // 使用 useFormSubmit hook
  const { handleSubmit, submitting } = useFormSubmit(
    async (values: any) => {
      if (isEdit && id) {
        return attendanceApi.updateShift(id, values);
      } else {
        return attendanceApi.createShift(values);
      }
    },
    {
      switchFields: ['isFlexible', 'enabled'],
      onSuccess: () => history.push('/attendance/shifts'),
      successMessage: isEdit ? '更新成功' : '创建成功',
    }
  );

  return (
    <FormPage
      title={isEdit ? '编辑班次' : '新增班次'}
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
          label="班次名称"
          width="lg"
          placeholder="如：早班、晚班、全天班"
          rules={[requiredRules('请输入班次名称')]}
          fieldProps={{
            showCount: true,
            maxLength: 100,
          }}
        />

        <ProFormText
          name="code"
          label="班次编码"
          width="lg"
          placeholder="如：MORNING、AFTERNOON"
          rules={[requiredRules('请输入班次编码')]}
          disabled={isEdit}
          extra="用于系统内部标识，编辑时不可修改"
          fieldProps={{
            showCount: true,
            maxLength: 50,
          }}
        />
      </Card>

      <Card title="时间设置" style={{ marginTop: 16 }}>
        <ProFormTimePicker
          name="startTime"
          label="上班时间"
          width="md"
          rules={[requiredRules('请选择上班时间')]}
          fieldProps={{
            format: 'HH:mm',
            needConfirm: false,
          }}
        />

        <ProFormTimePicker
          name="endTime"
          label="下班时间"
          width="md"
          rules={[requiredRules('请选择下班时间')]}
          fieldProps={{
            format: 'HH:mm',
            needConfirm: false,
          }}
        />

        <ProFormTimePicker
          name="breakStart"
          label="午休开始时间"
          width="md"
          fieldProps={{
            format: 'HH:mm',
            needConfirm: false,
          }}
        />

        <ProFormTimePicker
          name="breakEnd"
          label="午休结束时间"
          width="md"
          fieldProps={{
            format: 'HH:mm',
            needConfirm: false,
          }}
        />
      </Card>

      <Card title="考勤规则" style={{ marginTop: 16 }}>
        <ProFormInputNumber
          name="graceMinutes"
          label="宽限时间（分钟）"
          width="md"
          min={0}
          max={120}
          fieldProps={{
            precision: 0,
          }}
          extra="迟到在此时间范围内不计为迟到"
        />

        <ProFormInputNumber
          name="lateThresholdMinutes"
          label="迟到阈值（分钟）"
          width="md"
          min={0}
          max={240}
          fieldProps={{
            precision: 0,
          }}
          extra="超过此时间计为严重迟到或缺勤"
        />

        <ProFormInputNumber
          name="earlyThresholdMinutes"
          label="早退阈值（分钟）"
          width="md"
          min={0}
          max={240}
          fieldProps={{
            precision: 0,
          }}
          extra="提前下班超过此时间计为早退"
        />

        <ProFormSwitch
          name="isFlexible"
          label="弹性工作制"
          extra="开启后不计算迟到早退"
        />

        <ProFormSwitch
          name="enabled"
          label="启用状态"
          extra="禁用后该班次将无法使用"
        />
      </Card>
    </FormPage>
  );
};

export default ShiftFormPage;
