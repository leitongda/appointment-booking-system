import type { ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable } from '@ant-design/pro-components';
import { Tag, Drawer, Descriptions } from 'antd';
import { useState } from 'react';
import { refundApi } from '@hospital/api';
import { createListRequest } from '@/utils/proTable';
import { useListPage } from '@/hooks/useListPage';
import { OperationButton, OperationGroup } from '@/components/ListOperations';
import type { RefundRecordItem } from '@hospital/api';

const STATUS_MAP: Record<string, { text: string; color: string }> = {
  pending: { text: '待处理', color: 'default' },
  processing: { text: '处理中', color: 'orange' },
  success: { text: '退款成功', color: 'green' },
  failed: { text: '退款失败', color: 'red' },
};

const RefundListPage: React.FC = () => {
  const { actionRef } = useListPage();
  const [detailOpen, setDetailOpen] = useState(false);
  const [currentRecord, setCurrentRecord] = useState<RefundRecordItem | null>(null);

  const columns: ProColumns<RefundRecordItem>[] = [
    {
      title: '退款单号',
      dataIndex: 'refund_no',
      width: 180,
      copyable: true,
      ellipsis: true,
    },
    {
      title: '预约ID',
      dataIndex: 'appointment_id',
      width: 200,
      copyable: true,
      ellipsis: true,
      search: false,
    },
    {
      title: '原始金额',
      dataIndex: 'original_amount',
      width: 100,
      search: false,
      render: (val) => (val != null ? `¥${Number(val).toFixed(2)}` : '-'),
    },
    {
      title: '退款金额',
      dataIndex: 'refund_amount',
      width: 100,
      search: false,
      render: (val) => (val != null ? `¥${Number(val).toFixed(2)}` : '-'),
    },
    {
      title: '退款原因',
      dataIndex: 'refund_reason',
      ellipsis: true,
      search: false,
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 100,
      valueType: 'select',
      valueEnum: {
        pending: { text: '待处理' },
        processing: { text: '处理中' },
        success: { text: '退款成功' },
        failed: { text: '退款失败' },
      },
      render: (_, record) => {
        const s = STATUS_MAP[record.status] || { text: record.status, color: 'default' };
        return <Tag color={s.color}>{s.text}</Tag>;
      },
    },
    {
      title: '商户号',
      dataIndex: 'mch_id',
      width: 120,
      search: false,
      render: (val) => val || '-',
    },
    {
      title: '微信退款单号',
      dataIndex: 'wx_refund_id',
      width: 200,
      search: false,
      ellipsis: true,
      render: (val) => val || '-',
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      width: 160,
      valueType: 'dateTime',
      search: false,
    },
    {
      title: '操作',
      valueType: 'option',
      width: 80,
      fixed: 'right',
      render: (_, record) => (
        <OperationGroup>
          <OperationButton
            type="view"
            permission="appointment:refund"
            onClick={() => { setCurrentRecord(record); setDetailOpen(true); }}
          />
        </OperationGroup>
      ),
    },
  ];

  return (
    <PageContainer>
      <ProTable<RefundRecordItem>
        headerTitle="退款记录"
        actionRef={actionRef}
        rowKey="id"
        columns={columns}
        request={createListRequest(refundApi.getList, (params) => {
          const { status, ...rest } = params;
          return {
            ...rest,
            status: status || undefined,
          };
        })}
        pagination={{ defaultPageSize: 10 }}
        search={{ labelWidth: 'auto' }}
      />

      <Drawer
        title="退款详情"
        open={detailOpen}
        onClose={() => setDetailOpen(false)}
        width={600}
      >
        {currentRecord && (
          <Descriptions column={1} bordered size="small" items={[
            { key: 'refund_no', label: '退款单号', children: currentRecord.refund_no },
            { key: 'appointment_id', label: '预约ID', children: currentRecord.appointment_id },
            { key: 'out_trade_no', label: '商户订单号', children: currentRecord.out_trade_no || '-' },
            { key: 'original_amount', label: '原始金额', children: `¥${Number(currentRecord.original_amount).toFixed(2)}` },
            { key: 'refund_amount', label: '退款金额', children: `¥${Number(currentRecord.refund_amount).toFixed(2)}` },
            { key: 'refund_reason', label: '退款原因', children: currentRecord.refund_reason || '-' },
            { key: 'status', label: '状态', children: (
              <Tag color={(STATUS_MAP[currentRecord.status] || { color: 'default' }).color}>
                {(STATUS_MAP[currentRecord.status] || { text: currentRecord.status }).text}
              </Tag>
            )},
            { key: 'wx_refund_id', label: '微信退款单号', children: currentRecord.wx_refund_id || '-' },
            { key: 'mch_id', label: '商户号', children: currentRecord.mch_id || '-' },
            { key: 'sub_mchid', label: '子商户号', children: currentRecord.sub_mchid || '-' },
            { key: 'failed_reason', label: '失败原因', children: currentRecord.failed_reason || '-' },
            { key: 'created_at', label: '创建时间', children: currentRecord.created_at || '-' },
            { key: 'updated_at', label: '更新时间', children: currentRecord.updated_at || '-' },
          ]} />
        )}
      </Drawer>
    </PageContainer>
  );
};

export default RefundListPage;
