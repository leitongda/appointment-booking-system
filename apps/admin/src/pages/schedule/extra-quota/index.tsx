import type { ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable, ModalForm, ProFormTextArea } from '@ant-design/pro-components';
import { Tag, App, Button, Space } from 'antd';
import { CheckOutlined, CloseOutlined } from '@ant-design/icons';
import { useRef, useState, useMemo } from 'react';
import type { ActionType } from '@ant-design/pro-components';
import { scheduleApi } from '@hospital/api';
import { createListRequest } from '@/utils/proTable';
import { useDict } from '@/hooks/useDict';

const STATUS_MAP: Record<string, { text: string; color: string }> = {
  pending: { text: '待审批', color: 'gold' },
  approved: { text: '已通过', color: 'green' },
  rejected: { text: '已拒绝', color: 'red' },
};

const QUOTA_TYPE_MAP: Record<string, { text: string; color: string }> = {
  normal: { text: '普通加号', color: 'blue' },
  special: { text: '特批加号', color: 'purple' },
  green_channel: { text: '绿色通道', color: 'cyan' },
};

const TIME_SLOT_LABELS: Record<string, string> = {
  morning: '上午',
  afternoon: '下午',
  evening: '晚上',
};

interface ExtraQuotaRequest {
  id: string;
  scheduleId: string;
  doctorName: string;
  scheduleDate: string;
  timeSlot: string;
  quantity: number;
  quotaType: 'normal' | 'special' | 'green_channel';
  openToPublic: boolean;
  applicantName: string;
  approvalStatus: 'pending' | 'approved' | 'rejected';
  remark?: string;
  reviewerName?: string;
  reviewedAt?: string;
  createdAt: string;
}

