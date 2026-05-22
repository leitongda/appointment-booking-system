import { Modal, Button, Space, Alert, Steps, Select, Transfer, Table, Tag, Radio, App } from 'antd';
import { ProForm, ProFormCheckbox, ProFormSelect, ProFormTimePicker, ProFormDigit, ProFormRadio } from '@ant-design/pro-components';
import type { ScheduleTemplate, Department, Doctor, Store } from '@hospital/shared';
import { WEEKDAY_OPTIONS, SCHEDULE_MODE_OPTIONS } from '@hospital/shared';
import { useDict } from '@/hooks/useDict';
import { useState, useEffect, useMemo, useCallback } from 'react';
import { scheduleTemplateApi, doctorApi, departmentApi, storeApi } from '@hospital/api';
import { fetchAllData } from '@/utils/fetchAllData';
import { TEXT_SECONDARY } from '@/themes/scheduleColors';
import { ScheduleMessages } from '../../utils/message';

// ==================== 类型定义 ====================

export interface CopyRuleFormData {
  name: string;
  weekdays: number[];
  appointmentType: string;
  startTime: string;
  endTime: string;
  slotCount: number;
  slotCapacity: number;
  scheduleMode: string;
  breakTimes: { startTime: string; endTime: string }[];
}

export interface CrossStoreMapping {
  sourceDepartmentId: string;
  sourceDepartmentName: string;
  targetDepartmentId?: string;
  targetDoctorId?: string;
}

interface CopyRuleModalProps {
  open: boolean;
  onClose: () => void;
  onSuccess: () => void;
  sourceRule: ScheduleTemplate | null;
}

// ==================== 主组件 ====================

