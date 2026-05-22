import { PlusOutlined, StopOutlined, PlayCircleOutlined, DeleteOutlined } from '@ant-design/icons';
import type { ActionType, ProColumns, ProFormInstance } from '@ant-design/pro-components';
import { PageContainer, ProTable, ModalForm, ProFormSelect, ProFormDatePicker, ProFormDigit, ProFormTimePicker } from '@ant-design/pro-components';
import { Button, App, Space, Tag, Popconfirm, Alert, Tooltip } from 'antd';
import { useRef, useState, useMemo } from 'react';
import { useAccess, useModel } from '@umijs/max';
import { scheduleApi, doctorApi, departmentApi } from '@hospital/api';
import { createListRequest } from '@/utils/proTable';
import { fetchAllData } from '@/utils/fetchAllData';
import { useStoreWithPermission } from '@/hooks/useStoreWithPermission';
import { useDepartments } from '@/hooks/useDepartments';
import { useDoctors } from '@/hooks/useDoctors';
import type { Schedule, Doctor, Department } from '@hospital/shared';
import { useDict } from '@/hooks/useDict';
import ListPageSkeleton from '@/components/ListPageSkeleton';
import { ScheduleMessages } from '../utils/message';
import { TEXT_SECONDARY, COLOR_DANGER, COLOR_SUCCESS } from '@/themes/scheduleColors';

interface ScheduleDetailFormValues {
  doctorId: string;
  scheduleDate: string | { format: (fmt: string) => string };
  totalSlots: number;
  appointmentType?: string;
  startTime?: string | { format: (fmt: string) => string };
  endTime?: string | { format: (fmt: string) => string };
  [key: string]: unknown;
}

