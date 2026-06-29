/**
 * 只读审批流程图查看器
 *
 * 复用设计器的节点组件与 fromFlowSchema 转换逻辑，
 * 支持定义查看模式与实例审批进度模式（节点状态高亮）。
 * Hover 节点显示浮动 Tooltip，点击节点弹出抽屉查看详情。
 */
import { useCallback, useMemo, useState, useRef, useEffect } from 'react';
import {
  ReactFlow,
  ReactFlowProvider,
  Controls,
  MiniMap,
  Background,
  BackgroundVariant,
  type Node,
  type Edge,
  type NodeTypes,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { Drawer } from 'antd';
import { StartNode, ApprovalNode, ConditionNode, CcNode, EndNode } from '@/pages/approval/designer/nodes';
import { ConditionEdge } from '@/pages/approval/designer/edges';
import { fromFlowSchema } from '@/pages/approval/designer/utils/transform';
import NodeDetailContent from './NodeDetailContent';
import NodeTooltip from './NodeTooltip';

// ─── 类型 ──────────────────────────────────────────────
export type NodeStatus = 'completed' | 'current' | 'rejected' | 'skipped' | 'pending';

export interface FlowChartViewerProps {
  flowDefinition: any;          // 流程定义数据（含 nodes、edges）
  nodeStatuses?: Map<string, NodeStatus>;  // 实例模式下各节点的审批状态
  mode?: 'definition' | 'instance';
  height?: number;
  /** 实例模式下各节点的审批记录，点击节点时传递给抽屉展示 */
  instanceRecords?: Map<string, any[]>;
}

// ─── 只读节点类型（复用设计器节点 + 状态 class） ──────
const nodeTypes: NodeTypes = {
  startNode: StartNode,
  approvalNode: ApprovalNode,
  conditionNode: ConditionNode,
  ccNode: CcNode,
  endNode: EndNode,
};

const edgeTypes = {
  conditionEdge: ConditionEdge,
};

// ─── 内部组件 ──────────────────────────────────────────
const FlowChartInner: React.FC<FlowChartViewerProps & { onReady?: (fitView: () => void) => void }> = ({
  flowDefinition,
  nodeStatuses,
  instanceRecords,
  mode = 'definition',
  height = 480,
  onReady,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [tooltip, setTooltip] = useState<{ visible: boolean; x: number; y: number; data: any }>({
    visible: false,
    x: 0,
    y: 0,
    data: null,
  });
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [drawerData, setDrawerData] = useState<any>(null);

  // 转换流程定义数据 → ReactFlow 格式
  const { nodes: rawNodes, edges } = useMemo(() => {
    if (!flowDefinition) return { nodes: [] as Node[], edges: [] as Edge[] };
    const result = fromFlowSchema(flowDefinition);
    return result;
  }, [flowDefinition]);

  // 为节点注入 status class（实例模式）
  const nodes: Node[] = useMemo(() => {
    return rawNodes.map((n) => {
      const status: NodeStatus | undefined = nodeStatuses?.get(n.id);
      const className = [n.className || ''];
      if (status) className.push(`rf-node-status--${status}`);
      return { ...n, className: className.filter(Boolean).join(' ') };
    });
  }, [rawNodes, nodeStatuses]);

  // fitView
  useEffect(() => {
    onReady?.(() => {});
  }, []);

  // Tooltip: hover
  const handleNodeMouseEnter = useCallback((_event: React.MouseEvent, node: Node) => {
    const rect = containerRef.current?.getBoundingClientRect();
    if (!rect) return;
    setTooltip({
      visible: true,
      x: _event.clientX - rect.left + 12,
      y: _event.clientY - rect.top - 8,
      data: node.data,
    });
  }, []);

  const handleNodeMouseMove = useCallback((_event: React.MouseEvent, _node: Node) => {
    const rect = containerRef.current?.getBoundingClientRect();
    if (!rect) return;
    setTooltip((prev) => ({
      ...prev,
      x: _event.clientX - rect.left + 12,
      y: _event.clientY - rect.top - 8,
    }));
  }, []);

  const handleNodeMouseLeave = useCallback(() => {
    setTooltip((prev) => ({ ...prev, visible: false }));
  }, []);

  // 节点点击 → 打开详情抽屉
  const handleNodeClick = useCallback((_event: React.MouseEvent, node: Node) => {
    const d = node.data as any;
    const status: NodeStatus | undefined = nodeStatuses?.get(node.id);
    const records = instanceRecords?.get(node.id);
    setDrawerData({ ...d, nodeKey: node.id, status: status || null, records: records || null });
    setDrawerOpen(true);
  }, [nodeStatuses, instanceRecords]);

  return (
    <div ref={containerRef} style={{ position: 'relative', height, width: '100%' }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        nodesDraggable={false}
        nodesConnectable={false}
        elementsSelectable={false}
        panOnScroll
        zoomOnScroll
        preventScrolling={false}
        onNodeMouseEnter={handleNodeMouseEnter}
        onNodeMouseMove={handleNodeMouseMove}
        onNodeMouseLeave={handleNodeMouseLeave}
        onNodeClick={handleNodeClick}
        defaultEdgeOptions={{ type: 'smoothstep' }}
      >
        <Controls showInteractive={false} />
        <MiniMap zoomable pannable />
        <Background variant={BackgroundVariant.Dots} gap={16} size={1} />
      </ReactFlow>

      {/* 浮动 Tooltip */}
      <NodeTooltip
        visible={tooltip.visible}
        x={tooltip.x}
        y={tooltip.y}
        data={tooltip.data}
      />

      {/* 节点详情抽屉 */}
      <Drawer
        title={
          drawerData
            ? `${drawerData.label || drawerData.nodeName || '节点'} 详情`
            : '节点详情'
        }
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        width={400}
        destroyOnClose
        getContainer={false}
        mask={false}
        styles={{ wrapper: { position: 'absolute' }, body: { padding: '16px 0' } }}
      >
        {drawerData && (
          <NodeDetailContent data={drawerData} mode={mode} />
        )}
      </Drawer>
    </div>
  );
};

// ─── 导出（带 Provider） ───────────────────────────────

const FlowChartViewer: React.FC<FlowChartViewerProps> = (props) => (
  <ReactFlowProvider>
    <FlowChartInner {...props} />
  </ReactFlowProvider>
);

export default FlowChartViewer;
