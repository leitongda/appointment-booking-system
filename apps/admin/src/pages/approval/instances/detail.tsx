import { PageContainer } from '@ant-design/pro-components';
import { Card, Descriptions, Tag, Timeline, Button, Space, Modal, Input, message, Spin, Empty } from 'antd';
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  ClockCircleOutlined,
  SwapOutlined,
  UndoOutlined,
  UserOutlined,
} from '@ant-design/icons';
import { useHistory, useParams, useModel } from '@umijs/max';
import { useState, useEffect, useCallback } from 'react';
import { approvalInstanceApi } from '@hospital/api';
import type { ApprovalInstance, ApprovalRecord, ApprovalInstanceStatus } from '@hospital/shared';

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
  const { id } = useParams<{ id: string }>();
  const history = useHistory();
  const { initialState } = useModel('@@initialState');
  const [loading, setLoading] = useState(true);
  const [instance, setInstance] = useState<ApprovalInstance | null>(null);
  const [approveModalOpen, setApproveModalOpen] = useState(false);
  const [rejectModalOpen, setRejectModalOpen] = useState(false);
  const [delegateModalOpen, setDelegateModalOpen] = useState(false);
  const [comment, setComment] = useState('');
  const [delegateTargetId, setDelegateTargetId] = useState('');
  const [actionLoading, setActionLoading] = useState(false);

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

  const isMyPending = instance?.status === 'pending' && instance?.records?.some(
    (r) => r.approverId === initialState?.currentUser?.id && r.action === 'comment'
  );

  const isApplicant = instance?.applicantId === initialState?.currentUser?.id;

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
    </PageContainer>
  );
};

export default ApprovalInstanceDetailPage;
