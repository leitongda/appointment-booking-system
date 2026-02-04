import { PlusOutlined, SearchOutlined } from '@ant-design/icons';
import type { ActionType, ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable, ModalForm } from '@ant-design/pro-components';
import { Button, App, Tag, Popconfirm, Card, Form, DatePicker, Select } from 'antd';
import { useRef, useState, useEffect } from 'react';
import { history, useAccess, useModel } from '@umijs/max';
import { customScheduleApi, storeApi, doctorApi } from '@hospital/api';
import { toProTableResult } from '@/utils/proTable';
import { APPOINTMENT_TYPE_MAP } from '@hospital/shared';
import type { CustomSchedule } from '@hospital/api';

const CustomSchedulePage: React.FC = () => {
  const { message } = App.useApp();
  const access = useAccess();
  const { initialState } = useModel('@@initialState');
  const { currentUser, currentStore } = initialState ?? {};
  const isSuperAdmin = access.canSuperAdmin;
  const actionRef = useRef<ActionType>();
  const [effectiveModalOpen, setEffectiveModalOpen] = useState(false);
  const [stores, setStores] = useState<any[]>([]);
  const [effectiveSchedules, setEffectiveSchedules] = useState<CustomSchedule[]>([]);
  const [effectiveDoctors, setEffectiveDoctors] = useState<any[]>([]);
  const [form] = Form.useForm();

  useEffect(() => {
    loadStores();
  }, []);

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
      title: '休息日',
      dataIndex: 'isRestDay',
      width: 80,
      search: false,
      render: (_, record) => 
        record.isRestDay ? <Tag color="orange">休息日</Tag> : '-',
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
        access.hasPermission('schedule:custom') && (
          <Popconfirm 
            title="确定删除该排班吗？" 
            onConfirm={() => handleDelete(record.id)}
            disabled={record.bookedCount > 0}
          >
            <a style={{ color: record.bookedCount > 0 ? '#ccc' : '#ff4d4f' }}>
              删除
            </a>
          </Popconfirm>
        )
      ),
    },
  ];

  const effectiveColumns: ProColumns<CustomSchedule>[] = [
    { title: '门店', dataIndex: 'storeName', width: 120 },
    { title: '医生', dataIndex: 'doctorName', width: 80 },
    { title: '日期', dataIndex: 'scheduleDate', width: 110 },
    { title: '休息日', dataIndex: 'isRestDay', width: 80, render: (_, r) => r.isRestDay ? <Tag color="orange">休息日</Tag> : '-' },
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
          access.hasPermission('schedule:custom') && (
            <Button
              key="add"
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => history.push('/schedule/custom/create')}
            >
              添加
            </Button>
          ),
        ]}
        pagination={{ defaultPageSize: 10 }}
      />

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
