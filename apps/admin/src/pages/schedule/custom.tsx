import { PlusOutlined, CopyOutlined, DeleteOutlined, SearchOutlined } from '@ant-design/icons';
import type { ActionType, ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable, ModalForm, ProFormSelect, ProFormDatePicker, ProFormDigit, ProFormTimePicker } from '@ant-design/pro-components';
import { Button, App, Space, Tag, Popconfirm, Card, Form, Row, Col, DatePicker, Select } from 'antd';
import { useRef, useState, useEffect } from 'react';
import { customScheduleApi, storeApi, departmentApi, doctorApi } from '@hospital/api';
import { toProTableResult } from '@/utils/proTable';
import { APPOINTMENT_TYPE_OPTIONS, APPOINTMENT_TYPE_MAP } from '@hospital/shared';
import type { CustomSchedule } from '@hospital/api';
import dayjs from 'dayjs';

interface TimePeriodConfig {
  key: string;
  startTime?: string;
  endTime?: string;
  appointmentType?: string;
  slotCount?: number;
  maxPatients?: number;
}

const CustomSchedulePage: React.FC = () => {
  const { message } = App.useApp();
  const actionRef = useRef<ActionType>();
  const [modalOpen, setModalOpen] = useState(false);
  const [effectiveModalOpen, setEffectiveModalOpen] = useState(false);
  const [stores, setStores] = useState<any[]>([]);
  const [departments, setDepartments] = useState<any[]>([]);
  const [doctors, setDoctors] = useState<any[]>([]);
  const [selectedStore, setSelectedStore] = useState<string>();
  const [selectedDept, setSelectedDept] = useState<string>();
  const [timePeriods, setTimePeriods] = useState<TimePeriodConfig[]>([
    { key: '1', slotCount: 1, maxPatients: 1 }
  ]);
  const [effectiveSchedules, setEffectiveSchedules] = useState<CustomSchedule[]>([]);
  const [effectiveDoctors, setEffectiveDoctors] = useState<any[]>([]);
  const [form] = Form.useForm();

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
      setStores(res.data ?? []);
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

  const loadDoctorsByStore = async (storeId: string) => {
    try {
      const res = await doctorApi.getList({ storeId, pageSize: 100, status: 1 });
      setEffectiveDoctors(res.data ?? []);
    } catch (error) {
      console.error('加载医生失败', error);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await customScheduleApi.delete(id);
      message.success('删除成功');
      actionRef.current?.reload();
    } catch (error: any) {
      message.error(error.message || '删除失败');
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
          return false;
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
      setModalOpen(false);
      setTimePeriods([{ key: '1', slotCount: 1, maxPatients: 1 }]);
      actionRef.current?.reload();
      return true;
    } catch (error: any) {
      message.error(error.message || '创建失败');
      return false;
    }
  };

  const handleQueryEffective = async () => {
    const values = form.getFieldsValue();
    if (!values.effectiveStartDate || !values.effectiveEndDate) {
      message.warning('请选择查询日期范围');
      return;
    }
    try {
      const result = await customScheduleApi.getEffective({
        storeId: values.effectiveStoreId,
        doctorId: values.effectiveDoctorId,
        startDate: values.effectiveStartDate.format('YYYY-MM-DD'),
        endDate: values.effectiveEndDate.format('YYYY-MM-DD'),
      });
      setEffectiveSchedules(result);
      setEffectiveModalOpen(true);
    } catch (error: any) {
      message.error(error.message || '查询失败');
    }
  };

  const columns: ProColumns<CustomSchedule>[] = [
    {
      title: '门店',
      dataIndex: 'storeName',
      width: 120,
    },
    {
      title: '科室',
      dataIndex: 'departmentName',
      width: 100,
    },
    {
      title: '医生',
      dataIndex: 'doctorName',
      width: 80,
    },
    {
      title: '日期',
      dataIndex: 'scheduleDate',
      width: 110,
      valueType: 'date',
    },
    {
      title: '时段',
      width: 120,
      search: false,
      render: (_, record) => `${record.startTime?.slice(0, 5) || ''}-${record.endTime?.slice(0, 5) || ''}`,
    },
    {
      title: '预约类型',
      dataIndex: 'appointmentType',
      width: 80,
      render: (_, record) => (
        <Tag color="blue">{APPOINTMENT_TYPE_MAP[record.appointmentType] || record.appointmentType}</Tag>
      ),
    },
    {
      title: '预约人数',
      dataIndex: 'maxPatients',
      width: 80,
      search: false,
    },
    {
      title: '已预约',
      dataIndex: 'bookedCount',
      width: 70,
      search: false,
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 80,
      valueEnum: {
        1: { text: '启用', status: 'Success' },
        0: { text: '停用', status: 'Error' },
      },
    },
    {
      title: '创建时间',
      dataIndex: 'createdAt',
      width: 160,
      valueType: 'dateTime',
      search: false,
    },
    {
      title: '操作',
      valueType: 'option',
      width: 80,
      render: (_, record) => (
        <Popconfirm 
          title="确定删除该排班吗？" 
          onConfirm={() => handleDelete(record.id)}
          disabled={record.bookedCount > 0}
        >
          <a style={{ color: record.bookedCount > 0 ? '#ccc' : '#ff4d4f' }}>
            删除
          </a>
        </Popconfirm>
      ),
    },
  ];

  const effectiveColumns: ProColumns<CustomSchedule>[] = [
    { title: '门店', dataIndex: 'storeName', width: 120 },
    { title: '医生', dataIndex: 'doctorName', width: 80 },
    { title: '日期', dataIndex: 'scheduleDate', width: 110 },
    { title: '时段', width: 120, render: (_, r) => `${r.startTime?.slice(0, 5) || ''}-${r.endTime?.slice(0, 5) || ''}` },
    { title: '预约类型', dataIndex: 'appointmentType', width: 80, render: (_, r) => APPOINTMENT_TYPE_MAP[r.appointmentType] || r.appointmentType },
    { title: '预约人数', dataIndex: 'maxPatients', width: 80 },
    { title: '已预约', dataIndex: 'bookedCount', width: 70 },
  ];

  return (
    <PageContainer>
      <Card title="生效班次查询" style={{ marginBottom: 16 }}>
        <Form form={form} layout="inline">
          <Form.Item name="effectiveStoreId" label="门店">
            <Select
              style={{ width: 160 }}
              options={stores.map(s => ({ label: s.name, value: s.id }))}
              placeholder="请选择门店"
              allowClear
              onChange={(val) => {
                form.setFieldValue('effectiveDoctorId', undefined);
                if (val) {
                  loadDoctorsByStore(val);
                } else {
                  setEffectiveDoctors([]);
                }
              }}
            />
          </Form.Item>
          <Form.Item name="effectiveDoctorId" label="医生">
            <Select
              style={{ width: 160 }}
              options={effectiveDoctors.map(d => ({ label: d.name, value: d.id }))}
              placeholder="请选择医生"
              allowClear
            />
          </Form.Item>
          <Form.Item name="effectiveStartDate" label="开始日期">
            <DatePicker />
          </Form.Item>
          <Form.Item name="effectiveEndDate" label="结束日期">
            <DatePicker />
          </Form.Item>
          <Form.Item>
            <Button type="primary" icon={<SearchOutlined />} onClick={handleQueryEffective}>
              查询
            </Button>
          </Form.Item>
        </Form>
      </Card>

      <ProTable<CustomSchedule>
        headerTitle="自定义排班列表"
        actionRef={actionRef}
        rowKey="id"
        columns={columns}
        request={async (params) => {
          const { current, pageSize, ...rest } = params;
          return toProTableResult(await customScheduleApi.getList({
            ...rest,
            page: current,
            pageSize,
          }));
        }}
        toolBarRender={() => [
          <Button
            key="add"
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => setModalOpen(true)}
          >
            添加
          </Button>,
        ]}
        pagination={{ defaultPageSize: 10 }}
      />

      <ModalForm
        title="添加自定义排班"
        open={modalOpen}
        onOpenChange={setModalOpen}
        onFinish={handleSubmit}
        modalProps={{ destroyOnHidden: true, width: 800 }}
        initialValues={{ maxPatients: 1, slotCount: 1 }}
      >
        <Card title="基础设置" size="small" style={{ marginBottom: 16 }}>
          <Row gutter={16}>
            <Col span={8}>
              <ProFormSelect
                name="storeId"
                label="选择门店"
                options={stores.map(s => ({ label: s.name, value: s.id }))}
                rules={[{ required: true, message: '请选择门店' }]}
                fieldProps={{
                  onChange: (val) => setSelectedStore(val),
                }}
              />
            </Col>
            <Col span={8}>
              <ProFormSelect
                name="departmentId"
                label="选择科室"
                options={departments.map(d => ({ label: d.name, value: d.id }))}
                rules={[{ required: true, message: '请选择科室' }]}
                fieldProps={{
                  onChange: (val) => setSelectedDept(val),
                }}
              />
            </Col>
            <Col span={8}>
              <ProFormSelect
                name="doctorId"
                label="选择医生"
                options={doctors.map(d => ({ label: `${d.name} - ${d.title || ''}`, value: d.id }))}
                rules={[{ required: true, message: '请选择医生' }]}
              />
            </Col>
          </Row>
        </Card>

        <Card 
          title="排班设置" 
          size="small"
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
      </ModalForm>

      <ModalForm
        title="生效班次"
        open={effectiveModalOpen}
        onOpenChange={setEffectiveModalOpen}
        submitter={false}
        modalProps={{ width: 900 }}
      >
        <ProTable<CustomSchedule>
          columns={effectiveColumns}
          dataSource={effectiveSchedules}
          rowKey="id"
          search={false}
          toolBarRender={false}
          pagination={{ pageSize: 10 }}
        />
      </ModalForm>
    </PageContainer>
  );
};

export default CustomSchedulePage;
