import type { ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable, ModalForm, ProFormTextArea, ProFormRadio } from '@ant-design/pro-components';
import { Tag, Drawer, Descriptions } from 'antd';
import { AuditOutlined } from '@ant-design/icons';
import { useState } from 'react';
import { useModel } from '@umijs/max';
import { leaveRequestApi } from '@hospital/api';
import { createListRequest } from '@/utils/proTable';
import { useListPage } from '@/hooks/useListPage';
import { OperationButton, OperationGroup } from '@/components/ListOperations';
import type { LeaveRequest } from '@hospital/shared';

const TYPE_MAP: Record<string, string> = { stop_clinic: '停诊申请', schedule_change: '调班申请' };
const STATUS_MAP: Record<string, { text: string; color: string }> = {
  pending: { text: '待审核', color: 'gold' },
  approved: { text: '已通过', color: 'green' },
  rejected: { text: '已拒绝', color: 'red' },
  cancelled: { text: '已取消', color: 'default' },
};
const PERIOD_MAP: Record<string, string> = { morning: '上午', afternoon: '下午', evening: '晚上' };

const LeaveRequestPage: React.FC = () => {
  const { initialState } = useModel('@@initialState');
  const { actionRef, message, reload } = useListPage();
  const [reviewOpen, setReviewOpen] = useState(false);
  const [detailOpen, setDetailOpen] = useState(false);
  const [currentRecord, setCurrentRecord] = useState<LeaveRequest | null>(null);

  const handleReview = async (values: { status: string; comment?: string }) => {
    if (!currentRecord || !initialState?.currentUser?.id) return false;
    try {
      await leaveRequestApi.review(currentRecord.id, initialState.currentUser.id, values.status, values.comment);
      message.success('审核成功');
      setReviewOpen(false);
      reload();
      return true;
    } catch (error: any) {
      message.error(error.message || '审核失败');
      return false;
    }
  };

  const columns: ProColumns<LeaveRequest>[] = [
    { title: '医生', dataIndex: 'doctorName', width: 80 },
    { title: '科室', dataIndex: 'departmentName', width: 100 },
    {
      title: '类型',
      dataIndex: 'requestType',
      width: 100,
      valueEnum: { stop_clinic: '停诊', schedule_change: '调班' },
      render: (_, r) => TYPE_MAP[r.requestType] || '-',
    },
    { title: '日期', dataIndex: 'stopDate', width: 110 },
    { title: '时段', dataIndex: 'stopPeriod', width: 70, render: (_, r) => PERIOD_MAP[r.stopPeriod ?? ''] || '-' },
    { title: '原因', dataIndex: 'reason', ellipsis: true, search: false },
    {
      title: '状态',
      dataIndex: 'status',
      width: 90,
      valueEnum: Object.fromEntries(Object.entries(STATUS_MAP).map(([k, v]) => [k, { text: v.text }])),
      render: (_, r) => {
        const s = STATUS_MAP[r.status] || { text: '未知', color: 'default' };
        return <Tag color={s.color}>{s.text}</Tag>;
      },
    },
    { title: '申请时间', dataIndex: 'createdAt', valueType: 'dateTime', width: 160, search: false },
    {
      title: '操作',
      valueType: 'option',
      width: 150,
      fixed: 'right',
      render: (_, record) => (
        <OperationGroup>
          <OperationButton
            type="view"
            permission="leave-request:list"
            onClick={() => { setCurrentRecord(record); setDetailOpen(true); }}
          />
          {record.status === 'pending' && (
            <OperationButton
              type="custom"
              permission="leave-request:approve"
              icon={<AuditOutlined />}
              label="审核"
              onClick={() => { setCurrentRecord(record); setReviewOpen(true); }}
            />
          )}
        </OperationGroup>
      ),
    },
  ];

  return (
    <PageContainer>
      <ProTable<LeaveRequest>
        headerTitle="停诊审核"
        actionRef={actionRef}
        rowKey="id"
        columns={columns}
        request={createListRequest(leaveRequestApi.getList)}
        pagination={{ defaultPageSize: 10 }}
        search={{ labelWidth: 'auto' }}
      />

      <ModalForm
        title="审核申请"
        open={reviewOpen}
        onOpenChange={setReviewOpen}
        onFinish={handleReview}
        modalProps={{ destroyOnHidden: true }}
        initialValues={{ status: 'approved' }}
      >
        <ProFormRadio.Group
          name="status"
          label="审核结果"
          options={[
            { label: '通过', value: 'approved' },
            { label: '拒绝', value: 'rejected' },
          ]}
          rules={[{ required: true }]}
        />
        <ProFormTextArea name="comment" label="审核意见" />
      </ModalForm>

      <Drawer title="申请详情" open={detailOpen} onClose={() => setDetailOpen(false)} width={450}>
        {currentRecord && (
          <Descriptions column={1} bordered size="small" items={[
            { key: '0', label: '医生', children: currentRecord.doctorName },
            { key: '1', label: '科室', children: currentRecord.departmentName },
            { key: '2', label: '类型', children: TYPE_MAP[currentRecord.requestType] },
            { key: '3', label: '日期', children: currentRecord.stopDate },
            { key: '4', label: '时段', children: PERIOD_MAP[currentRecord.stopPeriod ?? ''] },
            { key: '5', label: '原因', children: currentRecord.reason },
            { key: '6', label: '状态', children: STATUS_MAP[currentRecord.status]?.text },
            ...(currentRecord.reviewComment ? [{ key: '7', label: '审核意见', children: currentRecord.reviewComment }] : []),
            ...(currentRecord.reviewedAt ? [{ key: '8', label: '审核时间', children: currentRecord.reviewedAt }] : []),
          ]} />
        )}
      </Drawer>
    </PageContainer>
  );
};

export default LeaveRequestPage;
