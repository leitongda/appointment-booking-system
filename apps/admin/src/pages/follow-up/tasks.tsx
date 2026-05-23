import { EyeOutlined, CheckOutlined, StopOutlined } from '@ant-design/icons';
import type { ActionType, ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable } from '@ant-design/pro-components';
import { App, Drawer, Descriptions, Input, Popconfirm, Space, Spin, Tag } from 'antd';
import { useRef, useState, useCallback } from 'react';
import { departmentApi, doctorApi, followUpApi } from '@hospital/api';
import type { FollowUpTask, FollowUpTaskListItem } from '@hospital/api';
import { createListRequest } from '@/utils/proTable';
import { fetchAllData } from '@/utils/fetchAllData';
import dayjs from 'dayjs';

const STATUS_MAP: Record<string, { text: string; color: string }> = {
  pending: { text: '待随访', color: 'processing' },
  completed: { text: '已完成', color: 'success' },
  skipped: { text: '已跳过', color: 'default' },
  overdue: { text: '已逾期', color: 'error' },
};

const FollowUpTasksPage: React.FC = () => {
  const { message } = App.useApp();
  const actionRef = useRef<ActionType>();
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);
  const [currentTask, setCurrentTask] = useState<FollowUpTask | null>(null);
  const [skipModalOpen, setSkipModalOpen] = useState(false);
  const [skipTaskId, setSkipTaskId] = useState<string>('');
  const [skipReason, setSkipReason] = useState('');

  const handleView = async (id: string) => {
    setDetailLoading(true);
    setDrawerOpen(true);
    try {
      const result = await followUpApi.getTaskDetail(id);
      setCurrentTask(result);
    } catch (error: any) {
      message.error(error.message || '加载详情失败');
      setDrawerOpen(false);
    } finally {
      setDetailLoading(false);
    }
  };

  const handleComplete = useCallback(
    async (id: string) => {
      try {
        await followUpApi.completeTask(id);
        message.success('已标记完成');
        actionRef.current?.reload();
      } catch (error: any) {
        message.error(error.message || '操作失败');
      }
    },
    [message],
  );

  const handleSkip = useCallback(async () => {
    if (!skipTaskId) return;
    try {
      await followUpApi.skipTask(skipTaskId, skipReason || '管理员跳过');
      message.success('已跳过');
      setSkipModalOpen(false);
      setSkipTaskId('');
      setSkipReason('');
      actionRef.current?.reload();
    } catch (error: any) {
      message.error(error.message || '操作失败');
    }
  }, [message, skipTaskId, skipReason]);

  const columns: ProColumns<FollowUpTaskListItem>[] = [
    {
      title: '关键字',
      dataIndex: 'keyword',
      hideInTable: true,
      fieldProps: { placeholder: '任务编号/患者姓名' },
    },
    {
      title: '医生',
      dataIndex: 'doctorId',
      hideInTable: true,
      valueType: 'select',
      fieldProps: { showSearch: true, optionFilterProp: 'label', placeholder: '请选择医生' },
      request: async () => {
        try {
          const docs = await fetchAllData((p, ps) => doctorApi.getList({ page: p, pageSize: ps }));
          return [{ label: '全部医生', value: '' }, ...docs.map((d: any) => ({ label: d.name, value: d.id }))];
        } catch {
          return [];
        }
      },
    },
    {
      title: '科室',
      dataIndex: 'departmentId',
      hideInTable: true,
      valueType: 'select',
      fieldProps: { showSearch: true, optionFilterProp: 'label', placeholder: '请选择科室' },
      request: async () => {
        try {
          const depts = await fetchAllData((p, ps) => departmentApi.getList({ page: p, pageSize: ps }));
          return [{ label: '全部科室', value: '' }, ...depts.map((d: any) => ({ label: d.name, value: d.id }))];
        } catch {
          return [];
        }
      },
    },
    {
      title: '状态',
      dataIndex: 'status',
      hideInTable: true,
      valueType: 'select',
      valueEnum: {
        '': { text: '全部' },
        pending: { text: '待随访' },
        completed: { text: '已完成' },
        skipped: { text: '已跳过' },
        overdue: { text: '已逾期' },
      },
    },
    {
      title: '计划日期',
      dataIndex: 'dateRange',
      hideInTable: true,
      valueType: 'dateRange',
      search: {
        transform: (value) => {
          if (!value) return {};
          return { startDate: value[0], endDate: value[1] };
        },
      },
    },
    { title: '任务编号', dataIndex: 'taskNo', width: 140, copyable: true, search: false },
    { title: '患者', dataIndex: 'patientName', width: 90, search: false },
    { title: '医生', dataIndex: 'doctorName', width: 90, search: false },
    { title: '科室', dataIndex: 'departmentName', width: 110, search: false },
    { title: '计划', dataIndex: 'planName', width: 120, ellipsis: true, search: false },
    { title: '步骤', dataIndex: 'stepOrder', width: 60, search: false, render: (_, r) => r.stepOrder ? `第${r.stepOrder}步` : '-' },
    {
      title: '计划日期',
      dataIndex: 'scheduledDate',
      width: 110,
      valueType: 'date',
      search: false,
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 80,
      search: false,
      render: (_, record) => {
        const s = STATUS_MAP[record.status || 'pending'];
        return <Tag color={s?.color}>{s?.text || record.status}</Tag>;
      },
    },
    {
      title: '操作',
      key: 'option',
      valueType: 'option',
      width: 200,
      fixed: 'right',
      render: (_, record) => (
        <Space size={4}>
          <a onClick={() => handleView(record.id)} style={{ fontSize: 13 }}>
            <EyeOutlined /> 查看
          </a>
          {record.status === 'pending' || record.status === 'overdue' ? (
            <>
              <Popconfirm title="确定标记为已完成吗？" onConfirm={() => handleComplete(record.id)}>
                <a style={{ color: '#52c41a', fontSize: 13 }}>
                  <CheckOutlined /> 完成
                </a>
              </Popconfirm>
              <a
                onClick={() => {
                  setSkipTaskId(record.id);
                  setSkipReason('');
                  setSkipModalOpen(true);
                }}
                style={{ fontSize: 13 }}
              >
                <StopOutlined /> 跳过
              </a>
            </>
          ) : null}
        </Space>
      ),
    },
  ];

  return (
    <PageContainer>
      <ProTable<FollowUpTaskListItem>
        headerTitle="随访任务"
        actionRef={actionRef}
        rowKey="id"
        columns={columns}
        request={createListRequest(followUpApi.getTaskList, ({ keyword, doctorId, departmentId, status, startDate, endDate, ...params }) => ({
          ...params,
          keyword: keyword || undefined,
          doctorId: doctorId || undefined,
          departmentId: departmentId || undefined,
          status: status || undefined,
          startDate: startDate || undefined,
          endDate: endDate || undefined,
        }))}
        pagination={{ defaultPageSize: 10 }}
        search={{ labelWidth: 'auto' }}
      />

      {/* 详情抽屉 */}
      <Drawer
        title={currentTask?.taskNo ? `随访任务 · ${currentTask.taskNo}` : '随访任务详情'}
        open={drawerOpen}
        onClose={() => {
          setDrawerOpen(false);
          setCurrentTask(null);
        }}
        width={580}
      >
        <Spin spinning={detailLoading}>
          {currentTask ? (
            <Descriptions column={2} bordered size="small" items={[
              { key: 'no', label: '任务编号', children: currentTask.taskNo, span: 2 },
              { key: 'patient', label: '患者', children: currentTask.patientName || '-' },
              { key: 'doctor', label: '医生', children: currentTask.doctorName || '-' },
              { key: 'dept', label: '科室', children: currentTask.departmentName || '-' },
              { key: 'plan', label: '随访计划', children: currentTask.planName || '-' },
              { key: 'step', label: '步骤', children: currentTask.stepOrder ? `第${currentTask.stepOrder}步` : '-' },
              { key: 'date', label: '计划日期', children: currentTask.scheduledDate || '-' },
              { key: 'status', label: '状态', children: <Tag color={STATUS_MAP[currentTask.status || 'pending']?.color}>{STATUS_MAP[currentTask.status || 'pending']?.text}</Tag> },
              { key: 'completedAt', label: '完成时间', children: currentTask.completedAt ? dayjs(currentTask.completedAt).format('YYYY-MM-DD HH:mm') : '-' },
              { key: 'skipReason', label: '跳过原因', children: currentTask.skipReason || '-', span: 2 },
              { key: 'createdAt', label: '创建时间', children: currentTask.createdAt ? dayjs(currentTask.createdAt).format('YYYY-MM-DD HH:mm:ss') : '-', span: 2 },
            ]} />
          ) : null}
        </Spin>
      </Drawer>

      {/* 跳过原因弹窗 */}
      <Drawer
        title="跳过随访任务"
        open={skipModalOpen}
        onClose={() => setSkipModalOpen(false)}
        width={400}
        footer={
          <div style={{ textAlign: 'right' }}>
            <Space>
              <a onClick={() => setSkipModalOpen(false)}>取消</a>
              <Popconfirm title="确定跳过此任务吗？" onConfirm={handleSkip}>
                <a style={{ color: '#ff4d4f' }}>确认跳过</a>
              </Popconfirm>
            </Space>
          </div>
        }
      >
        <div style={{ marginBottom: 8 }}>跳过原因：</div>
        <Input.TextArea
          rows={4}
          value={skipReason}
          onChange={(e) => setSkipReason(e.target.value)}
          placeholder="请输入跳过原因（可选）"
        />
      </Drawer>
    </PageContainer>
  );
};

export default FollowUpTasksPage;
