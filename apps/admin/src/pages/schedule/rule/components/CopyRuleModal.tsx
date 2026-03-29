import { Modal, Button, Space, Alert, Steps, Select, Transfer } from 'antd';
import { ProForm, ProFormCheckbox, ProFormSelect, ProFormTimePicker, ProFormDigit, ProFormRadio } from '@ant-design/pro-components';
import type { ScheduleTemplate, Department, Doctor } from '@hospital/shared';
import { APPOINTMENT_TYPE_OPTIONS, WEEKDAY_OPTIONS, SCHEDULE_MODE_OPTIONS } from '@hospital/shared';

export interface CopyRuleFormData {
  name: string;
  weekdays: number[];
  appointmentType: string;
  startTime: string;
  endTime: string;
  slotCount: number;
  slotCapacity: number;
  scheduleMode: string;
  breakTimes: any[];
}

interface CopyRuleModalProps {
  open: boolean;
  onCancel: () => void;
  onNextStep: () => void;
  onPrevStep: () => void;
  onConfirm: () => Promise<void>;
  sourceTemplate: ScheduleTemplate | null;
  formData: CopyRuleFormData | null;
  onFormDataChange: (data: CopyRuleFormData) => void;
  step: number;
  loading: boolean;
  targetDoctorIds: string[];
  onTargetDoctorIdsChange: (ids: string[]) => void;
  allDoctors: Doctor[];
  departments: Department[];
  deptFilter?: string;
  onDeptFilterChange: (deptId: string | undefined) => void;
  filteredDoctors: Doctor[];
}

const CopyRuleModal: React.FC<CopyRuleModalProps> = ({
  open,
  onCancel,
  onNextStep,
  onPrevStep,
  onConfirm,
  sourceTemplate,
  formData,
  onFormDataChange,
  step,
  loading,
  targetDoctorIds,
  onTargetDoctorIdsChange,
  allDoctors,
  departments,
  deptFilter,
  onDeptFilterChange,
  filteredDoctors,
}) => {
  return (
    <Modal
      title="复制排班规则"
      open={open}
      onCancel={onCancel}
      footer={
        <Space>
          <Button onClick={onCancel}>取消</Button>
          {step === 0 ? (
            <Button type="primary" onClick={onNextStep}>
              下一步：选择医生
            </Button>
          ) : (
            <>
              <Button onClick={onPrevStep}>上一步</Button>
              <Button
                type="primary"
                loading={loading}
                onClick={onConfirm}
                disabled={targetDoctorIds.length === 0}
              >
                确认复制 ({targetDoctorIds.length})
              </Button>
            </>
          )}
        </Space>
      }
      width={700}
      destroyOnHidden
    >
      <Steps
        current={step}
        items={[
          { title: '调整配置' },
          { title: '选择医生' },
        ]}
        style={{ marginBottom: 24 }}
      />

      {step === 0 && formData && (
        <div>
          <Alert
            message={
              <div>
                复制来源：<strong>{sourceTemplate?.name}</strong>
                <span style={{ marginLeft: 16, color: '#666' }}>
                  医生：{sourceTemplate?.doctorName}
                </span>
              </div>
            }
            type="info"
            showIcon
            style={{ marginBottom: 16 }}
          />

          <ProForm
            layout="horizontal"
            labelCol={{ span: 6 }}
            wrapperCol={{ span: 18 }}
            submitter={false}
            initialValues={formData}
            onValuesChange={(_, allValues) => {
              onFormDataChange(allValues);
            }}
          >
            <ProFormCheckbox.Group
              name="weekdays"
              label="选择星期"
              options={WEEKDAY_OPTIONS}
            />
            <ProFormSelect
              name="appointmentType"
              label="预约类型"
              options={APPOINTMENT_TYPE_OPTIONS}
            />
            <ProFormTimePicker
              name="startTime"
              label="开始时间"
              fieldProps={{ format: 'HH:mm' }}
            />
            <ProFormTimePicker
              name="endTime"
              label="结束时间"
              fieldProps={{ format: 'HH:mm' }}
            />
            <ProFormDigit
              name="slotCount"
              label="班次数量"
              min={1}
              max={50}
              fieldProps={{ style: { width: 120 } }}
            />
            <ProFormDigit
              name="slotCapacity"
              label="班次人数"
              min={1}
              max={200}
              fieldProps={{ style: { width: 120 } }}
            />
            <ProFormRadio.Group
              name="scheduleMode"
              label="排班方式"
              options={SCHEDULE_MODE_OPTIONS}
            />
          </ProForm>
        </div>
      )}

      {step === 1 && (
        <div>
          <Alert
            message="选择要复制规则的目标医生，可选择多个医生"
            type="info"
            showIcon
            style={{ marginBottom: 16 }}
          />

          <div style={{ marginBottom: 16 }}>
            <span style={{ marginRight: 8 }}>按科室筛选：</span>
            <Select
              allowClear
              placeholder="全部科室"
              style={{ width: 200 }}
              value={deptFilter}
              onChange={(val) => onDeptFilterChange(val)}
              options={departments.map(d => ({ label: d.name, value: d.id }))}
            />
          </div>

          <Transfer
            dataSource={filteredDoctors.map(d => ({
              key: d.id,
              title: d.name,
              description: `${d.departmentName || ''} ${d.title || ''}`.trim(),
            }))}
            titles={['可选医生', '已选医生']}
            targetKeys={targetDoctorIds}
            onChange={(nextTargetKeys) => onTargetDoctorIdsChange(nextTargetKeys as string[])}
            render={(item) => (
              <span>
                {item.title}
                {item.description && (
                  <span style={{ color: '#999', fontSize: 12, marginLeft: 8 }}>
                    {item.description}
                  </span>
                )}
              </span>
            )}
            listStyle={{
              width: 280,
              height: 350,
            }}
            showSearch
            filterOption={(inputValue, item) =>
              item.title!.toLowerCase().includes(inputValue.toLowerCase()) ||
              (item.description || '').toLowerCase().includes(inputValue.toLowerCase())
            }
          />
        </div>
      )}
    </Modal>
  );
};

export default CopyRuleModal;
