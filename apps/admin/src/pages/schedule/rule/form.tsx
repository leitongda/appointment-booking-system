import { PageContainer, ProForm, ProFormText, ProFormSelect, ProFormDigit, ProFormTimePicker, ProFormRadio, ProFormCheckbox, FooterToolbar } from '@ant-design/pro-components';
import type { ProFormInstance } from '@ant-design/pro-components';
import { Card, App, Button, Space, Row, Col, Collapse, TimePicker, Divider, Typography, Steps, Alert } from 'antd';
import { PlusOutlined, DeleteOutlined, SettingOutlined } from '@ant-design/icons';
import { useEffect, useState, useMemo, useRef } from 'react';
import { history, useParams, useAccess } from '@umijs/max';
import { scheduleTemplateApi, departmentApi, doctorApi, shiftTypeApi, ruleSetApi } from '@hospital/api';
import type { ShiftType, RuleSet } from '@hospital/shared';
import { useStoreWithPermission } from '@/hooks/useStoreWithPermission';
import { fetchAllData } from '@/utils/fetchAllData';
import type { ScheduleTemplate, Doctor, Department, BreakTime } from '@hospital/shared';
import {
  SCHEDULE_MODE_OPTIONS,
  WEEKDAY_OPTIONS,
  getDateInfo,
} from '@hospital/shared';
import { useDict } from '@/hooks/useDict';
import RulePreviewCalendar from '../components/RulePreviewCalendar';
import dayjs from 'dayjs';
import { ScheduleMessages } from '../utils/message';

// 格式化时间为 HH:mm 格式
const formatTime = (time: string | { format: (fmt: string) => string } | null | undefined): string | undefined => {
  if (!time) return undefined;
  if (typeof time === 'string') {
    return /^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$/.test(time) ? time : undefined;
  }
  if (typeof time.format === 'function') {
    return time.format('HH:mm');
  }
  return undefined;
};

interface ScheduleRuleFormValues {
  name: string;
  storeId: string;
  departmentId?: string;
  doctorId: string;
  shiftTypeId?: string;
  weekdays: number[];
  appointmentType: string;
  startTime: dayjs.Dayjs;
  endTime: dayjs.Dayjs;
  slotCount?: number;
  slotCapacity?: number;
  scheduleMode: string;
  ruleSetId?: string;
  [key: string]: unknown;
}

