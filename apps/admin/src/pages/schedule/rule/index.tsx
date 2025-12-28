import { PlusOutlined, ThunderboltOutlined, DeleteOutlined, StopOutlined, HistoryOutlined, CalendarOutlined } from '@ant-design/icons';
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
import { Button, App, Space, Popconfirm, Tag, Alert, Modal, Table, Tooltip, Dropdown } from 'antd';
import type { MenuProps } from 'antd';
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
import dayjs from 'dayjs';

// 操作类型映射
const ACTION_TYPE_MAP: Record<string, { text: string; color: string }> = {
  generate: { text: '生成排班', color: 'green' },
  delete: { text: '删除排班', color: 'red' },
  suspend: { text: '批量停诊', color: 'orange' },
};

const ScheduleRulePage: React.FC = () => {
  const { message, modal } = App.useApp();
  const access = useAccess();
  const { initialState } = useModel('@@initialState');
  const { currentUser } = initialState ?? {};
  const isSuperAdmin = access.canSuperAdmin;
  const actionRef = useRef<ActionType>();
  const [batchAddModalOpen, setBatchAddModalOpen] = useState(false);
  const [generateModalOpen, setGenerateModalOpen] = useState(false);
  const [logsModalOpen, setLogsModalOpen] = useState(false);
  const [selectedTemplates, setSelectedTemplates] = useState<string[]>([]);
  const [currentTemplate, setCurrentTemplate] = useState<ScheduleTemplate | null>(null);
  const [logs, setLogs] = useState<any[]>([]);
  const [logsLoading, setLogsLoading] = useState(false);

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

  // 批量删除排班
  const handleBatchDelete = async (record: ScheduleTemplate) => {
    modal.confirm({
      title: '确认删除排班',
      content: (
        <div>
          <p>确定要删除该规则生成的所有<strong>未来</strong>排班吗？</p>
          <p style={{ color: '#999', fontSize: 12 }}>注意：已有预约的排班不会被删除</p>
        </div>
      ),
      okText: '确认删除',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        try {
          const result = await scheduleTemplateApi.batchDelete(record.id);
          message.success(result.message);
          actionRef.current?.reload();
        } catch (error: any) {
          message.error(error.message || '删除失败');
        }
      },
    });
  };

  // 批量停诊
  const handleBatchSuspend = async (record: ScheduleTemplate) => {
    modal.confirm({
      title: '确认批量停诊',
      content: (
        <div>
          <p>确定要停诊该规则生成的所有<strong>未来</strong>排班吗？</p>
          <p style={{ color: '#999', fontSize: 12 }}>停诊后可在排班列表中恢复</p>
        </div>
      ),
      okText: '确认停诊',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        try {
          const result = await scheduleTemplateApi.batchSuspend(record.id);
          message.success(result.message);
          actionRef.current?.reload();
        } catch (error: any) {
          message.error(error.message || '停诊失败');
        }
      },
    });
  };

  // 查看历史记录
  const handleViewLogs = async (record: ScheduleTemplate) => {
    setCurrentTemplate(record);
    setLogsModalOpen(true);
    setLogsLoading(true);
    try {
      const result = await scheduleTemplateApi.getLogs(record.id, 1, 50);
      setLogs(result.data ?? []);
    } catch (error: any) {
      message.error(error.message || '加载历史记录失败');
    } finally {
      setLogsLoading(false);
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

    // 格式化日期
    const startDate = typeof dateRange[0] === 'string' 
      ? dateRange[0] 
      : dateRange[0].format('YYYY-MM-DD');
    const endDate = typeof dateRange[1] === 'string' 
      ? dateRange[1] 
      : dateRange[1].format('YYYY-MM-DD');

    // 检查是否已生成过排班
    let hasExisting = false;
    let totalExistingCount = 0;
    
    for (const templateId of selectedTemplates) {
      try {
        const checkResult = await scheduleTemplateApi.checkGenerated(templateId, startDate, endDate);
        if (checkResult.hasGenerated && checkResult.dateRangeCount > 0) {
          hasExisting = true;
          totalExistingCount += checkResult.dateRangeCount;
        }
      } catch (error) {
        console.error('检查生成状态失败', error);
      }
    }

    // 如果已存在排班，弹出确认框
    if (hasExisting) {
      const confirmed = await new Promise<boolean>((resolve) => {
        modal.confirm({
          title: '检测到已存在排班',
          content: (
            <div>
              <p>在所选日期范围内，已存在 <strong>{totalExistingCount}</strong> 条排班记录。</p>
              <p>是否继续生成？（不会删除已有排班，只会跳过已存在的时段）</p>
            </div>
          ),
          okText: '继续生成',
          cancelText: '取消',
          onOk: () => resolve(true),
          onCancel: () => resolve(false),
        });
      });

      if (!confirmed) {
        return false;
      }
    }

    try {
      const result = await scheduleTemplateApi.generate({
        templateIds: selectedTemplates,
        startDate,
        endDate,
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

  // 单个规则生成排班
  const handleSingleGenerate = (record: ScheduleTemplate) => {
    setSelectedTemplates([record.id]);
    setCurrentTemplate(record);
    setGenerateModalOpen(true);
  };

  // 操作菜单
  const getActionMenuItems = (record: ScheduleTemplate): MenuProps['items'] => [
    {
      key: 'generate',
      icon: <CalendarOutlined />,
      label: '生成排班',
      onClick: () => handleSingleGenerate(record),
    },
    {
      key: 'edit',
      label: '编辑',
      onClick: () => history.push(`/schedule/rule/${record.id}/edit`),
    },
    {
      key: 'logs',
      icon: <HistoryOutlined />,
      label: '历史记录',
      onClick: () => handleViewLogs(record),
    },
    {
      type: 'divider',
    },
    {
      key: 'batchDelete',
      icon: <DeleteOutlined />,
      label: '删除排班',
      danger: true,
      onClick: () => handleBatchDelete(record),
    },
    {
      key: 'batchSuspend',
      icon: <StopOutlined />,
      label: '批量停诊',
      danger: true,
      onClick: () => handleBatchSuspend(record),
    },
    {
      type: 'divider',
    },
    {
      key: 'delete',
      label: '删除规则',
      danger: true,
      onClick: () => {
        modal.confirm({
          title: '确认删除',
          content: '确定要删除该排班规则吗？删除后不可恢复。',
          okText: '删除',
          okType: 'danger',
          cancelText: '取消',
          onOk: () => handleDelete(record.id),
        });
      },
    },
  ];

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
      render: (_, record) => record.slotCapacity || 10,
    },
    {
      title: '排班方式',
      dataIndex: 'scheduleMode',
      width: 100,
      search: false,
      render: (_, record) => SCHEDULE_MODE_MAP[record.scheduleMode] || record.scheduleMode,
    },
    {
      title: '生成状态',
      dataIndex: 'lastGeneratedAt',
      width: 90,
      search: false,
      render: (_, record) => {
        if (record.lastGeneratedAt) {
          return <Tag color="success">已生成</Tag>;
        }
        return <Tag color="default">未生成</Tag>;
      },
    },
    {
      title: '上次生成时间',
      dataIndex: 'lastGeneratedAt',
      width: 160,
      search: false,
      render: (_, record) => {
        if (record.lastGeneratedAt) {
          return dayjs(record.lastGeneratedAt).format('YYYY-MM-DD HH:mm');
        }
        return '-';
      },
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
      width: 120,
      fixed: 'right',
      render: (_, record) => (
        <Space>
          {access.hasPermission('schedule:template') && (
            <Dropdown menu={{ items: getActionMenuItems(record) }} trigger={['click']}>
              <a onClick={(e) => e.preventDefault()}>操作 ▼</a>
            </Dropdown>
          )}
        </Space>
      ),
    },
  ];

  // 历史记录表格列
  const logsColumns = [
    {
      title: '操作类型',
      dataIndex: 'actionType',
      width: 100,
      render: (type: string) => {
        const info = ACTION_TYPE_MAP[type] || { text: type, color: 'default' };
        return <Tag color={info.color}>{info.text}</Tag>;
      },
    },
    {
      title: '操作人',
      dataIndex: 'operatorName',
      width: 100,
    },
    {
      title: '日期范围',
      width: 180,
      render: (_: any, record: any) => {
        if (record.startDate && record.endDate) {
          return `${record.startDate} ~ ${record.endDate}`;
        }
        return record.startDate || record.endDate || '-';
      },
    },
    {
      title: '影响记录数',
      dataIndex: 'affectedCount',
      width: 100,
    },
    {
      title: '操作时间',
      dataIndex: 'createdAt',
      width: 160,
      render: (time: string) => dayjs(time).format('YYYY-MM-DD HH:mm:ss'),
    },
    {
      title: '备注',
      dataIndex: 'remark',
      ellipsis: true,
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
        scroll={{ x: 1650 }}
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
        title={currentTemplate ? `生成排班 - ${currentTemplate.name}` : '根据规则生成排班'}
        open={generateModalOpen}
        onOpenChange={(open) => {
          setGenerateModalOpen(open);
          if (!open) {
            setCurrentTemplate(null);
          }
        }}
        onFinish={handleGenerateSubmit}
        modalProps={{ destroyOnHidden: true }}
        width={500}
      >
        {currentTemplate ? (
          <Alert
            message={
              <div>
                <div>规则：<strong>{currentTemplate.name}</strong></div>
                <div style={{ fontSize: 12, color: '#666', marginTop: 4 }}>
                  医生：{currentTemplate.doctorName} | 科室：{currentTemplate.departmentName} | 
                  星期：{(currentTemplate.weekdays || []).map((w: number) => WEEKDAY_MAP[w]).join('、')}
                </div>
              </div>
            }
            type="info"
            showIcon
            style={{ marginBottom: 16 }}
          />
        ) : (
          <Alert
            message={`已选择 ${selectedTemplates.length} 个规则`}
            type="info"
            showIcon
            style={{ marginBottom: 16 }}
          />
        )}
        <ProFormDateRangePicker
          name="dateRange"
          label="生成日期范围"
          rules={[{ required: true, message: '请选择日期范围' }]}
          extra="系统将根据规则配置的星期和排班方式，在日期范围内生成对应的排班"
        />
      </ModalForm>

      {/* 历史记录弹窗 */}
      <Modal
        title={`历史记录 - ${currentTemplate?.name || ''}`}
        open={logsModalOpen}
        onCancel={() => setLogsModalOpen(false)}
        footer={null}
        width={1300}
      >
        <Table
          columns={logsColumns}
          dataSource={logs}
          loading={logsLoading}
          rowKey="id"
          pagination={{ pageSize: 10 }}
          size="small"
          locale={{ emptyText: '暂无历史记录' }}
        />
      </Modal>
    </PageContainer>
  );
};

export default ScheduleRulePage;
