import { PageContainer, ProTable, ModalForm, ProFormTextArea } from '@ant-design/pro-components';
import type { ProColumns, ActionType } from '@ant-design/pro-components';
import { Button, Tag, Space, message, Popconfirm, Drawer, Descriptions, Image } from 'antd';
import { useRef, useState } from 'react';
import { feedbackApi } from '@hospital/api';
import type { Feedback } from '@hospital/shared';

const FeedbackPage: React.FC = () => {
  const actionRef = useRef<ActionType>();
  const [detailVisible, setDetailVisible] = useState(false);
  const [replyVisible, setReplyVisible] = useState(false);
  const [currentFeedback, setCurrentFeedback] = useState<Feedback | null>(null);

  const handleReply = async (values: { reply: string }) => {
    if (!currentFeedback) return false;
    
    try {
      // 模拟管理员ID
      const handlerId = localStorage.getItem('adminId') || 'admin';
      await feedbackApi.reply(currentFeedback.id, handlerId, values.reply);
      message.success('回复成功');
      setReplyVisible(false);
      actionRef.current?.reload();
      return true;
    } catch (error: any) {
      message.error(error.message || '回复失败');
      return false;
    }
  };

  const handleUpdateStatus = async (id: string, status: string) => {
    try {
      await feedbackApi.updateStatus(id, status);
      message.success('状态更新成功');
      actionRef.current?.reload();
    } catch (error: any) {
      message.error(error.message || '操作失败');
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await feedbackApi.delete(id);
      message.success('删除成功');
      actionRef.current?.reload();
    } catch (error: any) {
      message.error(error.message || '删除失败');
    }
  };

  const getStatusTag = (status: string) => {
    const map: Record<string, { color: string; text: string }> = {
      pending: { color: 'orange', text: '待处理' },
      processing: { color: 'processing', text: '处理中' },
      resolved: { color: 'success', text: '已解决' },
      closed: { color: 'default', text: '已关闭' },
    };
    const config = map[status] || { color: 'default', text: status };
    return <Tag color={config.color}>{config.text}</Tag>;
  };

  const getTypeTag = (type: string) => {
    const map: Record<string, { color: string; text: string }> = {
      suggestion: { color: 'blue', text: '建议' },
      complaint: { color: 'red', text: '投诉' },
      bug: { color: 'orange', text: '问题' },
      other: { color: 'default', text: '其他' },
    };
    const config = map[type] || { color: 'default', text: type };
    return <Tag color={config.color}>{config.text}</Tag>;
  };

  const columns: ProColumns<Feedback>[] = [
    { title: 'ID', dataIndex: 'id', width: 80, ellipsis: true, copyable: true },
    { 
      title: '类型', 
      dataIndex: 'feedbackType', 
      width: 80,
      render: (_, r) => getTypeTag(r.feedbackType),
      valueEnum: {
        suggestion: '建议',
        complaint: '投诉',
        bug: '问题',
        other: '其他',
      }
    },
    { title: '标题', dataIndex: 'title', width: 200, ellipsis: true },
    { title: '内容', dataIndex: 'content', width: 250, ellipsis: true, search: false },
    { title: '联系方式', dataIndex: 'contact', width: 120, search: false },
    { 
      title: '状态', 
      dataIndex: 'status', 
      width: 100,
      render: (_, r) => getStatusTag(r.status),
      valueEnum: {
        pending: '待处理',
        processing: '处理中',
        resolved: '已解决',
        closed: '已关闭',
      }
    },
    { title: '提交时间', dataIndex: 'createdAt', width: 160, valueType: 'dateTime', search: false },
    {
      title: '操作',
      valueType: 'option',
      width: 200,
      render: (_, record) => (
        <Space>
          <a onClick={() => { setCurrentFeedback(record); setDetailVisible(true); }}>
            详情
          </a>
          {record.status === 'pending' && (
            <>
              <a onClick={() => { setCurrentFeedback(record); setReplyVisible(true); }}>
                回复
              </a>
              <a onClick={() => handleUpdateStatus(record.id, 'processing')}>
                处理中
              </a>
            </>
          )}
          {record.status === 'processing' && (
            <a onClick={() => { setCurrentFeedback(record); setReplyVisible(true); }}>
              回复
            </a>
          )}
          {(record.status === 'resolved' || record.status === 'processing') && (
            <a onClick={() => handleUpdateStatus(record.id, 'closed')}>
              关闭
            </a>
          )}
          <Popconfirm title="确定删除吗？" onConfirm={() => handleDelete(record.id)}>
            <a style={{ color: 'red' }}>删除</a>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <PageContainer>
      <ProTable<Feedback>
        actionRef={actionRef}
        rowKey="id"
        columns={columns}
        search={{ labelWidth: 'auto' }}
        request={async (params) => {
          const { current, pageSize, feedbackType, status, title } = params;
          const result = await feedbackApi.getList({
            feedbackType,
            status,
            keyword: title,
            page: current,
            pageSize,
          });
          return { data: result.data, success: true, total: result.total };
        }}
      />

      {/* 详情抽屉 */}
      <Drawer
        title="反馈详情"
        open={detailVisible}
        onClose={() => setDetailVisible(false)}
        width={500}
      >
        {currentFeedback && (
          <Descriptions column={1} bordered size="small">
            <Descriptions.Item label="类型">{getTypeTag(currentFeedback.feedbackType)}</Descriptions.Item>
            <Descriptions.Item label="状态">{getStatusTag(currentFeedback.status)}</Descriptions.Item>
            <Descriptions.Item label="标题">{currentFeedback.title}</Descriptions.Item>
            <Descriptions.Item label="内容">{currentFeedback.content}</Descriptions.Item>
            {currentFeedback.images && currentFeedback.images.length > 0 && (
              <Descriptions.Item label="图片">
                <Image.PreviewGroup>
                  {currentFeedback.images.map((img, i) => (
                    <Image key={i} src={img} width={80} style={{ marginRight: 8 }} />
                  ))}
                </Image.PreviewGroup>
              </Descriptions.Item>
            )}
            <Descriptions.Item label="联系方式">{currentFeedback.contact || '-'}</Descriptions.Item>
            <Descriptions.Item label="提交时间">{currentFeedback.createdAt}</Descriptions.Item>
            {currentFeedback.reply && (
              <Descriptions.Item label="回复内容">
                <div style={{ background: '#f5f5f5', padding: 12, borderRadius: 4 }}>
                  {currentFeedback.reply}
                </div>
              </Descriptions.Item>
            )}
            {currentFeedback.handledAt && (
              <Descriptions.Item label="处理时间">{currentFeedback.handledAt}</Descriptions.Item>
            )}
          </Descriptions>
        )}
      </Drawer>

      {/* 回复弹窗 */}
      <ModalForm
        title="回复反馈"
        open={replyVisible}
        onOpenChange={setReplyVisible}
        onFinish={handleReply}
        modalProps={{ destroyOnClose: true }}
      >
        {currentFeedback && (
          <div style={{ marginBottom: 16, padding: 12, background: '#f5f5f5', borderRadius: 4 }}>
            <div><strong>{currentFeedback.title}</strong></div>
            <div style={{ color: '#666', marginTop: 8 }}>{currentFeedback.content}</div>
          </div>
        )}
        <ProFormTextArea
          name="reply"
          label="回复内容"
          rules={[{ required: true, message: '请输入回复内容' }]}
          fieldProps={{ rows: 4 }}
        />
      </ModalForm>
    </PageContainer>
  );
};

export default FeedbackPage;
