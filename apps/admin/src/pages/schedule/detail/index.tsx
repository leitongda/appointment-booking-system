import { PlusOutlined } from '@ant-design/icons';
import type { ActionType, ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable, ModalForm, ProFormSelect, ProFormDatePicker, ProFormDigit } from '@ant-design/pro-components';
import { Button, App, Space, Tag, Popconfirm } from 'antd';
import { useRef, useState, useEffect } from 'react';
import { useAccess, useModel } from '@umijs/max';
import { scheduleApi, doctorApi, departmentApi, storeApi } from '@hospital/api';
import { toProTableResult } from '@/utils/proTable';
import type { Schedule, Doctor, Department } from '@hospital/shared';
import { APPOINTMENT_TYPE_MAP } from '@hospital/shared';
import dayjs from 'dayjs';

const TIME_SLOTS = [
  { label: '上午', value: 'morning' },
  { label: '下午', value: 'afternoon' },
  { label: '晚上', value: 'evening' },
];

const ScheduleDetailPage: React.FC = () => {
  const { message } = App.useApp();
  const access = useAccess();
  const actionRef = useRef<ActionType>();
  const [modalOpen, setModalOpen] = useState(false);
  const [doctors, setDoctors] = useState<Doctor[]>([]);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [selectedDept, setSelectedDept] = useState<string>();
  
  const { initialState } = useModel('@@initialState');
  const { currentUser } = initialState ?? {};
  const isSuperAdmin = access.canSuperAdmin;
  // 多门店管理员也可以看到门店筛选
  const showStoreFilter = isSuperAdmin || (currentUser?.storeIds?.length ?? 0) > 1;

  useEffect(() => {
    loadDepartments();
  }, []);

  useEffect(() => {
    if (selectedDept) {
      loadDoctorsByDept(selectedDept);
    }
  }, [selectedDept]);

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

  const handleSubmit = async (values: any) => {
    try {
      await scheduleApi.create({
        doctorId: values.doctorId,
        scheduleDate: values.scheduleDate ? dayjs(values.scheduleDate).format('YYYY-MM-DD') : values.scheduleDate,
        timeSlot: values.timeSlot,
        totalSlots: values.totalSlots,
        status: 1,
      });
      message.success('创建成功');
      setModalOpen(false);
      actionRef.current?.reload();
      return true;
    } catch (error: any) {
      message.error(error.message || '创建失败');
      return false;
    }
  };

  const handleSuspend = async (id: string) => {
    try {
      await scheduleApi.suspend(id, '管理员停诊');
      message.success('停诊成功');
      actionRef.current?.reload();
    } catch (error: any) {
      message.error(error.message || '操作失败');
    }
  };

  const handleResume = async (id: string) => {
    try {
      await scheduleApi.resume(id);
      message.success('恢复成功');
      actionRef.current?.reload();
    } catch (error: any) {
      message.error(error.message || '操作失败');
    }
  };

  const columns: ProColumns<Schedule>[] = [
    // 超级管理员可以按门店筛选
    ...(showStoreFilter ? [{
      title: '门店',
      dataIndex: 'storeId',
      hideInTable: true,
      valueType: 'select',
      request: async () => {
        try {
          const stores = await storeApi.getAll();
          let storeList = stores ?? [];
          // 非超管只显示其关联的门店
          if (!isSuperAdmin && currentUser?.storeIds?.length) {
            storeList = storeList.filter((s: any) => currentUser.storeIds?.includes(s.id));
          }
          return [
            { label: '全部门店', value: '' },
            ...storeList.map((s: any) => ({ label: s.name, value: s.id })),
          ];
        } catch {
          return [];
        }
      },
    } as ProColumns<Schedule>] : []),
    {
      title: '日期',
      dataIndex: 'scheduleDate',
      width: 110,
      valueType: 'date',
      sorter: true,
    },
    {
      title: '医生',
      dataIndex: 'doctorName',
      width: 100,
    },
    {
      title: '科室',
      dataIndex: 'departmentName',
      width: 120,
    },
    {
      title: '时间段',
      dataIndex: 'startTime',
      width: 150,
      search: false,
      render: (_, record) => {
        if (record.startTime && record.endTime) {
          return `${record.startTime} - ${record.endTime}`;
        }
        return '-';
      },
    },
    {
      title: '预约类型',
      dataIndex: 'appointmentType',
      width: 100,
      search: false,
      render: (_, record) => {
        const typeMap: Record<string, string> = {
          urgent: 'red',
          normal: 'blue',
          expert: 'gold',
          medical_insurance: 'green',
          self_pay: 'purple',
        };
        return (
          <Tag color={typeMap[record.appointmentType || 'normal'] || 'default'}>
            {APPOINTMENT_TYPE_MAP[record.appointmentType || 'normal'] || record.appointmentType}
          </Tag>
        );
      },
    },
    {
      title: '总人数',
      dataIndex: 'totalSlots',
      width: 80,
      search: false,
    },
    {
      title: '已预约',
      dataIndex: 'bookedSlots',
      width: 80,
      search: false,
    },
    {
      title: '剩余',
      width: 80,
      search: false,
      render: (_, record) => {
        const remaining = (record.totalSlots || 0) - (record.bookedSlots || 0);
        return <span style={{ color: remaining > 0 ? '#52c41a' : '#ff4d4f' }}>{remaining}</span>;
      },
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 80,
      valueEnum: {
        1: { text: '正常', status: 'Success' },
        0: { text: '停诊', status: 'Error' },
      },
    },
    {
      title: '操作',
      valueType: 'option',
      width: 100,
      fixed: 'right',
      render: (_, record) => (
        <Space>
          {access.hasPermission('schedule:update') && (
            record.status === 1 ? (
              <Popconfirm title="确定停诊吗？" onConfirm={() => handleSuspend(record.id)}>
                <a style={{ color: '#ff4d4f' }}>停诊</a>
              </Popconfirm>
            ) : (
              <a onClick={() => handleResume(record.id)}>恢复</a>
            )
          )}
        </Space>
      ),
    },
  ];

  return (
    <PageContainer>
      <ProTable<Schedule>
        headerTitle="排班列表"
        actionRef={actionRef}
        rowKey="id"
        columns={columns}
        scroll={{ x: 1200 }}
        request={async (params) => {
          const { current, pageSize, ...rest } = params;
          return toProTableResult(await scheduleApi.getList({
            ...rest,
            page: current,
            pageSize,
          }));
        }}
        toolBarRender={() => [
          access.hasPermission('schedule:create') && (
            <Button
              key="add"
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => setModalOpen(true)}
            >
              新增排班
            </Button>
          ),
        ]}
        pagination={{ defaultPageSize: 20 }}
        search={{
          labelWidth: 'auto',
          defaultCollapsed: false,
        }}
      />

      <ModalForm
        title="新增排班"
        open={modalOpen}
        onOpenChange={setModalOpen}
        onFinish={handleSubmit}
        modalProps={{ destroyOnHidden: true }}
        initialValues={{ totalSlots: 20 }}
      >
        <ProFormSelect
          name="departmentId"
          label="选择科室"
          options={(departments ?? []).map((d) => ({ label: d.name, value: d.id }))}
          onChange={(val) => setSelectedDept(val as string)}
          rules={[{ required: true, message: '请选择科室' }]}
        />
        <ProFormSelect
          name="doctorId"
          label="选择医生"
          options={(doctors ?? []).map((d) => ({ label: `${d.name} - ${d.title || ''}`, value: d.id }))}
          rules={[{ required: true, message: '请选择医生' }]}
        />
        <ProFormDatePicker
          name="scheduleDate"
          label="排班日期"
          rules={[{ required: true, message: '请选择日期' }]}
        />
        <ProFormSelect
          name="timeSlot"
          label="时段"
          options={TIME_SLOTS}
          rules={[{ required: true, message: '请选择时段' }]}
        />
        <ProFormDigit
          name="totalSlots"
          label="号源数量"
          min={1}
          max={100}
          rules={[{ required: true, message: '请输入号源数量' }]}
        />
      </ModalForm>
    </PageContainer>
  );
};

export default ScheduleDetailPage;

