import { memo } from 'react';
import { Handle, Position, type NodeProps } from '@xyflow/react';
import { BranchesOutlined } from '@ant-design/icons';
import './nodes.css';

const ConditionNode = memo(({ data, selected }: NodeProps) => {
  const d = data as any;
  const branchCount = d.conditions?.length || 0;
  return (
    <div className="rf-node rf-node--condition" data-selected={selected}>
      <Handle type="target" position={Position.Top} className="rf-handle" />
      <BranchesOutlined className="rf-node__icon" />
      <div className="rf-node__body">
        <span className="rf-node__label">{d.label || '条件判断'}</span>
        {branchCount > 0 && (
          <div className="rf-node__meta">{branchCount} 个分支</div>
        )}
      </div>
      {(d.listeners?.length > 0) && (
        <div className="rf-node__listener-dot" title={`${d.listeners.length} 个监听器`} />
      )}
      <Handle
        type="source"
        position={Position.Bottom}
        id="default"
        className="rf-handle"
        style={{ left: '30%' }}
      />
      <Handle
        type="source"
        position={Position.Bottom}
        id="branch"
        className="rf-handle"
        style={{ left: '70%' }}
      />
    </div>
  );
});

ConditionNode.displayName = 'ConditionNode';
export default ConditionNode;
