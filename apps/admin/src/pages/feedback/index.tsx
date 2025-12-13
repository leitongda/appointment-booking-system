import type { ActionType, ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable, ModalForm, ProFormTextArea } from '@ant-design/pro-components';
import { App, Space, Tag, Button, Drawer, Descriptions, Image } from 'antd';
import { useRef, useState } from 'react';
import { useModel } from '@umijs/max';
import { feedbackApi } from '@hospital/api';
import { toProTableResult } from '@/utils/proTable';
import type { Feedback } from '@hospital/shared';

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

const FeedbackPage: React.FC = () => {
  const { message } = App.useApp();
  const { initialState } = useModel('@@initialState');
  const actionRef = useRef<ActionType>();
  const [replyOpen, setReplyOpen] = useState(false);
  const [detailOpen, setDetailOpen] = useState(false);
  const [currentRecord, setCurrentRecord] = useState<Feedback | null>(null);

  const handleReply = async (values: { reply: string }) => {
    if (!currentRecord || !initialState?.currentUser?.id) return false;
    try {
      await feedbackApi.reply(currentRecord.id, initialState.currentUser.id, values.reply);
      message.success('回复成功');
      setReplyOpen(false);
      actionRef.current?.reload();
      return true;
    } catch (error: any) {
      message.error(error.message || '回复失败');
      return false;
    }
  };

  const columns: ProColumns<Feedback>[] = [
    { title: '标题', dataIndex: 'title', ellipsis: true },
    {
      title: '类型',
      dataIndex: 'feedbackType',
      width: 80,
      valueEnum: Object.fromEntries(Object.entries(TYPE_MAP).map(([k, v]) => [k, { text: v.text }])),
      render: (_, r) => {
        const t = TYPE_MAP[r.feedbackType || 'other'];
        return <Tag color={t.color}>{t.text}</Tag>;
      },
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 80,
      valueEnum: Object.fromEntries(Object.entries(STATUS_MAP).map(([k, v]) => [k, { text: v.text }])),
      render: (_, r) => {
        const s = STATUS_MAP[r.status || 'pending'];
        return <Tag color={s.color}>{s.text}</Tag>;
      },
    },
    { title: '联系方式', dataIndex: 'contact', width: 120, search: false },
    { title: '提交时间', dataIndex: 'createdAt', valueType: 'dateTime', width: 160, search: false },
    {
      title: '操作',
      valueType: 'option',
      width: 120,
      render: (_, record) => (
        <Space>
          <a onClick={() => { setCurrentRecord(record); setDetailOpen(true); }}>详情</a>
          {record.status === 'pending' && (
            <a onClick={() => { setCurrentRecord(record); setReplyOpen(true); }}>回复</a>
          )}
        </Space>
      ),
    },
  ];

  return (
    <PageContainer>
      <ProTable<Feedback>
        headerTitle="用户反馈"
        actionRef={actionRef}
        rowKey="id"
        columns={columns}
        request={async (params) => {
          const { current, pageSize, title, ...rest } = params;
          return toProTableResult(await feedbackApi.getList({ ...rest, keyword: title, page: current, pageSize }));
        }}
        pagination={{ defaultPageSize: 10 }}
        search={{ labelWidth: 'auto' }}
      />

      <ModalForm
        title="回复反馈"
        open={replyOpen}
        onOpenChange={setReplyOpen}
        onFinish={handleReply}
        modalProps={{ destroyOnHidden: true }}
      >
        <ProFormTextArea name="reply" label="回复内容" rules={[{ required: true }]} />
      </ModalForm>

      <Drawer
        title="反馈详情"
        open={detailOpen}
        onClose={() => setDetailOpen(false)}
        width={500}
      >
        {currentRecord && (
          <Descriptions column={1} bordered size="small">
            <Descriptions.Item label="标题">{currentRecord.title}</Descriptions.Item>
            <Descriptions.Item label="类型">{TYPE_MAP[currentRecord.feedbackType || 'other'].text}</Descriptions.Item>
            <Descriptions.Item label="状态">{STATUS_MAP[currentRecord.status || 'pending'].text}</Descriptions.Item>
            <Descriptions.Item label="内容">{currentRecord.content}</Descriptions.Item>
            <Descriptions.Item label="联系方式">{currentRecord.contact || '-'}</Descriptions.Item>
            {currentRecord.images && currentRecord.images.length > 0 && (
              <Descriptions.Item label="图片">
                <Image.PreviewGroup>
                  {currentRecord.images.map((img, i) => (
                    <Image key={i} src={img} width={80} style={{ marginRight: 8 }} />
                  ))}
                </Image.PreviewGroup>
              </Descriptions.Item>
            )}
            <Descriptions.Item label="提交时间">{currentRecord.createdAt}</Descriptions.Item>
            {currentRecord.reply && (
              <Descriptions.Item label="回复内容">{currentRecord.reply}</Descriptions.Item>
            )}
            {currentRecord.repliedAt && (
              <Descriptions.Item label="回复时间">{currentRecord.repliedAt}</Descriptions.Item>
            )}
          </Descriptions>
        )}
      </Drawer>
    </PageContainer>
  );
};

export default FeedbackPage;
