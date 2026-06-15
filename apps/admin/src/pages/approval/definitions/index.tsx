import type { ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable } from '@ant-design/pro-components';
import { Tag, Button, Space, Modal, message, Drawer, Timeline, Card, Descriptions } from 'antd';
import { PlusOutlined, CopyOutlined, PlayCircleOutlined, PauseCircleOutlined, DeleteOutlined, EyeOutlined } from '@ant-design/icons';
import { useState, useRef } from 'react';
import type { ActionType } from '@ant-design/pro-components';
import { history } from '@umijs/max';
import { approvalFlowApi } from '@hospital/api';
import type { FlowDefinitionListItem, FlowDefinition } from '@hospital/shared';

const STATUS_MAP: Record<string, { text: string; color: string }> = {
  draft: { text: '草稿', color: 'default' },
  active: { text: '已激活', color: 'success' },
  archived: { text: '已归档', color: 'warning' },
};

const BUSINESS_TYPE_OPTIONS = [
  { label: '停诊审批', value: 'leave_request' },
  { label: '加号审批', value: 'extra_quota' },
];

const NODE_TYPE_MAP: Record<string, string> = {
  start: '开始',
  approval: '审批',
  cc: '抄送',
  condition: '条件',
  end: '结束',
};

const FlowDefinitionsPage: React.FC = () => {
  const actionRef = useRef<ActionType>();
  const [detailOpen, setDetailOpen] = useState(false);
  const [currentFlow, setCurrentFlow] = useState<FlowDefinition | null>(null);

  const fetchData = async (params: any) => {
    try {
      const res = await approvalFlowApi.getList({
        page: params.current,
        pageSize: params.pageSize,
        businessType: params.businessType,
        status: params.status,
      });
      const items = (res as any).items || res.data || [];
      return { data: items, success: true, total: res.total ?? items.length };
    } catch {
      return { data: [], success: false, total: 0 };
    }
  };

  const handleViewDetail = async (id: string) => {
    try {
      const data = await approvalFlowApi.getDetail(id);
      setCurrentFlow(data);
      setDetailOpen(true);
    } catch (e: any) {
      message.error(e.message || '获取详情失败');
    }
  };

  const handleActivate = async (id: string) => {
    Modal.confirm({
      title: '确认激活',
      content: '激活后将替换同业务类型的其他激活流程，确认？',
      onOk: async () => {
        try {
          await approvalFlowApi.activate(id);
          message.success('激活成功');
          actionRef.current?.reload();
        } catch (e: any) {
          message.error(e.message || '激活失败');
        }
      },
    });
  };

  const handleArchive = async (id: string) => {
    Modal.confirm({
      title: '确认归档',
      content: '归档后此流程定义将不再使用，确认？',
      onOk: async () => {
        try {
          await approvalFlowApi.archive(id);
          message.success('已归档');
          actionRef.current?.reload();
        } catch (e: any) {
          message.error(e.message || '归档失败');
        }
      },
    });
  };

  const handleCopy = async (id: string) => {
    try {
      await approvalFlowApi.copy(id);
      message.success('复制成功');
      actionRef.current?.reload();
    } catch (e: any) {
      message.error(e.message || '复制失败');
    }
  };

  const handleDelete = async (id: string) => {
    Modal.confirm({
      title: '确认删除',
      content: '仅草稿状态的流程可以删除，确认？',
      onOk: async () => {
        try {
          await approvalFlowApi.delete(id);
          message.success('已删除');
          actionRef.current?.reload();
        } catch (e: any) {
          message.error(e.message || '删除失败');
        }
      },
    });
  };

  const columns: ProColumns<FlowDefinitionListItem>[] = [
    {
      title: '流程名称',
      dataIndex: 'name',
      ellipsis: true,
    },
    {
      title: '业务类型',
      dataIndex: 'businessType',
      width: 120,
      valueEnum: Object.fromEntries(BUSINESS_TYPE_OPTIONS.map((o) => [o.value, { text: o.label }])),
      render: (_, r) => {
        const opt = BUSINESS_TYPE_OPTIONS.find((o) => o.value === r.businessType);
        return opt?.label || r.businessType;
      },
    },
    {
      title: '版本',
      dataIndex: 'version',
      width: 80,
      search: false,
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 100,
      valueEnum: Object.fromEntries(
        Object.entries(STATUS_MAP).map(([k, v]) => [k, { text: v.text }])
      ),
      render: (_, r) => {
        const s = STATUS_MAP[r.status] || { text: '未知', color: 'default' };
        return <Tag color={s.color}>{s.text}</Tag>;
      },
    },
    {
      title: '描述',
      dataIndex: 'description',
      ellipsis: true,
      search: false,
    },
    {
      title: '更新时间',
      dataIndex: 'updatedAt',
      valueType: 'dateTime',
      width: 160,
      search: false,
    },
    {
      title: '操作',
      valueType: 'option',
      width: 280,
      fixed: 'right',
      render: (_, record) => (
        <Space>
          <Button type="link" size="small" icon={<EyeOutlined />} onClick={() => handleViewDetail(record.id)}>
            查看
          </Button>
          <Button type="link" size="small" icon={<CopyOutlined />} onClick={() => handleCopy(record.id)}>
            复制
          </Button>
          {record.status === 'draft' && (
            <Button type="link" size="small" onClick={() => history.push(`/approval/definitions/designer/${record.id}`)}>
              编辑
            </Button>
          )}
          {record.status === 'draft' && (
            <>
              <Button type="link" size="small" style={{ color: '#52c41a' }} icon={<PlayCircleOutlined />} onClick={() => handleActivate(record.id)}>
                激活
              </Button>
              <Button type="link" size="small" danger icon={<DeleteOutlined />} onClick={() => handleDelete(record.id)}>
                删除
              </Button>
            </>
          )}
          {record.status === 'active' && (
            <Button type="link" size="small" icon={<PauseCircleOutlined />} onClick={() => handleArchive(record.id)}>
              归档
            </Button>
          )}
        </Space>
      ),
    },
  ];

  return (
    <PageContainer title="流程定义管理">
      <ProTable<FlowDefinitionListItem>
        actionRef={actionRef}
        rowKey="id"
        columns={columns}
        request={fetchData}
        pagination={{ defaultPageSize: 20 }}
        search={{ labelWidth: 'auto' }}
        scroll={{ x: 1000 }}
        toolBarRender={() => [
          <Button
            key="create"
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => history.push('/approval/definitions/designer/new')}
          >
            新建流程
          </Button>,
        ]}
      />

      {/* 流程详情抽屉 */}
      <Drawer
        title="流程定义详情"
        open={detailOpen}
        onClose={() => setDetailOpen(false)}
        width={600}
      >
        {currentFlow && (
          <>
            <Descriptions column={1} style={{ marginBottom: 24 }}>
              <Descriptions.Item label="流程名称">{currentFlow.name}</Descriptions.Item>
              <Descriptions.Item label="业务类型">
                {BUSINESS_TYPE_OPTIONS.find((o) => o.value === currentFlow.businessType)?.label || currentFlow.businessType}
              </Descriptions.Item>
              <Descriptions.Item label="版本">v{currentFlow.version}</Descriptions.Item>
              <Descriptions.Item label="状态">
                <Tag color={STATUS_MAP[currentFlow.status]?.color}>
                  {STATUS_MAP[currentFlow.status]?.text}
                </Tag>
              </Descriptions.Item>
              {currentFlow.description && (
                <Descriptions.Item label="描述">{currentFlow.description}</Descriptions.Item>
              )}
            </Descriptions>

            <Card title="流程节点" size="small">
              {currentFlow.nodes && currentFlow.nodes.length > 0 ? (
                <Timeline
                  items={currentFlow.nodes
                    .sort((a, b) => a.sortOrder - b.sortOrder)
                    .map((node) => ({
                      color: node.nodeType === 'approval' ? 'blue' : node.nodeType === 'condition' ? 'orange' : 'gray',
                      children: (
                        <div>
                          <Space>
                            <Tag color={node.nodeType === 'approval' ? 'blue' : 'default'}>
                              {NODE_TYPE_MAP[node.nodeType] || node.nodeType}
                            </Tag>
                            <span style={{ fontWeight: 500 }}>{node.nodeName}</span>
                            {node.approvalMode && (
                              <Tag>{node.approvalMode === 'and' ? '会签' : node.approvalMode === 'or' ? '或签' : '依次审批'}</Tag>
                            )}
                          </Space>
                          {node.assigneeType && (
                            <div style={{ color: '#666', fontSize: 12, marginTop: 4 }}>
                              审批人: {node.assigneeType}
                            </div>
                          )}
                          {node.conditions && node.conditions.length > 0 && (
                            <div style={{ color: '#666', fontSize: 12, marginTop: 4 }}>
                              条件: {node.conditions.map((c) => `${c.fieldName} ${c.operator} ${c.value}`).join(', ')}
                            </div>
                          )}
                        </div>
                      ),
                    }))}
                />
              ) : (
                <div style={{ color: '#999' }}>暂无节点</div>
              )}
            </Card>
          </>
        )}
      </Drawer>
    </PageContainer>
  );
};

export default FlowDefinitionsPage;
