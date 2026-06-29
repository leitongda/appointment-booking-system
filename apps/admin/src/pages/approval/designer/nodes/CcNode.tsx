import { memo } from 'react';
import { Handle, Position, type NodeProps } from '@xyflow/react';
import { MailOutlined } from '@ant-design/icons';
import './nodes.css';

const CcNode = memo(({ data, selected }: NodeProps) => {
  const d = data as any;
  return (
    <div className="rf-node rf-node--cc" data-selected={selected}>
      <Handle type="target" position={Position.Top} className="rf-handle" />
      <MailOutlined className="rf-node__icon" />
      <div className="rf-node__body">
        <span className="rf-node__label">{d.label || '抄送'}</span>
      </div>
      {(d.listeners?.length > 0) && (
        <div className="rf-node__listener-dot" title={`${d.listeners.length} 个监听器`} />
      )}
      <Handle type="source" position={Position.Bottom} className="rf-handle" />
    </div>
  );
});

CcNode.displayName = 'CcNode';
export default CcNode;
