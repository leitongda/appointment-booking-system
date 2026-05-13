import { Modal, Button, Space, Alert, Steps, Select, Transfer, Table, Tag, Radio } from 'antd';
import { ProForm, ProFormCheckbox, ProFormSelect, ProFormTimePicker, ProFormDigit, ProFormRadio } from '@ant-design/pro-components';
import type { ScheduleTemplate, Department, Doctor, Store } from '@hospital/shared';
import { APPOINTMENT_TYPE_OPTIONS, WEEKDAY_OPTIONS, SCHEDULE_MODE_OPTIONS } from '@hospital/shared';
import { useMemo } from 'react';

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

export interface CrossStoreMapping {
  sourceDepartmentId: string;
  sourceDepartmentName: string;
  targetDepartmentId?: string;
  targetDoctorId?: string;
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
  // 同院区复制相关
  targetDoctorIds: string[];
  onTargetDoctorIdsChange: (ids: string[]) => void;
  allDoctors: Doctor[];
  departments: Department[];
  deptFilter?: string;
  onDeptFilterChange: (deptId: string | undefined) => void;
  filteredDoctors: Doctor[];
  // 跨院区复制相关
  copyMode: 'same-store' | 'cross-store';
  onCopyModeChange: (mode: 'same-store' | 'cross-store') => void;
  stores: Store[];
  targetStoreId?: string;
  onTargetStoreIdChange: (storeId: string | undefined) => void;
  targetStoreDepartments: Department[];
  targetStoreDoctors: Doctor[];
  crossStoreMappings: CrossStoreMapping[];
  onCrossStoreMappingsChange: (mappings: CrossStoreMapping[]) => void;
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
  copyMode,
  onCopyModeChange,
  stores,
  targetStoreId,
  onTargetStoreIdChange,
  targetStoreDepartments,
  targetStoreDoctors,
  crossStoreMappings,
  onCrossStoreMappingsChange,
}) => {
  // 自动建议映射：根据科室名称匹配
  const autoSuggestMappings = (targetDepts: Department[], targetDocs: Doctor[]) => {
    if (!sourceTemplate) return;

    const sourceDept = departments.find(d => d.id === sourceTemplate.departmentId);
    if (!sourceDept) return;

    // 查找名称相同或相近的目标科室
    const matchedDept = targetDepts.find(d => d.name === sourceDept.name);
    if (!matchedDept) return;

    // 查找源医生名称在目标科室中的匹配
    const sourceDoc = allDoctors.find(d => d.id === sourceTemplate.doctorId);
    const matchedDoc = targetDocs.find(
      d => d.departmentId === matchedDept.id && d.name === sourceDoc?.name
    );

    const newMapping: CrossStoreMapping = {
      sourceDepartmentId: sourceTemplate.departmentId,
      sourceDepartmentName: sourceDept.name,
      targetDepartmentId: matchedDept.id,
      targetDoctorId: matchedDoc?.id,
    };

    onCrossStoreMappingsChange([newMapping]);
  };

  // 当目标门店变化时，尝试自动建议映射
  const handleTargetStoreChange = (storeId: string | undefined) => {
    onTargetStoreIdChange(storeId);
    onCrossStoreMappingsChange([]);
    if (storeId && targetStoreDepartments.length > 0) {
      // 延迟执行，等待部门和医生数据加载完成
      setTimeout(() => {
        autoSuggestMappings(targetStoreDepartments, targetStoreDoctors);
      }, 300);
    }
  };

  // 跨院区映射表格列
  const mappingColumns = useMemo(() => [
    {
      title: '源科室',
      dataIndex: 'sourceDepartmentName',
      key: 'sourceDepartmentName',
      width: 120,
    },
    {
      title: '目标科室',
      key: 'targetDepartment',
      width: 160,
      render: (_: any, record: CrossStoreMapping, index: number) => (
        <Select
          placeholder="选择科室"
          style={{ width: 140 }}
          value={record.targetDepartmentId}
          onChange={(val) => {
            const updated = [...crossStoreMappings];
            updated[index] = { ...record, targetDepartmentId: val, targetDoctorId: undefined };
            onCrossStoreMappingsChange(updated);
          }}
          options={targetStoreDepartments.map(d => ({ label: d.name, value: d.id }))}
        />
      ),
    },
    {
      title: '目标医生',
      key: 'targetDoctor',
      width: 160,
      render: (_: any, record: CrossStoreMapping, index: number) => {
        const availableDoctors = targetStoreDoctors.filter(
          d => d.departmentId === record.targetDepartmentId
        );
        return (
          <Select
            placeholder="选择医生"
            style={{ width: 140 }}
            value={record.targetDoctorId}
            onChange={(val) => {
              const updated = [...crossStoreMappings];
              updated[index] = { ...record, targetDoctorId: val };
              onCrossStoreMappingsChange(updated);
            }}
            options={availableDoctors.map(d => ({ label: d.name, value: d.id }))}
            disabled={!record.targetDepartmentId}
          />
        );
      },
    },
  ], [crossStoreMappings, targetStoreDepartments, targetStoreDoctors, onCrossStoreMappingsChange]);

  // 是否允许进入下一步/确认
  const canProceed = useMemo(() => {
    if (step === 0) return true;
    if (copyMode === 'same-store') {
      return targetDoctorIds.length > 0;
    }
    return crossStoreMappings.some(m => m.targetDepartmentId && m.targetDoctorId);
  }, [step, copyMode, targetDoctorIds, crossStoreMappings]);

  // 步骤标题
  const stepItems = copyMode === 'same-store'
    ? [{ title: '调整配置' }, { title: '选择医生' }]
    : [{ title: '调整配置' }, { title: '选择目标门店与映射' }];

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
              下一步
            </Button>
          ) : (
            <>
              <Button onClick={onPrevStep}>上一步</Button>
              <Button
                type="primary"
                loading={loading}
                onClick={onConfirm}
                disabled={!canProceed}
              >
                {copyMode === 'same-store'
                  ? `确认复制 (${targetDoctorIds.length})`
                  : `确认复制 (${crossStoreMappings.filter(m => m.targetDoctorId).length})`
                }
              </Button>
            </>
          )}
        </Space>
      }
      width={copyMode === 'cross-store' && step === 1 ? 900 : 700}
      destroyOnHidden
    >
      <Steps
        current={step}
        items={stepItems}
        style={{ marginBottom: 24 }}
      />

      {step === 0 && formData && (
        <div>
          <Alert
            title={
              <div>
                复制来源：<strong>{sourceTemplate?.name}</strong>
                <span style={{ marginLeft: 16, color: '#666' }}>
                  医生：{sourceTemplate?.doctorName}
                </span>
                <span style={{ marginLeft: 16, color: '#666' }}>
                  门店：{sourceTemplate?.storeName}
                </span>
              </div>
            }
            type="info"
            showIcon
            style={{ marginBottom: 16 }}
          />

          <div style={{ marginBottom: 16, padding: 12, background: '#f5f5f5', borderRadius: 4 }}>
            <div style={{ marginBottom: 8, fontWeight: 500 }}>复制模式</div>
            <Radio.Group
              value={copyMode}
              onChange={(e) => onCopyModeChange(e.target.value)}
            >
              <Radio value="same-store">同院区复制（当前门店内医生）</Radio>
              <Radio value="cross-store">跨院区复制（复制到其他门店）</Radio>
            </Radio.Group>
          </div>

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

      {step === 1 && copyMode === 'same-store' && (
        <div>
          <Alert
            title="选择要复制规则的目标医生，可选择多个医生"
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

      {step === 1 && copyMode === 'cross-store' && (
        <div>
          <Alert
            title="选择目标门店，并为源科室配置对应的目标科室和医生"
            type="info"
            showIcon
            style={{ marginBottom: 16 }}
          />

          <div style={{ marginBottom: 16 }}>
            <span style={{ marginRight: 8 }}>目标门店：</span>
            <Select
              placeholder="选择目标门店"
              style={{ width: 240 }}
              value={targetStoreId}
              onChange={handleTargetStoreChange}
              options={stores
                .filter(s => s.id !== sourceTemplate?.storeId)
                .map(s => ({ label: s.name, value: s.id }))}
            />
          </div>

          {targetStoreId && (
            <div>
              <div style={{ marginBottom: 8, fontWeight: 500 }}>
                科室/医生映射
                {crossStoreMappings.length > 0 && (
                  <Tag color="blue" style={{ marginLeft: 8 }}>
                    已匹配 {crossStoreMappings.filter(m => m.targetDoctorId).length} 项
                  </Tag>
                )}
              </div>
              <Table
                dataSource={crossStoreMappings}
                columns={mappingColumns}
                rowKey="sourceDepartmentId"
                pagination={false}
                size="small"
                bordered
              />
              {crossStoreMappings.length === 0 && (
                <div style={{ padding: 24, textAlign: 'center', color: '#999' }}>
                  未找到自动匹配的科室，请检查目标门店是否包含同名科室
                </div>
              )}
            </div>
          )}

          {!targetStoreId && (
            <div style={{ padding: 24, textAlign: 'center', color: '#999' }}>
              请先选择目标门店
            </div>
          )}
        </div>
      )}
    </Modal>
  );
};

export default CopyRuleModal;
