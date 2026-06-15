import { memo } from 'react';
import { Handle, Position, type NodeProps } from '@xyflow/react';
import { BranchesOutlined } from '@ant-design/icons';

const ConditionNode = memo(({ data, selected }: NodeProps) => {
  const d = data as any;
  const branchCount = d.conditions?.length || 0;
  return (
    <div
      style={{
        padding: '8px 16px',
        borderRadius: 8,
        border: selected ? '2px solid #1677ff' : '2px solid #fa8c16',
        background: '#fff7e6',
        minWidth: 120,
        textAlign: 'center',
        fontSize: 13,
        cursor: 'move',
        transform: 'rotate(0deg)',
      }}
    >
      <Handle type="target" position={Position.Top} style={{ width: 8, height: 8 }} />
      <div>
        <BranchesOutlined style={{ color: '#fa8c16', marginRight: 4 }} />
        <strong>{d.label || '条件判断'}</strong>
      </div>
      {branchCount > 0 && (
        <div style={{ fontSize: 11, color: '#666', marginTop: 2 }}>
          {branchCount} 个分支
        </div>
      )}
      <Handle
        type="source"
        position={Position.Bottom}
        id="default"
        style={{ width: 8, height: 8, left: '30%' }}
      />
      <Handle
        type="source"
        position={Position.Bottom}
        id="branch"
        style={{ width: 8, height: 8, left: '70%' }}
      />
    </div>
  );
});

ConditionNode.displayName = 'ConditionNode';
export default ConditionNode;
