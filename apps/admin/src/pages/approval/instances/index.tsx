import type { ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable } from '@ant-design/pro-components';
import { Tag, Button, Space, Modal, Input, message } from 'antd';
import { history, useModel } from '@umijs/max';
import { useState, useRef } from 'react';
import type { ActionType } from '@ant-design/pro-components';
import { approvalInstanceApi } from '@hospital/api';
import type { ApprovalInstanceListItem, ApprovalInstanceStatus } from '@hospital/shared';

const STATUS_MAP: Record<ApprovalInstanceStatus, { text: string; color: string }> = {
  pending: { text: '审批中', color: 'processing' },
  approved: { text: '已通过', color: 'success' },
  rejected: { text: '已拒绝', color: 'error' },
  cancelled: { text: '已取消', color: 'default' },
  withdrawn: { text: '已撤回', color: 'default' },
};

const BUSINESS_TYPE_MAP: Record<string, string> = {
  leave_request: '停诊审批',
  extra_quota: '加号审批',
};

type TabKey = 'pending' | 'done' | 'initiated';

const ApprovalInstancesPage: React.FC = () => {
  useModel('@@initialState');
  const [activeTab, setActiveTab] = useState<TabKey>('pending');
  const actionRef = useRef<ActionType>();
  const [approveModalOpen, setApproveModalOpen] = useState(false);
  const [rejectModalOpen, setRejectModalOpen] = useState(false);

  const [currentId, setCurrentId] = useState<string>('');
  const [comment, setComment] = useState('');
  const [loading, setLoading] = useState(false);

  const fetchData = async (params: any) => {
    const query = {
      page: params.current,
      pageSize: params.pageSize,
      status: params.status,
      businessType: params.businessType,
    };
    try {
      let res;
      if (activeTab === 'pending') {
        res = await approvalInstanceApi.getMyPending(query);
      } else if (activeTab === 'done') {
        res = await approvalInstanceApi.getMyDone(query);
      } else {
        res = await approvalInstanceApi.getMyInitiated(query);
      }
      const items = (res as any).items || res.data || [];
      return { data: items, success: true, total: res.total ?? items.length };
    } catch {
      return { data: [], success: false, total: 0 };
    }
  };

  const handleApprove = async () => {
    setLoading(true);
    try {
      await approvalInstanceApi.approve(currentId, comment || undefined);
      message.success('审批通过');
      setApproveModalOpen(false);
      setComment('');
      actionRef.current?.reload();
    } catch (e: any) {
      message.error(e.message || '操作失败');
    } finally {
      setLoading(false);
    }
  };

  const handleReject = async () => {
    if (!comment.trim()) {
      message.warning('请填写拒绝原因');
      return;
    }
    setLoading(true);
    try {
      await approvalInstanceApi.reject(currentId, comment);
      message.success('已拒绝');
      setRejectModalOpen(false);
      setComment('');
      actionRef.current?.reload();
    } catch (e: any) {
      message.error(e.message || '操作失败');
    } finally {
      setLoading(false);
    }
  };

  const handleWithdraw = async (id: string) => {
    Modal.confirm({
      title: '确认撤回',
      content: '撤回后此审批流程将终止，确认撤回？',
      onOk: async () => {
        try {
          await approvalInstanceApi.withdraw(id);
          message.success('已撤回');
          actionRef.current?.reload();
        } catch (e: any) {
          message.error(e.message || '撤回失败');
        }
      },
    });
  };

  const columns: ProColumns<ApprovalInstanceListItem>[] = [
    {
      title: '标题',
      dataIndex: 'title',
      ellipsis: true,
      search: false,
    },
    {
      title: '业务类型',
      dataIndex: 'businessType',
      width: 120,
      valueEnum: BUSINESS_TYPE_MAP,
      render: (_, r) => BUSINESS_TYPE_MAP[r.businessType] || r.businessType,
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
      title: '申请人',
      dataIndex: 'applicantName',
      width: 100,
      search: false,
    },
    {
      title: '申请时间',
      dataIndex: 'createdAt',
      valueType: 'dateTime',
      width: 180,
      search: false,
      sorter: true,
    },
    {
      title: '操作',
      valueType: 'option',
      width: 200,
      fixed: 'right',
      render: (_, record) => (
        <Space>
          <Button
            type="link"
            size="small"
            onClick={() => history.push(`/approval/instances/${record.id}`)}
          >
            查看
          </Button>
          {activeTab === 'pending' && record.status === 'pending' && (
            <>
              <Button
                type="link"
                size="small"
                style={{ color: '#52c41a' }}
                onClick={() => {
                  setCurrentId(record.id);
                  setApproveModalOpen(true);
                }}
              >
                通过
              </Button>
              <Button
                type="link"
                size="small"
                danger
                onClick={() => {
                  setCurrentId(record.id);
                  setRejectModalOpen(true);
                }}
              >
                拒绝
              </Button>
            </>
          )}
          {activeTab === 'initiated' && record.status === 'pending' && (
            <Button
              type="link"
              size="small"
              danger
              onClick={() => handleWithdraw(record.id)}
            >
              撤回
            </Button>
          )}
        </Space>
      ),
    },
  ];

  const tabItems = [
    { key: 'pending', label: '我的待办' },
    { key: 'done', label: '我的已办' },
    { key: 'initiated', label: '我发起的' },
  ];

  return (
    <PageContainer
      title="审批中心"
      tabList={tabItems}
      tabActiveKey={activeTab}
      onTabChange={(key) => setActiveTab(key as TabKey)}
    >
      <ProTable<ApprovalInstanceListItem>
        actionRef={actionRef}
        rowKey="id"
        columns={columns}
        request={fetchData}
        pagination={{ defaultPageSize: 20 }}
        search={{ labelWidth: 'auto' }}
        scroll={{ x: 900 }}
      />

      {/* 通过弹窗 */}
      <Modal
        title="审批通过"
        open={approveModalOpen}
        onOk={handleApprove}
        onCancel={() => { setApproveModalOpen(false); setComment(''); }}
        confirmLoading={loading}
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
        confirmLoading={loading}
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

export default ApprovalInstancesPage;
