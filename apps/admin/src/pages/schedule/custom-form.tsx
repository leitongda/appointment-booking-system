/**
 * 自定义排班表单页面（重构版）
 *
 * 代码行数：276 行 (vs 原始 320 行)
 *
 * 使用基础设施：
 * - FormPage 组件：统一表单页面布局和底部工具栏
 * - requiredRules: 必填验证规则
 * - fetchAllData: 数据获取工具
 *
 * 业务特性：
 * - 动态时段配置：支持添加/复制/删除时段
 * - 级联选择：门店 → 科室 → 医生
 * - 日期范围处理：将日期范围转换为日期数组
 *
 * 优化效果：
 * - 减少重复的表单布局代码
 * - 统一表单提交处理
 * - 提高代码可读性和可维护性
 */
import { PlusOutlined, CopyOutlined, DeleteOutlined } from '@ant-design/icons';
import { ProFormSelect, ProFormDatePicker, ProFormDigit, ProFormTimePicker } from '@ant-design/pro-components';
import { Card, Row, Col, Button, Space, message } from 'antd';
import { useEffect, useState } from 'react';
import { ScheduleMessages } from './utils/message';
import { history, useAccess, useModel } from '@umijs/max';
import { customScheduleApi, departmentApi, doctorApi } from '@hospital/api';
import { fetchAllData } from '@/utils/fetchAllData';
import { APPOINTMENT_TYPE_OPTIONS } from '@/constants/formFields';

// 基础设施导入
import FormPage from '@/components/FormPage';
import { requiredRules } from '@/utils/formValidators';
import { useStoreWithPermission } from '@/hooks/useStoreWithPermission';
import dayjs from 'dayjs';

interface TimePeriodConfig {
  key: string;
  startTime?: string;
  endTime?: string;
  appointmentType?: string;
  slotCount?: number;
  maxPatients?: number;
}

