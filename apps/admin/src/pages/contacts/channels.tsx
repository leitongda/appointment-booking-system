import type { ActionType, ProColumns } from '@ant-design/pro-components';
import {PageContainer, ProTable} from '@ant-design/pro-components';
import {Button, message, Popconfirm, Space, Tag} from 'antd';
import {DeleteOutlined, EditOutlined, ExperimentOutlined, MailOutlined, MobileOutlined, PlusOutlined, WechatOutlined} from '@ant-design/icons';
import {useState, useRef} from 'react';
import ChannelForm from './components/ChannelForm';

/** 渠道类型映射 */
const CHANNEL_TYPE_MAP: Record<string, { text: string; color: string; icon: React.ReactNode }> = {
  wechat: { text: '微信', color: 'green', icon: <WechatOutlined /> },
  sms: { text: '短信', color: 'blue', icon: <MobileOutlined /> },
  email: { text: '邮件', color: 'purple', icon: <MailOutlined /> },
  webhook: { text: 'Webhook', color: 'orange', icon: <ExperimentOutlined /> },
};

/** 状态映射 */
const STATUS_MAP: Record<number, { text: string; color: string }> = {
  1: { text: '正常', color: 'success' },
  0: { text: '禁用', color: 'error' },
  2: { text: '验证中', color: 'processing' },
};

const ChannelAccountsPage: React.FC = () => {
  const actionRef = useRef<ActionType>();
  const [formOpen, setFormOpen] = useState(false);
  const [editingAccount, setEditingAccount] = useState<Record<string, any> | null>(null);

  /** 删除渠道账号 */
  const handleDelete = async (id: string) => {
    try {
      await fetch(`/api/v1/channel-accounts/${id}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${localStorage.getItem('token')}` },
      });
      message.success('已删除');
      actionRef.current?.reload();
    } catch (e: any) {
      message.error(e.message || '删除失败');
    }
  };

  /** 测试连接 */
  const handleTest = async (id: string) => {
    try {
      const res = await fetch(`/api/v1/channel-accounts/${id}/test`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${localStorage.getItem('token')}` },
      });
      const data = await res.json();
      if (data.data?.success) {
        message.success('连接测试成功');
      } else {
        message.error(`连接测试失败：${data.data?.message || '未知错误'}`);
      }
      actionRef.current?.reload();
    } catch (e: any) {
      message.error(e.message || '测试失败');
    }
  };

  /** 表格列定义 */
  const columns: ProColumns[] = [
    {
      title: '渠道类型',
      dataIndex: 'channelType',
      width: 120,
      valueEnum: Object.fromEntries(
        Object.entries(CHANNEL_TYPE_MAP).map(([k, v]) => [k, { text: v.text }])
      ),
      render: (_, r) => {
        const t = CHANNEL_TYPE_MAP[r.channelType] || { text: r.channelType, color: 'default', icon: null };
        return (
          <Tag color={t.color} icon={t.icon}>
            {t.text}
          </Tag>
        );
      },
    },
    { title: '账号名称', dataIndex: 'name', width: 200 },
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
      title: '默认账号',
      dataIndex: 'isDefault',
      width: 100,
      render: (_, r) => (r.isDefault ? <Tag color="gold">默认</Tag> : null),
    },
    {
      title: '最后同步时间',
      dataIndex: 'lastSyncAt',
      valueType: 'dateTime',
      width: 180,
      search: false,
    },
    {
      title: '最后错误',
      dataIndex: 'lastError',
      width: 200,
      ellipsis: true,
      search: false,
      render: (_, r) => r.lastError ? <Tag color="red">{r.lastError}</Tag> : null,
    },
    {
      title: '创建时间',
      dataIndex: 'createdAt',
      valueType: 'dateTime',
      width: 160,
      sorter: true,
      search: false,
    },
    {
      title: '操作',
      valueType: 'option',
      width: 200,
      fixed: 'right',
      render: (_, r) => (
        <Space>
          <Button
            type="link"
            size="small"
            icon={<ExperimentOutlined />}
            onClick={() => handleTest(r.id)}
          >
            测试
          </Button>
          <Button
            type="link"
            size="small"
            icon={<EditOutlined />}
            onClick={() => {
              setEditingAccount(r);
              setFormOpen(true);
            }}
          >
            编辑
          </Button>
          <Popconfirm
            title="确认删除此渠道账号？"
            onConfirm={() => handleDelete(r.id)}
          >
            <Button type="link" size="small" danger icon={<DeleteOutlined />}>
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <PageContainer>
      <ProTable
        actionRef={actionRef}
        rowKey="id"
        columns={columns}
        request={async (params) => {
          const searchParams = new URLSearchParams();
          searchParams.set('page', String(params.current || 1));
          searchParams.set('page_size', String(params.pageSize || 20));
          if (params.channelType) searchParams.set('channel_type', params.channelType);
          if (params.status !== undefined && params.status !== null)
            searchParams.set('status', String(params.status));

          const res = await fetch(`/api/v1/channel-accounts?${searchParams}`, {
            headers: { Authorization: `Bearer ${localStorage.getItem('token')}` },
          });
          const data = await res.json();
          const items = data.data?.items || data.items || [];
          return { data: items, success: true, total: data.data?.total || data.total || 0 };
        }}
        pagination={{ defaultPageSize: 20 }}
        search={{ labelWidth: 'auto' }}
        scroll={{ x: 1200 }}
        toolBarRender={() => [
          <Button
            key="create"
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => {
              setEditingAccount(null);
              setFormOpen(true);
            }}
          >
            新建渠道账号
          </Button>,
        ]}
      />

      {/* 新建/编辑渠道账号 */}
      <ChannelForm
        open={formOpen}
        onClose={() => setFormOpen(false)}
        onSuccess={() => {
          setFormOpen(false);
          actionRef.current?.reload();
        }}
        initialValues={editingAccount}
      />
    </PageContainer>
  );
};

export default ChannelAccountsPage;
