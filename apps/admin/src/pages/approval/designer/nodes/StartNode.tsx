import { memo } from 'react';
import { Handle, Position, type NodeProps } from '@xyflow/react';
import { PlayCircleOutlined } from '@ant-design/icons';
import './nodes.css';

const StartNode = memo(({ data, selected }: NodeProps) => {
  return (
    <div className={`rf-node rf-node--start`} data-selected={selected}>
      <PlayCircleOutlined className="rf-node__icon" style={{ color: '#52c41a' }} />
      <span className="rf-node__label">{(data as any).label || '开始'}</span>
      <Handle type="source" position={Position.Bottom} className="rf-handle" />
    </div>
  );
});

StartNode.displayName = 'StartNode';
export default StartNode;
