import type { ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable, ModalForm, ProFormText, ProFormTextArea } from '@ant-design/pro-components';
import { Tag, Drawer, Descriptions, Card, Row, Col, Statistic, Popconfirm, App } from 'antd';
import { CheckCircleOutlined, StopOutlined, UndoOutlined, UserOutlined } from '@ant-design/icons';
import { useState, useEffect, useMemo } from 'react';
import { supportTicketApi } from '@hospital/api';
import { useDict } from '@/hooks/useDict';
import type { SupportTicket, SupportTicketStatistics } from '@hospital/api';
import { createListRequest } from '@/utils/proTable';
import { useListPage } from '@/hooks/useListPage';
import { OperationButton, OperationGroup } from '@/components/ListOperations';

const TYPE_MAP: Record<string, { text: string; color: string }> = {
  suggestion: { text: '建议', color: 'blue' },
  complaint: { text: '投诉', color: 'red' },
  bug: { text: '故障', color: 'orange' },
  other: { text: '其他', color: 'default' },
};

const STATUS_MAP: Record<string, { text: string; color: string }> = {
  pending: { text: '待处理', color: 'gold' },
  processing: { text: '处理中', color: 'blue' },
  resolved: { text: '已解决', color: 'green' },
  closed: { text: '已关闭', color: 'default' },
};

const PRIORITY_MAP: Record<string, { text: string; color: string }> = {
  low: { text: '低', color: 'default' },
  medium: { text: '中', color: 'blue' },
  high: { text: '高', color: 'orange' },
  urgent: { text: '紧急', color: 'red' },
};

