import type { ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable } from '@ant-design/pro-components';
import { Tag } from 'antd';
import { messageApi } from '@hospital/api';
import { createListRequest } from '@/utils/proTable';
import { useListPage } from '@/hooks/useListPage';
import { CreateButton } from '@/components/ListOperations';
import type { Message } from '@hospital/shared';

const TYPE_MAP: Record<string, { text: string; color: string }> = {
  system: { text: '系统', color: 'blue' },
  appointment: { text: '预约', color: 'green' },
  reminder: { text: '提醒', color: 'orange' },
  notice: { text: '公告', color: 'purple' },
};

const MessagePage: React.FC = () => {
  const { actionRef } = useListPage();

  const columns: ProColumns<Message>[] = [
    { title: '标题', dataIndex: 'title', ellipsis: true },
    {
      title: '类型',
      dataIndex: 'messageType',
      width: 80,
      valueEnum: Object.fromEntries(Object.entries(TYPE_MAP).map(([k, v]) => [k, { text: v.text }])),
      render: (_, r) => {
        const t = TYPE_MAP[r.messageType || 'system'];
        return <Tag color={t.color}>{t.text}</Tag>;
      },
    },
    {
      title: '用户类型',
      dataIndex: 'userType',
      width: 80,
      valueEnum: { patient: '患者', doctor: '医生' },
    },
    {
      title: '已读',
      dataIndex: 'isRead',
      width: 70,
      search: false,
      render: (_, r) => r.isRead ? <Tag color="green">已读</Tag> : <Tag>未读</Tag>,
    },
    { title: '发送时间', dataIndex: 'createdAt', valueType: 'dateTime', width: 160, search: false },
  ];

  return (
    <PageContainer>
      <ProTable<Message>
        headerTitle="消息列表"
        actionRef={actionRef}
        rowKey="id"
        columns={columns}
        request={createListRequest(messageApi.getAllList, (params) => {
          const { title, ...rest } = params;
          return { ...rest, keyword: title };
        })}
        toolBarRender={() => [
          <CreateButton
            key="add"
            permission="message:send"
            url="/message/create"
            label="发送消息"
          />,
        ]}
        pagination={{ defaultPageSize: 10 }}
        search={{ labelWidth: 'auto' }}
      />
    </PageContainer>
  );
};

export default MessagePage;
