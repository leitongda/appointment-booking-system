import { PlusOutlined, ThunderboltOutlined } from '@ant-design/icons';
import type { ActionType, ProColumns } from '@ant-design/pro-components';
import {
  PageContainer,
  ProTable,
  ModalForm,
  ProFormSelect,
  ProFormTimePicker,
  ProFormDateRangePicker,
  ProFormCheckbox,
  ProFormRadio,
  ProFormDigit,
} from '@ant-design/pro-components';
import { Button, App, Space, Popconfirm, Tag, Alert } from 'antd';
import { useRef, useState, useEffect, useMemo } from 'react';
import { history, useAccess, useModel } from '@umijs/max';
import { scheduleTemplateApi, doctorApi, departmentApi, storeApi } from '@hospital/api';
import { toProTableResult } from '@/utils/proTable';
import type { ScheduleTemplate, Doctor, Department, Store } from '@hospital/shared';
import {
  APPOINTMENT_TYPE_MAP,
  APPOINTMENT_TYPE_OPTIONS,
  SCHEDULE_MODE_MAP,
  SCHEDULE_MODE_OPTIONS,
  WEEKDAY_MAP,
  WEEKDAY_OPTIONS,
  getDateInfo,
} from '@hospital/shared';

const ScheduleRulePage: React.FC = () => {
  const { message } = App.useApp();
  const access = useAccess();
  const { initialState } = useModel('@@initialState');
  const { currentUser } = initialState ?? {};
  const isSuperAdmin = access.canSuperAdmin;
  const actionRef = useRef<ActionType>();
  const [batchAddModalOpen, setBatchAddModalOpen] = useState(false);
  const [generateModalOpen, setGenerateModalOpen] = useState(false);
  const [selectedTemplates, setSelectedTemplates] = useState<string[]>([]);

  const [stores, setStores] = useState<Store[]>([]);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [doctors, setDoctors] = useState<Doctor[]>([]);
  const [selectedDept, setSelectedDept] = useState<string>();

  // 当前日期信息
  const dateInfo = useMemo(() => getDateInfo(), []);

  useEffect(() => {
    loadStores();
    loadDepartments();
  }, []);

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

  const handleDelete = async (id: string) => {
    try {
      await scheduleTemplateApi.delete(id);
      message.success('删除成功');
      actionRef.current?.reload();
    } catch (error: any) {
      message.error(error.message || '删除失败');
    }
  };

  const handleBatchAddSubmit = async (values: any) => {
    const { dateRange, startTime, endTime, totalSlots, slotCount, ...rest } = values;
    if (!dateRange || dateRange.length !== 2) {
      message.error('请选择日期范围');
      return false;
    }

    // 验证时间字段
    if (!startTime || !endTime) {
      message.error('请填写开始时间和结束时间');
      return false;
    }

    try {
      // 格式化日期和时间
      const startDate = typeof dateRange[0] === 'string' 
        ? dateRange[0] 
        : dateRange[0].format('YYYY-MM-DD');
      const endDate = typeof dateRange[1] === 'string' 
        ? dateRange[1] 
        : dateRange[1].format('YYYY-MM-DD');
      
      // 格式化时间（ProFormTimePicker 返回的是 dayjs 对象）
      const formattedStartTime = typeof startTime === 'string' 
        ? startTime 
        : startTime.format('HH:mm');
      const formattedEndTime = typeof endTime === 'string' 
        ? endTime 
        : endTime.format('HH:mm');

      const result = await scheduleTemplateApi.batchAdd({
        ...rest,
        startTime: formattedStartTime,
        endTime: formattedEndTime,
        slotCapacity: totalSlots || 10, // totalSlots 对应后端的 slotCapacity
        slotCount: slotCount || 1, // 默认班次数量为 1
        startDate,
        endDate,
      });
      message.success(result.message);
      setBatchAddModalOpen(false);
      actionRef.current?.reload();
      return true;
    } catch (error: any) {
      message.error(error.message || '批量添加失败');
      return false;
    }
  };

  const handleGenerateSubmit = async (values: any) => {
    const { dateRange } = values;
    if (!dateRange || dateRange.length !== 2) {
      message.error('请选择日期范围');
      return false;
    }

    if (selectedTemplates.length === 0) {
      message.error('请先选择要使用的规则');
      return false;
    }

    try {
      const result = await scheduleTemplateApi.generate({
        templateIds: selectedTemplates,
        startDate: dateRange[0],
        endDate: dateRange[1],
      });
      message.success(result.message);
      setGenerateModalOpen(false);
      setSelectedTemplates([]);
      actionRef.current?.reload();
      return true;
    } catch (error: any) {
      message.error(error.message || '生成排班失败');
      return false;
    }
  };

  const columns: ProColumns<ScheduleTemplate>[] = [
    {
      title: '规则名称',
      dataIndex: 'name',
      width: 200,
    },
    {
      title: '门店',
      dataIndex: 'storeName',
      width: 120,
      search: false,
    },
    {
      title: '医生',
      dataIndex: 'doctorName',
      width: 100,
    },
    {
      title: '科室',
      dataIndex: 'departmentName',
      width: 100,
      search: false,
    },
    {
      title: '星期',
      dataIndex: 'weekdays',
      width: 150,
      search: false,
      render: (_, record) => {
        const weekdays = record.weekdays || [];
        return weekdays.map((w: number) => WEEKDAY_MAP[w]).join('、');
      },
    },
    {
      title: '预约类型',
      dataIndex: 'appointmentType',
      width: 80,
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
          <Tag color={typeMap[record.appointmentType] || 'default'}>
            {APPOINTMENT_TYPE_MAP[record.appointmentType] || record.appointmentType}
          </Tag>
        );
      },
    },
    {
      title: '时间区间',
      dataIndex: 'startTime',
      width: 150,
      search: false,
      render: (_, record) => `${record.startTime} - ${record.endTime}`,
    },
    {
      title: '班次数量',
      dataIndex: 'slotCount',
      width: 80,
      search: false,
      render: (_, record) => `${record.slotCount || 1}个`,
    },
    {
      title: '班次人数',
      dataIndex: 'slotCapacity',
      width: 80,
      search: false,
      render: (_, record) => record.slotCapacity || record.totalSlots || 10,
    },
    {
      title: '排班方式',
      dataIndex: 'scheduleMode',
      width: 100,
      search: false,
      render: (_, record) => SCHEDULE_MODE_MAP[record.scheduleMode] || record.scheduleMode,
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 80,
      valueEnum: {
        1: { text: '启用', status: 'Success' },
        0: { text: '禁用', status: 'Default' },
      },
    },
    {
      title: '操作',
      valueType: 'option',
      width: 180,
      render: (_, record) => (
        <Space>
          {access.hasPermission('schedule:template') && (
            <a onClick={() => history.push(`/schedule/rule/${record.id}/edit`)}>
              编辑
            </a>
          )}
          {access.hasPermission('schedule:template') && (
            <Popconfirm title="确定删除该规则吗？" onConfirm={() => handleDelete(record.id)}>
              <a style={{ color: '#ff4d4f' }}>删除</a>
            </Popconfirm>
          )}
        </Space>
      ),
    },
  ];

  return (
    <PageContainer>
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

      <ProTable<ScheduleTemplate>
        headerTitle="排班规则列表"
        actionRef={actionRef}
        rowKey="id"
        columns={columns}
        rowSelection={{
          selectedRowKeys: selectedTemplates,
          onChange: (keys) => setSelectedTemplates(keys as string[]),
        }}
        request={async (params) => {
          const { current, pageSize, ...rest } = params;
          return toProTableResult(
            await scheduleTemplateApi.getList({
              ...rest,
              page: current,
              pageSize,
            }),
          );
        }}
        toolBarRender={() => [
          access.hasPermission('schedule:template') && (
            <Button
              key="generate"
              icon={<ThunderboltOutlined />}
              disabled={selectedTemplates.length === 0}
              onClick={() => setGenerateModalOpen(true)}
            >
              生成排班 ({selectedTemplates.length})
            </Button>
          ),
          access.hasPermission('schedule:template') && (
            <Button
              key="batch"
              onClick={() => setBatchAddModalOpen(true)}
            >
              批量添加
            </Button>
          ),
          access.hasPermission('schedule:template') && (
            <Button
              key="add"
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => history.push('/schedule/rule/create')}
            >
              新增规则
            </Button>
          ),
        ]}
        pagination={{ defaultPageSize: 10 }}
      />

      {/* 批量添加弹窗 */}
      <ModalForm
        title="批量添加排班规则"
        open={batchAddModalOpen}
        onOpenChange={(open) => {
          setBatchAddModalOpen(open);
          if (!open) {
            setSelectedDept(undefined);
          }
        }}
        onFinish={handleBatchAddSubmit}
        initialValues={{
          appointmentType: 'normal',
          scheduleMode: 'weekly',
          totalSlots: 10,
          slotCount: 1,
          weekdays: [1, 2, 3, 4, 5],
        }}
        modalProps={{ destroyOnHidden: true }}
        width={600}
      >
        <Alert
          message={`当前为本月第${dateInfo.monthWeek}周，本年第${dateInfo.yearWeek}周（${dateInfo.isOddWeek ? '奇数' : '偶数'}周）`}
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
        />
        <ProFormSelect
          name="storeId"
          label="选择门店"
          options={stores.map((s) => ({ label: s.name, value: s.id }))}
          rules={[{ required: true, message: '请选择门店' }]}
        />
        <ProFormSelect
          name="departmentId"
          label="选择科室"
          options={departments.map((d) => ({ label: d.name, value: d.id }))}
          onChange={(val) => setSelectedDept(val as string)}
          rules={[{ required: true, message: '请选择科室' }]}
        />
        <ProFormSelect
          name="doctorId"
          label="选择医生"
          options={doctors.map((d) => ({ label: `${d.name} - ${d.title || ''}`, value: d.id }))}
          rules={[{ required: true, message: '请选择医生' }]}
          disabled={!selectedDept}
        />
        <ProFormSelect
          name="appointmentType"
          label="预约类型"
          options={APPOINTMENT_TYPE_OPTIONS}
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
          name="slotCount"
          label="班次数量"
          min={1}
          max={50}
          rules={[{ required: true, message: '请输入班次数量' }]}
          extra="根据时间区间均分生成多个班次"
        />
        <ProFormDigit
          name="totalSlots"
          label="班次人数"
          min={1}
          max={200}
          rules={[{ required: true, message: '请输入班次人数' }]}
          extra="每个班次可预约的人数"
        />
        <ProFormCheckbox.Group
          name="weekdays"
          label="选择星期"
          options={WEEKDAY_OPTIONS}
          rules={[{ required: true, message: '请选择星期' }]}
        />
        <ProFormRadio.Group
          name="scheduleMode"
          label="排班方式"
          options={SCHEDULE_MODE_OPTIONS}
          rules={[{ required: true, message: '请选择排班方式' }]}
        />
        <ProFormDateRangePicker
          name="dateRange"
          label="日期范围"
          rules={[{ required: true, message: '请选择日期范围' }]}
        />
      </ModalForm>

      {/* 生成排班弹窗 */}
      <ModalForm
        title="根据规则生成排班"
        open={generateModalOpen}
        onOpenChange={setGenerateModalOpen}
        onFinish={handleGenerateSubmit}
        modalProps={{ destroyOnHidden: true }}
        width={400}
      >
        <Alert
          message={`已选择 ${selectedTemplates.length} 个规则`}
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
        />
        <ProFormDateRangePicker
          name="dateRange"
          label="生成日期范围"
          rules={[{ required: true, message: '请选择日期范围' }]}
          extra="系统将根据规则配置的星期和排班方式，在日期范围内生成对应的排班"
        />
      </ModalForm>
    </PageContainer>
  );
};

export default ScheduleRulePage;

