import { ModalForm, ProFormSelect, ProFormTimePicker, ProFormDigit, ProFormCheckbox, ProFormRadio, ProFormDateRangePicker } from '@ant-design/pro-components';
import { Alert } from 'antd';
import type { ProFormInstance } from '@ant-design/pro-components';
import type { Store, Department, Doctor } from '@hospital/shared';
import type dayjs from 'dayjs';
import { WEEKDAY_OPTIONS, SCHEDULE_MODE_OPTIONS, getDateInfo } from '@hospital/shared';
import { useDict } from '@/hooks/useDict';

export interface BatchAddModalValues {
  storeId: string;
  departmentId: string;
  doctorId: string;
  appointmentType: string;
  startTime: string;
  endTime: string;
  slotCount: number;
  totalSlots: number;
  weekdays: number[];
  scheduleMode: string;
  dateRange: [string, string] | [dayjs.Dayjs, dayjs.Dayjs];
}

interface BatchAddModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onFinish: (values: BatchAddModalValues) => Promise<boolean>;
  stores: Store[];
  departments: Department[];
  doctors: Doctor[];
  selectedDept?: string;
  onDeptChange: (deptId: string) => void;
  formRef?: React.RefObject<ProFormInstance>;
}

const dateInfo = getDateInfo();

const BatchAddModal: React.FC<BatchAddModalProps> = ({
  open,
  onOpenChange,
  onFinish,
  stores,
  departments,
  doctors,
  selectedDept,
  onDeptChange,
  formRef,
}) => {
  const { options: appointmentTypeOptions } = useDict('appointment_type');
  return (
    <ModalForm
      title="批量添加排班规则"
      open={open}
      formRef={formRef}
      onOpenChange={(isOpen) => {
        onOpenChange(isOpen);
        if (!isOpen) {
          onDeptChange('');
        }
      }}
      onFinish={onFinish}
      initialValues={{
        appointmentType: 'normal',
        scheduleMode: 'weekly',
        totalSlots: 10,
        slotCount: 1,
        weekdays: [1, 2, 3, 4, 5],
      }}
      modalProps={{ destroyOnHidden: true }}
      width={600}
    >
      <Alert
        title={`当前为本月第${dateInfo.monthWeek}周，本年第${dateInfo.yearWeek}周（${dateInfo.isOddWeek ? '奇数' : '偶数'}周）`}
        type="info"
        showIcon
        style={{ marginBottom: 16 }}
      />
      <ProFormSelect
        name="storeId"
        label="选择门店"
        options={stores.map((s) => ({ label: s.name, value: s.id }))}
        rules={[{ required: true, message: '请选择门店' }]}
      />
      <ProFormSelect
        name="departmentId"
        label="选择科室"
        options={departments.map((d) => ({ label: d.name, value: d.id }))}
        onChange={(val) => {
          onDeptChange(val as string);
          formRef?.current?.setFieldValue('doctorId', undefined);
        }}
        rules={[{ required: true, message: '请选择科室' }]}
      />
      <ProFormSelect
        name="doctorId"
        label="选择医生"
        options={doctors.map((d) => ({ label: `${d.name} - ${d.title || ''}`, value: d.id }))}
        rules={[{ required: true, message: '请选择医生' }]}
        disabled={!selectedDept}
      />
      <ProFormSelect
        name="appointmentType"
        label="预约类型"
        options={appointmentTypeOptions}
        rules={[{ required: true, message: '请选择预约类型' }]}
      />
      <ProFormTimePicker
        name="startTime"
        label="开始时间"
        fieldProps={{ format: 'HH:mm' }}
        rules={[{ required: true, message: '请选择开始时间' }]}
      />
      <ProFormTimePicker
        name="endTime"
        label="结束时间"
        fieldProps={{ format: 'HH:mm' }}
        rules={[{ required: true, message: '请选择结束时间' }]}
      />
      <ProFormDigit
        name="slotCount"
        label="班次数量"
        min={1}
        max={50}
        rules={[{ required: true, message: '请输入班次数量' }]}
        extra="根据时间区间均分生成多个班次"
      />
      <ProFormDigit
        name="totalSlots"
        label="班次人数"
        min={1}
        max={200}
        rules={[{ required: true, message: '请输入班次人数' }]}
        extra="每个班次可预约的人数"
      />
      <ProFormCheckbox.Group
        name="weekdays"
        label="选择星期"
        options={WEEKDAY_OPTIONS}
        rules={[{ required: true, message: '请选择星期' }]}
      />
      <ProFormRadio.Group
        name="scheduleMode"
        label="排班方式"
        options={SCHEDULE_MODE_OPTIONS}
        rules={[{ required: true, message: '请选择排班方式' }]}
      />
      <ProFormDateRangePicker
        name="dateRange"
        label="日期范围"
        rules={[{ required: true, message: '请选择日期范围' }]}
      />
    </ModalForm>
  );
};

export default BatchAddModal;
