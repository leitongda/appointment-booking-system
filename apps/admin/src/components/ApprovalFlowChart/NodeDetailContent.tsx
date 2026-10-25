/**
 * 节点详情内容 — 根据节点类型展示完整配置信息
 *
 * 支持定义查看模式（展示审批人/条件/超时/监听器配置）
 * 和实例模式（额外展示审批状态和执行记录摘要）
 */
import React from 'react';
import { Descriptions, Tag, Divider } from 'antd';
import type { NodeStatus } from './index';

// 小工具
const SpaceTag: React.FC<{ children: React.ReactNode; color?: string }> = ({ children, color }) => (
  <Tag color={color} style={{ marginBottom: 4 }}>{children}</Tag>
);


// ─── 常量 ──────────────────────────────────────────────

const TYPE_LABEL_MAP: Record<string, string> = {
  start: '开始节点',
  approval: '审批节点',
  condition: '条件判断节点',
  cc: '抄送节点',
  end: '结束节点',
};

const TYPE_COLOR_MAP: Record<string, string> = {
  start: 'green',
  approval: 'blue',
  condition: 'orange',
  cc: 'default',
  end: 'red',
};

const MODE_MAP: Record<string, string> = {
  and: '会签（所有人通过才继续）',
  or: '或签（任一通过即继续）',
  sequential: '依次审批（按顺序逐个审批）',
};

const ASSIGNEE_LABEL_MAP: Record<string, string> = {
  role: '角色',
  user: '指定人',
  department: '部门负责人',
  dynamic: '动态计算',
};

const TIMEOUT_ACTION_MAP: Record<string, string> = {
  remind: '提醒',
  auto_approve: '自动通过',
  auto_reject: '自动拒绝',
  transfer: '转交上级',
};

const STATUS_MAP: Record<string, { text: string; color: string }> = {
  completed: { text: '已通过', color: 'green' },
  current: { text: '审批中', color: 'blue' },
  rejected: { text: '已拒绝', color: 'red' },
  skipped: { text: '已跳过', color: 'default' },
  pending: { text: '待审批', color: 'default' },
};

// ─── 组件 ──────────────────────────────────────────────

interface NodeDetailContentProps {
  data: any;
  mode?: 'definition' | 'instance';
}

