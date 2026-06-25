import { memo } from 'react';
import { Handle, Position, type NodeProps } from '@xyflow/react';
import { AuditOutlined } from '@ant-design/icons';
import './nodes.css';

const MODE_MAP: Record<string, string> = { and: '会签', or: '或签', sequential: '顺签' };
const ASSIGNEE_MAP: Record<string, string> = { role: '角色', user: '指定人', department: '部门负责人', dynamic: '动态' };

const ApprovalNode = memo(({ data, selected }: NodeProps) => {
  const d = data as any;
  return (
    <div className="rf-node rf-node--approval" data-selected={selected}>
      <Handle type="target" position={Position.Top} className="rf-handle" />
      <div>
        <AuditOutlined className="rf-node__icon" style={{ color: '#1677ff' }} />
        <span className="rf-node__label">{d.label || '审批节点'}</span>
      </div>
      {d.approvalMode && (
        <div className="rf-node__meta">
          {MODE_MAP[d.approvalMode] || d.approvalMode}
        </div>
      )}
      {d.assigneeType && (
        <div className="rf-node__meta">
          {ASSIGNEE_MAP[d.assigneeType] || d.assigneeType}
        </div>
      )}
      {(d.listeners?.length > 0) && (
        <div className="rf-node__listener-dot" title={`${d.listeners.length} 个监听器`} />
      )}
      <Handle type="source" position={Position.Bottom} className="rf-handle" />
    </div>
  );
});

ApprovalNode.displayName = 'ApprovalNode';
export default ApprovalNode;