const ScheduleDetailPage: React.FC = () => {
  const { message, modal } = App.useApp();
  const access = useAccess();
  const { dictItems: appointmentTypeItems, options: appointmentTypeOptions } = useDict('appointment_type');
  const appointmentTypeMap = useMemo(
    () => Object.fromEntries(appointmentTypeItems.map((i) => [i.value, i.label])),
    [appointmentTypeItems]
  );
  const actionRef = useRef<ActionType>();
  const formRef = useRef<ProFormInstance>();
  const [modalOpen, setModalOpen] = useState(false);
  const [selectedDept, setSelectedDept] = useState<string>();
  const [selectedRowKeys, setSelectedRowKeys] = useState<string[]>([]);
  const [selectedRows, setSelectedRows] = useState<Schedule[]>([]);
  const [initialLoading, setInitialLoading] = useState(true);

  const { initialState } = useModel('@@initialState');
  const { currentUser } = initialState ?? {};
  const isSuperAdmin = access.canSuperAdmin;
  // 多门店管理员也可以看到门店筛选
  const showStoreFilter = isSuperAdmin || (currentUser?.storeIds?.length ?? 0) > 1;
  const { stores } = useStoreWithPermission({ enabledOnly: true });

  // 使用共享 hooks 加载科室和医生数据（用于新增排班弹窗）
  const { departments } = useDepartments();
  const { doctors } = useDoctors({ departmentId: selectedDept, enabled: !!selectedDept });

  const handleSubmit = async (values: ScheduleDetailFormValues) => {
    try {
      const startTime = values.startTime ? (typeof values.startTime === 'string' ? values.startTime : values.startTime.format('HH:mm')) : undefined;
      const endTime = values.endTime ? (typeof values.endTime === 'string' ? values.endTime : values.endTime.format('HH:mm')) : undefined;

      const scheduleDate = typeof values.scheduleDate === 'string'
        ? values.scheduleDate
        : values.scheduleDate.format('YYYY-MM-DD');

      await scheduleApi.create({
        doctorId: values.doctorId,
        scheduleDate,
        totalSlots: values.totalSlots,
        appointmentType: values.appointmentType || 'normal',
        startTime,
        endTime,
        status: 1,
      });
      message.success(ScheduleMessages.createSuccess);
      setModalOpen(false);
      actionRef.current?.reload();
      return true;
    } catch (error: any) {
      message.error(error.message || ScheduleMessages.createFailed);
      return false;
    }
  };

  const handleSuspend = async (record: Schedule) => {
    try {
      await scheduleApi.suspendSchedule(record, '管理员停诊');
      message.success(ScheduleMessages.suspendSuccess);
      actionRef.current?.reload();
    } catch (error: any) {
      message.error(error.message || ScheduleMessages.operateFailed);
    }
  };

  const handleResume = async (record: Schedule) => {
    try {
      await scheduleApi.resumeSchedule(record);
      message.success(ScheduleMessages.restoreSuccess);
      actionRef.current?.reload();
    } catch (error: any) {
      message.error(error.message || ScheduleMessages.operateFailed);
    }
  };

  // 批量停诊
  const handleBatchSuspend = () => {
    const normalRows = selectedRows.filter(r => r.status === 1);
    if (normalRows.length === 0) {
      message.warning(ScheduleMessages.selectNormalStatus);
      return;
    }
    
    modal.confirm({
      title: '确认批量停诊',
      content: (
        <div>
          <p>确定要停诊选中的 <strong>{normalRows.length}</strong> 条排班吗？</p>
          {selectedRows.length !== normalRows.length && (
            <p style={{ color: TEXT_SECONDARY, fontSize: 12 }}>
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
          message.error(error.message || ScheduleMessages.batchSuspendFailed);
        }
      },
    });
  };

  // 批量恢复
  const handleBatchResume = () => {
    const suspendedRows = selectedRows.filter(r => r.status === 0);
    if (suspendedRows.length === 0) {
      message.warning(ScheduleMessages.selectSuspendedStatus);
      return;
    }
    
    modal.confirm({
      title: '确认批量恢复',
      content: (
        <div>
          <p>确定要恢复选中的 <strong>{suspendedRows.length}</strong> 条排班吗？</p>
          {selectedRows.length !== suspendedRows.length && (
            <p style={{ color: TEXT_SECONDARY, fontSize: 12 }}>
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
          message.error(error.message || ScheduleMessages.batchResumeFailed);
        }
      },
    });
  };

  // 批量删除
  const handleBatchDelete = () => {
    const deletableRows = selectedRows.filter(r => r.bookedSlots === 0);
    if (deletableRows.length === 0) {
      message.warning(ScheduleMessages.cannotDeleteWithBooking);
      return;
    }
    
    modal.confirm({
      title: '确认批量删除',
      content: (
        <div>
          <p>确定要删除选中的 <strong>{deletableRows.length}</strong> 条排班吗？</p>
          <p style={{ color: COLOR_DANGER, fontSize: 12 }}>此操作不可恢复！</p>
          {selectedRows.length !== deletableRows.length && (
            <p style={{ color: TEXT_SECONDARY, fontSize: 12 }}>
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
          message.error(error.message || ScheduleMessages.batchDeleteFailed);
        }
      },
    });
  };

  const columns: ProColumns<Schedule>[] = [
    // 超级管理员可以按门店筛选
    ...(showStoreFilter ? [{
      title: '门店',
      dataIndex: 'storeId',
      hideInTable: true,
      valueType: 'select',
      request: async () => {
        return [
          { label: '全部门店', value: '' },
          ...stores.map((s) => ({ label: s.name, value: s.id })),
        ];
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
      title: '科室',
      dataIndex: 'departmentId',
      width: 120,
      valueType: 'select',
      request: async () => {
        try {
          // 获取所有启用的科室
          const allDepts = await departmentApi.getAll();
          return allDepts.map((d: Department) => ({ label: d.name, value: d.id }));
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
      dependencies: ['departmentId'],
      request: async (params) => {
        try {
          // 如果选择了科室，只加载该科室的医生
          if (params.departmentId) {
            const data = await doctorApi.getByDepartment(params.departmentId);
            return (data ?? []).map((d: Doctor) => ({ label: `${d.name}${d.title ? ` - ${d.title}` : ''}`, value: d.id }));
          }
          // 未选择科室时，加载全部医生（使用分页加载）
          const allDoctors = await fetchAllData((page, pageSize) =>
            doctorApi.getList({ page, pageSize })
          );
          return allDoctors.map((d: Doctor) => ({ label: `${d.name}${d.title ? ` - ${d.title}` : ''}`, value: d.id }));
        } catch {
          return [];
        }
      },
      fieldProps: {
        showSearch: true,
        allowClear: true,
        placeholder: '请先选择科室',
        optionFilterProp: 'label',
      },
      render: (_, record) => record.doctorName,
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
            {appointmentTypeMap[record.appointmentType || 'normal'] || record.appointmentType}
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
        return <span style={{ color: remaining > 0 ? COLOR_SUCCESS : COLOR_DANGER }}>{remaining}</span>;
      },
    },
    {
      title: '生效状态',
      dataIndex: 'effectiveStatus',
      width: 110,
      search: false,
      render: (_, record) => {
        const status = record.effectiveStatus || (record.status === 0 ? 'suspended' : 'active');
        const statusMap: Record<string, { text: string; color: string; tooltip: string }> = {
          active: { text: '正常', color: 'success', tooltip: '该排班正常生效，患者可预约' },
          suspended: { text: '停诊', color: 'error', tooltip: '该排班已停诊，患者不可预约' },
          rest_day: { text: '休息日', color: 'orange', tooltip: '该日期为休息日，模板排班会被隐藏' },
          custom: { text: '自定义', color: 'processing', tooltip: '自定义排班，优先级最高，不受休息日影响' },
          overridden: { text: '被覆盖', color: 'default', tooltip: '该模板排班已被同时间段的自定义排班覆盖，患者不可见此排班' },
        };
        const info = statusMap[status] || statusMap.active;
        return (
          <Tooltip title={info.tooltip}>
            <Tag color={info.color}>{info.text}</Tag>
          </Tooltip>
        );
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
              <Popconfirm title="确定停诊吗？" onConfirm={() => handleSuspend(record)}>
                <a style={{ color: COLOR_DANGER }}>停诊</a>
              </Popconfirm>
            ) : (
              <a onClick={() => handleResume(record)}>恢复</a>
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
          title={
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
      
      {initialLoading && <ListPageSkeleton filterCount={5} rowCount={6} />}

      <div style={initialLoading ? { height: 0, overflow: 'hidden' } : undefined}>
        <ProTable<Schedule>
          headerTitle="排班列表"
          actionRef={actionRef}
          formRef={formRef}
          rowKey="id"
          columns={columns}
          scroll={{ x: 1200 }}
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
            try {
              return await (createListRequest(scheduleApi.getList) as any)(params);
            } finally {
              setInitialLoading(false);
            }
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
          pagination={{ defaultPageSize: 20 }}
          search={{
            labelWidth: 'auto',
            defaultCollapsed: false,
          }}
        />
      </div>

      <ModalForm
        title="新增排班"
        open={modalOpen}
        onOpenChange={setModalOpen}
        onFinish={handleSubmit}
        modalProps={{ destroyOnHidden: true }}
        initialValues={{ totalSlots: 20, appointmentType: 'normal' }}
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
          name="appointmentType"
          label="预约类型"
          options={appointmentTypeOptions}
          rules={[{ required: true, message: '请选择预约类型' }]}
        />
        <ProFormTimePicker
          name="startTime"
          label="开始时间"
          fieldProps={{ format: 'HH:mm' }}
          rules={[{ required: true, message: '请选择开始时间' }]}
        />
        <ProFormTimePicker
          name="endTime"
          label="结束时间"
          fieldProps={{ format: 'HH:mm' }}
          rules={[{ required: true, message: '请选择结束时间' }]}
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
