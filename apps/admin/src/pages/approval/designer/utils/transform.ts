import type { Node, Edge } from '@xyflow/react';

/** 后端 flowDef → React Flow nodes + edges */
export function fromFlowSchema(flowDef: any): { nodes: Node[]; edges: Edge[] } {
  const nodes: Node[] = (flowDef.nodes || []).map((n: any) => ({
    id: n.nodeKey,
    type: _nodeTypeMap(n.nodeType),
    position: { x: n.positionX ?? 0, y: n.positionY ?? 0 },
    data: {
      label: n.nodeName,
      nodeType: n.nodeType,
      nodeKey: n.nodeKey,
      approvalMode: n.approvalMode,
      assigneeType: n.assigneeType,
      assigneeConfig: n.assigneeConfig,
      timeoutHours: n.timeoutHours,
      timeoutAction: n.timeoutAction,
      conditions: n.conditions?.map((c: any) => ({
        targetNodeKey: c.targetNodeKey,
        fieldName: c.fieldName,
        operator: c.operator,
        value: c.value,
        priority: c.priority,
      })),
    },
  }));

  // 构建 nodeKey -> node 映射，用于条件边生成
  const nodeMap = new Map(nodes.map((n) => [n.id, n]));

  const edges: Edge[] = [];

  // 从后端 edges 生成边；条件节点的边使用 conditionEdge 类型并携带标签
  (flowDef.edges || []).forEach((e: any, i: number) => {
    const sourceNode = nodeMap.get(e.source);
    if (sourceNode && (sourceNode.data as any)?.nodeType === 'condition') {
      const isDefault = e.sourceHandle === 'default';
      const conditions = (sourceNode.data as any)?.conditions || [];
      let label = '';
      if (isDefault) {
        label = '默认';
      } else {
        const matched = conditions.find((c: any) => c.targetNodeKey === e.target);
        if (matched) {
          label = `${matched.fieldName} ${matched.operator} ${matched.value}`;
        }
      }
      edges.push({
        id: e.id || `edge-${i}`,
        source: e.source,
        target: e.target,
        sourceHandle: e.sourceHandle,
        targetHandle: e.targetHandle,
        type: 'conditionEdge',
        data: { label, isDefault },
      });
    } else {
      edges.push({
        id: e.id || `edge-${i}`,
        source: e.source,
        target: e.target,
        sourceHandle: e.sourceHandle,
        targetHandle: e.targetHandle,
        type: 'smoothstep',
      });
    }
  });

  return { nodes, edges };
}

/** React Flow nodes + edges → 后端 API 格式 */
export function toFlowSchema(nodes: Node[], edges: Edge[]): { nodes: any[]; edges: any[] } {
  const apiNodes = nodes.map((n, i) => ({
    nodeKey: n.id,
    nodeName: (n.data as any).label || n.id,
    nodeType: (n.data as any).nodeType,
    approvalMode: (n.data as any).approvalMode,
    assigneeType: (n.data as any).assigneeType,
    assigneeConfig: (n.data as any).assigneeConfig,
    timeoutHours: (n.data as any).timeoutHours,
    timeoutAction: (n.data as any).timeoutAction,
    sortOrder: i,
    positionX: n.position.x,
    positionY: n.position.y,
    conditions: (n.data as any).conditions || [],
  }));

  const apiEdges = edges.map((e) => ({
    id: e.id,
    source: e.source,
    target: e.target,
    sourceHandle: e.sourceHandle,
    targetHandle: e.targetHandle,
  }));

  return { nodes: apiNodes, edges: apiEdges };
}

function _nodeTypeMap(nodeType: string): string {
  const map: Record<string, string> = {
    start: 'startNode',
    approval: 'approvalNode',
    condition: 'conditionNode',
    cc: 'ccNode',
    end: 'endNode',
  };
  return map[nodeType] || 'approvalNode';
}