const NodeDetailContent: React.FC<NodeDetailContentProps> = ({ data, mode = 'definition' }) => {
  const nodeType: string = data?.nodeType || '';
  const typeLabel = TYPE_LABEL_MAP[nodeType] || nodeType;
  const typeColor = TYPE_COLOR_MAP[nodeType] || 'default';
  const status: NodeStatus = data?.status;
  const statusInfo = status ? STATUS_MAP[status] : null;

  return (
    <div style={{ padding: '0 16px' }}>
      <Descriptions column={1} size="small" colon={false}>
        {/* 基本信息（所有节点类型都有） */}
        <Descriptions.Item label="节点名称">
          {data.label || data.nodeName || '—'}
        </Descriptions.Item>
        <Descriptions.Item label="节点类型">
          <Tag color={typeColor}>{typeLabel}</Tag>
        </Descriptions.Item>
        {statusInfo && (
          <Descriptions.Item label="审批状态">
            <Tag color={statusInfo.color}>{statusInfo.text}</Tag>
          </Descriptions.Item>
        )}
        <Descriptions.Item label="节点标识">
          <code style={{ fontSize: 12, color: '#666' }}>{data.nodeKey}</code>
        </Descriptions.Item>
      </Descriptions>

      {/* 审批节点专属配置 */}
      {nodeType === 'approval' && (
        <>
          <Divider style={{ margin: '12px 0' }} />
          <Descriptions column={1} size="small" colon={false}>
            {data.approvalMode && (
              <Descriptions.Item label="审批模式">
                <Tag>{MODE_MAP[data.approvalMode] || data.approvalMode}</Tag>
              </Descriptions.Item>
            )}
            {data.assigneeType && (
              <Descriptions.Item label="审批人来源">
                <Tag>{ASSIGNEE_LABEL_MAP[data.assigneeType] || data.assigneeType}</Tag>
              </Descriptions.Item>
            )}
            {data.assigneeConfig && (
              <Descriptions.Item label="审批人配置">
                <code style={{ fontSize: 12 }}>
                  {JSON.stringify(data.assigneeConfig, null, 2)}
                </code>
              </Descriptions.Item>
            )}
            {data.timeoutHours && (
              <Descriptions.Item label="超时时间">
                {data.timeoutHours} 小时
              </Descriptions.Item>
            )}
            {data.timeoutAction && (
              <Descriptions.Item label="超时动作">
                <Tag>{TIMEOUT_ACTION_MAP[data.timeoutAction] || data.timeoutAction}</Tag>
              </Descriptions.Item>
            )}
          </Descriptions>
        </>
      )}

      {/* 条件节点专属配置 */}
      {nodeType === 'condition' && data.conditions && data.conditions.length > 0 && (
        <>
          <Divider style={{ margin: '12px 0' }} />
          <div style={{ fontWeight: 500, marginBottom: 8, fontSize: 13 }}>
            条件分支（{data.conditions.length}）
          </div>
          {data.conditions.map((c: any, i: number) => (
            <div key={i} style={{
              padding: '8px 12px',
              marginBottom: 6,
              background: '#fafafa',
              borderRadius: 6,
              border: '1px solid #f0f0f0',
              fontSize: 12,
            }}>
              <div style={{ color: '#666', marginBottom: 2 }}>
                {i === 0 ? '分支 1（优先）' : i === data.conditions.length - 1 ? '默认分支' : `分支 ${i + 1}`}
              </div>
              <code>{c.fieldName}</code>{' '}
              <Tag style={{ marginLeft: 4 }}>{c.operator}</Tag>{' '}
              <code>{c.value}</code>
              {c.targetNodeKey && (
                <div style={{ color: '#999', marginTop: 2 }}>→ {c.targetNodeKey}</div>
              )}
            </div>
          ))}
        </>
      )}

      {/* 监听器 */}
      {data.listeners && data.listeners.length > 0 && (
        <>
          <Divider style={{ margin: '12px 0' }} />
          <div style={{ fontWeight: 500, marginBottom: 8, fontSize: 13 }}>
            监听器（{data.listeners.length}）
          </div>
          {data.listeners.map((l: any, i: number) => (
            <div key={i} style={{
              padding: '8px 12px',
              marginBottom: 6,
              background: '#fafafa',
              borderRadius: 6,
              border: '1px solid #f0f0f0',
              fontSize: 12,
            }}>
              <SpaceTag>{l.event || l.eventType || '—'}</SpaceTag>
              <SpaceTag color="blue">{l.actionType || l.type || '—'}</SpaceTag>
              {l.url && <div style={{ color: '#666', marginTop: 4 }}>{l.url}</div>}
            </div>
          ))}
        </>
      )}

      {/* 实例模式：关联记录摘要 */}
      {mode === 'instance' && data.records && data.records.length > 0 && (
        <>
          <Divider style={{ margin: '12px 0' }} />
          <div style={{ fontWeight: 500, marginBottom: 8, fontSize: 13 }}>执行记录</div>
          {data.records.map((r: any, i: number) => (
            <div key={i} style={{ padding: '6px 0', fontSize: 12, color: '#666', borderBottom: '1px solid #fafafa' }}>
              <Tag color={r.action === 'approve' ? 'green' : r.action === 'reject' ? 'red' : 'default'}>
                {r.action}
              </Tag>
              {r.approverName || r.approverId} · {r.comment || '无评论'}
            </div>
          ))}
        </>
      )}
    </div>
  );
};


export default NodeDetailContent;
