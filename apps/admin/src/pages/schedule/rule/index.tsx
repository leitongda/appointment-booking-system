import { PlusOutlined, ThunderboltOutlined, DeleteOutlined, StopOutlined, HistoryOutlined, CalendarOutlined, CopyOutlined, SettingOutlined, AppstoreOutlined } from '@ant-design/icons';
import type { ActionType, ProColumns, ProFormInstance } from '@ant-design/pro-components';
import {
  PageContainer,
  ProTable,
} from '@ant-design/pro-components';
import { Button, App, Space, Tag, Alert, Dropdown } from 'antd';
import type { MenuProps } from 'antd';
import { useRef, useState, useMemo } from 'react';
import { history, useAccess } from '@umijs/max';
import { scheduleTemplateApi } from '@hospital/api';
import { useStoreWithPermission } from '@/hooks/useStoreWithPermission';
import { useDepartments } from '@/hooks/useDepartments';
import { useDoctors } from '@/hooks/useDoctors';
import { createListRequest } from '@/utils/proTable';
import type { ScheduleTemplate, SchedulePreviewGenerateResponse } from '@hospital/shared';
import { ScheduleMessages } from '../utils/message';
import {
  SCHEDULE_MODE_MAP,
  WEEKDAY_MAP,
  getDateInfo,
} from '@hospital/shared';
import { useDict } from '@/hooks/useDict';
import dayjs from 'dayjs';
import HistoryLogsModal from './components/HistoryLogsModal';
import BatchAddModal from './components/BatchAddModal';
import GenerateScheduleModal from './components/GenerateScheduleModal';
import CopyRuleModal from './components/CopyRuleModal';
import { TEXT_SECONDARY } from '@/themes/scheduleColors';

