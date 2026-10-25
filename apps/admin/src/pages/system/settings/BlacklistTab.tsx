import {Table, Input, Button, Space, Popconfirm, Tag, Typography} from 'antd';
import {PlusOutlined} from '@ant-design/icons';
import type { BlacklistItem } from '@hospital/api';
import type { BlacklistTabProps } from './types';

const { Text } = Typography;

const BlacklistTab: React.FC<BlacklistTabProps> = ({
  blacklist,
  blacklistTotal,
  blacklistPage,
  blacklistKeyword,
  blacklistLoading,
  onLoadBlacklist,
  onRemoveBlacklist,
  canAdd,
  canDelete,
  onAddModalChange,
}) => {
  const columns = [
    {
      title: '禁用门店',
      dataIndex: 'storeName',
      width: 120,
      render: (val: string) => val || '全部',
    },
    {
      title: '用户',
      dataIndex: 'userName',
      width: 120,
      render: (val: string, record: BlacklistItem) => val || record.userPhone || '-',
    },
    { title: '关键词', dataIndex: 'keyword', width: 150 },
    { title: '创建时间', dataIndex: 'createdAt', width: 160 },
    { title: '解禁时间', dataIndex: 'expireAt', width: 160, render: (val: string) => val || '永久' },
    { title: '备注', dataIndex: 'reason', width: 150, ellipsis: true },
    {
      title: '来源',
      dataIndex: 'source',
      width: 80,
      render: (val: number) => (
        <Tag color={val === 2 ? 'orange' : 'blue'}>{val === 2 ? '自动' : '手动'}</Tag>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 80,
      render: (val: number) => (
        <Tag color={val === 1 ? 'red' : 'default'}>{val === 1 ? '生效中' : '已解禁'}</Tag>
      ),
    },
    {
      title: '操作',
      width: 80,
      render: (_: any, record: BlacklistItem) =>
        canDelete && record.status === 1 ? (
          <Popconfirm title="确定解禁该用户吗？" onConfirm={() => onRemoveBlacklist(record.id)}>
            <a>解禁</a>
          </Popconfirm>
        ) : (
          '-'
        ),
    },
  ];

  return (
    <div>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between' }}>
        <Space>
          <span>用户：</span>
          <Input.Search
            placeholder="搜索(用户昵称/电话/身份证)"
            style={{ width: 280 }}
            onSearch={(val) => {
              onLoadBlacklist(1, val);
            }}
            allowClear
          />
        </Space>
        {canAdd && (
          <Button type="primary" icon={<PlusOutlined />} onClick={() => onAddModalChange(true)}>
            添加黑名单
          </Button>
        )}
      </div>
      <Text type="secondary" style={{ display: 'block', marginBottom: 16 }}>
        注：黑名单规则，如果只填关键词则判断就诊卡的手机号或者身份证，如果选择的是用户则该用户无法预约，选择门店只针对该门店不选择则针对所有门店
      </Text>
      <Table
        columns={columns}
        dataSource={blacklist}
        rowKey="id"
        loading={blacklistLoading}
        pagination={{
          current: blacklistPage,
          total: blacklistTotal,
          pageSize: 20,
          showSizeChanger: false,
          onChange: (page) => onLoadBlacklist(page, blacklistKeyword),
        }}
        scroll={{ x: 1200 }}
        size="middle"
      />
    </div>
  );
};

export default BlacklistTab;
