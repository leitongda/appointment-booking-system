import { memo } from 'react';
import { Card, Typography } from 'antd';
import {
  PlayCircleOutlined, AuditOutlined, BranchesOutlined,
  MailOutlined, StopOutlined,
} from '@ant-design/icons';
import type { CSSProperties } from 'react';
import './nodes/nodes.css';

const { Text } = Typography;

type NodeItem = {
  type: string;
  label: string;
  icon: React.ReactNode;
  accent: string;   // 主题色（图标 + 徽章底色来源）
  soft: string;     // 浅底色（rgba，徽章背景）
};

const NODE_ITEMS: NodeItem[] = [
  { type: 'startNode',     label: '开始', icon: <PlayCircleOutlined />, accent: 'var(--color-success)', soft: 'rgba(82,196,26,0.1)' },
  { type: 'approvalNode',  label: '审批', icon: <AuditOutlined />,     accent: 'var(--color-primary)', soft: 'rgba(22,119,255,0.1)' },
  { type: 'conditionNode', label: '条件', icon: <BranchesOutlined />,  accent: 'var(--color-evening)', soft: 'rgba(250,140,22,0.1)' },
  { type: 'ccNode',        label: '抄送', icon: <MailOutlined />,      accent: '#8c8c8c', soft: 'rgba(140,140,140,0.1)' },
  { type: 'endNode',       label: '结束', icon: <StopOutlined />,      accent: 'var(--color-error)', soft: 'rgba(255,77,79,0.1)' },
];

const NodePanel: React.FC = memo(() => {
  const onDragStart = (event: React.DragEvent, nodeType: string, label: string) => {
    event.dataTransfer.setData('application/reactflow', nodeType);
    event.dataTransfer.setData('application/label', label);
    event.dataTransfer.effectAllowed = 'move';
  };

  return (
    <Card size="small" title="节点" style={{ width: 200 }} styles={{ body: { padding: 8 } }}>
      {NODE_ITEMS.map((item) => {
        const itemStyle: CSSProperties = {
          // 注入主题色变量，供 hover 边框使用
          ['--np-accent' as any]: item.accent,
        };
        const badgeStyle: CSSProperties = {
          background: item.soft,
          color: item.accent,
        };

        return (
          <div
            key={item.type}
            className="np-item"
            style={itemStyle}
            draggable
            onDragStart={(e) => onDragStart(e, item.type, item.label)}
          >
            <span className="np-item__badge" style={badgeStyle}>
              {item.icon}
            </span>
            <Text className="np-item__label">{item.label}</Text>
          </div>
        );
      })}
    </Card>
  );
});

NodePanel.displayName = 'NodePanel';

export default NodePanel;
