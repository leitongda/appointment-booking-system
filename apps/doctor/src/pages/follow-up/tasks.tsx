import { PageContainer, ProTable } from '@ant-design/pro-components';
import type { ProColumns, ActionType } from '@ant-design/pro-components';
import { Button, Tag, Drawer, Descriptions, Input, Popconfirm, Space, Spin, message } from 'antd';
import { EyeOutlined, CheckOutlined, StopOutlined } from '@ant-design/icons';
import { useRef, useState } from 'react';
import { followUpApi } from '@hospital/api';
import type { FollowUpTaskListItem, FollowUpTask } from '@hospital/api';
import dayjs from 'dayjs';

const STATUS_MAP: Record<string, { text: string; color: string }> = {
  pending: { text: '待随访', color: 'processing' },
  completed: { text: '已完成', color: 'success' },
  skipped: { text: '已跳过', color: 'default' },
  overdue: { text: '已逾期', color: 'error' },
};

const FollowUpTasksPage: React.FC = () => {
  const actionRef = useRef<ActionType>();
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);
  const [currentTask, setCurrentTask] = useState<FollowUpTask | null>(null);
  const [skipDrawerOpen, setSkipDrawerOpen] = useState(false);
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

  const handleComplete = async (id: string) => {
    try {
      await followUpApi.completeTask(id);
      message.success('已标记完成');
      actionRef.current?.reload();
    } catch (error: any) {
      message.error(error.message || '操作失败');
    }
  };

  const handleSkip = async () => {
    if (!skipTaskId) return;
    try {
      await followUpApi.skipTask(skipTaskId, skipReason || '医生跳过');
      message.success('已跳过');
      setSkipDrawerOpen(false);
      setSkipTaskId('');
      setSkipReason('');
      actionRef.current?.reload();
    } catch (error: any) {
      message.error(error.message || '操作失败');
    }
  };

  const columns: ProColumns<FollowUpTaskListItem>[] = [
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
    { title: '任务编号', dataIndex: 'taskNo', width: 150, search: false },
    { title: '患者', dataIndex: 'patientName', width: 100, search: false },
    { title: '科室', dataIndex: 'departmentName', width: 110, search: false },
    { title: '随访计划', dataIndex: 'planName', width: 130, ellipsis: true, search: false },
    {
      title: '步骤',
      dataIndex: 'stepOrder',
      width: 70,
      search: false,
      render: (_, r) => (r.stepOrder ? `第${r.stepOrder}步` : '-'),
    },
    { title: '计划日期', dataIndex: 'scheduledDate', width: 110, valueType: 'date', search: false },
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
      valueType: 'option',
      width: 220,
      render: (_, record) => (
        <Space size={4}>
          <Button type="link" icon={<EyeOutlined />} onClick={() => handleView(record.id)}>
            查看
          </Button>
          {(record.status === 'pending' || record.status === 'overdue') && (
            <>
              <Popconfirm title="确定标记为已完成吗？" onConfirm={() => handleComplete(record.id)}>
                <Button type="link" icon={<CheckOutlined />} style={{ color: '#52c41a' }}>
                  完成
                </Button>
              </Popconfirm>
              <Button
                type="link"
                icon={<StopOutlined />}
                onClick={() => {
                  setSkipTaskId(record.id);
                  setSkipReason('');
                  setSkipDrawerOpen(true);
                }}
              >
                跳过
              </Button>
            </>
          )}
        </Space>
      ),
    },
  ];

  return (
    <PageContainer>
      <ProTable<FollowUpTaskListItem>
        actionRef={actionRef}
        rowKey="id"
        columns={columns}
        search={{ labelWidth: 'auto' }}
        request={async (params) => {
          try {
            const { current, pageSize, status, ...rest } = params;
            const result = await followUpApi.getMyTasks({
              page: current || 1,
              pageSize: pageSize || 10,
              status: status || undefined,
              ...rest,
            });
            return { data: result.data, success: true, total: result.total };
          } catch (error: any) {
            message.error(error.message || '获取随访任务失败');
            return { data: [], success: false, total: 0 };
          }
        }}
      />

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
            <Descriptions column={2} bordered size="small">
              <Descriptions.Item label="任务编号" span={2}>{currentTask.taskNo}</Descriptions.Item>
              <Descriptions.Item label="患者">{currentTask.patientName || '-'}</Descriptions.Item>
              <Descriptions.Item label="科室">{currentTask.departmentName || '-'}</Descriptions.Item>
              <Descriptions.Item label="随访计划">{currentTask.planName || '-'}</Descriptions.Item>
              <Descriptions.Item label="步骤">{currentTask.stepOrder ? `第${currentTask.stepOrder}步` : '-'}</Descriptions.Item>
              <Descriptions.Item label="计划日期">{currentTask.scheduledDate || '-'}</Descriptions.Item>
              <Descriptions.Item label="状态">
                <Tag color={STATUS_MAP[currentTask.status || 'pending']?.color}>
                  {STATUS_MAP[currentTask.status || 'pending']?.text}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="完成时间">
                {currentTask.completedAt ? dayjs(currentTask.completedAt).format('YYYY-MM-DD HH:mm') : '-'}
              </Descriptions.Item>
              <Descriptions.Item label="跳过原因">{currentTask.skipReason || '-'}</Descriptions.Item>
            </Descriptions>
          ) : null}
        </Spin>
      </Drawer>

      <Drawer
        title="跳过随访任务"
        open={skipDrawerOpen}
        onClose={() => setSkipDrawerOpen(false)}
        width={400}
        footer={
          <div style={{ textAlign: 'right' }}>
            <Space>
              <a onClick={() => setSkipDrawerOpen(false)}>取消</a>
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