const ExtraQuotaPage: React.FC = () => {
  const { message } = App.useApp();
  const actionRef = useRef<ActionType>();
  const { options: quotaTypeOptions } = useDict('extra_quota_type');
  const quotaTypeEnum = useMemo(
    () => Object.fromEntries(quotaTypeOptions.map((o) => [o.value, { text: o.label }])),
    [quotaTypeOptions],
  );
  const [reviewType, setReviewType] = useState<'approve' | 'reject'>('approve');
  const [reviewOpen, setReviewOpen] = useState(false);
  const [currentRecord, setCurrentRecord] = useState<ExtraQuotaRequest | null>(null);

  const reload = () => actionRef.current?.reload();

  const handleApprove = (record: ExtraQuotaRequest) => {
    setCurrentRecord(record);
    setReviewType('approve');
    setReviewOpen(true);
  };

  const handleReject = async (record: ExtraQuotaRequest) => {
    setCurrentRecord(record);
    setReviewType('reject');
    setReviewOpen(true);
  };

  const handleReviewSubmit = async (values: { remark?: string }) => {
    if (!currentRecord) return false;
    try {
      if (reviewType === 'approve') {
        await scheduleApi.approveExtraQuota(currentRecord.id, { remark: values.remark });
        message.success('已通过');
      } else {
        if (!values.remark) {
          message.error('请填写拒绝原因');
          return false;
        }
        await scheduleApi.rejectExtraQuota(currentRecord.id, { remark: values.remark });
        message.success('已拒绝');
      }
      setReviewOpen(false);
      setCurrentRecord(null);
      reload();
      return true;
    } catch (error: any) {
      message.error(error.message || '操作失败');
      return false;
    }
  };

  const columns: ProColumns<ExtraQuotaRequest>[] = [
    {
      title: '申请时间',
      dataIndex: 'createdAt',
      valueType: 'dateTime',
      width: 160,
      search: false,
    },
    {
      title: '医生',
      dataIndex: 'doctorName',
      width: 100,
      search: false,
    },
    {
      title: '日期',
      dataIndex: 'scheduleDate',
      width: 110,
      valueType: 'date',
      fieldProps: {
        placeholder: '选择日期',
      },
    },
    {
      title: '时段',
      dataIndex: 'timeSlot',
      width: 80,
      search: false,
      render: (_, record) => TIME_SLOT_LABELS[record.timeSlot] || record.timeSlot || '-',
    },
    {
      title: '加号类型',
      dataIndex: 'quotaType',
      width: 100,
      valueEnum: quotaTypeEnum,
      render: (_, record) => {
        const info = QUOTA_TYPE_MAP[record.quotaType] || { text: record.quotaType, color: 'default' };
        return <Tag color={info.color}>{info.text}</Tag>;
      },
    },
    {
      title: '数量',
      dataIndex: 'quantity',
      width: 70,
      search: false,
      align: 'center',
    },
    {
      title: '申请人',
      dataIndex: 'applicantName',
      width: 100,
      search: false,
    },
    {
      title: '审批状态',
      dataIndex: 'approvalStatus',
      width: 100,
      valueEnum: {
        pending: { text: '待审批', status: 'Warning' },
        approved: { text: '已通过', status: 'Success' },
        rejected: { text: '已拒绝', status: 'Error' },
      },
      render: (_, record) => {
        const info = STATUS_MAP[record.approvalStatus] || { text: '未知', color: 'default' };
        return <Tag color={info.color}>{info.text}</Tag>;
      },
    },
    {
      title: '审批备注',
      dataIndex: 'remark',
      ellipsis: true,
      search: false,
      render: (_, record) => record.remark || '-',
    },
    {
      title: '操作',
      valueType: 'option',
      width: 140,
      fixed: 'right',
      render: (_, record) => {
        if (record.approvalStatus !== 'pending') {
          return record.reviewedAt ? (
            <span style={{ color: '#999', fontSize: 12 }}>
              {record.reviewerName ? `${record.reviewerName} ` : ''}已审批
            </span>
          ) : null;
        }
        return (
          <Space>
            <Button
              type="link"
              size="small"
              icon={<CheckOutlined />}
              onClick={() => handleApprove(record)}
            >
              通过
            </Button>
            <Button
              type="link"
              size="small"
              danger
              icon={<CloseOutlined />}
              onClick={() => handleReject(record)}
            >
              拒绝
            </Button>
          </Space>
        );
      },
    },
  ];

  return (
    <PageContainer>
      <ProTable<ExtraQuotaRequest>
        headerTitle="加号管理"
        actionRef={actionRef}
        rowKey="id"
        columns={columns}
        request={createListRequest(scheduleApi.getExtraQuotaRequests)}
        pagination={{ defaultPageSize: 10 }}
        search={{ labelWidth: 'auto' }}
        scroll={{ x: 1100 }}
      />

      <ModalForm
        title={reviewType === 'approve' ? '审批通过' : '审批拒绝'}
        open={reviewOpen}
        onOpenChange={(open) => {
          setReviewOpen(open);
          if (!open) setCurrentRecord(null);
        }}
        onFinish={handleReviewSubmit}
        modalProps={{ destroyOnHidden: true }}
        width={420}
      >
        {currentRecord && (
          <div style={{ marginBottom: 16, padding: '8px 12px', background: '#f5f5f5', borderRadius: 6 }}>
            <div>医生：{currentRecord.doctorName}</div>
            <div>
              日期：{currentRecord.scheduleDate}{' '}
              {TIME_SLOT_LABELS[currentRecord.timeSlot] || currentRecord.timeSlot}
            </div>
            <div>
              类型：{QUOTA_TYPE_MAP[currentRecord.quotaType]?.text || currentRecord.quotaType}，
              数量：{currentRecord.quantity}
            </div>
          </div>
        )}
        <ProFormTextArea
          name="remark"
          label={reviewType === 'approve' ? '审批备注（可选）' : '拒绝原因（必填）'}
          placeholder={
            reviewType === 'approve'
              ? '请输入审批备注（可选）'
              : '请输入拒绝原因'
          }
          rules={
            reviewType === 'reject'
              ? [{ required: true, message: '请输入拒绝原因' }]
              : undefined
          }
          fieldProps={{ rows: 3, maxLength: 200, showCount: true }}
        />
      </ModalForm>
    </PageContainer>
  );
};

export default ExtraQuotaPage;
