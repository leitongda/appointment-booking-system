/** 低代码编辑器 — 树操作工具函数 */

import type { LowCodeNode } from '@hospital/shared';

/**
 * 在节点数组中递归查找指定 ID 的节点。
 *
 * @param nodes  要搜索的节点数组
 * @param id     目标节点 ID
 * @returns 找到的节点，或 null
 */
export function findNodeById(
  nodes: LowCodeNode[],
  id: string,
): LowCodeNode | null {
  for (const node of nodes) {
    if (node.id === id) return node;
    if (node.children) {
      const found = findNodeById(node.children, id);
      if (found) return found;
    }
  }
  return null;
}

/**
 * 判断 descendantId 是否为 ancestorId 的（直接或间接）后代节点。
 *
 * @param nodes         根节点数组
 * @param ancestorId    祖先节点 ID
 * @param descendantId  待判断的后代节点 ID
 */
export function isDescendant(
  nodes: LowCodeNode[],
  ancestorId: string,
  descendantId: string,
): boolean {
  const ancestor = findNodeById(nodes, ancestorId);
  if (!ancestor) return false;
  return findNodeById(ancestor.children || [], descendantId) !== null;
}

/**
 * 查找指定子节点的父节点。
 *
 * @param nodes   根节点数组
 * @param childId 子节点 ID
 * @returns 父节点，或 null（根节点无父节点 / 未找到）
 */
export function findParentNode(
  nodes: LowCodeNode[],
  childId: string,
): LowCodeNode | null {
  for (const node of nodes) {
    if (node.children?.some((c) => c.id === childId)) return node;
    if (node.children) {
      const found = findParentNode(node.children, childId);
      if (found) return found;
    }
  }
  return null;
}

/**
 * 为节点及其子节点重新生成唯一 ID（用于复制粘贴、snippet 展开等场景）。
 *
 * @param node  原始节点
 * @returns 新 ID 的节点树副本
 */
export function regenerateIds(node: LowCodeNode): LowCodeNode {
  const newNode = {
    ...node,
    id: `node_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
    props: { ...node.props },
  };
  if (node.children) {
    newNode.children = node.children.map((child) => regenerateIds(child));
  }
  return newNode;
}
