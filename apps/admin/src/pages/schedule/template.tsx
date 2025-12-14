import { PageContainer, ProForm, ProFormSelect, ProFormDateRangePicker, ProFormDigit, ProFormCheckbox } from '@ant-design/pro-components';
import { Card, App } from 'antd';
import { useState, useEffect } from 'react';
import { scheduleApi, doctorApi, departmentApi } from '@hospital/api';
import type { Doctor, Department } from '@hospital/shared';

const TIME_SLOTS = [
  { label: '上午', value: 'morning' },
  { label: '下午', value: 'afternoon' },
  { label: '晚上', value: 'evening' },
];

const WEEKDAYS = [
  { label: '周一', value: 1 },
  { label: '周二', value: 2 },
  { label: '周三', value: 3 },
  { label: '周四', value: 4 },
  { label: '周五', value: 5 },
  { label: '周六', value: 6 },
  { label: '周日', value: 0 },
];

const ScheduleTemplatePage: React.FC = () => {
  const { message } = App.useApp();
  const [loading, setLoading] = useState(false);
  const [doctors, setDoctors] = useState<Doctor[]>([]);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [selectedDept, setSelectedDept] = useState<string>();

  useEffect(() => {
    loadDepartments();
  }, []);

  useEffect(() => {
    if (selectedDept) {
      loadDoctorsByDept(selectedDept);
    }
  }, [selectedDept]);

  const loadDepartments = async () => {
    try {
      const res = await departmentApi.getList({ pageSize: 100, status: 1 });
      setDepartments(res.data ?? []);
    } catch (error) {
      console.error('加载科室失败', error);
    }
  };

  const loadDoctorsByDept = async (deptId: string) => {
    try {
      const data = await doctorApi.getByDepartment(deptId);
      setDoctors(data ?? []);
    } catch (error) {
      console.error('加载医生失败', error);
    }
  };

  const handleSubmit = async (values: any) => {
    const { dateRange, ...rest } = values;
    if (!dateRange || dateRange.length !== 2) {
      message.error('请选择日期范围');
      return;
    }

    setLoading(true);
    try {
      await scheduleApi.batchCreate({
        ...rest,
        startDate: dateRange[0],
        endDate: dateRange[1],
      });
      message.success('批量创建排班成功');
    } catch (error: any) {
      message.error(error.message || '创建失败');
    } finally {
      setLoading(false);
    }
  };

  return (
    <PageContainer title="排班模板" subTitle="批量创建医生排班">
      <Card>
        <ProForm
          onFinish={handleSubmit}
          loading={loading}
          initialValues={{ totalSlots: 20, weekdays: [1, 2, 3, 4, 5], timeSlots: ['morning', 'afternoon'] }}
          submitter={{
            searchConfig: { submitText: '批量创建排班' },
            resetButtonProps: { style: { display: 'none' } },
          }}
        >
          <ProFormSelect
            name="departmentId"
            label="选择科室"
            width="lg"
            options={(departments ?? []).map((d) => ({ label: d.name, value: d.id }))}
            onChange={(val) => setSelectedDept(val as string)}
            rules={[{ required: true, message: '请选择科室' }]}
          />
          <ProFormSelect
            name="doctorId"
            label="选择医生"
            width="lg"
            options={(doctors ?? []).map((d) => ({ label: `${d.name} - ${d.title || ''}`, value: d.id }))}
            rules={[{ required: true, message: '请选择医生' }]}
          />
          <ProFormDateRangePicker
            name="dateRange"
            label="日期范围"
            width="lg"
            rules={[{ required: true, message: '请选择日期范围' }]}
          />
          <ProFormCheckbox.Group
            name="weekdays"
            label="工作日"
            options={WEEKDAYS}
            rules={[{ required: true, message: '请选择工作日' }]}
          />
          <ProFormCheckbox.Group
            name="timeSlots"
            label="出诊时段"
            options={TIME_SLOTS}
            rules={[{ required: true, message: '请选择出诊时段' }]}
          />
          <ProFormDigit
            name="totalSlots"
            label="每时段号源"
            width="sm"
            min={1}
            max={100}
            rules={[{ required: true, message: '请输入号源数量' }]}
          />
        </ProForm>
      </Card>
    </PageContainer>
  );
};

export default ScheduleTemplatePage;
