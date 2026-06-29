import { PageContainer } from '@ant-design/pro-components';
import { Card, Descriptions, Tag, Timeline, Button, Space, Modal, Input, Select, Dropdown, message, Spin, Empty, Steps } from 'antd';
import type { MenuProps } from 'antd';
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  ClockCircleOutlined,
  SwapOutlined,
  UndoOutlined,
  UserOutlined,
  EllipsisOutlined,
  RollbackOutlined,
  UserAddOutlined,
  FastForwardOutlined,
  BranchesOutlined,
} from '@ant-design/icons';
import { history, useParams, useModel } from '@umijs/max';
import { useState, useEffect, useCallback } from 'react';
import { approvalInstanceApi, approvalFlowApi } from '@hospital/api';
import type { ApprovalInstance, ApprovalRecord, ApprovalInstanceStatus, ApprovalProgress } from '@hospital/shared';
import FlowChartViewer from '@/components/ApprovalFlowChart';
import type { NodeStatus } from '@/components/ApprovalFlowChart';

const STATUS_MAP: Record<ApprovalInstanceStatus, { text: string; color: string }> = {
  pending: { text: '审批中', color: 'processing' },
  approved: { text: '已通过', color: 'success' },
  rejected: { text: '已拒绝', color: 'error' },
  cancelled: { text: '已取消', color: 'default' },
  withdrawn: { text: '已撤回', color: 'default' },
};

const ACTION_MAP: Record<string, { text: string; color: string; icon: React.ReactNode }> = {
  approve: { text: '通过', color: 'green', icon: <CheckCircleOutlined /> },
  reject: { text: '拒绝', color: 'red', icon: <CloseCircleOutlined /> },
  delegate: { text: '转交', color: 'blue', icon: <SwapOutlined /> },
  comment: { text: '评论', color: 'gray', icon: <ClockCircleOutlined /> },
  withdraw: { text: '撤回', color: 'orange', icon: <UndoOutlined /> },
};

const BUSINESS_TYPE_MAP: Record<string, string> = {
  leave_request: '停诊审批',
  extra_quota: '加号审批',
};

