import type { Node, Edge } from '@xyflow/react';

export function validateFlow(nodes: Node[], edges: Edge[]): string[] {
  const errors: string[] = [];

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
  if (nodes.length > 0 && startNodes.length > 0) {
    const adj: Record<string, string[]> = {};
    nodes.forEach((n) => { adj[n.id] = []; });
    edges.forEach((e) => {
      if (adj[e.source]) adj[e.source].push(e.target);
    });
    const visited = new Set<string>();
    const queue = [startNodes[0].id];
    while (queue.length > 0) {
      const curr = queue.shift()!;
      if (visited.has(curr)) continue;
      visited.add(curr);
      for (const neighbor of adj[curr] || []) {
        if (!visited.has(neighbor)) queue.push(neighbor);
      }
    }
    const unreachable = nodes.filter((n) => !visited.has(n.id));
    if (unreachable.length > 0) {
      errors.push(`存在不可达节点: ${unreachable.map((n) => (n.data as any).label).join(', ')}`);
    }
  }

  return errors;
}