const CopyRuleModal: React.FC<CopyRuleModalProps> = ({
  open,
  onClose,
  onSuccess,
  sourceRule,
}) => {
  const { message } = App.useApp();
  const { options: appointmentTypeOptions } = useDict('appointment_type');

  // 步骤管理
  const [step, setStep] = useState(0);
  const [loading, setLoading] = useState(false);

  // 表单数据
  const [formData, setFormData] = useState<CopyRuleFormData | null>(null);

  // 同院区复制状态
  const [copyMode, setCopyMode] = useState<'same-store' | 'cross-store'>('same-store');
  const [targetDoctorIds, setTargetDoctorIds] = useState<string[]>([]);
  const [deptFilter, setDeptFilter] = useState<string | undefined>(undefined);

  // 数据列表
  const [allDoctors, setAllDoctors] = useState<Doctor[]>([]);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [stores, setStores] = useState<Store[]>([]);

  // 跨院区复制状态
  const [targetStoreId, setTargetStoreId] = useState<string | undefined>(undefined);
  const [targetStoreDepartments, setTargetStoreDepartments] = useState<Department[]>([]);
  const [targetStoreDoctors, setTargetStoreDoctors] = useState<Doctor[]>([]);
  const [crossStoreMappings, setCrossStoreMappings] = useState<CrossStoreMapping[]>([]);

  // 加载基础数据
  const loadData = async () => {
    try {
      const [deptData, doctorData, storeData] = await Promise.all([
        departmentApi.getAll(),
        fetchAllData((page, pageSize) => doctorApi.getList({ page, pageSize, status: 1 })),
        storeApi.getAll(),
      ]);
      setDepartments(deptData ?? []);
      setAllDoctors(doctorData);
      setStores(storeData ?? []);
    } catch (error) {
      console.error('加载数据失败', error);
    }
  };

  // 初始化：打开弹窗时加载数据并重置状态
  useEffect(() => {
    if (open && sourceRule) {
      // 初始化表单数据
      setFormData({
        name: sourceRule.name,
        weekdays: sourceRule.weekdays || [],
        appointmentType: sourceRule.appointmentType || 'normal',
        startTime: sourceRule.startTime,
        endTime: sourceRule.endTime,
        slotCount: sourceRule.slotCount || 1,
        slotCapacity: sourceRule.slotCapacity || 10,
        scheduleMode: sourceRule.scheduleMode || 'weekly',
        breakTimes: sourceRule.breakTimes || [],
      });
      // 重置状态
      setStep(0);
      setCopyMode('same-store');
      setTargetDoctorIds([]);
      setDeptFilter(undefined);
      setTargetStoreId(undefined);
      setTargetStoreDepartments([]);
      setTargetStoreDoctors([]);
      setCrossStoreMappings([]);
      // 加载数据
      loadData();
    }
  }, [open, sourceRule]);

  // 加载目标门店数据
  const loadTargetStoreData = useCallback(async (storeId: string) => {
    try {
      const [depts, docs] = await Promise.all([
        departmentApi.getAll(storeId),
        doctorApi.getByStore(storeId),
      ]);
      setTargetStoreDepartments(depts ?? []);
      setTargetStoreDoctors(docs ?? []);
    } catch (error) {
      console.error('加载目标门店数据失败', error);
    }
  }, []);

  // 自动建议映射：根据科室名称匹配
  const autoSuggestMappings = useCallback((targetDepts: Department[], targetDocs: Doctor[]) => {
    if (!sourceRule) return;
    const sourceDept = departments.find(d => d.id === sourceRule.departmentId);
    if (!sourceDept) return;
    const matchedDept = targetDepts.find(d => d.name === sourceDept.name);
    if (!matchedDept) return;
    const sourceDoc = allDoctors.find(d => d.id === sourceRule.doctorId);
    const matchedDoc = targetDocs.find(
      d => d.departmentId === matchedDept.id && d.name === sourceDoc?.name
    );
    setCrossStoreMappings([{
      sourceDepartmentId: sourceRule.departmentId,
      sourceDepartmentName: sourceDept.name,
      targetDepartmentId: matchedDept.id,
      targetDoctorId: matchedDoc?.id,
    }]);
  }, [sourceRule, departments, allDoctors]);

  // 目标门店变化处理
  const handleTargetStoreChange = useCallback((storeId: string | undefined) => {
    setTargetStoreId(storeId);
    setCrossStoreMappings([]);
    if (storeId) {
      loadTargetStoreData(storeId).then(() => {
        // 延迟建议，等待数据加载
        setTimeout(() => {
          autoSuggestMappings(targetStoreDepartments, targetStoreDoctors);
        }, 300);
      });
    } else {
      setTargetStoreDepartments([]);
      setTargetStoreDoctors([]);
    }
  }, [loadTargetStoreData, autoSuggestMappings, targetStoreDepartments, targetStoreDoctors]);

  // 过滤后的医生列表（同院区模式）
  const filteredDoctors = useMemo(() => {
    let list = allDoctors;
    if (sourceRule) {
      list = list.filter(d => d.id !== sourceRule.doctorId);
    }
    if (deptFilter) {
      list = list.filter(d => d.departmentId === deptFilter);
    }
    return list;
  }, [allDoctors, sourceRule, deptFilter]);

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
            setCrossStoreMappings(updated);
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
              setCrossStoreMappings(updated);
            }}
            options={availableDoctors.map(d => ({ label: d.name, value: d.id }))}
            disabled={!record.targetDepartmentId}
          />
        );
      },
    },
  ], [crossStoreMappings, targetStoreDepartments, targetStoreDoctors]);

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

  // 步骤导航
  const handleNext = () => setStep(1);
  const handlePrev = () => setStep(0);

  // 确认复制
  const handleConfirm = async () => {
    if (!sourceRule || !formData) {
      message.error(ScheduleMessages.copySourceNotFound);
      return;
    }

    setLoading(true);
    try {
      if (copyMode === 'same-store') {
        if (targetDoctorIds.length === 0) {
          message.error(ScheduleMessages.selectTargetDoctor);
          setLoading(false);
          return;
        }
        const result = await scheduleTemplateApi.copy(sourceRule.id, {
          targetDoctorIds,
          name: formData.name,
          weekdays: formData.weekdays,
          appointmentType: formData.appointmentType,
          startTime: formData.startTime,
          endTime: formData.endTime,
          slotCount: formData.slotCount,
          slotCapacity: formData.slotCapacity,
          scheduleMode: formData.scheduleMode,
          breakTimes: formData.breakTimes,
        });
        message.success(result.message);
      } else {
        const validMappings = crossStoreMappings.filter(
          (m) => m.targetDepartmentId && m.targetDoctorId
        );
        if (validMappings.length === 0) {
          message.error('请至少配置一个有效的科室/医生映射');
          setLoading(false);
          return;
        }
        const result = await scheduleTemplateApi.copyCrossStore(sourceRule.id, {
          targetStoreId: targetStoreId!,
          mappings: validMappings.map((m) => ({
            sourceDepartmentId: m.sourceDepartmentId,
            targetDepartmentId: m.targetDepartmentId!,
            targetDoctorId: m.targetDoctorId!,
          })),
          name: formData.name,
          weekdays: formData.weekdays,
          appointmentType: formData.appointmentType,
          startTime: formData.startTime,
          endTime: formData.endTime,
          slotCount: formData.slotCount,
          slotCapacity: formData.slotCapacity,
          scheduleMode: formData.scheduleMode,
          breakTimes: formData.breakTimes,
        });
        message.success(result.message);
        if (result.failedMappings && result.failedMappings.length > 0) {
          message.warning(`${result.failedMappings.length} 条映射因校验失败被跳过`);
        }
      }
      onSuccess();
    } catch (error: any) {
      message.error(error.message || ScheduleMessages.copyFailed);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal
      title="复制排班规则"
      open={open}
      onCancel={onClose}
      footer={
        <Space>
          <Button onClick={onClose}>取消</Button>
          {step === 0 ? (
            <Button type="primary" onClick={handleNext}>
              下一步
            </Button>
          ) : (
            <>
              <Button onClick={handlePrev}>上一步</Button>
              <Button
                type="primary"
                loading={loading}
                onClick={handleConfirm}
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
                复制来源：<strong>{sourceRule?.name}</strong>
                <span style={{ marginLeft: 16, color: '#666' }}>
                  医生：{sourceRule?.doctorName}
                </span>
                <span style={{ marginLeft: 16, color: '#666' }}>
                  门店：{sourceRule?.storeName}
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
              onChange={(e) => {
                setCopyMode(e.target.value);
                if (e.target.value === 'cross-store' && targetStoreId) {
                  loadTargetStoreData(targetStoreId);
                }
              }}
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
              setFormData(allValues as CopyRuleFormData);
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
              options={appointmentTypeOptions}
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
              onChange={(val) => setDeptFilter(val)}
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
            onChange={(nextTargetKeys) => setTargetDoctorIds(nextTargetKeys as string[])}
            render={(item) => (
              <span>
                {item.title}
                {item.description && (
                  <span style={{ color: TEXT_SECONDARY, fontSize: 12, marginLeft: 8 }}>
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
                .filter(s => s.id !== sourceRule?.storeId)
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
                <div style={{ padding: 24, textAlign: 'center', color: TEXT_SECONDARY }}>
                  未找到自动匹配的科室，请检查目标门店是否包含同名科室
                </div>
              )}
            </div>
          )}

          {!targetStoreId && (
            <div style={{ padding: 24, textAlign: 'center', color: TEXT_SECONDARY }}>
              请先选择目标门店
            </div>
          )}
        </div>
      )}
    </Modal>
  );
};

export default CopyRuleModal;
