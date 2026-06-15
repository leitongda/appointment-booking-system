import { memo } from 'react';
import { Handle, Position, type NodeProps } from '@xyflow/react';
import { PlayCircleOutlined } from '@ant-design/icons';

const StartNode = memo(({ data, selected }: NodeProps) => {
  return (
    <div
      style={{
        padding: '8px 16px',
        borderRadius: 20,
        border: selected ? '2px solid #1677ff' : '2px solid #52c41a',
        background: '#f6ffed',
        minWidth: 80,
        textAlign: 'center',
        fontSize: 13,
        cursor: 'move',
      }}
    >
      <PlayCircleOutlined style={{ color: '#52c41a', marginRight: 4 }} />
      <span>{(data as any).label || '开始'}</span>
      <Handle type="source" position={Position.Bottom} style={{ width: 8, height: 8 }} />
    </div>
  );
});

StartNode.displayName = 'StartNode';
export default StartNode;
