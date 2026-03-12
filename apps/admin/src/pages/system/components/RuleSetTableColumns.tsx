import type { ProColumns } from '@ant-design/pro-components';
import { Popconfirm, Space, Tag } from 'antd';
import { history } from '@umijs/max';
import type { RuleSet } from '@hospital/shared';
import { confirmDelete } from '@/components/ConfirmModal';

interface ColumnHandlers {
  handleToggleEnabled: (record: RuleSet) => void;
  handleDelete: (id: string) => void;
  handleView?: (record: RuleSet) => void;
  canSuperAdmin: boolean;
}

/**
 * 规则组列表列定义
 */
export const getRuleSetColumns = (handlers: ColumnHandlers): ProColumns<RuleSet>[] => [
  {
    title: '规则名称',
    dataIndex: 'name',
    ellipsis: true,
  },
  {
    title: '优先级',
    dataIndex: 'priority',
    width: 80,
    search: false,
    render: (text) => <Tag color="blue">{text}</Tag>,
  },
  {
    title: '班次类型',
    dataIndex: 'shiftTypes',
    width: 150,
    search: false,
    render: (_, record) => (
      <Space size={4} wrap>
        {record.shiftTypes?.map((st) => (
          <Tag key={st.id}>{st.name}</Tag>
        ))}
      </Space>
    ),
  },
  {
    title: '时间来源',
    dataIndex: 'timeSource',
    width: 100,
    valueType: 'select',
    valueEnum: {
      SERVER: { text: '服务端时间' },
      CLIENT: { text: '客户端时间' },
    },
    search: false,
  },
  {
    title: '比较精度',
    dataIndex: 'comparePrecision',
    width: 100,
    valueType: 'select',
    valueEnum: {
      SECOND: { text: '秒' },
      MILLISECOND: { text: '毫秒' },
      MINUTE: { text: '分钟' },
    },
    search: false,
  },
  {
    title: '状态',
    dataIndex: 'enabled',
    width: 80,
    valueType: 'select',
    valueEnum: {
      true: { text: '启用', status: 'Success' },
      false: { text: '禁用', status: 'Default' },
    },
  },
  {
    title: '创建时间',
    dataIndex: 'createdAt',
    valueType: 'dateTime',
    width: 160,
    search: false,
  },
  {
    title: '操作',
    valueType: 'option',
    width: 220,
    fixed: 'right',
    render: (_, record) => (
      <Space>
        {handlers.handleView && (
          <a onClick={() => handlers.handleView!(record)}>查看</a>
        )}
        {handlers.canSuperAdmin ? (
          <a onClick={() => history.push(`/system/rule-sets/${record.id}/edit`)}>编辑</a>
        ) : (
          <a style={{ color: 'rgba(0, 0, 0, 0.25)', cursor: 'not-allowed' }}>编辑</a>
        )}
        {handlers.canSuperAdmin ? (
          <Popconfirm
            title={record.enabled ? '确定禁用该规则组吗？' : '确定启用该规则组吗？'}
            onConfirm={() => handlers.handleToggleEnabled(record)}
          >
            <a>{record.enabled ? '禁用' : '启用'}</a>
          </Popconfirm>
        ) : (
          <a style={{ color: 'rgba(0, 0, 0, 0.25)', cursor: 'not-allowed' }}>
            {record.enabled ? '禁用' : '启用'}
          </a>
        )}
        {handlers.canSuperAdmin && (
          <a
            style={{ color: '#ff4d4f' }}
            onClick={() => {
              const shiftTypesText = record.shiftTypes && record.shiftTypes.length > 0
                ? `影响班次类型：${record.shiftTypes.map(st => st.name).join('、')}`
                : undefined;

              confirmDelete({
                title: '确认删除规则组',
                content: (
                  <div>
                    <p>确定要删除规则组 <strong>{record.name}</strong> 吗？</p>
                    <p style={{ marginTop: 8 }}>删除后相关配置也会受影响。</p>
                  </div>
                ),
                alertMessage: shiftTypesText,
                onOk: () => handlers.handleDelete(record.id),
              });
            }}
          >
            删除
          </a>
        )}
      </Space>
    ),
  },
];
