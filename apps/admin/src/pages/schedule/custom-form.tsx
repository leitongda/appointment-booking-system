import { PlusOutlined, CopyOutlined, DeleteOutlined } from '@ant-design/icons';
import { PageContainer, ProForm, ProFormSelect, ProFormDatePicker, ProFormDigit, ProFormTimePicker, FooterToolbar } from '@ant-design/pro-components';
import type { ProFormInstance } from '@ant-design/pro-components';
import { Card, App, Row, Col, Button, Space } from 'antd';
import { useEffect, useState, useRef } from 'react';
import { history, useAccess, useModel } from '@umijs/max';
import { customScheduleApi, storeApi, departmentApi, doctorApi } from '@hospital/api';
import { APPOINTMENT_TYPE_OPTIONS } from '@hospital/shared';
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
  const { message } = App.useApp();
  const access = useAccess();
  const { initialState } = useModel('@@initialState');
  const { currentUser, currentStore } = initialState ?? {};
  const isSuperAdmin = access.canSuperAdmin;
  const formRef = useRef<ProFormInstance>();
  const [stores, setStores] = useState<any[]>([]);
  const [departments, setDepartments] = useState<any[]>([]);
  const [doctors, setDoctors] = useState<any[]>([]);
  const [selectedStore, setSelectedStore] = useState<string>();
  const [selectedDept, setSelectedDept] = useState<string>();
  const [timePeriods, setTimePeriods] = useState<TimePeriodConfig[]>([
    { key: '1', slotCount: 1, maxPatients: 1 }
  ]);

  useEffect(() => {
    loadStores();
  }, []);

  useEffect(() => {
    if (selectedStore) {
      loadDepartmentsByStore(selectedStore);
    }
  }, [selectedStore]);

  useEffect(() => {
    if (selectedDept) {
      loadDoctorsByDept(selectedDept);
    }
  }, [selectedDept]);

  const loadStores = async () => {
    try {
      const res = await storeApi.getList({ pageSize: 100, status: 1 });
      let storeList = res.data ?? [];
      // 非超管只显示其关联的门店
      if (!isSuperAdmin && currentUser?.storeIds?.length) {
        storeList = storeList.filter((s) => currentUser.storeIds?.includes(s.id));
      }
      setStores(storeList);
    } catch (error) {
      console.error('加载门店失败', error);
    }
  };

  const loadDepartmentsByStore = async (storeId: string) => {
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

  const handleAddTimePeriod = () => {
    setTimePeriods([
      ...timePeriods,
      { key: Date.now().toString(), slotCount: 1, maxPatients: 1 }
    ]);
  };

  const handleCopyTimePeriod = (index: number) => {
    const period = timePeriods[index];
    setTimePeriods([
      ...timePeriods,
      { ...period, key: Date.now().toString() }
    ]);
  };

  const handleRemoveTimePeriod = (index: number) => {
    if (timePeriods.length === 1) {
      message.warning('至少保留一个排班时段');
      return;
    }
    const newPeriods = [...timePeriods];
    newPeriods.splice(index, 1);
    setTimePeriods(newPeriods);
  };

  const handleTimePeriodChange = (index: number, field: string, value: any) => {
    const newPeriods = [...timePeriods];
    (newPeriods[index] as any)[field] = value;
    setTimePeriods(newPeriods);
  };

  const handleSubmit = async (values: any) => {
    try {
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
          message.error('请完整填写所有排班时段配置');
          return;
        }
      }

      await customScheduleApi.create({
        storeId: values.storeId,
        departmentId: values.departmentId,
        doctorId: values.doctorId,
        scheduleDates,
        timePeriods: formattedTimePeriods,
      });
      message.success('创建成功');
      history.push('/schedule/custom');
    } catch (error: any) {
      message.error(error.message || '创建失败');
    }
  };

  return (
    <PageContainer title="添加自定义排班">
      <ProForm
        formRef={formRef}
        onFinish={handleSubmit}
        submitter={{
          render: (props, dom) => (
            <FooterToolbar>
              <Space>
                <Button onClick={() => history.back()}>取消</Button>
                <Button type="primary" onClick={() => props.form?.submit()}>
                  创建
                </Button>
              </Space>
            </FooterToolbar>
          ),
        }}
      >
        <Card title="基础设置" style={{ marginBottom: 16 }}>
          <ProForm.Group>
            <ProFormSelect
              name="storeId"
              label="选择门店"
              width="md"
              options={stores.map(s => ({ label: s.name, value: s.id }))}
              rules={[{ required: true, message: '请选择门店' }]}
              fieldProps={{
                onChange: (val) => setSelectedStore(val),
              }}
            />
            <ProFormSelect
              name="departmentId"
              label="选择科室"
              width="md"
              options={departments.map(d => ({ label: d.name, value: d.id }))}
              rules={[{ required: true, message: '请选择科室' }]}
              fieldProps={{
                onChange: (val) => {
                  setSelectedDept(val);
                  formRef.current?.setFieldValue('doctorId', undefined);
                },
              }}
            />
            <ProFormSelect
              name="doctorId"
              label="选择医生"
              width="md"
              options={doctors.map(d => ({ label: `${d.name} - ${d.title || ''}`, value: d.id }))}
              rules={[{ required: true, message: '请选择医生' }]}
            />
          </ProForm.Group>
        </Card>

        <Card 
          title="排班设置" 
          extra={<span style={{ fontSize: 12, color: '#999' }}>说明：排班数量为所选时间段均分班次数量，预约人数是每个班次的预约人数！</span>}
        >
          <ProFormDatePicker.Range
            name="scheduleDates"
            label="排班日期"
            rules={[{ required: true, message: '请选择排班日期' }]}
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
      </ProForm>
    </PageContainer>
  );
};

export default CustomScheduleFormPage;

