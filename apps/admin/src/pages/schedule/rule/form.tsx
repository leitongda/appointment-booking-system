import { PageContainer, ProForm, ProFormText, ProFormSelect, ProFormDigit, ProFormTimePicker, ProFormRadio, ProFormCheckbox, FooterToolbar } from '@ant-design/pro-components';
import type { ProFormInstance } from '@ant-design/pro-components';
import { Card, App, Alert, Button, Space, Spin, Row, Col } from 'antd';
import { useEffect, useState, useMemo, useRef } from 'react';
import { history, useParams, useAccess, useModel } from '@umijs/max';
import { scheduleTemplateApi, storeApi, departmentApi, doctorApi } from '@hospital/api';
import type { ScheduleTemplate, Doctor, Department, Store } from '@hospital/shared';
import {
  APPOINTMENT_TYPE_OPTIONS,
  SCHEDULE_MODE_OPTIONS,
  WEEKDAY_OPTIONS,
  getDateInfo,
} from '@hospital/shared';
import RulePreviewCalendar from '../components/RulePreviewCalendar';
import dayjs from 'dayjs';

// 格式化时间为 HH:mm 格式
const formatTime = (time: any): string | undefined => {
  if (!time) return undefined;
  if (typeof time === 'string') {
    // 如果已经是字符串，检查格式是否正确
    return /^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$/.test(time) ? time : undefined;
  }
  // 如果是 dayjs 对象，直接格式化
  if (time?.format && typeof time.format === 'function') {
    return time.format('HH:mm');
  }
  // 尝试转换为 dayjs 对象
  try {
    return dayjs(time).format('HH:mm');
  } catch {
    return undefined;
  }
};

const ScheduleRuleFormPage: React.FC = () => {
  const { message } = App.useApp();
  const { id } = useParams();
  const access = useAccess();
  const { initialState } = useModel('@@initialState');
  const { currentUser } = initialState ?? {};
  const isSuperAdmin = access.canSuperAdmin;
  const isEdit = !!id;
  const [loading, setLoading] = useState(false);
  const [template, setTemplate] = useState<ScheduleTemplate | null>(null);
  const formRef = useRef<ProFormInstance>();

  const [stores, setStores] = useState<Store[]>([]);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [doctors, setDoctors] = useState<Doctor[]>([]);
  const [selectedDept, setSelectedDept] = useState<string>();

  // 表单值，用于实时更新日历预览
  const [formValues, setFormValues] = useState<any>({});

  const dateInfo = useMemo(() => getDateInfo(), []);

  useEffect(() => {
    loadStores();
    loadDepartments();
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

  const loadStores = async () => {
    try {
      const data = await storeApi.getAll();
      let storeList = data ?? [];
      // 非超管只显示其关联的门店
      if (!isSuperAdmin && currentUser?.storeIds?.length) {
        storeList = storeList.filter((s) => currentUser.storeIds?.includes(s.id));
      }
      setStores(storeList);
    } catch (error) {
      console.error('加载门店失败', error);
    }
  };

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

  const loadTemplate = async () => {
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
    } catch (error: any) {
      message.error('加载排班规则信息失败');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (values: any) => {
    console.log("🚀 ~ handleSubmit ~ values:", values)
    try {
      // 使用 formatTime 函数格式化时间，支持字符串和 dayjs 对象
      const startTime = formatTime(values.startTime);
      const endTime = formatTime(values.endTime);
      
      if (!startTime || !endTime) {
        message.error('请填写有效的开始时间和结束时间');
        return;
      }
      
      const data = {
        name: values.name,
        storeId: values.storeId,
        doctorId: values.doctorId,
        departmentId: values.departmentId,
        weekdays: values.weekdays || [],
        appointmentType: values.appointmentType,
        startTime,
        endTime,
        slotCount: values.slotCount || 1,
        slotCapacity: values.slotCapacity || 10,
        scheduleMode: values.scheduleMode,
      };

      if (isEdit && id) {
        await scheduleTemplateApi.update(id, data);
        message.success('更新成功');
      } else {
        await scheduleTemplateApi.create(data);
        message.success('创建成功');
      }
      history.push('/schedule/rule');
    } catch (error: any) {
      message.error(error.message || '操作失败');
    }
  };

  const handleValuesChange = (changedValues: any, allValues: any) => {
    setFormValues(allValues);
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
              showExisting={!!formValues.doctorId}
            />
          </Card>
        </Col>

        {/* 右侧表单 */}
        <Col span={12}>
          <ProForm
            formRef={formRef}
            onFinish={handleSubmit}
            onValuesChange={handleValuesChange}
            initialValues={initialValues}
            submitter={{
              render: (props, dom) => (
                <FooterToolbar>
                  <Space>
                    <Button onClick={() => history.back()}>取消</Button>
                    <Button type="primary" onClick={() => props.form?.submit()}>
                      {isEdit ? '保存' : '创建'}
                    </Button>
                  </Space>
                </FooterToolbar>
              ),
            }}
          >
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
                    onChange: (val) => setSelectedDept(val as string),
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
            </Card>

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
                  options={APPOINTMENT_TYPE_OPTIONS}
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
                  extra="每个班次可预约的人数"
                />
              </ProForm.Group>
            </Card>

            <Card title="排班方式" loading={loading}>
              <ProFormRadio.Group
                name="scheduleMode"
                options={SCHEDULE_MODE_OPTIONS}
                rules={[{ required: true, message: '请选择排班方式' }]}
              />
            </Card>
          </ProForm>
        </Col>
      </Row>
    </PageContainer>
  );
};

export default ScheduleRuleFormPage;

