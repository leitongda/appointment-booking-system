import {PageContainer, ProTable, ProColumns} from '@ant-design/pro-components';
import {Tag, Modal, Input} from 'antd';
import {attendanceApi} from '@hospital/api';
import {createListRequest} from '@/utils/proTable';
import {useListPage} from '@/hooks/useListPage';
import {OperationButton, OperationGroup} from '@/components/ListOperations';
import {useState} from 'react';

interface LeaveRequest {
  id: string;
  accountName?: string;
  leaveTypeName?: string;
  status: string;
  startDate: string;
  endDate: string;
  durationDays: number;
  reason?: string;
  reviewerId?: string;
  reviewComment?: string;
  createdAt?: string;
}

/** 假期申请状态映射 */
const STATUS_MAP: Record<string, { text: string; color: string }> = {
  pending: { text: '待审批', color: 'processing' },
  approved: { text: '已通过', color: 'success' },
  rejected: { text: '已驳回', color: 'error' },
  cancelled: { text: '已取消', color: 'default' },
};

/**
 * 假期申请管理列表页
 *
 * 功能：管理员查看所有假期申请，支持审批通过/驳回
 * 后端：apps/server/app/modules/attendance_leave/router.py
 */
const LeaveRequestListPage: React.FC = () => {
  const { actionRef, handleAction } = useListPage();
  const [reviewModalVisible, setReviewModalVisible] = useState(false);
  const [reviewTarget, setReviewTarget] = useState<{ id: string; action: 'approve' | 'reject' } | null>(null);
  const [reviewComment, setReviewComment] = useState('');

  const handleReview = async () => {
    if (!reviewTarget) return;
    const { id, action } = reviewTarget;
    const fn = action === 'approve'
      ? () => attendanceApi.approveLeaveRequest(id, reviewComment)
      : () => attendanceApi.rejectLeaveRequest(id, reviewComment);

    await handleAction(fn, {
      successText: action === 'approve' ? '审批通过' : '已驳回',
      errorText: '操作失败',
      reloadOnSuccess: true,
    });

    setReviewModalVisible(false);
    setReviewTarget(null);
    setReviewComment('');
  };

  const columns: ProColumns<LeaveRequest>[] = [
    {
      title: '申请人',
      dataIndex: 'accountName',
      width: 120,
      fixed: 'left',
    },
    {
      title: '关键词',
      dataIndex: 'keyword',
      hideInTable: true,
      fieldProps: { placeholder: '搜索申请人/原因' },
      search: { transform: (value: string) => ({ keyword: value }) },
    },
    {
      title: '假期类型',
      dataIndex: 'leaveTypeName',
      width: 120,
      search: false,
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 100,
      valueType: 'select',
      valueEnum: {
        pending: { text: '待审批', status: 'Processing' },
        approved: { text: '已通过', status: 'Success' },
        rejected: { text: '已驳回', status: 'Error' },
        cancelled: { text: '已取消', status: 'Default' },
      },
      render: (_, record) => {
        const s = STATUS_MAP[record.status] || { text: record.status, color: 'default' };
        return <Tag color={s.color}>{s.text}</Tag>;
      },
    },
    {
      title: '开始日期',
      dataIndex: 'startDate',
      width: 120,
      search: false,
      valueType: 'date',
    },
    {
      title: '结束日期',
      dataIndex: 'endDate',
      width: 120,
      search: false,
      valueType: 'date',
    },
    {
      title: '天数',
      dataIndex: 'durationDays',
      width: 80,
      search: false,
    },
    {
      title: '原因',
      dataIndex: 'reason',
      width: 200,
      search: false,
      ellipsis: true,
    },
    {
      title: '审批人',
      dataIndex: 'reviewerId',
      width: 120,
      search: false,
      render: (_, record) => record.reviewerId || '-',
    },
    {
      title: '审批意见',
      dataIndex: 'reviewComment',
      width: 150,
      search: false,
      ellipsis: true,
      render: (_, record) => record.reviewComment || '-',
    },
    {
      title: '创建时间',
      dataIndex: 'createdAt',
      width: 160,
      search: false,
      valueType: 'dateTime',
    },
    {
      title: '操作',
      width: 150,
      valueType: 'option',
      render: (_, record) => {
        if (record.status !== 'pending') return '-';
        return (
          <OperationGroup>
            <OperationButton
              type="custom"
              label="通过"
              onClick={() => {
                setReviewTarget({ id: record.id, action: 'approve' });
                setReviewComment('');
                setReviewModalVisible(true);
              }}
            />
            <OperationButton
              type="custom"
              label="驳回"
              danger
              onClick={() => {
                setReviewTarget({ id: record.id, action: 'reject' });
                setReviewComment('');
                setReviewModalVisible(true);
              }}
            />
          </OperationGroup>
        );
      },
    },
  ];

  return (
    <PageContainer
      title="假期申请管理"
      content="查看和审批所有假期申请，支持按状态筛选"
    >
      <ProTable<LeaveRequest>
        columns={columns}
        actionRef={actionRef}
        rowKey="id"
        request={createListRequest(attendanceApi.getAllLeaveRequests)}
        columnsState={{ persistenceKey: 'attendance-leave-requests', persistenceType: 'localStorage' }}
        search={{ labelWidth: 'auto' }}
        pagination={{ defaultPageSize: 10, showSizeChanger: true, showQuickJumper: true }}
      />

      <Modal
        title={reviewTarget?.action === 'approve' ? '审批通过' : '驳回申请'}
        open={reviewModalVisible}
        onOk={handleReview}
        onCancel={() => {
          setReviewModalVisible(false);
          setReviewTarget(null);
          setReviewComment('');
        }}
        okText={reviewTarget?.action === 'approve' ? '通过' : '驳回'}
        okButtonProps={{ danger: reviewTarget?.action === 'reject' }}
      >
        <div style={{ marginBottom: 12 }}>
          <span>审批意见（可选）：</span>
        </div>
        <Input.TextArea
          value={reviewComment}
          onChange={(e) => setReviewComment(e.target.value)}
          placeholder="请输入审批意见..."
          rows={3}
        />
      </Modal>
    </PageContainer>
  );
};

export default LeaveRequestListPage;
