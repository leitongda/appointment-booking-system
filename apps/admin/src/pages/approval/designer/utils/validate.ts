import type { Node, Edge } from '@xyflow/react';

export function validateFlow(nodes: Node[], edges: Edge[]): string[] {
  const errors: string[] = [];
  const nodeIds = new Set(nodes.map((n) => n.id));
  const outgoing: Record<string, Edge[]> = {};
  const incoming: Record<string, Edge[]> = {};
  nodes.forEach((n) => {
    outgoing[n.id] = [];
    incoming[n.id] = [];
  });

  // 1. 开始节点数量
  const startNodes = nodes.filter((n) => (n.data as any).nodeType === 'start');
  if (startNodes.length === 0) errors.push('缺少开始节点');
  else if (startNodes.length > 1) errors.push('只能有一个开始节点');

  // 2. 结束节点
  const endNodes = nodes.filter((n) => (n.data as any).nodeType === 'end');
  if (endNodes.length === 0) errors.push('缺少结束节点');

  // 3. 审批节点配置
  nodes.forEach((n) => {
    const d = n.data as any;
    if (d.nodeType === 'approval') {
      if (!d.assigneeType) errors.push(`审批节点 [${d.label}] 未配置审批人类型`);
    }
  });

  // 4. 条件节点
  nodes.forEach((n) => {
    const d = n.data as any;
    if (d.nodeType === 'condition') {
      if (!d.conditions || d.conditions.length === 0) errors.push(`条件节点 [${d.label}] 没有条件规则`);
    }
  });

  // 5. 连通性检查
  if (edges.length === 0) {
    errors.push('流程定义缺少连线');
  }

  edges.forEach((e) => {
    if (!nodeIds.has(e.source)) {
      errors.push(`连线的源节点 [${e.source}] 不存在`);
    }
    if (!nodeIds.has(e.target)) {
      errors.push(`连线的目标节点 [${e.target}] 不存在`);
    }
    if (outgoing[e.source]) outgoing[e.source].push(e);
    if (incoming[e.target]) incoming[e.target].push(e);
  });

  if (nodes.length > 0 && startNodes.length > 0) {
    const visited = new Set<string>();
    const queue = [startNodes[0].id];
    while (queue.length > 0) {
      const curr = queue.shift()!;
      if (visited.has(curr)) continue;
      visited.add(curr);
      for (const edge of outgoing[curr] || []) {
        const neighbor = edge.target;
        if (!visited.has(neighbor)) queue.push(neighbor);
      }
    }
    const unreachable = nodes.filter((n) => !visited.has(n.id));
    if (unreachable.length > 0) {
      errors.push(`存在不可达节点: ${unreachable.map((n) => (n.data as any).label).join(', ')}`);
    }
  }

  // 6. 图结构约束
  nodes.forEach((n) => {
    const d = n.data as any;
    const nodeOutgoing = outgoing[n.id] || [];
    const nodeIncoming = incoming[n.id] || [];

    if (d.nodeType !== 'start' && nodeIncoming.length === 0) {
      errors.push(`节点 [${d.label}] 没有入边`);
    }

    if (d.nodeType === 'end') {
      if (nodeOutgoing.length > 0) {
        errors.push(`结束节点 [${d.label}] 不允许有出边`);
      }
      return;
    }

    if (nodeOutgoing.length === 0) {
      errors.push(`节点 [${d.label}] 没有出边`);
    }

    if (d.nodeType === 'condition') {
      const defaultEdges = nodeOutgoing.filter((e) => e.sourceHandle === 'default');
      if (defaultEdges.length > 1) {
        errors.push(`条件节点 [${d.label}] 默认分支只能有一条`);
      }

      const conditionTargets = new Set<string>(
        (d.conditions || [])
          .map((condition: any) => condition.targetNodeKey || condition.target_node_key)
          .filter(Boolean),
      );
      const edgeTargets = new Set<string>(nodeOutgoing.map((e) => e.target));
      const missingTargets = [...conditionTargets].filter((target) => !edgeTargets.has(target));
      if (missingTargets.length > 0) {
        errors.push(`条件节点 [${d.label}] 的条件目标缺少连线: ${missingTargets.join(', ')}`);
      }
    } else if (nodeOutgoing.length > 1) {
      errors.push(`节点 [${d.label}] 存在多条出边，无法确定下一节点`);
    }
  });

  return errors;
}
