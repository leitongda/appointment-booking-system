import { PlusOutlined } from '@ant-design/icons';
import type { ActionType, ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable, ModalForm, ProFormSelect, ProFormDatePicker, ProFormDigit } from '@ant-design/pro-components';
import { Button, App, Space, Tag, Popconfirm } from 'antd';
import { useRef, useState, useEffect } from 'react';
import { useAccess } from '@umijs/max';
import { scheduleApi, doctorApi, departmentApi } from '@hospital/api';
import { toProTableResult } from '@/utils/proTable';
import type { Schedule, Doctor, Department } from '@hospital/shared';

const TIME_SLOTS = [
  { label: '上午', value: 'morning' },
  { label: '下午', value: 'afternoon' },
  { label: '晚上', value: 'evening' },
];

const ScheduleListPage: React.FC = () => {
  const { message } = App.useApp();
  const access = useAccess();
  const actionRef = useRef<ActionType>();
  const [modalOpen, setModalOpen] = useState(false);
  const [doctors, setDoctors] = useState<Doctor[]>([]);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [selectedDept, setSelectedDept] = useState<string>();

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

  const handleSubmit = async (values: any) => {
    try {
      await scheduleApi.create({
        ...values,
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

  const columns: ProColumns<Schedule>[] = [
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
      title: '日期',
      dataIndex: 'scheduleDate',
      width: 110,
      valueType: 'date',
    },
    {
      title: '时段',
      dataIndex: 'timeSlot',
      width: 80,
      valueEnum: {
        morning: '上午',
        afternoon: '下午',
        evening: '晚上',
      },
    },
    {
      title: '总号源',
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
      render: (_, record) => (record.totalSlots || 0) - (record.bookedSlots || 0),
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
        pagination={{ defaultPageSize: 10 }}
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

export default ScheduleListPage;
