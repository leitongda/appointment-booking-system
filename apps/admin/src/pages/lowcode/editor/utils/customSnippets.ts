/**
 * 自定义 Snippet 管理
 *
 * 支持用户将选中的组件树保存为自定义 snippet，存储在 localStorage 中。
 */

import type { LowCodeNode } from '@hospital/shared';
import { regenerateIds } from './tree';

const STORAGE_KEY = 'lowcode-custom-snippets';

/** 自定义 Snippet 定义 */
export interface CustomSnippet {
  /** 唯一标识 */
  id: string;
  /** 显示名称 */
  name: string;
  /** 创建时间 */
  createdAt: number;
  /** 组件树（存储时已深拷贝） */
  nodes: LowCodeNode[];
}

/** 最大自定义 snippet 数量 */
const MAX_CUSTOM_SNIPPETS = 50;

/** 生成唯一 ID */
function generateId(): string {
  return `snippet_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
}

/** 深拷贝节点（用于存储，避免引用问题） */
function cloneNodes(nodes: LowCodeNode[]): LowCodeNode[] {
  if (typeof structuredClone === 'function') {
    return structuredClone(nodes);
  }
  return JSON.parse(JSON.stringify(nodes));
}

/** 获取租户隔离的存储 key */
function getStorageKey(): string {
  try {
    const tenantId = localStorage.getItem('hospital_current_tenant_id') || 'default';
    return `${STORAGE_KEY}-${tenantId}`;
  } catch {
    return STORAGE_KEY;
  }
}

/** 加载所有自定义 snippet */
export function loadCustomSnippets(): CustomSnippet[] {
  try {
    const key = getStorageKey();
    const raw = localStorage.getItem(key);
    if (!raw) return [];
    return JSON.parse(raw) as CustomSnippet[];
  } catch {
    return [];
  }
}

/** 保存自定义 snippet */
export function saveCustomSnippet(name: string, nodes: LowCodeNode[]): CustomSnippet {
  const snippets = loadCustomSnippets();
  const newSnippet: CustomSnippet = {
    id: generateId(),
    name,
    createdAt: Date.now(),
    nodes: cloneNodes(nodes),
  };
  snippets.unshift(newSnippet); // 新的放在前面

  // 超出上限时删除最旧的
  if (snippets.length > MAX_CUSTOM_SNIPPETS) {
    snippets.splice(MAX_CUSTOM_SNIPPETS);
  }

  try {
    const key = getStorageKey();
    localStorage.setItem(key, JSON.stringify(snippets));
  } catch (e) {
    console.error('保存自定义 snippet 失败:', e);
  }

  return newSnippet;
}

/** 删除自定义 snippet */
export function deleteCustomSnippet(id: string): void {
  const snippets = loadCustomSnippets().filter((s) => s.id !== id);
  try {
    const key = getStorageKey();
    localStorage.setItem(key, JSON.stringify(snippets));
  } catch (e) {
    console.error('删除自定义 snippet 失败:', e);
  }
}

/** 展开 snippet 为新的节点树（重新生成 ID） */
export function expandCustomSnippet(snippet: CustomSnippet): LowCodeNode[] {
  return snippet.nodes.map((node) => regenerateIds(node));
}

/** 重命名自定义 snippet */
export function renameCustomSnippet(id: string, newName: string): void {
  const snippets = loadCustomSnippets();
  const snippet = snippets.find((s) => s.id === id);
  if (snippet) {
    snippet.name = newName;
    try {
      const key = getStorageKey();
      localStorage.setItem(key, JSON.stringify(snippets));
    } catch (e) {
      console.error('重命名自定义 snippet 失败:', e);
    }
  }
}
