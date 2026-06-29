/**
 * 节点浮动 Tooltip — 简洁摘要（节点名、类型、审批模式/条件概要）
 */
import React from 'react';

const TYPE_LABEL_MAP: Record<string, string> = {
  start: '开始',
  approval: '审批节点',
  condition: '条件判断',
  cc: '抄送',
  end: '结束',
};

const MODE_MAP: Record<string, string> = {
  and: '会签',
  or: '或签',
  sequential: '顺签',
};

const ASSIGNEE_LABEL_MAP: Record<string, string> = {
  role: '角色',
  user: '指定人',
  department: '部门负责人',
  dynamic: '动态计算',
};

interface NodeTooltipProps {
  visible: boolean;
  x: number;
  y: number;
  data: any;
}

const NodeTooltip: React.FC<NodeTooltipProps> = ({ visible, x, y, data }) => {
  if (!visible || !data) return null;

  const nodeType = data.nodeType || '';
  const typeLabel = TYPE_LABEL_MAP[nodeType] || nodeType;
  const name = data.label || data.nodeName || '';
  const lines: string[] = [typeLabel];

  if (data.approvalMode) lines.push(MODE_MAP[data.approvalMode] || data.approvalMode);
  if (data.assigneeType) lines.push(ASSIGNEE_LABEL_MAP[data.assigneeType] || data.assigneeType);
  if (data.conditions && data.conditions.length > 0) {
    lines.push(`${data.conditions.length} 个条件分支`);
  }

  return (
    <div
      style={{
        position: 'absolute',
        left: x,
        top: y,
        zIndex: 1000,
        background: '#1f1f1f',
        color: '#fff',
        padding: '6px 12px',
        borderRadius: 6,
        fontSize: 12,
        lineHeight: '20px',
        pointerEvents: 'none',
        whiteSpace: 'nowrap',
        boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
      }}
    >
      <div style={{ fontWeight: 600, marginBottom: 2 }}>{name}</div>
      {lines.map((line, i) => (
        <div key={i} style={{ opacity: 0.8 }}>{line}</div>
      ))}
    </div>
  );
};

export default NodeTooltip;