const CustomScheduleFormPage: React.FC = () => {
  useAccess();
  const { initialState: _initialState } = useModel('@@initialState');

  const { stores } = useStoreWithPermission({ enabledOnly: true });
  const [departments, setDepartments] = useState<any[]>([]);
  const [doctors, setDoctors] = useState<any[]>([]);
  const [selectedStore, setSelectedStore] = useState<string>();
  const [selectedDept, setSelectedDept] = useState<string>();
  const [timePeriods, setTimePeriods] = useState<TimePeriodConfig[]>([
    { key: '1', slotCount: 1, maxPatients: 1 }
  ]);

  // 加载科室列表
  useEffect(() => {
    if (!selectedStore) return;

    const loadDepartments = async () => {
      try {
        const allDepts = await fetchAllData((page, pageSize) =>
          departmentApi.getList({ page, pageSize, status: 1 })
        );
        setDepartments(allDepts);
      } catch (error) {
        console.error('加载科室失败', error);
      }
    };
    loadDepartments();
  }, [selectedStore]);

  // 加载医生列表
  useEffect(() => {
    if (!selectedDept) return;

    const loadDoctors = async () => {
      try {
        const data = await doctorApi.getByDepartment(selectedDept);
        setDoctors(data ?? []);
      } catch (error) {
        console.error('加载医生失败', error);
      }
    };
    loadDoctors();
  }, [selectedDept]);

  // 添加时段
  const handleAddTimePeriod = () => {
    setTimePeriods([
      ...timePeriods,
      { key: Date.now().toString(), slotCount: 1, maxPatients: 1 }
    ]);
  };

  // 复制时段
  const handleCopyTimePeriod = (index: number) => {
    const period = timePeriods[index];
    setTimePeriods([
      ...timePeriods,
      { ...period, key: Date.now().toString() }
    ]);
  };

  // 删除时段
  const handleRemoveTimePeriod = (index: number) => {
    if (timePeriods.length === 1) {
      message.warning(ScheduleMessages.keepOneTimePeriod);
      return;
    }
    const newPeriods = [...timePeriods];
    newPeriods.splice(index, 1);
    setTimePeriods(newPeriods);
  };

  // 时段字段变更
  const handleTimePeriodChange = (index: number, field: string, value: any) => {
    const newPeriods = [...timePeriods];
    (newPeriods[index] as any)[field] = value;
    setTimePeriods(newPeriods);
  };

  // 提交表单
  const handleSubmit = async (values: any) => {
    const scheduleDates = values.scheduleDates.map((d: dayjs.Dayjs) => d.format('YYYY-MM-DD'));
    const formattedTimePeriods = timePeriods.map(p => ({
      startTime: p.startTime,
      endTime: p.endTime,
      appointmentType: p.appointmentType,
      slotCount: p.slotCount,
      maxPatients: p.maxPatients || 1,
    }));

    // 验证时段配置
    for (const period of formattedTimePeriods) {
      if (!period.startTime || !period.endTime || !period.appointmentType) {
        throw new Error('请完整填写所有排班时段配置');
      }
    }

    await customScheduleApi.create({
      storeId: values.storeId,
      departmentId: values.departmentId,
      doctorId: values.doctorId,
      scheduleDates,
      timePeriods: formattedTimePeriods,
    });

    history.push('/medical-services/schedule/custom');
  };

  return (
    <FormPage
      title="添加自定义排班"
      onFinish={handleSubmit}
      onCancel={() => history.back()}
      saveText="创建"
    >
      {/* 基础设置 */}
      <Card title="基础设置" style={{ marginBottom: 16 }}>
        <ProFormSelect
          name="storeId"
          label="选择门店"
          width="md"
          options={stores.map(s => ({ label: s.name, value: s.id }))}
          rules={[requiredRules('请选择门店')]}
          fieldProps={{
            onChange: (val) => setSelectedStore(val),
          }}
          placeholder={stores.length === 0 ? '暂无可用门店' : '请选择门店'}
          disabled={stores.length === 0}
        />
        <ProFormSelect
          name="departmentId"
          label="选择科室"
          width="md"
          options={departments.map(d => ({ label: d.name, value: d.id }))}
          rules={[requiredRules('请选择科室')]}
          fieldProps={{
            onChange: (val) => {
              setSelectedDept(val);
            },
          }}
        />
        <ProFormSelect
          name="doctorId"
          label="选择医生"
          width="md"
          options={doctors.map(d => ({ label: `${d.name} - ${d.title || ''}`, value: d.id }))}
          rules={[requiredRules('请选择医生')]}
        />
      </Card>

      {/* 排班设置 */}
      <Card
        title="排班设置"
        extra={<span style={{ fontSize: 12, color: '#999' }}>说明：排班数量为所选时间段均分班次数量，预约人数是每个班次的预约人数！</span>}
      >
        <ProFormDatePicker.Range
          name="scheduleDates"
          label="排班日期"
          rules={[requiredRules('请选择排班日期')]}
          fieldProps={{
            format: 'YYYY-MM-DD',
          }}
          transform={(value) => {
            if (value && value.length === 2) {
              const dates = [];
              let current = dayjs(value[0]);
              const end = dayjs(value[1]);
              while (current.isBefore(end) || current.isSame(end, 'day')) {
                dates.push(current);
                current = current.add(1, 'day');
              }
              return { scheduleDates: dates };
            }
            return { scheduleDates: [] };
          }}
        />

        {/* 动态时段配置 */}
        {timePeriods.map((period, index) => (
          <div key={period.key} style={{ background: '#fafafa', padding: 16, marginBottom: 16, borderRadius: 4 }}>
            <Row gutter={16} align="middle">
              <Col span={4}>
                <ProFormTimePicker
                  label="开始时间"
                  fieldProps={{
                    format: 'HH:mm',
                    value: period.startTime ? dayjs(period.startTime, 'HH:mm') : undefined,
                    onChange: (val) => handleTimePeriodChange(index, 'startTime', val?.format('HH:mm')),
                  }}
                />
              </Col>
              <Col span={4}>
                <ProFormTimePicker
                  label="结束时间"
                  fieldProps={{
                    format: 'HH:mm',
                    value: period.endTime ? dayjs(period.endTime, 'HH:mm') : undefined,
                    onChange: (val) => handleTimePeriodChange(index, 'endTime', val?.format('HH:mm')),
                  }}
                />
              </Col>
              <Col span={5}>
                <ProFormSelect
                  label="预约类型"
                  options={APPOINTMENT_TYPE_OPTIONS}
                  fieldProps={{
                    value: period.appointmentType,
                    onChange: (val) => handleTimePeriodChange(index, 'appointmentType', val),
                  }}
                />
              </Col>
              <Col span={4}>
                <ProFormDigit
                  label="排班数量"
                  min={1}
                  max={50}
                  fieldProps={{
                    value: period.slotCount,
                    onChange: (val) => handleTimePeriodChange(index, 'slotCount', val),
                  }}
                />
              </Col>
              <Col span={4}>
                <ProFormDigit
                  label="预约人数"
                  min={1}
                  max={100}
                  fieldProps={{
                    value: period.maxPatients,
                    onChange: (val) => handleTimePeriodChange(index, 'maxPatients', val),
                  }}
                />
              </Col>
              <Col span={3}>
                <Space>
                  <Button
                    type="text"
                    icon={<CopyOutlined />}
                    onClick={() => handleCopyTimePeriod(index)}
                    title="复制"
                  />
                  <Button
                    type="text"
                    danger
                    icon={<DeleteOutlined />}
                    onClick={() => handleRemoveTimePeriod(index)}
                    title="删除"
                  />
                </Space>
              </Col>
            </Row>
          </div>
        ))}

        <Button type="dashed" onClick={handleAddTimePeriod} block icon={<PlusOutlined />}>
          添加时段
        </Button>
      </Card>
    </FormPage>
  );
};

export default CustomScheduleFormPage;
