import { useEffect, useState } from 'react';
import { Drawer, Card, Descriptions, Table, Tag, Spin, message } from 'antd';
import type { ColumnsType } from 'antd/es/table';

/** 联系人类型映射 */
const CONTACT_TYPE_MAP: Record<string, { text: string; color: string }> = {
  patient: { text: '患者', color: 'blue' },
  doctor: { text: '医生', color: 'green' },
  admin: { text: '管理员', color: 'purple' },
  staff: { text: '员工', color: 'cyan' },
  external: { text: '外部联系人', color: 'orange' },
};

/** 性别映射 */
const GENDER_MAP: Record<number, string> = {
  0: '未知',
  1: '男',
  2: '女',
};

/** 状态映射 */
const STATUS_MAP: Record<number, { text: string; color: string }> = {
  1: { text: '正常', color: 'success' },
  0: { text: '禁用', color: 'error' },
};

/** 渠道类型映射 */
const CHANNEL_TYPE_MAP: Record<string, string> = {
  phone: '手机',
  email: '邮箱',
  wechat: '微信',
  sms: '短信',
};

interface ChannelInfo {
  id: string;
  channelType: string;
  channelValue: string;
  isPrimary: number;
  verified: number;
}

interface GroupBrief {
  id: string;
  name: string;
}

interface TagBrief {
  id: string;
  name: string;
  color?: string;
}

interface ContactDetailData {
  id: string;
  name: string;
  nickname?: string;
  avatar?: string;
  gender: number;
  phone?: string;
  email?: string;
  contactType: string;
  position?: string;
  organization?: string;
  notes?: string;
  status: number;
  channels: ChannelInfo[];
  groups: GroupBrief[];
  tags: TagBrief[];
  createdAt?: string;
  updatedAt?: string;
}

interface ContactDetailProps {
  /** 联系人 ID */
  contactId: string | null;
  /** 是否可见 */
  open: boolean;
  /** 关闭回调 */
  onClose: () => void;
}

const ContactDetail: React.FC<ContactDetailProps> = ({ contactId, open, onClose }) => {
  const [loading, setLoading] = useState(false);
  const [detail, setDetail] = useState<ContactDetailData | null>(null);

  useEffect(() => {
    if (!open || !contactId) {
      setDetail(null);
      return;
    }

    const fetchDetail = async () => {
      setLoading(true);
      try {
        const res = await fetch(`/api/v1/contacts/${contactId}`, {
          headers: { Authorization: `Bearer ${localStorage.getItem('token')}` },
        });
        if (!res.ok) throw new Error('获取详情失败');
        const data = await res.json();
        setDetail(data.data || data);
      } catch (e: any) {
        message.error(e.message || '获取联系人详情失败');
      } finally {
        setLoading(false);
      }
    };

    fetchDetail();
  }, [open, contactId]);

  /** 渠道信息表格列 */
  const channelColumns: ColumnsType<ChannelInfo> = [
    {
      title: '渠道类型',
      dataIndex: 'channelType',
      width: 100,
      render: (v: string) => CHANNEL_TYPE_MAP[v] || v,
    },
    {
      title: '标识值',
      dataIndex: 'channelValue',
      ellipsis: true,
    },
    {
      title: '主要渠道',
      dataIndex: 'isPrimary',
      width: 90,
      align: 'center',
      render: (v: number) => (v === 1 ? <Tag color="blue">是</Tag> : <Tag>否</Tag>),
    },
    {
      title: '已验证',
      dataIndex: 'verified',
      width: 80,
      align: 'center',
      render: (v: number) => (v === 1 ? <Tag color="green">是</Tag> : <Tag>否</Tag>),
    },
  ];

  const typeInfo = detail?.contactType ? CONTACT_TYPE_MAP[detail.contactType] : null;
  const statusInfo = detail?.status !== undefined ? STATUS_MAP[detail.status] : null;

  return (
    <Drawer
      title="联系人详情"
      open={open}
      onClose={onClose}
      width={520}
      destroyOnClose
    >
      <Spin spinning={loading}>
        {detail && (
          <>
            {/* 基础信息 */}
            <Card title="基础信息" size="small" style={{ marginBottom: 16 }}>
              <Descriptions column={1} size="small" labelStyle={{ width: 90 }}>
                <Descriptions.Item label="姓名">{detail.name}</Descriptions.Item>
                <Descriptions.Item label="昵称">{detail.nickname || '-'}</Descriptions.Item>
                <Descriptions.Item label="性别">{GENDER_MAP[detail.gender] || '未知'}</Descriptions.Item>
                <Descriptions.Item label="手机">{detail.phone || '-'}</Descriptions.Item>
                <Descriptions.Item label="邮箱">{detail.email || '-'}</Descriptions.Item>
                <Descriptions.Item label="类型">
                  {typeInfo ? <Tag color={typeInfo.color}>{typeInfo.text}</Tag> : detail.contactType}
                </Descriptions.Item>
                <Descriptions.Item label="职位">{detail.position || '-'}</Descriptions.Item>
                <Descriptions.Item label="机构">{detail.organization || '-'}</Descriptions.Item>
                <Descriptions.Item label="状态">
                  {statusInfo ? <Tag color={statusInfo.color}>{statusInfo.text}</Tag> : '-'}
                </Descriptions.Item>
                <Descriptions.Item label="备注">{detail.notes || '-'}</Descriptions.Item>
              </Descriptions>
            </Card>

            {/* 渠道信息 */}
            <Card title="渠道信息" size="small" style={{ marginBottom: 16 }}>
              <Table<ChannelInfo>
                columns={channelColumns}
                dataSource={detail.channels || []}
                rowKey="id"
                pagination={false}
                size="small"
                locale={{ emptyText: '暂无渠道信息' }}
              />
            </Card>

            {/* 分组信息 */}
            <Card title="分组信息" size="small" style={{ marginBottom: 16 }}>
              {detail.groups?.length ? (
                detail.groups.map((g) => (
                  <Tag key={g.id} color="blue" style={{ marginBottom: 4 }}>
                    {g.name}
                  </Tag>
                ))
              ) : (
                <span style={{ color: 'var(--color-text-tertiary)' }}>暂无分组</span>
              )}
            </Card>

            {/* 标签信息 */}
            <Card title="标签信息" size="small">
              {detail.tags?.length ? (
                detail.tags.map((t) => (
                  <Tag key={t.id} color={t.color || 'default'} style={{ marginBottom: 4 }}>
                    {t.name}
                  </Tag>
                ))
              ) : (
                <span style={{ color: 'var(--color-text-tertiary)' }}>暂无标签</span>
              )}
            </Card>
          </>
        )}
      </Spin>
    </Drawer>
  );
};

export default ContactDetail;