const ApprovalInstanceDetailPage: React.FC = () => {
  const params = useParams();
  const id = params.id as string | undefined;
  const { initialState } = useModel('@@initialState');
  const [loading, setLoading] = useState(true);
  const [instance, setInstance] = useState<ApprovalInstance | null>(null);
  const [approveModalOpen, setApproveModalOpen] = useState(false);
  const [rejectModalOpen, setRejectModalOpen] = useState(false);
  const [delegateModalOpen, setDelegateModalOpen] = useState(false);
  const [rollbackModalOpen, setRollbackModalOpen] = useState(false);
  const [addSignerModalOpen, setAddSignerModalOpen] = useState(false);
  const [jumpModalOpen, setJumpModalOpen] = useState(false);
  const [comment, setComment] = useState('');
  const [actionLoading, setActionLoading] = useState(false);
  const [targetUserId, setTargetUserId] = useState('');
  const [targetUserName, setTargetUserName] = useState('');
  const [targetNodeKey, setTargetNodeKey] = useState('');
  const [progress, setProgress] = useState<ApprovalProgress | null>(null);
  const [flowDefinition, setFlowDefinition] = useState<any>(null);
  const [nodeStatuses, setNodeStatuses] = useState<Map<string, NodeStatus>>(new Map());
  const [instanceRecords, setInstanceRecords] = useState<Map<string, any[]>>(new Map());

  const fetchDetail = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    try {
      const data = await approvalInstanceApi.getDetail(id);
      setInstance(data);
    } catch (e: any) {
      message.error(e.message || '获取详情失败');
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    fetchDetail();
  }, [fetchDetail]);

  // 加载流程定义数据，用于渲染流程图
  useEffect(() => {
    if (!instance?.flowDefId) return;
    approvalFlowApi.getDetail(instance.flowDefId).then((flowDef: any) => {
      setFlowDefinition(flowDef);

      // 根据实例记录和当前节点计算各节点状态
      const statusMap = new Map<string, NodeStatus>();
      const recordActions = new Map<string, { action: string; comment?: string }[]>();

      // 收集每个节点的审批记录
      (instance.records || []).forEach((r: ApprovalRecord) => {
        if (r.nodeKey) {
          const actions = recordActions.get(r.nodeKey) || [];
          actions.push({ action: r.action, comment: r.comment });
          recordActions.set(r.nodeKey, actions);
        }
      });

      // 标记节点状态
      const allNodeKeys = (flowDef.nodes || []).map((n: any) => n.nodeKey);
      for (const nodeKey of allNodeKeys) {
        const actions = recordActions.get(nodeKey);
        if (actions) {
          // 有审批记录 → 检查是否被拒绝
          const hasReject = actions.some((a) => a.action === 'reject');
          statusMap.set(nodeKey, hasReject ? 'rejected' : 'completed');
        }
      }

      // 标记当前节点
      if (instance.currentNodeKey) {
        statusMap.set(instance.currentNodeKey, 'current');
      }

      // 被拒绝流程的其余节点标记为跳过
      if (instance.status === 'rejected' || instance.status === 'cancelled' || instance.status === 'withdrawn') {
        for (const nodeKey of allNodeKeys) {
          if (!statusMap.has(nodeKey)) {
            statusMap.set(nodeKey, 'skipped');
          }
        }
      }

      setNodeStatuses(statusMap);

      // 同时构建节点→记录映射，供流程图节点点击抽屉展示
      const recMap = new Map<string, any[]>();
      (instance.records || []).forEach((r: ApprovalRecord) => {
        if (r.nodeKey) {
          const arr = recMap.get(r.nodeKey) || [];
          arr.push(r);
          recMap.set(r.nodeKey, arr);
        }
      });
      setInstanceRecords(recMap);
    }).catch(() => {
      // 流程定义加载失败（非关键，流程图区域显示为空）
      setFlowDefinition(null);
    });
  }, [instance?.flowDefId, instance?.records, instance?.currentNodeKey, instance?.status]);

  useEffect(() => {
    if (!id || !instance) return;
    approvalInstanceApi.getProgress(id).then(setProgress).catch(() => setProgress(null));
  }, [id, instance]);

  const isApplicant = instance?.applicantId === initialState?.currentUser?.id;
  const isAssignee = instance?.tasks?.some(
    (t) => t.assigneeId === initialState?.currentUser?.id && t.status === 'pending',
  ) ?? false;

  const handleApprove = async () => {
    if (!id) return;
    setActionLoading(true);
    try {
      await approvalInstanceApi.approve(id, comment || undefined);
      message.success('审批通过');
      setApproveModalOpen(false);
      setComment('');
      fetchDetail();
    } catch (e: any) {
      message.error(e.message || '操作失败');
    } finally {
      setActionLoading(false);
    }
  };

  const handleReject = async () => {
    if (!id) return;
    if (!comment.trim()) {
      message.warning('请填写拒绝原因');
      return;
    }
    setActionLoading(true);
    try {
      await approvalInstanceApi.reject(id, comment);
      message.success('已拒绝');
      setRejectModalOpen(false);
      setComment('');
      fetchDetail();
    } catch (e: any) {
      message.error(e.message || '操作失败');
    } finally {
      setActionLoading(false);
    }
  };

  const handleWithdraw = async () => {
    if (!id) return;
    Modal.confirm({
      title: '确认撤回',
      content: '撤回后此审批流程将终止，确认撤回？',
      onOk: async () => {
        try {
          await approvalInstanceApi.withdraw(id);
          message.success('已撤回');
          fetchDetail();
        } catch (e: any) {
          message.error(e.message || '撤回失败');
        }
      },
    });
  };

  const handleDelegate = async () => {
    if (!id) return;
    if (!targetUserId.trim()) {
      message.warning('请填写目标用户 ID');
      return;
    }
    setActionLoading(true);
    try {
      await approvalInstanceApi.delegate(id, targetUserId, targetUserName || undefined, comment || undefined);
      message.success('已转交');
      setDelegateModalOpen(false);
      setTargetUserId('');
      setTargetUserName('');
      setComment('');
      fetchDetail();
    } catch (e: any) {
      message.error(e.message || '操作失败');
    } finally {
      setActionLoading(false);
    }
  };

  const handleRollback = async () => {
    if (!id) return;
    if (!targetNodeKey.trim()) {
      message.warning('请选择回退目标节点');
      return;
    }
    if (!comment.trim()) {
      message.warning('请填写回退原因');
      return;
    }
    setActionLoading(true);
    try {
      await approvalInstanceApi.rollback(id, targetNodeKey, comment);
      message.success('已回退');
      setRollbackModalOpen(false);
      setTargetNodeKey('');
      setComment('');
      fetchDetail();
    } catch (e: any) {
      message.error(e.message || '操作失败');
    } finally {
      setActionLoading(false);
    }
  };

  const handleAddSigner = async () => {
    if (!id) return;
    if (!targetUserId.trim()) {
      message.warning('请填写用户 ID');
      return;
    }
    setActionLoading(true);
    try {
      await approvalInstanceApi.addSigner(id, [targetUserId], comment || undefined);
      message.success('已加签');
      setAddSignerModalOpen(false);
      setTargetUserId('');
      setTargetUserName('');
      setComment('');
      fetchDetail();
    } catch (e: any) {
      message.error(e.message || '操作失败');
    } finally {
      setActionLoading(false);
    }
  };

  const handleJump = async () => {
    if (!id) return;
    if (!targetNodeKey.trim()) {
      message.warning('请选择跳转目标节点');
      return;
    }
    if (!comment.trim()) {
      message.warning('请填写跳转原因');
      return;
    }
    setActionLoading(true);
    try {
      await approvalInstanceApi.jump(id, targetNodeKey, comment);
      message.success('已跳转');
      setJumpModalOpen(false);
      setTargetNodeKey('');
      setComment('');
      fetchDetail();
    } catch (e: any) {
      message.error(e.message || '操作失败');
    } finally {
      setActionLoading(false);
    }
  };

  /** 从 records 中提取已审批过的节点（去重），用于回退目标 */
  const getCompletedNodeOptions = () => {
    if (!instance?.records) return [];
    const seen = new Set<string>();
    const options: { label: string; value: string }[] = [];
    for (const r of instance.records) {
      if (r.nodeKey && !seen.has(r.nodeKey)) {
        seen.add(r.nodeKey);
        options.push({ label: r.nodeName || r.nodeKey, value: r.nodeKey });
      }
    }
    return options;
  };

  /** 从 tasks 中提取所有节点，用于跳转目标 */
  const getAllNodeOptions = () => {
    if (!instance?.tasks) return [];
    const seen = new Set<string>();
    const options: { label: string; value: string }[] = [];
    for (const t of instance.tasks) {
      if (t.nodeKey && !seen.has(t.nodeKey)) {
        seen.add(t.nodeKey);
        options.push({ label: t.nodeName || t.nodeKey, value: t.nodeKey });
      }
    }
    return options;
  };

  if (loading) {
    return (
      <PageContainer title="审批详情">
        <div style={{ textAlign: 'center', padding: 100 }}>
          <Spin size="large" />
        </div>
      </PageContainer>
    );
  }

  if (!instance) {
    return (
      <PageContainer title="审批详情">
        <Empty description="审批实例不存在" />
      </PageContainer>
    );
  }

  const statusInfo = STATUS_MAP[instance.status] || { text: '未知', color: 'default' };

  return (
    <PageContainer
      title={instance.title || '审批详情'}
      onBack={() => history.goBack()}
      extra={
        instance.status === 'pending' && (
          <Space>
            <Button
              type="primary"
              onClick={() => setApproveModalOpen(true)}
            >
              通过
            </Button>
            <Button
              danger
              onClick={() => setRejectModalOpen(true)}
            >
              拒绝
            </Button>
            {isAssignee && (
              <Button
                icon={<SwapOutlined />}
                onClick={() => setDelegateModalOpen(true)}
              >
                转交
              </Button>
            )}
            <Dropdown
              menu={{
                items: [
                  {
                    key: 'rollback',
                    icon: <RollbackOutlined />,
                    label: '回退',
                    onClick: () => setRollbackModalOpen(true),
                  },
                  {
                    key: 'addSigner',
                    icon: <UserAddOutlined />,
                    label: '加签',
                    onClick: () => setAddSignerModalOpen(true),
                  },
                  {
                    key: 'jump',
                    icon: <FastForwardOutlined />,
                    label: '跳转',
                    onClick: () => setJumpModalOpen(true),
                  },
                ] as MenuProps['items'],
              }}
            >
              <Button icon={<EllipsisOutlined />}>
                更多操作
              </Button>
            </Dropdown>
            {isApplicant && (
              <Button onClick={handleWithdraw}>
                撤回
              </Button>
            )}
          </Space>
        )
      }
    >
      {/* 基本信息 */}
      <Card title="基本信息" style={{ marginBottom: 16 }}>
        <Descriptions column={2}>
          <Descriptions.Item label="审批标题">{instance.title}</Descriptions.Item>
          <Descriptions.Item label="业务类型">
            {BUSINESS_TYPE_MAP[instance.businessType] || instance.businessType}
          </Descriptions.Item>
          <Descriptions.Item label="申请人">
            <Space>
              <UserOutlined />
              {instance.applicantName || instance.applicantId}
            </Space>
          </Descriptions.Item>
          <Descriptions.Item label="状态">
            <Tag color={statusInfo.color}>{statusInfo.text}</Tag>
          </Descriptions.Item>
          <Descriptions.Item label="申请时间">{instance.createdAt}</Descriptions.Item>
          {instance.approvedAt && (
            <Descriptions.Item label="通过时间">{instance.approvedAt}</Descriptions.Item>
          )}
          {instance.rejectedAt && (
            <Descriptions.Item label="拒绝时间">{instance.rejectedAt}</Descriptions.Item>
          )}
          {instance.cancelledAt && (
            <Descriptions.Item label="撤回时间">{instance.cancelledAt}</Descriptions.Item>
          )}
        </Descriptions>
      </Card>

      {/* 审批进度 */}
      {progress && progress.approvers && progress.approvers.length > 0 && (
        <Card title="审批进度" style={{ marginBottom: 16 }}>
          <Steps
            current={progress.approvedCount}
            items={progress.approvers.map((approver, index) => {
              let stepStatus: 'finish' | 'process' | 'wait' = 'wait';
              if (approver.approved) {
                stepStatus = 'finish';
              } else if (index === progress.approvedCount) {
                stepStatus = 'process';
              }
              return {
                title: approver.name,
                description: approver.approved ? '已审批' : index === progress.approvedCount ? '审批中' : '待审批',
                status: stepStatus,
              };
            })}
          />
        </Card>
      )}

      {/* 流程图 */}
      {flowDefinition && (
        <Card
          title={
            <Space>
              <BranchesOutlined />
              流程图
            </Space>
          }
          style={{ marginBottom: 16 }}
        >
          <div style={{ border: '1px solid #eee', borderRadius: 8, overflow: 'hidden' }}>
            <FlowChartViewer
              flowDefinition={flowDefinition}
              nodeStatuses={nodeStatuses}
              instanceRecords={instanceRecords}
              mode="instance"
              height={450}
            />
          </div>
        </Card>
      )}

      {/* 表单数据 */}
      {instance.formData && Object.keys(instance.formData).length > 0 && (
        <Card title="申请内容" style={{ marginBottom: 16 }}>
          <Descriptions column={2}>
            {Object.entries(instance.formData).map(([key, value]) => (
              <Descriptions.Item key={key} label={key}>
                {typeof value === 'object' ? JSON.stringify(value) : String(value ?? '-')}
              </Descriptions.Item>
            ))}
          </Descriptions>
        </Card>
      )}

      {/* 审批记录 */}
      <Card title="审批记录">
        {instance.records && instance.records.length > 0 ? (
          <Timeline
            items={instance.records.map((record: ApprovalRecord) => {
              const actionInfo = ACTION_MAP[record.action] || {
                text: record.action,
                color: 'gray',
                icon: <ClockCircleOutlined />,
              };
              return {
                color: actionInfo.color,
                dot: actionInfo.icon,
                children: (
                  <div>
                    <Space>
                      <span style={{ fontWeight: 500 }}>
                        {record.approverName || record.approverId}
                      </span>
                      <Tag color={actionInfo.color}>{actionInfo.text}</Tag>
                      {record.nodeName && (
                        <Tag>{record.nodeName}</Tag>
                      )}
                    </Space>
                    {record.comment && (
                      <div style={{ color: '#666', marginTop: 4 }}>
                        {record.comment}
                      </div>
                    )}
                    <div style={{ color: '#999', fontSize: 12, marginTop: 4 }}>
                      {record.createdAt}
                    </div>
                  </div>
                ),
              };
            })}
          />
        ) : (
          <Empty description="暂无审批记录" image={Empty.PRESENTED_IMAGE_SIMPLE} />
        )}
      </Card>

      {/* 通过弹窗 */}
      <Modal
        title="审批通过"
        open={approveModalOpen}
        onOk={handleApprove}
        onCancel={() => { setApproveModalOpen(false); setComment(''); }}
        confirmLoading={actionLoading}
      >
        <Input.TextArea
          placeholder="审批意见（选填）"
          value={comment}
          onChange={(e) => setComment(e.target.value)}
          rows={3}
        />
      </Modal>

      {/* 拒绝弹窗 */}
      <Modal
        title="审批拒绝"
        open={rejectModalOpen}
        onOk={handleReject}
        onCancel={() => { setRejectModalOpen(false); setComment(''); }}
        confirmLoading={actionLoading}
      >
        <Input.TextArea
          placeholder="请填写拒绝原因"
          value={comment}
          onChange={(e) => setComment(e.target.value)}
          rows={3}
        />
      </Modal>

      {/* 转交弹窗 */}
      <Modal
        title="转交审批"
        open={delegateModalOpen}
        onOk={handleDelegate}
        onCancel={() => {
          setDelegateModalOpen(false);
          setTargetUserId('');
          setTargetUserName('');
          setComment('');
        }}
        confirmLoading={actionLoading}
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <Input
            placeholder="目标用户 ID（必填）"
            value={targetUserId}
            onChange={(e) => setTargetUserId(e.target.value)}
          />
          <Input
            placeholder="目标用户姓名（选填）"
            value={targetUserName}
            onChange={(e) => setTargetUserName(e.target.value)}
          />
          <Input.TextArea
            placeholder="转交原因（选填）"
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            rows={3}
          />
        </div>
      </Modal>

      {/* 回退弹窗 */}
      <Modal
        title="回退到指定节点"
        open={rollbackModalOpen}
        onOk={handleRollback}
        onCancel={() => {
          setRollbackModalOpen(false);
          setTargetNodeKey('');
          setComment('');
        }}
        confirmLoading={actionLoading}
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <Select
            placeholder="选择回退目标节点"
            value={targetNodeKey || undefined}
            onChange={(val) => setTargetNodeKey(val)}
            options={getCompletedNodeOptions()}
            style={{ width: '100%' }}
          />
          <Input.TextArea
            placeholder="回退原因（必填）"
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            rows={3}
          />
        </div>
      </Modal>

      {/* 加签弹窗 */}
      <Modal
        title="添加审批人"
        open={addSignerModalOpen}
        onOk={handleAddSigner}
        onCancel={() => {
          setAddSignerModalOpen(false);
          setTargetUserId('');
          setTargetUserName('');
          setComment('');
        }}
        confirmLoading={actionLoading}
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <Input
            placeholder="用户 ID（必填）"
            value={targetUserId}
            onChange={(e) => setTargetUserId(e.target.value)}
          />
          <Input
            placeholder="用户姓名（选填）"
            value={targetUserName}
            onChange={(e) => setTargetUserName(e.target.value)}
          />
          <Input.TextArea
            placeholder="加签原因（选填）"
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            rows={3}
          />
        </div>
      </Modal>

      {/* 跳转弹窗 */}
      <Modal
        title="自由跳转"
        open={jumpModalOpen}
        onOk={handleJump}
        onCancel={() => {
          setJumpModalOpen(false);
          setTargetNodeKey('');
          setComment('');
        }}
        confirmLoading={actionLoading}
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <Select
            placeholder="选择跳转目标节点"
            value={targetNodeKey || undefined}
            onChange={(val) => setTargetNodeKey(val)}
            options={getAllNodeOptions()}
            style={{ width: '100%' }}
          />
          <Input.TextArea
            placeholder="跳转原因（必填）"
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            rows={3}
          />
        </div>
      </Modal>
    </PageContainer>
  );
};

export default ApprovalInstanceDetailPage;
