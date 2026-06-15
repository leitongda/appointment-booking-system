import { memo } from 'react';
import { Handle, Position, type NodeProps } from '@xyflow/react';
import { MailOutlined } from '@ant-design/icons';

const CcNode = memo(({ data, selected }: NodeProps) => {
  return (
    <div
      style={{
        padding: '8px 16px',
        borderRadius: 8,
        border: selected ? '2px solid #1677ff' : '2px solid #8c8c8c',
        background: '#fafafa',
        minWidth: 100,
        textAlign: 'center',
        fontSize: 13,
        cursor: 'move',
      }}
    >
      <Handle type="target" position={Position.Top} style={{ width: 8, height: 8 }} />
      <MailOutlined style={{ color: '#8c8c8c', marginRight: 4 }} />
      <span>{(data as any).label || '抄送'}</span>
      <Handle type="source" position={Position.Bottom} style={{ width: 8, height: 8 }} />
    </div>
  );
});

CcNode.displayName = 'CcNode';
export default CcNode;
