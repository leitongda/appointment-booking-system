import { memo } from 'react';
import { Handle, Position, type NodeProps } from '@xyflow/react';
import { StopOutlined } from '@ant-design/icons';
import './nodes.css';

const EndNode = memo(({ data, selected }: NodeProps) => {
  return (
    <div className={`rf-node rf-node--end`} data-selected={selected}>
      <Handle type="target" position={Position.Top} className="rf-handle" />
      <StopOutlined className="rf-node__icon" style={{ color: '#ff4d4f' }} />
      <span className="rf-node__label">{(data as any).label || '结束'}</span>
    </div>
  );
});

EndNode.displayName = 'EndNode';
export default EndNode;