const ScheduleRulePage: React.FC = () => {
  const { message, modal } = App.useApp();
  const access = useAccess();
  const { stores } = useStoreWithPermission({ enabledOnly: true });
  const { dictItems: appointmentTypeItems } = useDict('appointment_type');
  const appointmentTypeMap = useMemo(
    () => Object.fromEntries(appointmentTypeItems.map((i) => [i.value, i.label])),
    [appointmentTypeItems]
  );
  const actionRef = useRef<ActionType>();
  const generateFormRef = useRef<ProFormInstance>(null);
  const batchAddFormRef = useRef<ProFormInstance>(null);
  const [batchAddModalOpen, setBatchAddModalOpen] = useState(false);
  const [generateModalOpen, setGenerateModalOpen] = useState(false);
  const [selectedTemplates, setSelectedTemplates] = useState<string[]>([]);
  const [currentTemplate, setCurrentTemplate] = useState<ScheduleTemplate | null>(null);

  // 历史记录相关状态
  const [logsModalOpen, setLogsModalOpen] = useState(false);
  const [logs, setLogs] = useState<any[]>([]);
  const [logsLoading, setLogsLoading] = useState(false);

  // 预览相关状态
  const [previewData, setPreviewData] = useState<SchedulePreviewGenerateResponse[]>([]);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [showPreview, setShowPreview] = useState(false);
  const [editedCapacities, setEditedCapacities] = useState<Record<string, number>>({});
  const [generateLoading, setGenerateLoading] = useState(false);

  const [selectedDept, setSelectedDept] = useState<string>();

  // 复制规则相关状态
  const [copyModalOpen, setCopyModalOpen] = useState(false);
  const [copySourceTemplate, setCopySourceTemplate] = useState<ScheduleTemplate | null>(null);

  // 当前日期信息
  const dateInfo = useMemo(() => getDateInfo(), []);

  // 使用共享 hooks 加载科室和医生数据
  const { departments } = useDepartments();
  const { doctors } = useDoctors({ departmentId: selectedDept, enabled: !!selectedDept });

  const handleOpenCopyModal = (record: ScheduleTemplate) => {
    setCopySourceTemplate(record);
    setCopyModalOpen(true);
  };

  const handleDelete = async (id: string) => {
    try {
      await scheduleTemplateApi.delete(id);
      message.success(ScheduleMessages.deleteSuccess);
      actionRef.current?.reload();
    } catch (error: any) {
      message.error(error.message || ScheduleMessages.deleteFailed);
    }
  };

  const handleBatchDelete = async (record: ScheduleTemplate) => {
    modal.confirm({
      title: '确认删除排班',
      content: (
        <div>
          <p>确定要删除该规则生成的所有<strong>未来</strong>排班吗？</p>
          <p style={{ color: TEXT_SECONDARY, fontSize: 12 }}>注意：已有预约的排班不会被删除</p>
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
          message.error(error.message || ScheduleMessages.deleteFailed);
        }
      },
    });
  };

  const handleBatchSuspend = async (record: ScheduleTemplate) => {
    modal.confirm({
      title: '确认批量停诊',
      content: (
        <div>
          <p>确定要停诊该规则生成的所有<strong>未来</strong>排班吗？</p>
          <p style={{ color: TEXT_SECONDARY, fontSize: 12 }}>停诊后可在排班列表中恢复</p>
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
          message.error(error.message || ScheduleMessages.operateFailed);
        }
      },
    });
  };

  const handleViewLogs = async (record: ScheduleTemplate) => {
    setCurrentTemplate(record);
    setLogsModalOpen(true);
    setLogsLoading(true);
    try {
      const result = await scheduleTemplateApi.getLogs(record.id, 1, 50);
      setLogs(result.data ?? []);
    } catch (error: any) {
      message.error(error.message || ScheduleMessages.loadLogsFailed);
    } finally {
      setLogsLoading(false);
    }
  };

  const handleBatchAddSubmit = async (values: any) => {
    const { dateRange, startTime, endTime, totalSlots, slotCount, ...rest } = values;
    if (!dateRange || dateRange.length !== 2) {
      message.error(ScheduleMessages.selectDateRange);
      return false;
    }

    if (!startTime || !endTime) {
      message.error(ScheduleMessages.selectTimeRequired);
      return false;
    }

    try {
      const startDate = typeof dateRange[0] === 'string'
        ? dateRange[0]
        : dateRange[0].format('YYYY-MM-DD');
      const endDate = typeof dateRange[1] === 'string'
        ? dateRange[1]
        : dateRange[1].format('YYYY-MM-DD');

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
        slotCapacity: totalSlots || 10,
        slotCount: slotCount || 1,
        startDate,
        endDate,
      });
      message.success(result.message);
      setBatchAddModalOpen(false);
      actionRef.current?.reload();
      return true;
    } catch (error: any) {
      message.error(error.message || ScheduleMessages.batchAddFailed);
      return false;
    }
  };

  const handlePreviewGenerate = async () => {
    const values = generateFormRef.current?.getFieldsValue();
    const { startDate: startDateVal, endDate: endDateVal } = values || {};

    if (selectedTemplates.length === 0) {
      message.error(ScheduleMessages.selectRuleRequired);
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
      message.error(error.message || ScheduleMessages.previewGenerateFailed);
    } finally {
      setPreviewLoading(false);
    }
  };

  const handleConfirmGenerate = async () => {
    const values = generateFormRef.current?.getFieldsValue();
    const { startDate: startDateVal, endDate: endDateVal } = values || {};

    const startDate = startDateVal
      ? (typeof startDateVal === 'string' ? startDateVal : startDateVal.format('YYYY-MM-DD'))
      : undefined;
    const endDate = endDateVal
      ? (typeof endDateVal === 'string' ? endDateVal : endDateVal.format('YYYY-MM-DD'))
      : undefined;

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
      message.error(error.message || ScheduleMessages.generateFailed);
    } finally {
      setGenerateLoading(false);
    }
  };

  const handleGenerateSubmit = async (values: any) => {
    const { startDate: startDateVal, endDate: endDateVal } = values;

    if (selectedTemplates.length === 0) {
      message.error(ScheduleMessages.selectRuleRequired);
      return false;
    }

    const startDate = startDateVal
      ? (typeof startDateVal === 'string' ? startDateVal : startDateVal.format('YYYY-MM-DD'))
      : undefined;
    const endDate = endDateVal
      ? (typeof endDateVal === 'string' ? endDateVal : endDateVal.format('YYYY-MM-DD'))
      : undefined;

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
      message.error(error.message || ScheduleMessages.generateFailed);
      return false;
    } finally {
      setGenerateLoading(false);
    }
  };

  const handleSingleGenerate = (record: ScheduleTemplate) => {
    setSelectedTemplates([record.id]);
    setCurrentTemplate(record);
    setGenerateModalOpen(true);
  };

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
      onClick: () => history.push(`/medical-services/schedule/rule/${record.id}/edit`),
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
            {appointmentTypeMap[record.appointmentType] || record.appointmentType}
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
      hideInTable: true,
      render: (_, record) => `${record.slotCount || 1}个`,
    },
    {
      title: '班次人数',
      dataIndex: 'slotCapacity',
      width: 80,
      search: false,
      hideInTable: true,
      render: (_, record) => record.slotCapacity || 10,
    },
    {
      title: '排班方式',
      dataIndex: 'scheduleMode',
      width: 100,
      search: false,
      hideInTable: true,
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
      hideInTable: true,
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

  return (
    <PageContainer>
      <Alert
        title={
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
        scroll={{ x: 1400 }}
        rowSelection={{
          selectedRowKeys: selectedTemplates,
          onChange: (keys) => setSelectedTemplates(keys as string[]),
        }}
        request={createListRequest(scheduleTemplateApi.getList)}
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
          <Button
            key="rule-sets"
            icon={<SettingOutlined />}
            onClick={() => history.push('/organization/medical-config/rule-sets')}
          >
            规则组管理
          </Button>,
          <Button
            key="shift-types"
            icon={<AppstoreOutlined />}
            onClick={() => history.push('/organization/medical-config/shift-types')}
          >
            班次类型
          </Button>,
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
              onClick={() => history.push('/medical-services/schedule/rule/create')}
            >
              新增规则
            </Button>
          ),
        ]}
        pagination={{ defaultPageSize: 10 }}
      />

      <BatchAddModal
        open={batchAddModalOpen}
        onOpenChange={setBatchAddModalOpen}
        onFinish={handleBatchAddSubmit}
        stores={stores}
        departments={departments}
        doctors={doctors}
        selectedDept={selectedDept}
        onDeptChange={setSelectedDept}
        formRef={batchAddFormRef}
      />

      <GenerateScheduleModal
        open={generateModalOpen}
        onCancel={() => {
          setGenerateModalOpen(false);
          setCurrentTemplate(null);
          setShowPreview(false);
          setPreviewData([]);
          setEditedCapacities({});
        }}
        onGenerate={handleGenerateSubmit}
        onPreview={handlePreviewGenerate}
        onConfirmGenerate={handleConfirmGenerate}
        formRef={generateFormRef}
        currentTemplate={currentTemplate}
        selectedTemplates={selectedTemplates}
        previewData={previewData}
        showPreview={showPreview}
        previewLoading={previewLoading}
        generateLoading={generateLoading}
        editedCapacities={editedCapacities}
        onCapacityChange={(key, value) => setEditedCapacities(prev => ({ ...prev, [key]: value }))}
      />

      <HistoryLogsModal
        open={logsModalOpen}
        onCancel={() => setLogsModalOpen(false)}
        logs={logs}
        loading={logsLoading}
        templateName={currentTemplate?.name}
      />

      <CopyRuleModal
        open={copyModalOpen}
        onClose={() => {
          setCopyModalOpen(false);
          setCopySourceTemplate(null);
        }}
        onSuccess={() => {
          setCopyModalOpen(false);
          setCopySourceTemplate(null);
          actionRef.current?.reload();
        }}
        sourceRule={copySourceTemplate}
      />
    </PageContainer>
  );
};

export default ScheduleRulePage;