const ScheduleRuleFormPage: React.FC = () => {
  const { message } = App.useApp();
  const { id } = useParams();
  const { options: appointmentTypeOptions } = useDict('appointment_type');
  useAccess();
  const { stores } = useStoreWithPermission({ enabledOnly: true });
  const isEdit = !!id;
  const [loading, setLoading] = useState(false);
  const [template, setTemplate] = useState<ScheduleTemplate | null>(null);
  const formRef = useRef<ProFormInstance>();

  const [departments, setDepartments] = useState<Department[]>([]);
  const [doctors, setDoctors] = useState<Doctor[]>([]);
  const [shiftTypes, setShiftTypes] = useState<ShiftType[]>([]);
  const [ruleSets, setRuleSets] = useState<RuleSet[]>([]);
  const [selectedDept, setSelectedDept] = useState<string>();

  // 表单值，用于实时更新日历预览
  const [formValues, setFormValues] = useState<Partial<ScheduleRuleFormValues>>({});
  
  // 排除时间段（午休时间等）
  const [breakTimes, setBreakTimes] = useState<{ startTime?: dayjs.Dayjs | null; endTime?: dayjs.Dayjs | null }[]>([]);
  const [currentStep, setCurrentStep] = useState(0);
  const [showGuide, setShowGuide] = useState(false);

  const _dateInfo = useMemo(() => getDateInfo(), []);

  // 首次访问显示引导提示
  useEffect(() => {
    const hasSeenGuide = localStorage.getItem('schedule_rule_form_guide_seen');
    if (!hasSeenGuide) {
      setShowGuide(true);
    }
  }, []);

  const dismissGuide = () => {
    localStorage.setItem('schedule_rule_form_guide_seen', 'true');
    setShowGuide(false);
  };

  async function loadDepartments() {
    try {
      // 获取所有启用的科室
      const allDepts = await fetchAllData((page, pageSize) =>
        departmentApi.getList({ page, pageSize, status: 1 })
      );
      setDepartments(allDepts);
    } catch (error) {
      console.error('加载科室失败', error);
    }
  }

  async function loadDoctorsByDept(deptId: string) {
    try {
      const data = await doctorApi.getByDepartment(deptId);
      setDoctors(data ?? []);
    } catch (error) {
      console.error('加载医生失败', error);
    }
  }

  async function loadShiftTypes() {
    try {
      const data = await shiftTypeApi.getEnabled();
      setShiftTypes(data ?? []);
    } catch (error) {
      console.error('加载班次类型失败', error);
    }
  }

  async function loadRuleSets() {
    try {
      const result = await ruleSetApi.getList({ enabled: true });
      setRuleSets(result?.data ?? []);
    } catch (error) {
      console.error('加载规则组失败', error);
    }
  }

  async function loadTemplate() {
    if (!id) return;
    setLoading(true);
    try {
      const data = await scheduleTemplateApi.getDetail(id);
      setTemplate(data);
      if (data.departmentId) {
        setSelectedDept(data.departmentId);
      }
      // 异步加载完成后，使用 setFieldsValue 更新表单值
      const formData = {
        ...data,
        weekdays: data.weekdays || [],
        slotCount: data.slotCount || 1,
        slotCapacity: data.slotCapacity || 10,
        startTime: data.startTime ? dayjs(data.startTime, 'HH:mm') : undefined,
        endTime: data.endTime ? dayjs(data.endTime, 'HH:mm') : undefined,
      };
      formRef.current?.setFieldsValue(formData);
      setFormValues(formData);
      
      // 加载排除时间段
      if (data.breakTimes && data.breakTimes.length > 0) {
        setBreakTimes(data.breakTimes.map(bt => ({
          startTime: bt.startTime ? dayjs(bt.startTime, 'HH:mm') : undefined,
          endTime: bt.endTime ? dayjs(bt.endTime, 'HH:mm') : undefined,
        })));
      }
    } catch (error: any) {
      message.error(error.message || ScheduleMessages.loadTemplateFailed);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadDepartments();
    loadShiftTypes();
    loadRuleSets();
    if (isEdit) {
      loadTemplate();
    }
  }, [id]);

  useEffect(() => {
    if (selectedDept) {
      loadDoctorsByDept(selectedDept);
    } else {
      setDoctors([]);
    }
  }, [selectedDept]);

  const handleSubmit = async (values: ScheduleRuleFormValues) => {
    try {
      // 使用 formatTime 函数格式化时间，支持字符串和 dayjs 对象
      const startTime = formatTime(values.startTime);
      const endTime = formatTime(values.endTime);

      if (!startTime || !endTime) {
        message.error(ScheduleMessages.validTimeRequired);
        return;
      }
      
      // 格式化排除时间段
      const formattedBreakTimes: BreakTime[] = breakTimes
        .filter(bt => bt.startTime && bt.endTime)
        .map(bt => ({
          startTime: formatTime(bt.startTime) || '',
          endTime: formatTime(bt.endTime) || '',
        }))
        .filter(bt => bt.startTime && bt.endTime);
      
      const data = {
        name: values.name!,
        storeId: values.storeId!,
        doctorId: values.doctorId!,
        departmentId: values.departmentId!,
        shiftTypeId: values.shiftTypeId!,
        weekdays: values.weekdays || [],
        appointmentType: values.appointmentType!,
        startTime,
        endTime,
        slotCount: values.slotCount || 1,
        slotCapacity: values.slotCapacity || 10,
        scheduleMode: values.scheduleMode!,
        breakTimes: formattedBreakTimes.length > 0 ? formattedBreakTimes : undefined,
        ruleSetId: values.ruleSetId || undefined,
      };

      if (isEdit && id) {
        await scheduleTemplateApi.update(id, data);
        message.success(ScheduleMessages.updateSuccess);
      } else {
        await scheduleTemplateApi.create(data);
        message.success(ScheduleMessages.createSuccess);
      }
      history.push('/medical-services/schedule/rule');
    } catch (error: any) {
      message.error(error.message || ScheduleMessages.operateFailed);
    }
  };

  const handleValuesChange = (_changedValues: Partial<ScheduleRuleFormValues>, allValues: ScheduleRuleFormValues) => {
    setFormValues(allValues);
  };

  const stepFields: string[][] = [
    ['name', 'storeId', 'departmentId', 'doctorId'],
    ['weekdays', 'appointmentType', 'startTime', 'endTime', 'slotCount', 'slotCapacity', 'scheduleMode'],
    [], // 高级设置无必填
  ];

  const handleStepChange = async (nextStep: number) => {
    if (nextStep > currentStep) {
      const fieldsToValidate = stepFields[currentStep];
      if (fieldsToValidate.length > 0) {
        try {
          await formRef.current?.validateFields(fieldsToValidate);
        } catch {
          message.error('请完善当前步骤的必填信息');
          return;
        }
      }
    }
    setCurrentStep(nextStep);
  };

  const initialValues = template ? {
    ...template,
    startTime: template.startTime ? dayjs(template.startTime, 'HH:mm') : undefined,
    endTime: template.endTime ? dayjs(template.endTime, 'HH:mm') : undefined,
  } : {
    appointmentType: 'normal',
    scheduleMode: 'weekly',
    slotCount: 1,
    slotCapacity: 10,
    weekdays: [],
  };

  return (
    <PageContainer title={isEdit ? '编辑排班规则' : '新增排班规则'}>
      <Row gutter={16}>
        {/* 左侧日历预览 */}
        <Col span={12}>
          <Card title="排班预览" style={{ position: 'sticky', top: 16 }}>
            <RulePreviewCalendar
              doctorId={formValues.doctorId}
              weekdays={formValues.weekdays || []}
              scheduleMode={formValues.scheduleMode}
              startTime={formatTime(formValues.startTime)}
              endTime={formatTime(formValues.endTime)}
              slotCount={formValues.slotCount || 1}
              breakTimes={breakTimes
                .filter(bt => bt.startTime && bt.endTime)
                .map(bt => ({
                  startTime: formatTime(bt.startTime) || '',
                  endTime: formatTime(bt.endTime) || '',
                }))
                .filter(bt => bt.startTime && bt.endTime)
              }
              showExisting={!!formValues.doctorId}
            />
          </Card>
        </Col>

        {/* 右侧表单 */}
        <Col span={12}>
          {showGuide && (
            <Alert
              title="排班规则配置引导"
              description="创建排班规则分为 3 步：基本信息 → 时间配置 → 高级设置。填写过程中左侧日历会实时预览排班效果。"
              type="info"
              showIcon
              closable
              onClose={dismissGuide}
              style={{ marginBottom: 16 }}
            />
          )}

          <Steps
            current={currentStep}
            onChange={handleStepChange}
            size="small"
            style={{ marginBottom: 16 }}
            items={[
              { title: '基本信息', content: '名称、门店、医生' },
              { title: '时间配置', content: '星期、时段、班次' },
              { title: '高级设置', content: '排除时间等' },
            ]}
          />

          <ProForm
            formRef={formRef}
            onFinish={handleSubmit}
            onValuesChange={handleValuesChange}
            initialValues={initialValues}
            submitter={{
              render: (props, _dom) => (
                <FooterToolbar>
                  <Space>
                    {currentStep > 0 && (
                      <Button onClick={() => handleStepChange(currentStep - 1)}>
                        上一步
                      </Button>
                    )}
                    {currentStep < 2 && (
                      <Button type="primary" onClick={() => handleStepChange(currentStep + 1)}>
                        下一步
                      </Button>
                    )}
                    {currentStep === 2 && (
                      <Button type="primary" onClick={() => props.form?.submit()}>
                        {isEdit ? '保存' : '创建'}
                      </Button>
                    )}
                    <Button onClick={() => history.back()}>取消</Button>
                  </Space>
                </FooterToolbar>
              ),
            }}
          >
            <div style={{ display: currentStep === 0 ? 'block' : 'none' }}>
              <Card title="基础信息" style={{ marginBottom: 16 }} loading={loading}>
              <ProFormText
                name="name"
                label="规则名称"
                width="lg"
                placeholder="如：张医生周一至周五上午门诊"
                rules={[{ required: true, message: '请输入规则名称' }]}
              />
              <ProForm.Group>
                <ProFormSelect
                  name="storeId"
                  label="所属门店"
                  width="md"
                  options={stores.map((s) => ({ label: s.name, value: s.id }))}
                  rules={[{ required: true, message: '请选择门店' }]}
                />
                <ProFormSelect
                  name="departmentId"
                  label="选择科室"
                  width="md"
                  options={departments.map((d) => ({ label: d.name, value: d.id }))}
                  fieldProps={{
                    onChange: (val) => {
                      setSelectedDept(val as string);
                      formRef.current?.setFieldValue('doctorId', undefined);
                    },
                  }}
                  rules={[{ required: true, message: '请选择科室' }]}
                />
              </ProForm.Group>
              <ProFormSelect
                name="doctorId"
                label="选择医生"
                width="md"
                options={doctors.map((d) => ({ label: `${d.name} - ${d.title || ''}`, value: d.id }))}
                rules={[{ required: true, message: '请选择医生' }]}
                disabled={!selectedDept}
                extra={!selectedDept ? '请先选择科室' : undefined}
              />
              <ProFormSelect
                name="shiftTypeId"
                label="班次类型"
                width="md"
                options={shiftTypes.filter(st => st.enabled).map((st) => ({ label: st.name, value: st.id }))}
                rules={[{ required: true, message: '请选择班次类型' }]}
                placeholder="请选择班次类型"
                extra={
                  <Button
                    type="link"
                    size="small"
                    style={{ padding: 0, height: 'auto' }}
                    onClick={() => window.open('/organization/medical-config/shift-types', '_blank')}
                  >
                    管理班次类型
                  </Button>
                }
              />
              <ProFormSelect
                name="ruleSetId"
                label="关联规则组"
                width="md"
                options={ruleSets.map((rs) => ({
                  label: `${rs.name} (优先级: ${rs.priority})`,
                  value: rs.id,
                }))}
                placeholder="不指定则按班次类型自动匹配"
                fieldProps={{
                  allowClear: true,
                  showSearch: true,
                  filterOption: (input: string, option?: { label?: string; value?: string }) =>
                    (option?.label ?? '').toLowerCase().includes(input.toLowerCase()),
                }}
                tooltip="指定规则组后，该模板生成的排班将使用此规则组的预约/签到/取消策略"
              />
            </Card>
            </div>

            <div style={{ display: currentStep === 1 ? 'block' : 'none' }}>
            <Card title="排班设置" style={{ marginBottom: 16 }} loading={loading}>
              <ProFormCheckbox.Group
                name="weekdays"
                label="选择星期"
                options={WEEKDAY_OPTIONS}
                rules={[{ required: true, message: '请选择星期' }]}
              />
              <ProForm.Group>
                <ProFormSelect
                  name="appointmentType"
                  label="预约类型"
                  width="md"
                  options={appointmentTypeOptions}
                  rules={[{ required: true, message: '请选择预约类型' }]}
                />
              </ProForm.Group>
              <ProForm.Group>
                <ProFormTimePicker
                  name="startTime"
                  label="开始时间"
                  width="sm"
                  fieldProps={{ format: 'HH:mm' }}
                  rules={[{ required: true, message: '请选择开始时间' }]}
                />
                <ProFormTimePicker
                  name="endTime"
                  label="结束时间"
                  width="sm"
                  fieldProps={{ format: 'HH:mm' }}
                  rules={[{ required: true, message: '请选择结束时间' }]}
                />
              </ProForm.Group>
              <ProForm.Group>
                <ProFormDigit
                  name="slotCount"
                  label="班次数量"
                  width="sm"
                  min={1}
                  max={50}
                  rules={[{ required: true, message: '请输入班次数量' }]}
                  extra="根据时间区间均分生成多个班次"
                />
                <ProFormDigit
                  name="slotCapacity"
                  label="班次人数"
                  width="sm"
                  min={1}
                  max={200}
                  rules={[{ required: true, message: '请输入班次人数' }]}
                  extra="每个班次可生成的号源数量。例如设置为 10，则该班次可接受 10 个预约。注意：此为号源物理上限，如需限制预约频率，请在规则组的容量策略中配置。"
                />
              </ProForm.Group>
            </Card>

            <Card title="排班方式" style={{ marginBottom: 16 }} loading={loading}>
              <ProFormRadio.Group
                name="scheduleMode"
                options={SCHEDULE_MODE_OPTIONS}
                rules={[{ required: true, message: '请选择排班方式' }]}
              />
            </Card>
            </div>

            <div style={{ display: currentStep === 2 ? 'block' : 'none' }}>
            <Collapse
              items={[
                {
                  key: 'advanced',
                  label: (
                    <Space>
                      <SettingOutlined />
                      <span>高级设置</span>
                      {breakTimes.length > 0 && (
                        <Typography.Text type="secondary">
                          (已配置 {breakTimes.length} 个排除时间段)
                        </Typography.Text>
                      )}
                    </Space>
                  ),
                  children: (
                    <div>
                      <Typography.Text type="secondary" style={{ display: 'block', marginBottom: 16 }}>
                        设置排除时间段（如午休时间），生成班次时会自动跳过这些时间段
                      </Typography.Text>
                      
                      {breakTimes.map((bt, index) => (
                        <div key={index} style={{ display: 'flex', alignItems: 'center', marginBottom: 12, gap: 8 }}>
                          <TimePicker
                            placeholder="开始时间"
                            format="HH:mm"
                            value={bt.startTime}
                            onChange={(val) => {
                              const newBreakTimes = [...breakTimes];
                              newBreakTimes[index] = { ...newBreakTimes[index], startTime: val };
                              setBreakTimes(newBreakTimes);
                            }}
                            style={{ width: 120 }}
                          />
                          <span>至</span>
                          <TimePicker
                            placeholder="结束时间"
                            format="HH:mm"
                            value={bt.endTime}
                            onChange={(val) => {
                              const newBreakTimes = [...breakTimes];
                              newBreakTimes[index] = { ...newBreakTimes[index], endTime: val };
                              setBreakTimes(newBreakTimes);
                            }}
                            style={{ width: 120 }}
                          />
                          <Button
                            type="text"
                            danger
                            icon={<DeleteOutlined />}
                            onClick={() => {
                              const newBreakTimes = breakTimes.filter((_, i) => i !== index);
                              setBreakTimes(newBreakTimes);
                            }}
                          />
                        </div>
                      ))}
                      
                      <Button
                        type="dashed"
                        onClick={() => setBreakTimes([...breakTimes, { startTime: undefined, endTime: undefined }])}
                        icon={<PlusOutlined />}
                        style={{ width: '100%' }}
                      >
                        添加排除时间段
                      </Button>
                      
                      <Divider />
                      
                      <Typography.Text type="secondary">
                        <strong>示例：</strong>如果工作时间是 09:00-18:00，午休时间是 12:00-13:30，
                        班次数量设为 4，则会在 09:00-12:00 和 13:30-18:00 期间均匀分配 4 个班次。
                      </Typography.Text>
                    </div>
                  ),
                },
              ]}
              style={{ marginBottom: 16 }}
            />
            </div>
          </ProForm>
        </Col>
      </Row>
    </PageContainer>
  );
};

export default ScheduleRuleFormPage;

