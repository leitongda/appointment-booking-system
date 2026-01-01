import { PlusOutlined, StopOutlined, PlayCircleOutlined, DeleteOutlined, EditOutlined } from '@ant-design/icons';
import type { ActionType, ProColumns, ProFormInstance } from '@ant-design/pro-components';
import { PageContainer, ProTable, ModalForm, ProFormSelect, ProFormDatePicker, ProFormDigit, ProFormDateRangePicker } from '@ant-design/pro-components';
import { Button, App, Space, Tag, Popconfirm, Alert, Tooltip } from 'antd';
import { useRef, useState, useEffect } from 'react';
import { useAccess, useModel } from '@umijs/max';
import { scheduleApi, doctorApi, departmentApi, storeApi } from '@hospital/api';
import { toProTableResult } from '@/utils/proTable';
import type { Schedule, Doctor, Department } from '@hospital/shared';
import dayjs from 'dayjs';

const TIME_SLOTS = [
  { label: '上午', value: 'morning' },
  { label: '下午', value: 'afternoon' },
  { label: '晚上', value: 'evening' },
];

const ScheduleListPage: React.FC = () => {
  const { message, modal } = App.useApp();
  const access = useAccess();
  const actionRef = useRef<ActionType>();
  const formRef = useRef<ProFormInstance>();
  const editFormRef = useRef<ProFormInstance>();
  const [modalOpen, setModalOpen] = useState(false);
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [currentSchedule, setCurrentSchedule] = useState<Schedule | null>(null);
  const [doctors, setDoctors] = useState<Doctor[]>([]);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [selectedDept, setSelectedDept] = useState<string>();
  const [selectedRowKeys, setSelectedRowKeys] = useState<string[]>([]);
  const [selectedRows, setSelectedRows] = useState<Schedule[]>([]);
  
  const { initialState } = useModel('@@initialState');
  const { currentUser, currentStore } = initialState ?? {};
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

  // 批量停诊
  const handleBatchSuspend = () => {
    const normalRows = selectedRows.filter(r => r.status === 1);
    if (normalRows.length === 0) {
      message.warning('请选择状态为"正常"的排班');
      return;
    }
    
    modal.confirm({
      title: '确认批量停诊',
      content: (
        <div>
          <p>确定要停诊选中的 <strong>{normalRows.length}</strong> 条排班吗？</p>
          {selectedRows.length !== normalRows.length && (
            <p style={{ color: '#999', fontSize: 12 }}>
              注意：{selectedRows.length - normalRows.length} 条已停诊的排班将被跳过
            </p>
          )}
        </div>
      ),
      okText: '确认停诊',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        try {
          const result = await scheduleApi.batchSuspend(normalRows.map(r => r.id));
          message.success(result.message);
          setSelectedRowKeys([]);
          setSelectedRows([]);
          actionRef.current?.reload();
        } catch (error: any) {
          message.error(error.message || '批量停诊失败');
        }
      },
    });
  };

  // 批量恢复
  const handleBatchResume = () => {
    const suspendedRows = selectedRows.filter(r => r.status === 0);
    if (suspendedRows.length === 0) {
      message.warning('请选择状态为"停诊"的排班');
      return;
    }
    
    modal.confirm({
      title: '确认批量恢复',
      content: (
        <div>
          <p>确定要恢复选中的 <strong>{suspendedRows.length}</strong> 条排班吗？</p>
          {selectedRows.length !== suspendedRows.length && (
            <p style={{ color: '#999', fontSize: 12 }}>
              注意：{selectedRows.length - suspendedRows.length} 条正常排班将被跳过
            </p>
          )}
        </div>
      ),
      okText: '确认恢复',
      cancelText: '取消',
      onOk: async () => {
        try {
          const result = await scheduleApi.batchResume(suspendedRows.map(r => r.id));
          message.success(result.message);
          setSelectedRowKeys([]);
          setSelectedRows([]);
          actionRef.current?.reload();
        } catch (error: any) {
          message.error(error.message || '批量恢复失败');
        }
      },
    });
  };

  // 批量删除
  const handleBatchDelete = () => {
    const deletableRows = selectedRows.filter(r => r.bookedSlots === 0);
    if (deletableRows.length === 0) {
      message.warning('选中的排班都有预约，无法删除');
      return;
    }
    
    modal.confirm({
      title: '确认批量删除',
      content: (
        <div>
          <p>确定要删除选中的 <strong>{deletableRows.length}</strong> 条排班吗？</p>
          <p style={{ color: '#ff4d4f', fontSize: 12 }}>此操作不可恢复！</p>
          {selectedRows.length !== deletableRows.length && (
            <p style={{ color: '#999', fontSize: 12 }}>
              注意：{selectedRows.length - deletableRows.length} 条有预约的排班将被跳过
            </p>
          )}
        </div>
      ),
      okText: '确认删除',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        try {
          const result = await scheduleApi.batchDelete(selectedRows.map(r => r.id));
          message.success(result.message);
          setSelectedRowKeys([]);
          setSelectedRows([]);
          actionRef.current?.reload();
        } catch (error: any) {
          message.error(error.message || '批量删除失败');
        }
      },
    });
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

  // 编辑排班
  const handleEdit = (record: Schedule) => {
    setCurrentSchedule(record);
    setEditModalOpen(true);
  };

  const handleEditSubmit = async (values: any) => {
    if (!currentSchedule) return false;
    
    try {
      await scheduleApi.update(currentSchedule.id, {
        totalSlots: values.totalSlots,
      });
      message.success('修改成功');
      setEditModalOpen(false);
      setCurrentSchedule(null);
      actionRef.current?.reload();
      return true;
    } catch (error: any) {
      message.error(error.message || '修改失败');
      return false;
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
      title: '日期范围',
      dataIndex: 'dateRange',
      valueType: 'dateRange',
      hideInTable: true,
      search: {
        transform: (value) => {
          if (value && value.length === 2) {
            return {
              startDate: value[0],
              endDate: value[1],
            };
          }
          return {};
        },
      },
    },
    {
      title: '科室',
      dataIndex: 'departmentId',
      width: 120,
      valueType: 'select',
      request: async () => {
        try {
          const res = await departmentApi.getList({ pageSize: 100, status: 1 });
          console.log("🚀 ~ ScheduleListPage ~ res:", res)
          return (res.data ?? []).map((d: Department) => ({ label: d.name, value: d.id }));
        } catch {
          return [];
        }
      },
      fieldProps: {
        showSearch: true,
        allowClear: true,
        placeholder: '请选择科室',
        optionFilterProp: 'label',
        onChange: () => {
          formRef.current?.setFieldValue('doctorId', undefined);
        },
      },
      render: (_, record) => record.departmentName,
    },
    {
      title: '医生',
      dataIndex: 'doctorId',
      width: 100,
      valueType: 'select',
      request: async () => {
        try {
          const res = await doctorApi.getList({ pageSize: 200 });
          return (res.data ?? []).map((d: Doctor) => ({ label: `${d.name}${d.title ? ` - ${d.title}` : ''}`, value: d.id }));
        } catch {
          return [];
        }
      },
      fieldProps: {
        showSearch: true,
        allowClear: true,
        placeholder: '请选择医生',
        optionFilterProp: 'label',
      },
      render: (_, record) => record.doctorName,
    },
    {
      title: '日期',
      dataIndex: 'scheduleDate',
      width: 110,
      valueType: 'date',
      search: false,
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
      width: 140,
      render: (_, record) => (
        <Space>
          {access.hasPermission('schedule:update') && (
            <Tooltip title="修改可预约人数">
              <a onClick={() => handleEdit(record)}>
                <EditOutlined /> 编辑
              </a>
            </Tooltip>
          )}
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
      {selectedRowKeys.length > 0 && (
        <Alert
          message={
            <Space>
              <span>已选择 <strong>{selectedRowKeys.length}</strong> 项</span>
              <Button size="small" onClick={() => { setSelectedRowKeys([]); setSelectedRows([]); }}>
                取消选择
              </Button>
            </Space>
          }
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
        />
      )}
      
      <ProTable<Schedule>
        headerTitle="排班列表"
        actionRef={actionRef}
        formRef={formRef}
        rowKey="id"
        columns={columns}
        rowSelection={{
          selectedRowKeys,
          onChange: (keys, rows) => {
            setSelectedRowKeys(keys as string[]);
            setSelectedRows(rows);
          },
        }}
        tableAlertRender={false}
        tableAlertOptionRender={false}
        request={async (params) => {
          const { current, pageSize, ...rest } = params;
          return toProTableResult(await scheduleApi.getList({
            ...rest,
            page: current,
            pageSize,
          }));
        }}
        toolBarRender={() => [
          selectedRowKeys.length > 0 && access.hasPermission('schedule:update') && (
            <Button
              key="batchSuspend"
              icon={<StopOutlined />}
              danger
              onClick={handleBatchSuspend}
            >
              批量停诊
            </Button>
          ),
          selectedRowKeys.length > 0 && access.hasPermission('schedule:update') && (
            <Button
              key="batchResume"
              icon={<PlayCircleOutlined />}
              onClick={handleBatchResume}
            >
              批量恢复
            </Button>
          ),
          selectedRowKeys.length > 0 && access.hasPermission('schedule:delete') && (
            <Button
              key="batchDelete"
              icon={<DeleteOutlined />}
              danger
              onClick={handleBatchDelete}
            >
              批量删除
            </Button>
          ),
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

      {/* 编辑排班弹窗 */}
      <ModalForm
        title="编辑排班"
        open={editModalOpen}
        formRef={editFormRef}
        onOpenChange={(open) => {
          setEditModalOpen(open);
          if (!open) {
            setCurrentSchedule(null);
          }
        }}
        onFinish={handleEditSubmit}
        modalProps={{ destroyOnClose: true }}
        initialValues={{
          totalSlots: currentSchedule?.totalSlots || 20,
        }}
      >
        {currentSchedule && (
          <Alert
            message={
              <div>
                <div><strong>医生：</strong>{currentSchedule.doctorName}</div>
                <div><strong>日期：</strong>{currentSchedule.scheduleDate}</div>
                <div><strong>时段：</strong>
                  {currentSchedule.startTime && currentSchedule.endTime 
                    ? `${currentSchedule.startTime} - ${currentSchedule.endTime}`
                    : currentSchedule.timeSlot === 'morning' ? '上午' 
                    : currentSchedule.timeSlot === 'afternoon' ? '下午' 
                    : '晚上'}
                </div>
                <div><strong>已预约：</strong>{currentSchedule.bookedSlots || 0} 人</div>
              </div>
            }
            type="info"
            style={{ marginBottom: 16 }}
          />
        )}
        <ProFormDigit
          name="totalSlots"
          label="可预约人数"
          min={currentSchedule?.bookedSlots || 1}
          max={200}
          rules={[
            { required: true, message: '请输入可预约人数' },
            {
              validator: (_: unknown, value: number) => {
                if (value < (currentSchedule?.bookedSlots || 0)) {
                  return Promise.reject(`不能小于已预约人数 (${currentSchedule?.bookedSlots || 0})`);
                }
                return Promise.resolve();
              },
            },
          ]}
          extra={`当前已预约 ${currentSchedule?.bookedSlots || 0} 人，不能设置小于此值`}
        />
      </ModalForm>
    </PageContainer>
  );
};

export default ScheduleListPage;
