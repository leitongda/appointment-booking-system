import { PageContainer, ProForm, ProFormText, ProFormSelect, ProFormDigit, ProFormTimePicker, ProFormRadio, FooterToolbar } from '@ant-design/pro-components';
import type { ProFormInstance } from '@ant-design/pro-components';
import { Card, App, Alert, Button, Space, Spin } from 'antd';
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
import dayjs from 'dayjs';

const ScheduleTemplateFormPage: React.FC = () => {
  const { message } = App.useApp();
  const { id } = useParams<{ id: string }>();
  const access = useAccess();
  const { initialState } = useModel('@@initialState');
  const { currentUser, currentStore } = initialState ?? {};
  const isSuperAdmin = access.canSuperAdmin;
  const isEdit = !!id;
  const [loading, setLoading] = useState(false);
  const [template, setTemplate] = useState<ScheduleTemplate | null>(null);
  const formRef = useRef<ProFormInstance>();

  const [stores, setStores] = useState<Store[]>([]);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [doctors, setDoctors] = useState<Doctor[]>([]);
  const [selectedDept, setSelectedDept] = useState<string>();

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
      formRef.current?.setFieldsValue({
        ...data,
        startTime: data.startTime ? dayjs(data.startTime, 'HH:mm') : undefined,
        endTime: data.endTime ? dayjs(data.endTime, 'HH:mm') : undefined,
      });
    } catch (error: any) {
      message.error('加载排班模板信息失败');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (values: any) => {
    try {
      // 验证必填字段
      if (!values.startTime || !values.endTime) {
        message.error('请填写开始时间和结束时间');
        return;
      }
      
      // 格式化时间，确保有效性
      const startTimeFormatted = dayjs(values.startTime);
      const endTimeFormatted = dayjs(values.endTime);
      
      if (!startTimeFormatted.isValid() || !endTimeFormatted.isValid()) {
        message.error('开始时间和结束时间格式不正确');
        return;
      }
      
      const startTime = startTimeFormatted.format('HH:mm');
      const endTime = endTimeFormatted.format('HH:mm');
      
      // 将 weekday（单数）转换为 weekdays（复数数组）
      const weekdays = values.weekday ? [values.weekday] : [];
      
      const data = {
        name: values.name,
        storeId: values.storeId,
        doctorId: values.doctorId,
        departmentId: values.departmentId,
        weekdays, // 使用 weekdays 数组
        appointmentType: values.appointmentType,
        startTime,
        endTime,
        slotCount: 1, // 默认班次数量为 1
        slotCapacity: values.totalSlots || 10, // totalSlots 对应后端的 slotCapacity
        scheduleMode: values.scheduleMode,
      };

      if (isEdit && id) {
        await scheduleTemplateApi.update(id, data);
        message.success('更新成功');
      } else {
        await scheduleTemplateApi.create(data);
        message.success('创建成功');
      }
      history.push('/schedule/template');
    } catch (error: any) {
      message.error(error.message || '操作失败');
    }
  };

  const initialValues = template ? {
    ...template,
  } : {
    appointmentType: 'normal',
    scheduleMode: 'weekly',
    totalSlots: 10,
  };

  return (
    <PageContainer title={isEdit ? '编辑排班模板' : '新增排班模板'}>
      <Alert
        message={
          <span>
            当前日期：{new Date().toLocaleDateString('zh-CN')}，
            为本月第<strong>{dateInfo.monthWeek}</strong>周，
            本周为本年<strong>{dateInfo.isOddWeek ? '奇数' : '偶数'}</strong>周（第{dateInfo.yearWeek}周）
          </span>
        }
        type="info"
        showIcon
        style={{ marginBottom: 16 }}
      />

      <ProForm
        formRef={formRef}
        onFinish={handleSubmit}
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
            label="模板名称"
            width="lg"
            placeholder="如：某医生周一上午普通门诊"
            rules={[{ required: true, message: '请输入模板名称' }]}
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
        </Card>

        <Card title="排班设置" style={{ marginBottom: 16 }} loading={loading}>
          <ProForm.Group>
            <ProFormSelect
              name="weekday"
              label="选择星期"
              width="md"
              options={WEEKDAY_OPTIONS}
              rules={[{ required: true, message: '请选择星期' }]}
            />
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
            <ProFormDigit
              name="totalSlots"
              label="班次人数"
              width="sm"
              min={1}
              max={200}
              rules={[{ required: true, message: '请输入班次人数' }]}
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
    </PageContainer>
  );
};

export default ScheduleTemplateFormPage;

