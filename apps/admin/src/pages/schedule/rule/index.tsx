import { PlusOutlined, ThunderboltOutlined, DeleteOutlined, StopOutlined, HistoryOutlined, CalendarOutlined, CopyOutlined } from '@ant-design/icons';
import type { ActionType, ProColumns, ProFormInstance } from '@ant-design/pro-components';
import {
  PageContainer,
  ProTable,
  ModalForm,
  ProForm,
  ProFormSelect,
  ProFormTimePicker,
  ProFormDateRangePicker,
  ProFormDatePicker,
  ProFormCheckbox,
  ProFormRadio,
  ProFormDigit,
} from '@ant-design/pro-components';
import { Button, App, Space, Popconfirm, Tag, Alert, Modal, Table, Tooltip, Dropdown, InputNumber, Tabs, Steps, Transfer, Select } from 'antd';
import { EyeOutlined } from '@ant-design/icons';
import type { MenuProps } from 'antd';
import { useRef, useState, useEffect, useMemo } from 'react';
import { history, useAccess, useModel } from '@umijs/max';
import { scheduleTemplateApi, doctorApi, departmentApi, storeApi } from '@hospital/api';
import { toProTableResult } from '@/utils/proTable';
import { fetchAllData } from '@/utils/fetchAllData';
import type { ScheduleTemplate, Doctor, Department, Store, ScheduleSlotPreview, SchedulePreviewGenerateResponse } from '@hospital/shared';
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
  const generateFormRef = useRef<ProFormInstance>();
  const batchAddFormRef = useRef<ProFormInstance>();
  const [batchAddModalOpen, setBatchAddModalOpen] = useState(false);
  const [generateModalOpen, setGenerateModalOpen] = useState(false);
  const [logsModalOpen, setLogsModalOpen] = useState(false);
  const [selectedTemplates, setSelectedTemplates] = useState<string[]>([]);
  const [currentTemplate, setCurrentTemplate] = useState<ScheduleTemplate | null>(null);
  const [logs, setLogs] = useState<any[]>([]);
  const [logsLoading, setLogsLoading] = useState(false);
  
  // 预览相关状态
  const [previewData, setPreviewData] = useState<SchedulePreviewGenerateResponse[]>([]);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [showPreview, setShowPreview] = useState(false);
  // 存储编辑过的班次容量
  const [editedCapacities, setEditedCapacities] = useState<Record<string, number>>({});
  // 生成排班 loading 状态
  const [generateLoading, setGenerateLoading] = useState(false);

  const [stores, setStores] = useState<Store[]>([]);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [doctors, setDoctors] = useState<Doctor[]>([]);
  const [selectedDept, setSelectedDept] = useState<string>();

  // 复制规则相关状态
  const [copyModalOpen, setCopyModalOpen] = useState(false);
  const [copyStep, setCopyStep] = useState(0); // 0: 编辑配置, 1: 选择医生
  const [copySourceTemplate, setCopySourceTemplate] = useState<ScheduleTemplate | null>(null);
  const [copyFormData, setCopyFormData] = useState<any>(null);
  const [copyTargetDoctorIds, setCopyTargetDoctorIds] = useState<string[]>([]);
  const [copyLoading, setCopyLoading] = useState(false);
  const [allDoctors, setAllDoctors] = useState<Doctor[]>([]);
  const [copyDeptFilter, setCopyDeptFilter] = useState<string | undefined>(undefined);

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
      const data = await departmentApi.getAll();
      setDepartments(data ?? []);
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

  // 加载所有医生（用于复制弹窗）
  const loadAllDoctors = async () => {
    try {
      const doctors = await fetchAllData((page, pageSize) =>
        doctorApi.getList({ page, pageSize, status: 1 })
      );
      setAllDoctors(doctors);
    } catch (error) {
      console.error('加载所有医生失败', error);
    }
  };

  // 打开复制弹窗
  const handleOpenCopyModal = async (record: ScheduleTemplate) => {
    setCopySourceTemplate(record);
    // 初始化表单数据
    setCopyFormData({
      name: record.name,
      weekdays: record.weekdays || [],
      appointmentType: record.appointmentType || 'normal',
      startTime: record.startTime,
      endTime: record.endTime,
      slotCount: record.slotCount || 1,
      slotCapacity: record.slotCapacity || 10,
      scheduleMode: record.scheduleMode || 'weekly',
      breakTimes: record.breakTimes || [],
    });
    setCopyStep(0);
    setCopyTargetDoctorIds([]);
    setCopyDeptFilter(undefined);
    setCopyModalOpen(true);
    // 加载所有医生
    await loadAllDoctors();
  };

  // 复制规则下一步
  const handleCopyNextStep = () => {
    setCopyStep(1);
  };

  // 复制规则上一步
  const handleCopyPrevStep = () => {
    setCopyStep(0);
  };

  // 确认复制
  const handleConfirmCopy = async () => {
    if (copyTargetDoctorIds.length === 0) {
      message.error('请选择至少一个目标医生');
      return;
    }

    if (!copySourceTemplate) {
      message.error('复制源规则不存在');
      return;
    }

    setCopyLoading(true);
    try {
      const result = await scheduleTemplateApi.copy(copySourceTemplate.id, {
        targetDoctorIds: copyTargetDoctorIds,
        name: copyFormData.name,
        weekdays: copyFormData.weekdays,
        appointmentType: copyFormData.appointmentType,
        startTime: copyFormData.startTime,
        endTime: copyFormData.endTime,
        slotCount: copyFormData.slotCount,
        slotCapacity: copyFormData.slotCapacity,
        scheduleMode: copyFormData.scheduleMode,
        breakTimes: copyFormData.breakTimes,
      });
      message.success(result.message);
      setCopyModalOpen(false);
      actionRef.current?.reload();
    } catch (error: any) {
      message.error(error.message || '复制失败');
    } finally {
      setCopyLoading(false);
    }
  };

  // 过滤后的医生列表（排除源规则的医生）
  const filteredDoctors = useMemo(() => {
    let list = allDoctors;
    // 排除源规则的医生
    if (copySourceTemplate) {
      list = list.filter(d => d.id !== copySourceTemplate.doctorId);
    }
    // 按科室过滤
    if (copyDeptFilter) {
      list = list.filter(d => d.departmentId === copyDeptFilter);
    }
    return list;
  }, [allDoctors, copySourceTemplate, copyDeptFilter]);

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

  // 预览生成排班
  const handlePreviewGenerate = async () => {
    const values = generateFormRef.current?.getFieldsValue();
    const { startDate: startDateVal, endDate: endDateVal } = values || {};

    if (selectedTemplates.length === 0) {
      message.error('请先选择要使用的规则');
      return;
    }

    const startDate = startDateVal 
      ? (typeof startDateVal === 'string' ? startDateVal : startDateVal.format('YYYY-MM-DD'))
      : undefined;
    const endDate = endDateVal 
      ? (typeof endDateVal === 'string' ? endDateVal : endDateVal.format('YYYY-MM-DD'))
      : dayjs().add(30, 'day').format('YYYY-MM-DD');

    setPreviewLoading(true);
    try {
      const result = await scheduleTemplateApi.previewGenerate({
        templateIds: selectedTemplates,
        startDate,
        endDate,
      });
      setPreviewData(result);
      setEditedCapacities({});
      setShowPreview(true);
    } catch (error: any) {
      message.error(error.message || '预览生成失败');
    } finally {
      setPreviewLoading(false);
    }
  };

  // 确认生成（带自定义容量）
  const handleConfirmGenerate = async () => {
    const values = generateFormRef.current?.getFieldsValue();
    const { startDate: startDateVal, endDate: endDateVal } = values || {};

    const startDate = startDateVal 
      ? (typeof startDateVal === 'string' ? startDateVal : startDateVal.format('YYYY-MM-DD'))
      : undefined;
    const endDate = endDateVal 
      ? (typeof endDateVal === 'string' ? endDateVal : endDateVal.format('YYYY-MM-DD'))
      : undefined;

    // 构建容量覆盖数据
    const slotCapacities = Object.entries(editedCapacities).map(([key, capacity]) => {
      const [scheduleDate, startTime, endTime] = key.split('|');
      return { scheduleDate, startTime, endTime, slotCapacity: capacity };
    });

    setGenerateLoading(true);
    try {
      const result = await scheduleTemplateApi.generateWithCapacity({
        templateIds: selectedTemplates,
        startDate,
        endDate,
        slotCapacities: slotCapacities.length > 0 ? slotCapacities : undefined,
      });
      message.success(result.message);
      setGenerateModalOpen(false);
      setShowPreview(false);
      setPreviewData([]);
      setEditedCapacities({});
      setSelectedTemplates([]);
      actionRef.current?.reload();
    } catch (error: any) {
      message.error(error.message || '生成排班失败');
    } finally {
      setGenerateLoading(false);
    }
  };

  const handleGenerateSubmit = async (values: any) => {
    const { startDate: startDateVal, endDate: endDateVal } = values;

    if (selectedTemplates.length === 0) {
      message.error('请先选择要使用的规则');
      return false;
    }

    // 格式化日期（可选，为空时后端会使用默认值）
    const startDate = startDateVal 
      ? (typeof startDateVal === 'string' ? startDateVal : startDateVal.format('YYYY-MM-DD'))
      : undefined;
    const endDate = endDateVal 
      ? (typeof endDateVal === 'string' ? endDateVal : endDateVal.format('YYYY-MM-DD'))
      : undefined;

    // 检查是否已生成过排班（只在有日期时检查）
    if (startDate || endDate) {
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
    }

    setGenerateLoading(true);
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
    } finally {
      setGenerateLoading(false);
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
      key: 'copy',
      icon: <CopyOutlined />,
      label: '复制规则',
      onClick: () => handleOpenCopyModal(record),
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
        formRef={batchAddFormRef}
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
          onChange={(val) => {
            setSelectedDept(val as string);
            batchAddFormRef.current?.setFieldValue('doctorId', undefined);
          }}
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
      <Modal
        title={currentTemplate ? `生成排班 - ${currentTemplate.name}` : '根据规则生成排班'}
        open={generateModalOpen}
        onCancel={() => {
          setGenerateModalOpen(false);
          setCurrentTemplate(null);
          setShowPreview(false);
          setPreviewData([]);
          setEditedCapacities({});
        }}
        footer={showPreview ? (
          <Space>
            <Button onClick={() => setShowPreview(false)} disabled={generateLoading}>返回设置</Button>
            <Button type="primary" onClick={handleConfirmGenerate} loading={generateLoading}>
              确认生成 ({previewData.reduce((acc, p) => acc + p.totalCount, 0)} 条)
            </Button>
          </Space>
        ) : (
          <Space>
            <Button onClick={() => setGenerateModalOpen(false)} disabled={generateLoading}>取消</Button>
            <Button
              icon={<EyeOutlined />}
              onClick={handlePreviewGenerate}
              loading={previewLoading}
              disabled={generateLoading}
            >
              预览班次
            </Button>
            <Button type="primary" onClick={() => generateFormRef.current?.submit()} loading={generateLoading}>
              直接生成
            </Button>
          </Space>
        )}
        destroyOnHidden
        width={showPreview ? 900 : 500}
      >
        {!showPreview ? (
          <ProForm
            formRef={generateFormRef}
            onFinish={handleGenerateSubmit}
            submitter={false}
          >
            {currentTemplate ? (
              <Alert
                message={
                  <div>
                    <div>规则：<strong>{currentTemplate.name}</strong></div>
                    <div style={{ fontSize: 12, color: '#666', marginTop: 4 }}>
                      医生：{currentTemplate.doctorName} | 科室：{currentTemplate.departmentName} | 
                      星期：{(currentTemplate.weekdays || []).map((w: number) => WEEKDAY_MAP[w]).join('、')}
                      {currentTemplate.breakTimes && currentTemplate.breakTimes.length > 0 && (
                        <span> | 排除时间：{currentTemplate.breakTimes.map(bt => `${bt.startTime}-${bt.endTime}`).join('、')}</span>
                      )}
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
            
            {/* 快捷选择按钮 */}
            <div style={{ marginBottom: 16 }}>
              <div style={{ marginBottom: 8, color: '#666' }}>快捷选择：</div>
              <Space wrap>
                {[
                  { label: '1个月', months: 1 },
                  { label: '2个月', months: 2 },
                  { label: '3个月', months: 3 },
                  { label: '6个月', months: 6 },
                  { label: '1年', months: 12 },
                  { label: '2年', months: 24 },
                  { label: '3年', months: 36 },
                ].map((item) => (
                  <Button
                    key={item.label}
                    size="small"
                    onClick={() => {
                      const start = dayjs();
                      const end = dayjs().add(item.months, 'month');
                      generateFormRef.current?.setFieldsValue({
                        startDate: start,
                        endDate: end,
                      });
                    }}
                  >
                    {item.label}
                  </Button>
                ))}
              </Space>
            </div>
            
            <ProFormDatePicker
              name="startDate"
              label="开始日期"
              placeholder="不选则默认今天"
              extra="可选，不填写默认从今天开始"
            />
            <ProFormDatePicker
              name="endDate"
              label="结束日期"
              placeholder="不选则默认1年后"
              extra="可选，不填写默认生成到1年后（预览默认30天）"
            />
            <Alert
              message="点击「预览班次」可查看并编辑每个班次的可预约人数，或直接点击「直接生成」使用默认设置"
              type="info"
              showIcon
              style={{ marginTop: 8 }}
            />
          </ProForm>
        ) : (
          <div>
            <Alert
              message={`预览：共 ${previewData.reduce((acc, p) => acc + p.totalCount, 0)} 个班次，可修改每个班次的可预约人数`}
              type="success"
              showIcon
              style={{ marginBottom: 16 }}
            />
            
            {previewData.map((preview) => {
              // 按时段分组
              const groupedByPeriod: Record<string, typeof preview.slots> = {};
              preview.slots.forEach((slot) => {
                const periodName = slot.periodName || '其他';
                if (!groupedByPeriod[periodName]) {
                  groupedByPeriod[periodName] = [];
                }
                groupedByPeriod[periodName].push(slot);
              });
              const periodNames = Object.keys(groupedByPeriod);
              
              return (
                <div key={preview.templateId} style={{ marginBottom: 16 }}>
                  <div style={{ marginBottom: 8 }}>
                    <span style={{ fontWeight: 500 }}>
                      {preview.templateName} - {preview.doctorName} ({preview.departmentName})
                    </span>
                    {preview.dailyDurationHours !== undefined && (
                      <span style={{ marginLeft: 16, color: '#666', fontSize: 12 }}>
                        每日总时长：{preview.dailyDurationHours}小时
                        {preview.dailyDurationMinutes !== undefined && preview.dailyDurationMinutes > 0 && `${preview.dailyDurationMinutes}分钟`}
                      </span>
                    )}
                  </div>
                  
                  {periodNames.length > 1 ? (
                    <Tabs
                      items={periodNames.map((periodName) => ({
                        key: periodName,
                        label: `${periodName} (${groupedByPeriod[periodName].length})`,
                        children: (
                          <Table
                            size="small"
                            dataSource={groupedByPeriod[periodName]}
                            rowKey={(record) => `${record.scheduleDate}-${record.startTime}-${record.endTime}`}
                            pagination={{ pageSize: 10, showSizeChanger: true, showTotal: (total) => `共 ${total} 条` }}
                            columns={[
                              { title: '日期', dataIndex: 'scheduleDate', width: 110 },
                              { title: '星期', dataIndex: 'weekdayName', width: 70 },
                              { title: '时间段', render: (_, record) => `${record.startTime} - ${record.endTime}`, width: 130 },
                              {
                                title: '可预约人数',
                                dataIndex: 'slotCapacity',
                                width: 120,
                                render: (val, record) => {
                                  const key = `${record.scheduleDate}|${record.startTime}|${record.endTime}`;
                                  const editedValue = editedCapacities[key];
                                  return (
                                    <InputNumber
                                      size="small"
                                      min={1}
                                      max={200}
                                      value={editedValue !== undefined ? editedValue : val}
                                      onChange={(newVal) => {
                                        if (newVal !== null) {
                                          setEditedCapacities(prev => ({ ...prev, [key]: newVal }));
                                        }
                                      }}
                                      style={{ width: 80 }}
                                    />
                                  );
                                },
                              },
                            ]}
                          />
                        ),
                      }))}
                    />
                  ) : (
                    <Table
                      size="small"
                      dataSource={preview.slots}
                      rowKey={(record) => `${record.scheduleDate}-${record.startTime}-${record.endTime}`}
                      pagination={{ pageSize: 10, showSizeChanger: true, showTotal: (total) => `共 ${total} 条` }}
                      columns={[
                        { title: '日期', dataIndex: 'scheduleDate', width: 110 },
                        { title: '星期', dataIndex: 'weekdayName', width: 70 },
                        { title: '时间段', render: (_, record) => `${record.startTime} - ${record.endTime}`, width: 130 },
                        { title: '时段', dataIndex: 'periodName', width: 80 },
                        {
                          title: '可预约人数',
                          dataIndex: 'slotCapacity',
                          width: 120,
                          render: (val, record) => {
                            const key = `${record.scheduleDate}|${record.startTime}|${record.endTime}`;
                            const editedValue = editedCapacities[key];
                            return (
                              <InputNumber
                                size="small"
                                min={1}
                                max={200}
                                value={editedValue !== undefined ? editedValue : val}
                                onChange={(newVal) => {
                                  if (newVal !== null) {
                                    setEditedCapacities(prev => ({ ...prev, [key]: newVal }));
                                  }
                                }}
                                style={{ width: 80 }}
                              />
                            );
                          },
                        },
                      ]}
                    />
                  )}
                </div>
              );
            })}
          </div>
        )}
      </Modal>

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

      {/* 复制规则弹窗 */}
      <Modal
        title="复制排班规则"
        open={copyModalOpen}
        onCancel={() => {
          setCopyModalOpen(false);
          setCopySourceTemplate(null);
          setCopyFormData(null);
          setCopyStep(0);
          setCopyTargetDoctorIds([]);
        }}
        footer={
          <Space>
            <Button onClick={() => setCopyModalOpen(false)}>取消</Button>
            {copyStep === 0 ? (
              <Button type="primary" onClick={handleCopyNextStep}>
                下一步：选择医生
              </Button>
            ) : (
              <>
                <Button onClick={handleCopyPrevStep}>上一步</Button>
                <Button
                  type="primary"
                  loading={copyLoading}
                  onClick={handleConfirmCopy}
                  disabled={copyTargetDoctorIds.length === 0}
                >
                  确认复制 ({copyTargetDoctorIds.length})
                </Button>
              </>
            )}
          </Space>
        }
        width={700}
        destroyOnHidden
      >
        <Steps
          current={copyStep}
          items={[
            { title: '调整配置' },
            { title: '选择医生' },
          ]}
          style={{ marginBottom: 24 }}
        />

        {copyStep === 0 && copyFormData && (
          <div>
            <Alert
              message={
                <div>
                  复制来源：<strong>{copySourceTemplate?.name}</strong>
                  <span style={{ marginLeft: 16, color: '#666' }}>
                    医生：{copySourceTemplate?.doctorName}
                  </span>
                </div>
              }
              type="info"
              showIcon
              style={{ marginBottom: 16 }}
            />
            
            <ProForm
              layout="horizontal"
              labelCol={{ span: 6 }}
              wrapperCol={{ span: 18 }}
              submitter={false}
              initialValues={copyFormData}
              onValuesChange={(_, allValues) => {
                setCopyFormData(allValues);
              }}
            >
              <ProFormCheckbox.Group
                name="weekdays"
                label="选择星期"
                options={WEEKDAY_OPTIONS}
              />
              <ProFormSelect
                name="appointmentType"
                label="预约类型"
                options={APPOINTMENT_TYPE_OPTIONS}
              />
              <ProFormTimePicker
                name="startTime"
                label="开始时间"
                fieldProps={{ format: 'HH:mm' }}
              />
              <ProFormTimePicker
                name="endTime"
                label="结束时间"
                fieldProps={{ format: 'HH:mm' }}
              />
              <ProFormDigit
                name="slotCount"
                label="班次数量"
                min={1}
                max={50}
                fieldProps={{ style: { width: 120 } }}
              />
              <ProFormDigit
                name="slotCapacity"
                label="班次人数"
                min={1}
                max={200}
                fieldProps={{ style: { width: 120 } }}
              />
              <ProFormRadio.Group
                name="scheduleMode"
                label="排班方式"
                options={SCHEDULE_MODE_OPTIONS}
              />
            </ProForm>
          </div>
        )}

        {copyStep === 1 && (
          <div>
            <Alert
              message="选择要复制规则的目标医生，可选择多个医生"
              type="info"
              showIcon
              style={{ marginBottom: 16 }}
            />
            
            <div style={{ marginBottom: 16 }}>
              <span style={{ marginRight: 8 }}>按科室筛选：</span>
              <Select
                allowClear
                placeholder="全部科室"
                style={{ width: 200 }}
                value={copyDeptFilter}
                onChange={(val) => setCopyDeptFilter(val)}
                options={departments.map(d => ({ label: d.name, value: d.id }))}
              />
            </div>
            
            <Transfer
              dataSource={filteredDoctors.map(d => ({
                key: d.id,
                title: d.name,
                description: `${d.departmentName || ''} ${d.title || ''}`.trim(),
              }))}
              titles={['可选医生', '已选医生']}
              targetKeys={copyTargetDoctorIds}
              onChange={(nextTargetKeys) => setCopyTargetDoctorIds(nextTargetKeys as string[])}
              render={(item) => (
                <span>
                  {item.title}
                  {item.description && (
                    <span style={{ color: '#999', fontSize: 12, marginLeft: 8 }}>
                      {item.description}
                    </span>
                  )}
                </span>
              )}
              listStyle={{
                width: 280,
                height: 350,
              }}
              showSearch
              filterOption={(inputValue, item) =>
                item.title!.toLowerCase().includes(inputValue.toLowerCase()) ||
                (item.description || '').toLowerCase().includes(inputValue.toLowerCase())
              }
            />
          </div>
        )}
      </Modal>
    </PageContainer>
  );
};

export default ScheduleRulePage;
