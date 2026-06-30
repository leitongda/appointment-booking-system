import type { ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable, ModalForm, ProFormTextArea } from '@ant-design/pro-components';
import { Tag, Button, Drawer, Descriptions, Table, Statistic, Row, Col, Card, Popconfirm, message } from 'antd';
import { DollarOutlined, DownloadOutlined } from '@ant-design/icons';
import { useState, useEffect } from 'react';
import { freelanceSettlementApi } from '@hospital/api';
import type { FreelanceSettlement, FreelanceSettlementItem } from '@hospital/api';
import { createListRequest } from '@/utils/proTable';
import { useListPage } from '@/hooks/useListPage';
import { OperationButton, OperationGroup } from '@/components/ListOperations';

const STATUS_MAP: Record<string, { text: string; color: string }> = {
  pending: { text: '待确认', color: 'gold' },
  confirmed: { text: '已确认', color: 'blue' },
  paid: { text: '已支付', color: 'green' },
  cancelled: { text: '已驳回', color: 'red' },
};

const ITEM_TYPE_MAP: Record<string, string> = {
  base: '基础金额',
  bonus: '一周补贴',
  likes_bonus: '点赞奖励',
  interaction: '互动奖励',
};

const SettlementsPage: React.FC = () => {
  const { actionRef, reload } = useListPage();
  const [detailOpen, setDetailOpen] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [rejectOpen, setRejectOpen] = useState(false);
  const [currentRecord, setCurrentRecord] = useState<FreelanceSettlement | null>(null);
  const [statistics, setStatistics] = useState<{
    totalFreelancers: number;
    totalSettledAmount: number;
    totalPendingAmount: number;
  } | null>(null);

  const loadStats = async () => {
    try {
      const data = await freelanceSettlementApi.getStatistics();
      setStatistics(data);
    } catch {
      // 统计加载失败不影响主功能
    }
  };

  useEffect(() => { loadStats(); }, []);

  const handleConfirm = async (values: any) => {
    if (!currentRecord) return false;
    try {
      await freelanceSettlementApi.confirm(currentRecord.id, values.remark);
      message.success('已确认');
      setConfirmOpen(false);
      reload();
      loadStats();
      return true;
    } catch (error: any) {
      message.error(error.message || '操作失败');
      return false;
    }
  };

  const handleReject = async (values: any) => {
    if (!currentRecord) return false;
    try {
      await freelanceSettlementApi.reject(currentRecord.id, values.rejectReason);
      message.success('已驳回');
      setRejectOpen(false);
      reload();
      return true;
    } catch (error: any) {
      message.error(error.message || '操作失败');
      return false;
    }
  };

  const handleMarkPaid = async (id: string) => {
    try {
      await freelanceSettlementApi.markPaid(id);
      message.success('已标记为已支付');
      reload();
      loadStats();
    } catch (error: any) {
      message.error(error.message || '操作失败');
    }
  };

  const openDetail = async (record: FreelanceSettlement) => {
    try {
      const detail = await freelanceSettlementApi.getDetail(record.id);
      setCurrentRecord(detail);
    } catch {
      setCurrentRecord(record);
    }
    setDetailOpen(true);
  };

  const columns: ProColumns<FreelanceSettlement>[] = [
    { title: '结算单号', dataIndex: 'settlementNo', width: 180, ellipsis: true },
    { title: '兼职人员', dataIndex: 'freelancerName', width: 100, search: false },
    {
      title: '状态',
      dataIndex: 'status',
      width: 90,
      valueEnum: Object.fromEntries(Object.entries(STATUS_MAP).map(([k, v]) => [k, { text: v.text }])),
      render: (_, r) => {
        const s = STATUS_MAP[r.status] || { text: r.status, color: 'default' };
        return <Tag color={s.color}>{s.text}</Tag>;
      },
    },
    { title: '基础金额', dataIndex: 'baseTotal', width: 90, search: false, render: (_, r) => `¥${Number(r.baseTotal).toFixed(2)}` },
    { title: '补贴金额', dataIndex: 'bonusTotal', width: 90, search: false, render: (_, r) => `¥${Number(r.bonusTotal).toFixed(2)}` },
    { title: '点赞奖励', dataIndex: 'likesBonusTotal', width: 90, search: false, render: (_, r) => `¥${Number(r.likesBonusTotal).toFixed(2)}` },
    { title: '互动金额', dataIndex: 'interactionTotal', width: 90, search: false, render: (_, r) => `¥${Number(r.interactionTotal).toFixed(2)}` },
    { title: '总金额', dataIndex: 'totalAmount', width: 100, search: false, render: (_, r) => <strong>¥{Number(r.totalAmount).toFixed(2)}</strong> },
    { title: '创建时间', dataIndex: 'createdAt', valueType: 'dateTime', width: 160, search: false },
    {
      title: '操作',
      valueType: 'option',
      width: 200,
      fixed: 'right',
      render: (_, record) => (
        <OperationGroup>
          <OperationButton type="view" permission="freelance:list" onClick={() => openDetail(record)} />
          {record.status === 'pending' && (
            <>
              <OperationButton type="custom" permission="freelance:settle" label="确认" onClick={() => { setCurrentRecord(record); setConfirmOpen(true); }} />
              <OperationButton type="custom" permission="freelance:settle" label="驳回" danger onClick={() => { setCurrentRecord(record); setRejectOpen(true); }} />
            </>
          )}
          {record.status === 'confirmed' && (
            <Popconfirm title="确定标记为已支付？" onConfirm={() => handleMarkPaid(record.id)}>
              <OperationButton type="custom" permission="freelance:settle" label="标记支付" />
            </Popconfirm>
          )}
        </OperationGroup>
      ),
    },
  ];

  const itemColumns = [
    { title: '类型', dataIndex: 'itemType', render: (v: string) => ITEM_TYPE_MAP[v] || v },
    { title: '描述', dataIndex: 'description', ellipsis: true },
    { title: '金额', dataIndex: 'amount', render: (v: number) => `¥${Number(v).toFixed(2)}` },
  ];

  return (
    <PageContainer>
      {statistics && (
        <Row gutter={16} style={{ marginBottom: 16 }}>
          <Col span={8}>
            <Card><Statistic title="兼职人员数" value={statistics.totalFreelancers} /></Card>
          </Col>
          <Col span={8}>
            <Card><Statistic title="已结算金额" value={statistics.totalSettledAmount} precision={2} prefix="¥" /></Card>
          </Col>
          <Col span={8}>
            <Card><Statistic title="待结算金额" value={statistics.totalPendingAmount} precision={2} prefix="¥" valueStyle={{ color: 'var(--color-warning)' }} /></Card>
          </Col>
        </Row>
      )}

      <ProTable<FreelanceSettlement>
        headerTitle="结算管理"
        actionRef={actionRef}
        rowKey="id"
        columns={columns}
        request={createListRequest(freelanceSettlementApi.getList)}
        pagination={{ defaultPageSize: 10 }}
        search={{ labelWidth: 'auto' }}
        toolBarRender={() => [
          <Button key="export" icon={<DownloadOutlined />} onClick={() => {
            window.open(freelanceSettlementApi.getExportSettlementsUrl(), '_blank');
          }}>
            导出
          </Button>,
        ]}
      />

      <Drawer title="结算详情" open={detailOpen} onClose={() => setDetailOpen(false)} width={700}>
        {currentRecord && (
          <>
            <Descriptions column={2} bordered size="small" items={[
              { key: '0', label: '结算单号', children: currentRecord.settlementNo, span: 2 },
              { key: '1', label: '兼职人员', children: currentRecord.freelancerName || currentRecord.freelancerId },
              { key: '2', label: '状态', children: STATUS_MAP[currentRecord.status]?.text || currentRecord.status },
              { key: '3', label: '基础金额', children: `¥${Number(currentRecord.baseTotal).toFixed(2)}` },
              { key: '4', label: '补贴金额', children: `¥${Number(currentRecord.bonusTotal).toFixed(2)}` },
              { key: '5', label: '点赞奖励', children: `¥${Number(currentRecord.likesBonusTotal).toFixed(2)}` },
              { key: '6', label: '互动金额', children: `¥${Number(currentRecord.interactionTotal).toFixed(2)}` },
              { key: '7', label: '总金额', children: <strong>¥{Number(currentRecord.totalAmount).toFixed(2)}</strong> },
              { key: '8', label: '税额', children: `¥${Number(currentRecord.taxAmount).toFixed(2)}` },
              { key: '9', label: '实际支付', children: <strong style={{ color: 'var(--color-success)' }}>¥{Number(currentRecord.actualAmount).toFixed(2)}</strong> },
              ...(currentRecord.rejectReason ? [{ key: '10', label: '驳回原因', children: currentRecord.rejectReason, span: 2 }] : []),
              ...(currentRecord.remark ? [{ key: '11', label: '备注', children: currentRecord.remark, span: 2 }] : []),
            ]} />
            {currentRecord.items && currentRecord.items.length > 0 && (
              <div style={{ marginTop: 16 }}>
                <h4>结算明细</h4>
                <Table columns={itemColumns} dataSource={currentRecord.items} rowKey="id" size="small" pagination={false} />
              </div>
            )}
          </>
        )}
      </Drawer>

      <ModalForm title="确认结算" open={confirmOpen} onOpenChange={setConfirmOpen} onFinish={handleConfirm} modalProps={{ destroyOnHidden: true }}>
        <ProFormTextArea name="remark" label="备注" />
      </ModalForm>

      <ModalForm title="驳回结算" open={rejectOpen} onOpenChange={setRejectOpen} onFinish={handleReject} modalProps={{ destroyOnHidden: true }}>
        <ProFormTextArea name="rejectReason" label="驳回原因" rules={[{ required: true }]} />
      </ModalForm>
    </PageContainer>
  );
};

export default SettlementsPage;
