import { memo } from 'react';
import { Handle, Position, type NodeProps } from '@xyflow/react';
import { StopOutlined } from '@ant-design/icons';

const EndNode = memo(({ data, selected }: NodeProps) => {
  return (
    <div
      style={{
        padding: '8px 16px',
        borderRadius: 20,
        border: selected ? '2px solid #1677ff' : '2px solid #ff4d4f',
        background: '#fff2f0',
        minWidth: 80,
        textAlign: 'center',
        fontSize: 13,
        cursor: 'move',
      }}
    >
      <Handle type="target" position={Position.Top} style={{ width: 8, height: 8 }} />
      <StopOutlined style={{ color: '#ff4d4f', marginRight: 4 }} />
      <span>{(data as any).label || '结束'}</span>
    </div>
  );
});

EndNode.displayName = 'EndNode';
export default EndNode;