const SupportTicketPage: React.FC = () => {
  const { message } = App.useApp();
  const { actionRef, reload } = useListPage();
  const { options: ticketTypeOptions } = useDict('support_ticket_type');
  const { options: priorityOptions } = useDict('support_ticket_priority');
  const ticketTypeEnum = useMemo(
    () => Object.fromEntries(ticketTypeOptions.map((o) => [o.value, { text: o.label }])),
    [ticketTypeOptions],
  );
  const priorityEnum = useMemo(
    () => Object.fromEntries(priorityOptions.map((o) => [o.value, { text: o.label }])),
    [priorityOptions],
  );
  const [detailOpen, setDetailOpen] = useState(false);
  const [currentRecord, setCurrentRecord] = useState<SupportTicket | null>(null);
  const [resolveOpen, setResolveOpen] = useState(false);
  const [assignOpen, setAssignOpen] = useState(false);
  const [statistics, setStatistics] = useState<SupportTicketStatistics | null>(null);

  const loadStatistics = async () => {
    try {
      const stats = await supportTicketApi.getStatistics();
      setStatistics(stats);
    } catch {
      // ignore
    }
  };

  useEffect(() => {
    loadStatistics();
  }, []);

  const handleAssign = async (values: { assigneeId: string }) => {
    if (!currentRecord) return false;
    try {
      await supportTicketApi.assign(currentRecord.id, values.assigneeId);
      message.success('分配成功');
      setAssignOpen(false);
      reload();
      loadStatistics();
      return true;
    } catch (error: any) {
      message.error(error.message || '分配失败');
      return false;
    }
  };

  const handleResolve = async (values: { resolution?: string }) => {
    if (!currentRecord) return false;
    try {
      await supportTicketApi.resolve(currentRecord.id, values.resolution);
      message.success('已解决');
      setResolveOpen(false);
      reload();
      loadStatistics();
      return true;
    } catch (error: any) {
      message.error(error.message || '操作失败');
      return false;
    }
  };

  const handleClose = async (id: string) => {
    try {
      await supportTicketApi.close(id);
      message.success('已关闭');
      reload();
      loadStatistics();
    } catch (error: any) {
      message.error(error.message || '操作失败');
    }
  };

  const handleReopen = async (id: string) => {
    try {
      await supportTicketApi.reopen(id);
      message.success('已重开');
      reload();
      loadStatistics();
    } catch (error: any) {
      message.error(error.message || '操作失败');
    }
  };

  const columns: ProColumns<SupportTicket>[] = [
    { title: '标题', dataIndex: 'title', ellipsis: true },
    {
      title: '类型',
      dataIndex: 'type',
      width: 80,
      valueEnum: ticketTypeEnum,
      render: (_, r) => {
        const t = TYPE_MAP[r.type || 'other'];
        return <Tag color={t.color}>{t.text}</Tag>;
      },
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 90,
      valueEnum: Object.fromEntries(Object.entries(STATUS_MAP).map(([k, v]) => [k, { text: v.text }])),
      render: (_, r) => {
        const s = STATUS_MAP[r.status || 'pending'];
        return <Tag color={s.color}>{s.text}</Tag>;
      },
    },
    {
      title: '优先级',
      dataIndex: 'priority',
      width: 80,
      valueEnum: priorityEnum,
      render: (_, r) => {
        const p = PRIORITY_MAP[r.priority || 'medium'];
        return <Tag color={p.color}>{p.text}</Tag>;
      },
    },
    { title: '联系方式', dataIndex: 'contactInfo', width: 120, search: false },
    { title: '创建时间', dataIndex: 'createdAt', valueType: 'dateTime', width: 160, search: false },
    {
      title: '操作',
      valueType: 'option',
      width: 200,
      fixed: 'right',
      render: (_, record) => (
        <OperationGroup>
          <OperationButton
            type="view"
            permission="support_ticket:view"
            onClick={() => { setCurrentRecord(record); setDetailOpen(true); }}
          />
          {record.status === 'pending' && (
            <OperationButton
              type="custom"
              permission="support_ticket:manage"
              icon={<UserOutlined />}
              label="分配"
              onClick={() => { setCurrentRecord(record); setAssignOpen(true); }}
            />
          )}
          {(record.status === 'pending' || record.status === 'processing') && (
            <OperationButton
              type="custom"
              permission="support_ticket:manage"
              icon={<CheckCircleOutlined />}
              label="解决"
              onClick={() => { setCurrentRecord(record); setResolveOpen(true); }}
            />
          )}
          {record.status === 'resolved' && (
            <Popconfirm title="确定关闭该工单吗？" onConfirm={() => handleClose(record.id)}>
              <OperationButton
                type="custom"
                permission="support_ticket:manage"
                icon={<StopOutlined />}
                label="关闭"
              />
            </Popconfirm>
          )}
          {record.status === 'closed' && (
            <Popconfirm title="确定重开该工单吗？" onConfirm={() => handleReopen(record.id)}>
              <OperationButton
                type="custom"
                permission="support_ticket:manage"
                icon={<UndoOutlined />}
                label="重开"
              />
            </Popconfirm>
          )}
        </OperationGroup>
      ),
    },
  ];

  return (
    <PageContainer>
      {statistics && (
        <Row gutter={16} style={{ marginBottom: 16 }}>
          <Col span={6}>
            <Card size="small">
              <Statistic title="全部" value={statistics.total} />
            </Card>
          </Col>
          <Col span={6}>
            <Card size="small">
              <Statistic title="待处理" value={statistics.pending} valueStyle={{ color: '#faad14' }} />
            </Card>
          </Col>
          <Col span={6}>
            <Card size="small">
              <Statistic title="处理中" value={statistics.processing} valueStyle={{ color: '#1677ff' }} />
            </Card>
          </Col>
          <Col span={6}>
            <Card size="small">
              <Statistic title="已解决" value={statistics.resolved} valueStyle={{ color: '#52c41a' }} />
            </Card>
          </Col>
        </Row>
      )}

      <ProTable<SupportTicket>
        headerTitle="工单列表"
        actionRef={actionRef}
        rowKey="id"
        columns={columns}
        request={createListRequest(supportTicketApi.getList)}
        pagination={{ defaultPageSize: 10 }}
        search={{ labelWidth: 'auto' }}
      />

      {/* 分配弹窗 */}
      <ModalForm
        title="分配工单"
        open={assignOpen}
        onOpenChange={setAssignOpen}
        onFinish={handleAssign}
        modalProps={{ destroyOnHidden: true }}
      >
        <ProFormText
          name="assigneeId"
          label="处理人ID"
          rules={[{ required: true, message: '请输入处理人ID' }]}
          placeholder="请输入处理人的用户ID"
        />
      </ModalForm>

      {/* 解决弹窗 */}
      <ModalForm
        title="解决工单"
        open={resolveOpen}
        onOpenChange={setResolveOpen}
        onFinish={handleResolve}
        modalProps={{ destroyOnHidden: true }}
      >
        <ProFormTextArea
          name="resolution"
          label="解决方案"
          placeholder="请输入解决方案或备注（可选）"
          fieldProps={{ rows: 4 }}
        />
      </ModalForm>

      {/* 详情抽屉 */}
      <Drawer
        title="工单详情"
        open={detailOpen}
        onClose={() => setDetailOpen(false)}
        width={500}
      >
        {currentRecord && (
          <Descriptions column={1} bordered size="small" items={[
            { key: 'title', label: '标题', children: currentRecord.title },
            {
              key: 'type', label: '类型',
              children: <Tag color={TYPE_MAP[currentRecord.type || 'other'].color}>{TYPE_MAP[currentRecord.type || 'other'].text}</Tag>,
            },
            {
              key: 'status', label: '状态',
              children: <Tag color={STATUS_MAP[currentRecord.status || 'pending'].color}>{STATUS_MAP[currentRecord.status || 'pending'].text}</Tag>,
            },
            {
              key: 'priority', label: '优先级',
              children: <Tag color={PRIORITY_MAP[currentRecord.priority || 'medium'].color}>{PRIORITY_MAP[currentRecord.priority || 'medium'].text}</Tag>,
            },
            { key: 'description', label: '描述', children: currentRecord.description },
            { key: 'contact', label: '联系方式', children: currentRecord.contactInfo || '-' },
            { key: 'assignee', label: '处理人', children: currentRecord.assigneeId || '未分配' },
            ...(currentRecord.resolution ? [{ key: 'resolution', label: '解决方案', children: currentRecord.resolution }] : []),
            { key: 'created', label: '创建时间', children: currentRecord.createdAt },
            { key: 'updated', label: '更新时间', children: currentRecord.updatedAt },
            ...(currentRecord.closedAt ? [{ key: 'closed', label: '关闭时间', children: currentRecord.closedAt }] : []),
          ]} />
        )}
      </Drawer>
    </PageContainer>
  );
};

export default SupportTicketPage;
