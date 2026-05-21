import { PlusOutlined } from '@ant-design/icons';
import type { ActionType, ProColumns } from '@ant-design/pro-components';
import {
  PageContainer,
  ProTable,
  ModalForm,
  ProFormSelect,
  ProFormText,
  ProFormDatePicker,
  ProFormRadio,
} from '@ant-design/pro-components';
import { Button, App, Tag, Popconfirm, Checkbox, Space, Drawer, Descriptions, Table, Divider, Alert, Statistic, Row, Col } from 'antd';
import { useRef, useState, useEffect } from 'react';
import { useAccess } from '@umijs/max';
import { scheduleSuspensionApi, doctorApi } from '@hospital/api';
import { fetchAllData } from '@/utils/fetchAllData';
import { useStoreWithPermission } from '@/hooks/useStoreWithPermission';
import { toProTableResult } from '@/utils/proTable';
import type {
  ScheduleSuspension,
  AvailableScheduleForSuspension,
  ProcessingMethod,
  ProcessingStatus,
  SuspensionProcessResult,
} from '@hospital/api';
import { ScheduleMessages } from './utils/message';
import { COLOR_DANGER, TEXT_SECONDARY } from '@/themes/scheduleColors';

// ── 处置方式映射 ──────────────────────────────────────────────
const PROCESSING_METHOD_ENUM: Record<ProcessingMethod, { text: string; color: string }> = {
  auto_refund: { text: '自动退号退款', color: 'red' },
  reschedule: { text: '转约其他医生', color: 'orange' },
  change_date: { text: '改期其他时间', color: 'blue' },
  manual: { text: '人工处理', color: 'default' },
};

// ── 处置状态映射 ──────────────────────────────────────────────
const PROCESSING_STATUS_ENUM: Record<ProcessingStatus, { text: string; color: string }> = {
  pending: { text: '待处置', color: 'default' },
  processing: { text: '处置中', color: 'processing' },
  completed: { text: '已完成', color: 'success' },
  failed: { text: '处置失败', color: 'error' },
};

// ── 处置方式 Radio 选项 ──────────────────────────────────────
const PROCESSING_METHOD_OPTIONS = [
  { label: '自动退号退款', value: 'auto_refund' },
  { label: '转约其他医生', value: 'reschedule' },
  { label: '改期其他时间', value: 'change_date' },
  { label: '人工处理', value: 'manual' },
];

