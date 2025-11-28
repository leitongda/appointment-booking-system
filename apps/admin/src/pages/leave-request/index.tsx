import { PageContainer, ProTable, ModalForm, ProFormTextArea, ProFormRadio } from '@ant-design/pro-components';
import type { ProColumns, ActionType } from '@ant-design/pro-components';
import { Tag, Space, message, Drawer, Descriptions, Badge, Card, Statistic, Row, Col } from 'antd';
import { useRef, useState, useEffect } from 'react';
import { leaveRequestApi } from '@hospital/api';
import type { LeaveRequest } from '@hospital/shared';

const LeaveRequestPage: React.FC = () => {
  const actionRef = useRef<ActionType>();
  const [detailVisible, setDetailVisible] = useState(false);
  const [reviewVisible, setReviewVisible] = useState(false);
  const [currentRequest, setCurrentRequest] = useState<LeaveRequest | null>(null);
  const [pendingCount, setPendingCount] = useState(0);

  useEffect(() => {
    loadPendingCount();
  }, []);

  const loadPendingCount = async () => {
    try {
      const result = await leaveRequestApi.getPendingCount();
      setPendingCount(result.count);
    } catch (error) {
      console.error('获取待审核数量失败', error);
    }
  };

  const handleReview = async (values: { status: string; comment?: string }) => {
    if (!currentRequest) return false;
    
    try {
      const reviewerId = localStorage.getItem('adminId') || 'admin';
      await leaveRequestApi.review(currentRequest.id, reviewerId, values.status, values.comment);
      message.success('审核完成');
      setReviewVisible(false);
      actionRef.current?.reload();
      loadPendingCount();
      return true;
    } catch (error: any) {
      message.error(error.message || '审核失败');
      return false;
    }
  };

  const getStatusTag = (status: string) => {
    const map: Record<string, { color: string; text: string }> = {
      pending: { color: 'orange', text: '待审核' },
      approved: { color: 'success', text: '已通过' },
      rejected: { color: 'error', text: '已拒绝' },
      cancelled: { color: 'default', text: '已取消' },
    };
    const config = map[status] || { color: 'default', text: status };
    return <Tag color={config.color}>{config.text}</Tag>;
  };

  const getTypeTag = (type: string) => {
    return type === 'stop_clinic' 
      ? <Tag color="red">停诊</Tag> 
      : <Tag color="blue">调班</Tag>;
  };

  const getPeriodText = (period?: string) => {
    if (!period) return '-';
    const map: Record<string, string> = {
      morning: '上午',
      afternoon: '下午',
      evening: '晚上',
      all: '全天',
    };
    return map[period] || period;
  };

  const columns: ProColumns<LeaveRequest>[] = [
    { title: '医生', dataIndex: 'doctorName', width: 100, search: false },
    { 
      title: '类型', 
      dataIndex: 'requestType', 
      width: 80,
      render: (_, r) => getTypeTag(r.requestType),
      valueEnum: {
        stop_clinic: '停诊',
        schedule_change: '调班',
      }
    },
    { 
      title: '日期/时段', 
      width: 180,
      search: false,
      render: (_, r) => {
        if (r.requestType === 'stop_clinic') {
          return `${r.stopDate} ${getPeriodText(r.stopPeriod)}`;
        }
        return (
          <div>
            <div>原：{r.originalDate} {getPeriodText(r.originalPeriod)}</div>
            <div>调：{r.targetDate} {getPeriodText(r.targetPeriod)}</div>
          </div>
        );
      }
    },
    { title: '原因', dataIndex: 'reason', width: 200, ellipsis: true, search: false },
    { 
      title: '受影响预约', 
      dataIndex: 'affectedAppointments', 
      width: 100,
      search: false,
      render: (val) => val ? <Badge count={val} style={{ backgroundColor: '#ff4d4f' }} /> : '-'
    },
    { 
      title: '状态', 
      dataIndex: 'status', 
      width: 100,
      render: (_, r) => getStatusTag(r.status),
      valueEnum: {
        pending: '待审核',
        approved: '已通过',
        rejected: '已拒绝',
        cancelled: '已取消',
      }
    },
    { title: '申请时间', dataIndex: 'createdAt', width: 160, valueType: 'dateTime', search: false },
    {
      title: '操作',
      valueType: 'option',
      width: 120,
      render: (_, record) => (
        <Space>
          <a onClick={() => { setCurrentRequest(record); setDetailVisible(true); }}>
            详情
          </a>
          {record.status === 'pending' && (
            <a onClick={() => { setCurrentRequest(record); setReviewVisible(true); }}>
              审核
            </a>
          )}
        </Space>
      ),
    },
  ];

  return (
    <PageContainer>
      {/* 统计卡片 */}
      <Card style={{ marginBottom: 16 }}>
        <Row gutter={16}>
          <Col span={6}>
            <Statistic 
              title="待审核" 
              value={pendingCount} 
              valueStyle={{ color: pendingCount > 0 ? '#faad14' : undefined }}
            />
          </Col>
        </Row>
      </Card>

      <ProTable<LeaveRequest>
        actionRef={actionRef}
        rowKey="id"
        columns={columns}
        search={{ labelWidth: 'auto' }}
        request={async (params) => {
          const { current, pageSize, requestType, status } = params;
          const result = await leaveRequestApi.getList({
            requestType,
            status,
            page: current,
            pageSize,
          });
          return { data: result.data, success: true, total: result.total };
        }}
      />

      {/* 详情抽屉 */}
      <Drawer
        title="申请详情"
        open={detailVisible}
        onClose={() => setDetailVisible(false)}
        width={500}
      >
        {currentRequest && (
          <Descriptions column={1} bordered size="small">
            <Descriptions.Item label="医生">{currentRequest.doctorName || currentRequest.doctorId}</Descriptions.Item>
            <Descriptions.Item label="类型">{getTypeTag(currentRequest.requestType)}</Descriptions.Item>
            <Descriptions.Item label="状态">{getStatusTag(currentRequest.status)}</Descriptions.Item>
            
            {currentRequest.requestType === 'stop_clinic' ? (
              <>
                <Descriptions.Item label="停诊日期">{currentRequest.stopDate}</Descriptions.Item>
                <Descriptions.Item label="停诊时段">{getPeriodText(currentRequest.stopPeriod)}</Descriptions.Item>
              </>
            ) : (
              <>
                <Descriptions.Item label="原日期">{currentRequest.originalDate}</Descriptions.Item>
                <Descriptions.Item label="原时段">{getPeriodText(currentRequest.originalPeriod)}</Descriptions.Item>
                <Descriptions.Item label="调整至日期">{currentRequest.targetDate}</Descriptions.Item>
                <Descriptions.Item label="调整至时段">{getPeriodText(currentRequest.targetPeriod)}</Descriptions.Item>
              </>
            )}
            
            <Descriptions.Item label="申请原因">{currentRequest.reason}</Descriptions.Item>
            <Descriptions.Item label="受影响预约">
              {currentRequest.affectedAppointments > 0 ? (
                <Tag color="red">{currentRequest.affectedAppointments} 人</Tag>
              ) : '无'}
            </Descriptions.Item>
            <Descriptions.Item label="申请时间">{currentRequest.createdAt}</Descriptions.Item>
            
            {currentRequest.reviewComment && (
              <Descriptions.Item label="审核意见">{currentRequest.reviewComment}</Descriptions.Item>
            )}
            {currentRequest.reviewedAt && (
              <Descriptions.Item label="审核时间">{currentRequest.reviewedAt}</Descriptions.Item>
            )}
          </Descriptions>
        )}
      </Drawer>

      {/* 审核弹窗 */}
      <ModalForm
        title="审核申请"
        open={reviewVisible}
        onOpenChange={setReviewVisible}
        onFinish={handleReview}
        modalProps={{ destroyOnClose: true }}
      >
        {currentRequest && (
          <div style={{ marginBottom: 16, padding: 12, background: '#f5f5f5', borderRadius: 4 }}>
            <div><strong>{getTypeTag(currentRequest.requestType)} {currentRequest.doctorName}</strong></div>
            <div style={{ marginTop: 8 }}>
              {currentRequest.requestType === 'stop_clinic' 
                ? `${currentRequest.stopDate} ${getPeriodText(currentRequest.stopPeriod)}`
                : `${currentRequest.originalDate} → ${currentRequest.targetDate}`
              }
            </div>
            <div style={{ color: '#666', marginTop: 8 }}>原因：{currentRequest.reason}</div>
            {currentRequest.affectedAppointments > 0 && (
              <div style={{ color: '#ff4d4f', marginTop: 8 }}>
                ⚠️ 将影响 {currentRequest.affectedAppointments} 位患者的预约
              </div>
            )}
          </div>
        )}
        
        <ProFormRadio.Group
          name="status"
          label="审核结果"
          rules={[{ required: true, message: '请选择审核结果' }]}
          options={[
            { label: '通过', value: 'approved' },
            { label: '拒绝', value: 'rejected' },
          ]}
        />
        
        <ProFormTextArea
          name="comment"
          label="审核意见"
          fieldProps={{ rows: 3 }}
        />
      </ModalForm>
    </PageContainer>
  );
};

export default LeaveRequestPage;
