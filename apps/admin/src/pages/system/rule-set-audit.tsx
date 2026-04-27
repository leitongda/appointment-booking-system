import type { ActionType, ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable } from '@ant-design/pro-components';
import { Tag, Descriptions, Badge, Space } from 'antd';
import { useRef, useState, useEffect } from 'react';
import { useParams, useSearchParams } from '@umijs/max';
import { ruleSetApi } from '@hospital/api';
import type { RuleSetAuditLog } from '@hospital/shared';
import { history } from '@umijs/max';

interface ChangeItem {
  key: string;
  before?: any;
  after?: any;
  nested?: ChangeItem[];
}

interface ChangesData {
  changes?: ChangeItem[];
  created?: boolean;
  deleted?: boolean;
}

const getActionTag = (action: string) => {
  const map: Record<string, { text: string; color: string }> = {
    CREATE: { text: '创建', color: 'success' },
    UPDATE: { text: '更新', color: 'processing' },
    DELETE: { text: '删除', color: 'error' },
    ENABLE: { text: '启用', color: 'success' },
    DISABLE: { text: '禁用', color: 'warning' },
  };
  const info = map[action] || { text: action, color: 'default' };
  return <Tag color={info.color}>{info.text}</Tag>;
};

const renderChangeValue = (value: any) => {
  if (value === null || value === undefined) {
    return <span style={{ color: '#999' }}>-</span>;
  }
  if (typeof value === 'boolean') {
    return <Tag color={value ? 'success' : 'default'}>{value ? '是' : '否'}</Tag>;
  }
  if (typeof value === 'object') {
    return <code style={{ fontSize: '12px' }}>{JSON.stringify(value)}</code>;
  }
  return String(value);
};

const renderChangeItem = (item: ChangeItem, depth = 0) => {
  const isAdd = item.before === null || item.before === undefined;
  const isRemove = item.after === null || item.after === undefined;
  const isModify = !isAdd && !isRemove;

  let bgColor = 'transparent';
  if (isAdd) bgColor = '#f6ffed';
  if (isRemove) bgColor = '#fff1f0';
  if (isModify) bgColor = '#fffbe6';

  return (
    <div key={item.key} style={{ marginLeft: depth * 16, marginBottom: 4 }}>
      <div
        style={{
          padding: '4px 8px',
          backgroundColor: bgColor,
          borderRadius: 4,
          border: '1px solid #f0f0f0',
        }}
      >
        <Space size={8}>
          <span style={{ fontWeight: 500 }}>
            {item.key.startsWith('[新增]') || item.key.startsWith('[删除]') ? item.key : item.key}
          </span>
          {isModify && (
            <>
              <span style={{ color: '#ff4d4f' }}>{renderChangeValue(item.before)}</span>
              <span>&rarr;</span>
              <span style={{ color: '#52c41a' }}>{renderChangeValue(item.after)}</span>
            </>
          )}
          {isAdd && <span style={{ color: '#52c41a' }}>{renderChangeValue(item.after)}</span>}
          {isRemove && <span style={{ color: '#ff4d4f' }}>{renderChangeValue(item.before)}</span>}
        </Space>
        {item.nested && item.nested.length > 0 && (
          <div style={{ marginTop: 4 }}>
            {item.nested.map((child) => renderChangeItem(child, depth + 1))}
          </div>
        )}
      </div>
    </div>
  );
};

const RuleSetAuditPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [searchParams] = useSearchParams();
  const actionRef = useRef<ActionType>();
  const [ruleSetName, setRuleSetName] = useState(searchParams.get('name') || '');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const fetchRuleSetName = async () => {
      if (id && !ruleSetName) {
        try {
          const ruleSet = await ruleSetApi.getById(id);
          setRuleSetName(ruleSet.name || '');
        } catch (error) {
          console.error('获取规则组信息失败:', error);
        }
      }
    };
    fetchRuleSetName();
  }, [id, ruleSetName]);

  const columns: ProColumns<RuleSetAuditLog>[] = [
    {
      title: '操作类型',
      dataIndex: 'action',
      width: 100,
      render: (_, record) => getActionTag(record.action),
      valueEnum: {
        CREATE: { text: '创建', status: 'Success' },
        UPDATE: { text: '更新', status: 'Processing' },
        DELETE: { text: '删除', status: 'Error' },
        ENABLE: { text: '启用', status: 'Success' },
        DISABLE: { text: '禁用', status: 'Warning' },
      },
    },
    {
      title: '资源类型',
      dataIndex: 'resourceType',
      width: 120,
      search: false,
    },
    {
      title: '操作人ID',
      dataIndex: 'operatorId',
      width: 150,
      search: false,
      ellipsis: true,
    },
    {
      title: '操作时间',
      dataIndex: 'createdAt',
      valueType: 'dateTime',
      width: 160,
      sorter: true,
      defaultSortOrder: 'descend',
    },
    {
      title: '变更详情',
      dataIndex: 'changes',
      search: false,
      width: 80,
      render: (_, record) => {
        if (!record.changes) return <span style={{ color: '#999' }}>-</span>;
        try {
          const data: ChangesData = JSON.parse(record.changes);
          const count = data.created ? 0 : data.deleted ? 0 : data.changes?.length || 0;
          return <Badge count={count} showZero color="blue" />;
        } catch {
          return <span style={{ color: '#999' }}>-</span>;
        }
      },
    },
  ];

  const expandedRowRender = (record: RuleSetAuditLog) => {
    if (!record.changes) {
      return (
        <div style={{ padding: 16, color: '#999' }}>
          无详细变更信息
        </div>
      );
    }

    try {
      const data: ChangesData = JSON.parse(record.changes);

      if (data.created) {
        return (
          <div style={{ padding: 16 }}>
            <Tag color="success">新创建</Tag>
            <div style={{ marginTop: 8, fontSize: 12, color: '#666' }}>
              该规则组为新创建，无变更前数据
            </div>
          </div>
        );
      }

      if (data.deleted) {
        return (
          <div style={{ padding: 16 }}>
            <Tag color="error">已删除</Tag>
            <div style={{ marginTop: 8, fontSize: 12, color: '#666' }}>
              该规则组已被删除
            </div>
          </div>
        );
      }

      if (!data.changes || data.changes.length === 0) {
        return (
          <div style={{ padding: 16, color: '#999' }}>
            无字段变更
          </div>
        );
      }

      return (
        <div style={{ padding: 16 }}>
          <Descriptions title="字段级变更对比" size="small" column={1} bordered />
          <div style={{ marginTop: 12 }}>
            {data.changes.map((item) => renderChangeItem(item))}
          </div>
        </div>
      );
    } catch (error) {
      return (
        <div style={{ padding: 16, color: '#ff4d4f' }}>
          解析变更数据失败
        </div>
      );
    }
  };

  return (
    <PageContainer
      title={`审计日志: ${ruleSetName || id}`}
      onBack={() => history.back()}
    >
      <ProTable<RuleSetAuditLog>
        headerTitle="变更历史"
        actionRef={actionRef}
        rowKey="id"
        columns={columns}
        search={false}
        request={async (params) => {
          if (!id) {
            return { data: [], success: false, total: 0 };
          }
          const result = await ruleSetApi.getAuditLogs(id, {
            page: params.current,
            pageSize: params.pageSize,
          });
          return {
            data: result.data || [],
            success: true,
            total: result.total || 0,
          };
        }}
        pagination={{
          defaultPageSize: 20,
          showSizeChanger: true,
          showQuickJumper: true,
        }}
        expandable={{
          expandedRowRender,
          defaultExpandAllRows: false,
        }}
      />
    </PageContainer>
  );
};

export default RuleSetAuditPage;