const SuspensionPage: React.FC = () => {
  const { message } = App.useApp();
  useAccess();
  const { stores } = useStoreWithPermission({ enabledOnly: true });
  const actionRef = useRef<ActionType>();
  const [modalOpen, setModalOpen] = useState(false);
  const [doctors, setDoctors] = useState<any[]>([]);
  const [selectedStore, setSelectedStore] = useState<string>();
  const [selectedDoctor, setSelectedDoctor] = useState<string>();
  const [selectedDate, setSelectedDate] = useState<string>();
  const [availableSchedules, setAvailableSchedules] = useState<AvailableScheduleForSuspension[]>([]);
  const [selectedTimeSlots, setSelectedTimeSlots] = useState<string[]>([]);
  const [selectedScheduleIds, setSelectedScheduleIds] = useState<string[]>([]);

  // ── 处置结果 Drawer ──────────────────────────────────────────
  const [processDrawerOpen, setProcessDrawerOpen] = useState(false);
  const [processDrawerLoading, setProcessDrawerLoading] = useState(false);
  const [processResult, setProcessResult] = useState<SuspensionProcessResult | null>(null);
  const [processDrawerTitle, setProcessDrawerTitle] = useState('');

  // ── 执行处置确认弹窗 ────────────────────────────────────────
  const [processConfirmOpen, setProcessConfirmOpen] = useState(false);
  const [processTarget, setProcessTarget] = useState<ScheduleSuspension | null>(null);
  const [processConfirmLoading, setProcessConfirmLoading] = useState(false);

  async function loadDoctorsByStore(storeId: string) {
    try {
      const allDoctors = await fetchAllData((page, pageSize) =>
        doctorApi.getList({ storeId, page, pageSize, status: 1 })
      );
      setDoctors(allDoctors);
    } catch (error) {
      console.error('加载医生失败', error);
    }
  }

  async function loadAvailableSchedules() {
    if (!selectedStore || !selectedDoctor || !selectedDate) return;
    try {
      const result = await scheduleSuspensionApi.getAvailableSchedules(
        selectedStore,
        selectedDoctor,
        selectedDate
      );
      setAvailableSchedules(result);
    } catch (error: any) {
      console.error('加载排班失败', error);
    }
  }

  useEffect(() => {
    if (selectedStore) {
      loadDoctorsByStore(selectedStore);
    }
  }, [selectedStore]);

  useEffect(() => {
    if (selectedStore && selectedDoctor && selectedDate) {
      loadAvailableSchedules();
    }
  }, [selectedStore, selectedDoctor, selectedDate]);

  const handleDelete = async (id: string) => {
    try {
      await scheduleSuspensionApi.delete(id);
      message.success(ScheduleMessages.deleteSuccess);
      actionRef.current?.reload();
    } catch (error: any) {
      message.error(error.message || ScheduleMessages.deleteFailed);
    }
  };

  const handleCancel = async (id: string) => {
    try {
      await scheduleSuspensionApi.cancel(id);
      message.success(ScheduleMessages.cancelSuccess);
      actionRef.current?.reload();
    } catch (error: any) {
      message.error(error.message || ScheduleMessages.operateFailed);
    }
  };

  const handleScheduleSelect = (schedule: AvailableScheduleForSuspension, checked: boolean) => {
    if (checked) {
      setSelectedTimeSlots([...selectedTimeSlots, schedule.timeSlot]);
      setSelectedScheduleIds([...selectedScheduleIds, schedule.scheduleId]);
    } else {
      setSelectedTimeSlots(selectedTimeSlots.filter(t => t !== schedule.timeSlot));
      setSelectedScheduleIds(selectedScheduleIds.filter(id => id !== schedule.scheduleId));
    }
  };

  // ── 查看处置结果 ────────────────────────────────────────────
  const handleViewProcessResult = async (record: ScheduleSuspension) => {
    setProcessDrawerTitle(`处置详情 - ${record.title}`);
    setProcessDrawerOpen(true);
    setProcessDrawerLoading(true);
    try {
      const countResult = await scheduleSuspensionApi.getAffectedCount(record.id);
      // 处置结果无法从 getAffectedCount 获取完整 details，
      // 这里展示当前状态信息
      setProcessResult({
        suspensionId: record.id,
        processingMethod: (record.processingMethod as ProcessingMethod) || 'manual',
        processingStatus: (record.processingStatus as ProcessingStatus) || 'pending',
        totalAffected: countResult.affectedCount,
        successCount: 0,
        failedCount: 0,
        details: undefined,
      });
    } catch (error: any) {
      message.error(error.message || ScheduleMessages.queryFailed);
      setProcessResult(null);
    } finally {
      setProcessDrawerLoading(false);
    }
  };

  // ── 打开处置确认 ────────────────────────────────────────────
  const handleOpenProcessConfirm = (record: ScheduleSuspension) => {
    setProcessTarget(record);
    setProcessConfirmOpen(true);
  };

  // ── 执行处置 ────────────────────────────────────────────────
  const handleExecuteProcess = async (method: ProcessingMethod) => {
    if (!processTarget) return;
    setProcessConfirmLoading(true);
    try {
      const result = await scheduleSuspensionApi.process(processTarget.id, method);
      message.success(`处置完成: 成功 ${result.successCount}，失败 ${result.failedCount}`);
      setProcessConfirmOpen(false);
      setProcessTarget(null);
      actionRef.current?.reload();
      // 直接展示处置结果
      setProcessResult(result);
      setProcessDrawerTitle(`处置结果 - ${processTarget.title}`);
      setProcessDrawerOpen(true);
    } catch (error: any) {
      message.error(error.message || ScheduleMessages.operateFailed);
    } finally {
      setProcessConfirmLoading(false);
    }
  };

  const handleSubmit = async (values: any) => {
    try {
      await scheduleSuspensionApi.create({
        storeId: values.storeId,
        doctorId: values.doctorId,
        title: values.title,
        suspensionDate: values.suspensionDate.format('YYYY-MM-DD'),
        scheduleIds: selectedScheduleIds.length > 0 ? selectedScheduleIds : undefined,
        timeSlots: selectedTimeSlots.length > 0 ? selectedTimeSlots : undefined,
        processingMethod: values.processingMethod || 'manual',
      });
      message.success(ScheduleMessages.createSuccess);
      setModalOpen(false);
      setSelectedTimeSlots([]);
      setSelectedScheduleIds([]);
      setAvailableSchedules([]);
      actionRef.current?.reload();
      return true;
    } catch (error: any) {
      message.error(error.message || ScheduleMessages.createFailed);
      return false;
    }
  };

  const columns: ProColumns<ScheduleSuspension>[] = [
    {
      title: '门店',
      dataIndex: 'storeName',
      width: 150,
    },
    {
      title: '医生',
      dataIndex: 'doctorName',
      width: 100,
    },
    {
      title: '停诊标题',
      dataIndex: 'title',
      width: 150,
      ellipsis: true,
    },
    {
      title: '停诊日期',
      dataIndex: 'suspensionDate',
      width: 110,
      valueType: 'date',
    },
    {
      title: '停诊时段',
      dataIndex: 'timeSlots',
      width: 250,
      search: false,
      render: (_, record) => {
        if (!record.timeSlots || record.timeSlots.length === 0) {
          return <Tag color="red">全天停诊</Tag>;
        }
        return (
          <Space wrap>
            {record.timeSlots.map((slot, index) => (
              <Tag key={index} color="orange">{slot}</Tag>
            ))}
          </Space>
        );
      },
    },
    {
      title: '处置方式',
      dataIndex: 'processingMethod',
      width: 130,
      valueEnum: {
        auto_refund: { text: '自动退号退款' },
        reschedule: { text: '转约其他医生' },
        change_date: { text: '改期其他时间' },
        manual: { text: '人工处理' },
      },
      render: (_, record) => {
        const method = record.processingMethod as ProcessingMethod | undefined;
        if (!method) return <span style={{ color: TEXT_SECONDARY }}>-</span>;
        const config = PROCESSING_METHOD_ENUM[method];
        return config ? <Tag color={config.color}>{config.text}</Tag> : method;
      },
    },
    {
      title: '处置状态',
      dataIndex: 'processingStatus',
      width: 100,
      valueEnum: {
        pending: { text: '待处置', status: 'Default' },
        processing: { text: '处置中', status: 'Processing' },
        completed: { text: '已完成', status: 'Success' },
        failed: { text: '处置失败', status: 'Error' },
      },
      render: (_, record) => {
        const status = record.processingStatus as ProcessingStatus | undefined;
        if (!status) return <span style={{ color: TEXT_SECONDARY }}>-</span>;
        const config = PROCESSING_STATUS_ENUM[status];
        return config ? <Tag color={config.color}>{config.text}</Tag> : status;
      },
    },
    {
      title: '受影响预约',
      dataIndex: 'affectedAppointmentCount',
      width: 100,
      search: false,
      render: (_, record) => {
        const count = record.affectedAppointmentCount;
        if (count === undefined || count === null) return <span style={{ color: TEXT_SECONDARY }}>-</span>;
        return <span style={{ fontWeight: 500 }}>{count}</span>;
      },
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 80,
      valueEnum: {
        1: { text: '生效中', status: 'Error' },
        0: { text: '已取消', status: 'Default' },
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
      width: 200,
      render: (_, record) => {
        const processingStatus = record.processingStatus as ProcessingStatus | undefined;
        const canProcess = record.status === 1 && (!processingStatus || processingStatus === 'pending' || processingStatus === 'failed');
        return [
          canProcess && (
            <a
              key="process"
              onClick={() => handleOpenProcessConfirm(record)}
            >
              处置
            </a>
          ),
          processingStatus && processingStatus !== 'pending' && (
            <a
              key="view-process"
              onClick={() => handleViewProcessResult(record)}
            >
              查看处置
            </a>
          ),
          record.status === 1 && (
            <Popconfirm
              key="cancel"
              title="确定取消该停诊吗？"
              onConfirm={() => handleCancel(record.id)}
            >
              <a>取消</a>
            </Popconfirm>
          ),
          <Popconfirm
            key="delete"
            title="确定删除该记录吗？"
            onConfirm={() => handleDelete(record.id)}
          >
            <a style={{ color: COLOR_DANGER }}>删除</a>
          </Popconfirm>,
        ];
      },
    },
  ];

  return (
    <PageContainer>
      <ProTable<ScheduleSuspension>
        headerTitle="停诊管理"
        actionRef={actionRef}
        rowKey="id"
        columns={columns}
        request={async (params) => {
          const { current, pageSize, ...rest } = params;
          return toProTableResult(await scheduleSuspensionApi.getList({
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

      {/* ── 添加停诊弹窗 ──────────────────────────────────────── */}
      <ModalForm
        title="添加停诊"
        open={modalOpen}
        onOpenChange={(open) => {
          setModalOpen(open);
          if (!open) {
            setSelectedTimeSlots([]);
            setSelectedScheduleIds([]);
            setAvailableSchedules([]);
            setSelectedStore(undefined);
            setSelectedDoctor(undefined);
            setSelectedDate(undefined);
          }
        }}
        onFinish={handleSubmit}
        modalProps={{ destroyOnHidden: true }}
        initialValues={{ processingMethod: 'manual' }}
      >
        <ProFormSelect
          name="storeId"
          label="门店"
          options={stores.map(s => ({ label: s.name, value: s.id }))}
          rules={[{ required: true, message: '请选择门店' }]}
          fieldProps={{
            onChange: (val: any) => {
              setSelectedStore(val);
              setSelectedDoctor(undefined);
              setAvailableSchedules([]);
            },
          }}
        />
        <ProFormSelect
          name="doctorId"
          label="医生"
          options={doctors.map(d => ({ label: d.name, value: d.id }))}
          rules={[{ required: true, message: '请选择医生' }]}
          fieldProps={{
            onChange: (val: any) => {
              setSelectedDoctor(val);
              setAvailableSchedules([]);
            },
          }}
        />
        <ProFormText
          name="title"
          label="停诊标题"
          placeholder="请输入停诊标题"
          rules={[{ required: true, message: '请输入停诊标题' }]}
        />
        <ProFormDatePicker
          name="suspensionDate"
          label="停诊日期"
          rules={[{ required: true, message: '请选择停诊日期' }]}
          fieldProps={{
            onChange: (val: any) => {
              setSelectedDate(val?.format('YYYY-MM-DD'));
            },
          }}
        />

        {availableSchedules.length > 0 && (
          <div style={{ marginTop: 16 }}>
            <div style={{ marginBottom: 8, fontWeight: 500 }}>选择排班：</div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
              {availableSchedules.map((schedule) => (
                <Checkbox
                  key={schedule.scheduleId}
                  checked={selectedScheduleIds.includes(schedule.scheduleId)}
                  onChange={(e) => handleScheduleSelect(schedule, e.target.checked)}
                >
                  <Tag color={schedule.scheduleType === 'custom' ? 'purple' : 'blue'}>
                    {schedule.timeSlot}
                  </Tag>
                  <span style={{ fontSize: 12, color: TEXT_SECONDARY }}>
                    ({schedule.bookedCount}/{schedule.maxPatients})
                  </span>
                </Checkbox>
              ))}
            </div>
            {/* 受影响预约提示 */}
            {selectedScheduleIds.length > 0 && (() => {
              const totalBooked = availableSchedules
                .filter(s => selectedScheduleIds.includes(s.scheduleId))
                .reduce((sum, s) => sum + s.bookedCount, 0);
              if (totalBooked > 0) {
                return (
                  <Alert
                    style={{ marginTop: 8 }}
                    type="warning"
                    showIcon
                    message={`选中排班共有 ${totalBooked} 个已预约号源将受影响`}
                  />
                );
              }
              return null;
            })()}
            <div style={{ marginTop: 8, fontSize: 12, color: TEXT_SECONDARY }}>
              不选择则全天停诊
            </div>
          </div>
        )}

        {selectedStore && selectedDoctor && selectedDate && availableSchedules.length === 0 && (
          <div style={{ marginTop: 16, color: TEXT_SECONDARY }}>
            该日期暂无排班
          </div>
        )}

        <Divider style={{ margin: '16px 0 12px' }} />
        <ProFormRadio.Group
          name="processingMethod"
          label="处置方式"
          options={PROCESSING_METHOD_OPTIONS}
          rules={[{ required: true, message: '请选择处置方式' }]}
          fieldProps={{
            optionType: 'button',
            buttonStyle: 'solid',
          }}
        />
        <div style={{ fontSize: 12, color: TEXT_SECONDARY, marginTop: -8, marginBottom: 8 }}>
          选择处置方式后，停诊创建时将自动执行对受影响预约的处置
        </div>
      </ModalForm>

      {/* ── 处置确认弹窗 ──────────────────────────────────────── */}
      <ModalForm
        title="确认处置"
        open={processConfirmOpen}
        onOpenChange={(open) => {
          setProcessConfirmOpen(open);
          if (!open) setProcessTarget(null);
        }}
        submitter={false}
        modalProps={{ destroyOnHidden: true }}
      >
        {processTarget && (
          <>
            <Alert
              type="info"
              showIcon
              message={`停诊: ${processTarget.title}`}
              description={`${processTarget.storeName || ''} ${processTarget.doctorName || ''} ${processTarget.suspensionDate}`}
              style={{ marginBottom: 16 }}
            />
            <div style={{ marginBottom: 8, fontWeight: 500 }}>请选择处置方式：</div>
            <Space direction="vertical" style={{ width: '100%' }}>
              {PROCESSING_METHOD_OPTIONS.map(opt => (
                <Button
                  key={opt.value}
                  block
                  size="large"
                  loading={processConfirmLoading}
                  onClick={() => handleExecuteProcess(opt.value as ProcessingMethod)}
                  style={{ textAlign: 'left', height: 'auto', padding: '12px 16px' }}
                >
                  <div>
                    <div style={{ fontWeight: 500 }}>{opt.label}</div>
                    <div style={{ fontSize: 12, color: TEXT_SECONDARY, marginTop: 2 }}>
                      {opt.value === 'auto_refund' && '自动取消预约并触发退款，已支付的号源将原路退回'}
                      {opt.value === 'reschedule' && '标记预约为待转约，通知患者选择其他医生重新预约'}
                      {opt.value === 'change_date' && '标记预约为待改期，通知患者选择其他日期重新预约'}
                      {opt.value === 'manual' && '仅记录处置标记，等待工作人员人工逐一处理'}
                    </div>
                  </div>
                </Button>
              ))}
            </Space>
          </>
        )}
      </ModalForm>

      {/* ── 处置结果 Drawer ────────────────────────────────────── */}
      <Drawer
        title={processDrawerTitle}
        open={processDrawerOpen}
        onClose={() => {
          setProcessDrawerOpen(false);
          setProcessResult(null);
        }}
        width={560}
      >
        {processDrawerLoading ? (
          <div style={{ textAlign: 'center', padding: 40 }}>加载中...</div>
        ) : processResult ? (
          <>
            <Row gutter={16} style={{ marginBottom: 24 }}>
              <Col span={8}>
                <Statistic title="总受影响" value={processResult.totalAffected} />
              </Col>
              <Col span={8}>
                <Statistic
                  title="成功处置"
                  value={processResult.successCount}
                  valueStyle={{ color: '#52c41a' }}
                />
              </Col>
              <Col span={8}>
                <Statistic
                  title="处置失败"
                  value={processResult.failedCount}
                  valueStyle={{ color: processResult.failedCount > 0 ? '#ff4d4f' : undefined }}
                />
              </Col>
            </Row>

            <Descriptions column={1} bordered size="small" style={{ marginBottom: 16 }}>
              <Descriptions.Item label="处置方式">
                {(() => {
                  const config = PROCESSING_METHOD_ENUM[processResult.processingMethod];
                  return config ? <Tag color={config.color}>{config.text}</Tag> : processResult.processingMethod;
                })()}
              </Descriptions.Item>
              <Descriptions.Item label="处置状态">
                {(() => {
                  const config = PROCESSING_STATUS_ENUM[processResult.processingStatus];
                  return config ? <Tag color={config.color}>{config.text}</Tag> : processResult.processingStatus;
                })()}
              </Descriptions.Item>
            </Descriptions>

            {/* 人工处理提示 */}
            {processResult.processingMethod === 'manual' && (
              <Alert
                type="info"
                showIcon
                message="人工处理"
                description="该停诊已标记为人工处理，请联系受影响患者逐一安排退号或改约。"
                style={{ marginBottom: 16 }}
              />
            )}

            {/* 处置明细 */}
            {processResult.details && processResult.details.length > 0 && (
              <>
                <Divider>处置明细</Divider>
                <Table
                  size="small"
                  rowKey="appointmentId"
                  pagination={false}
                  dataSource={processResult.details}
                  columns={[
                    { title: '患者', dataIndex: 'patientName', width: 100 },
                    {
                      title: '结果',
                      dataIndex: 'success',
                      width: 80,
                      render: (val: boolean) => (
                        <Tag color={val ? 'success' : 'error'}>
                          {val ? '成功' : '失败'}
                        </Tag>
                      ),
                    },
                    {
                      title: '退款',
                      dataIndex: 'refunded',
                      width: 80,
                      render: (val: boolean | undefined, record) => {
                        if (record.processingMethod !== 'auto_refund') return '-';
                        return val ? (
                          <Tag color="success">已退款</Tag>
                        ) : (
                          <Tag color="default">无需退款</Tag>
                        );
                      },
                    },
                    {
                      title: '金额',
                      dataIndex: 'paymentAmount',
                      width: 100,
                      render: (val: number | undefined) =>
                        val ? `¥${val.toFixed(2)}` : '-',
                    },
                    {
                      title: '错误信息',
                      dataIndex: 'error',
                      ellipsis: true,
                      render: (val: string | undefined) =>
                        val ? <span style={{ color: '#ff4d4f' }}>{val}</span> : '-',
                    },
                  ]}
                />
              </>
            )}
          </>
        ) : (
          <div style={{ textAlign: 'center', color: TEXT_SECONDARY, padding: 40 }}>
            暂无处置信息
          </div>
        )}
      </Drawer>
    </PageContainer>
  );
};

export default SuspensionPage;
