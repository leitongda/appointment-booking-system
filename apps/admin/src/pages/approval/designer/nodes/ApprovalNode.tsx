import { memo } from 'react';
import { Handle, Position, type NodeProps } from '@xyflow/react';
import { AuditOutlined } from '@ant-design/icons';

const MODE_MAP: Record<string, string> = { and: '会签', or: '或签', sequential: '顺签' };
const ASSIGNEE_MAP: Record<string, string> = { role: '角色', user: '指定人', department: '部门负责人', dynamic: '动态' };

const ApprovalNode = memo(({ data, selected }: NodeProps) => {
  const d = data as any;
  return (
    <div
      style={{
        padding: '8px 16px',
        borderRadius: 8,
        border: selected ? '2px solid #1677ff' : '2px solid #1677ff',
        background: '#e6f4ff',
        minWidth: 120,
        textAlign: 'center',
        fontSize: 13,
        cursor: 'move',
      }}
    >
      <Handle type="target" position={Position.Top} style={{ width: 8, height: 8 }} />
      <div>
        <AuditOutlined style={{ color: '#1677ff', marginRight: 4 }} />
        <strong>{d.label || '审批节点'}</strong>
      </div>
      {d.approvalMode && (
        <div style={{ fontSize: 11, color: '#666', marginTop: 2 }}>
          {MODE_MAP[d.approvalMode] || d.approvalMode}
        </div>
      )}
      {d.assigneeType && (
        <div style={{ fontSize: 11, color: '#999' }}>
          {ASSIGNEE_MAP[d.assigneeType] || d.assigneeType}
        </div>
      )}
      <Handle type="source" position={Position.Bottom} style={{ width: 8, height: 8 }} />
    </div>
  );
});

ApprovalNode.displayName = 'ApprovalNode';
export default ApprovalNode;
