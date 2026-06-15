import { memo } from 'react';
import { Card, Typography } from 'antd';
import {
  PlayCircleOutlined, AuditOutlined, BranchesOutlined,
  MailOutlined, StopOutlined,
} from '@ant-design/icons';

const { Text } = Typography;

const NODE_ITEMS = [
  { type: 'startNode', label: '开始', icon: <PlayCircleOutlined style={{ color: '#52c41a' }} />, color: '#f6ffed', border: '#52c41a' },
  { type: 'approvalNode', label: '审批', icon: <AuditOutlined style={{ color: '#1677ff' }} />, color: '#e6f4ff', border: '#1677ff' },
  { type: 'conditionNode', label: '条件', icon: <BranchesOutlined style={{ color: '#fa8c16' }} />, color: '#fff7e6', border: '#fa8c16' },
  { type: 'ccNode', label: '抄送', icon: <MailOutlined style={{ color: '#8c8c8c' }} />, color: '#fafafa', border: '#8c8c8c' },
  { type: 'endNode', label: '结束', icon: <StopOutlined style={{ color: '#ff4d4f' }} />, color: '#fff2f0', border: '#ff4d4f' },
];

const NODE_TYPE_MAP: Record<string, string> = {
  startNode: 'start',
  approvalNode: 'approval',
  conditionNode: 'condition',
  ccNode: 'cc',
  endNode: 'end',
};

const NodePanel: React.FC = memo(() => {
  const onDragStart = (event: React.DragEvent, nodeType: string, label: string) => {
    event.dataTransfer.setData('application/reactflow', nodeType);
    event.dataTransfer.setData('application/label', label);
    event.dataTransfer.effectAllowed = 'move';
  };

  return (
    <Card size="small" title="节点" style={{ width: 180 }} styles={{ body: { padding: 8 } }}>
      {NODE_ITEMS.map((item) => (
        <div
          key={item.type}
          draggable
          onDragStart={(e) => onDragStart(e, item.type, item.label)}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            padding: '8px 12px',
            marginBottom: 4,
            borderRadius: 6,
            border: `1px solid ${item.border}`,
            background: item.color,
            cursor: 'grab',
            fontSize: 13,
            transition: 'box-shadow 0.2s',
          }}
          onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.boxShadow = '0 2px 8px rgba(0,0,0,0.15)'; }}
          onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.boxShadow = 'none'; }}
        >
          {item.icon}
          <Text>{item.label}</Text>
        </div>
      ))}
    </Card>
  );
});

NodePanel.displayName = 'NodePanel';

export default NodePanel;
