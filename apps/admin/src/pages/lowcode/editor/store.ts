/** 低代码编辑器状态管理 */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { LowCodeNode, LowCodeSchema, EventHandler, ApiDataSource, LowCodeTheme } from '@hospital/shared';

/** 页面状态变量定义 */
export interface StateVariable {
  type: string;
  defaultValue: any;
  label: string;
}

interface HistoryEntry {
  schema: LowCodeSchema;
  dataSources: ApiDataSource[];
  stateSchema: Record<string, StateVariable>;
}

interface EditorStore {
  /** 页面 Schema */
  schema: LowCodeSchema;
  /** 选中的节点 ID（首个） */
  selectedNodeId: string | null;
  /** 多选节点 ID 列表 */
  selectedNodeIds: string[];
  /** 历史记录 */
  history: HistoryEntry[];
  /** 当前历史索引 */
  historyIndex: number;
  /** 是否正在加载 */
  loading: boolean;
  /** 页面 ID */
  pageId: string | null;
  /** 上次保存时的 Schema 快照，用于判断是否有未保存更改 */
  savedSchema: LowCodeSchema;
  /** 页面级数据源列表 */
  dataSources: ApiDataSource[];
  /** 页面状态变量定义 */
  stateSchema: Record<string, StateVariable>;

  // --- Actions ---
  /** 设置 Schema */
  setSchema: (schema: LowCodeSchema) => void;
  /** 设置页面 ID */
  setPageId: (id: string | null) => void;
  /** 设置加载状态 */
  setLoading: (loading: boolean) => void;
  /** 选中节点 */
  selectNode: (nodeId: string | null) => void;
  /** 切换节点选中状态（多选） */
  toggleNodeSelect: (nodeId: string) => void;
  /** 全选所有节点 */
  selectAll: () => void;
  /** 清除所有选中 */
  clearSelection: () => void;
  /** 添加节点 */
  addNode: (node: LowCodeNode, parentId: string, index: number) => void;
  /** 在根级别添加节点 */
  addToRoot: (node: LowCodeNode, index: number) => void;
  /** 移动节点 */
  moveNode: (nodeId: string, newParentId: string, index: number) => void;
  /** 更新节点属性 */
  updateNodeProps: (nodeId: string, props: Record<string, any>) => void;
  /** 更新节点事件处理器 */
  updateNodeEvents: (nodeId: string, events: EventHandler[]) => void;
  /** 更新节点数据绑定 */
  updateNodeDataBinding: (nodeId: string, propName: string, expression: string | null) => void;
  /** 删除节点 */
  removeNode: (nodeId: string) => void;
  /** 添加数据源 */
  addDataSource: (ds: ApiDataSource) => void;
  /** 更新数据源 */
  updateDataSource: (id: string, updates: Partial<ApiDataSource>) => void;
  /** 删除数据源 */
  removeDataSource: (id: string) => void;
  /** 设置页面状态变量 */
  setStateSchema: (schema: Record<string, StateVariable>) => void;
  /** 设置节点绑定表达式 */
  updateNodeBinding: (nodeId: string, propName: string, expression: string) => void;
  /** 移除节点绑定 */
  removeNodeBinding: (nodeId: string, propName: string) => void;
  /** 撤销 */
  undo: () => void;
  /** 重做 */
  redo: () => void;
  /** 重置状态 */
  reset: () => void;
  /** 标记当前 Schema 为已保存 */
  markSaved: () => void;
  /** 更新页面主题配置 */
  updateTheme: (theme: LowCodeTheme) => void;
}

const MAX_HISTORY = 50;

const DEFAULT_SCHEMA: LowCodeSchema = {
  componentName: 'Page',
  props: {
    navigationBarTitleText: '新页面',
    navigationBarBackgroundColor: '#ffffff',
    navigationBarTextStyle: 'black',
  },
  children: [],
};

/** 递归查找节点的父节点 */
function findParent(
  nodes: LowCodeNode[],
  targetId: string,
): LowCodeNode | null {
  for (const node of nodes) {
    if (node.id === targetId) return null; // 根节点没有父节点
    if (node.children) {
      if (node.children.some((c) => c.id === targetId)) return node;
      const found = findParent(node.children, targetId);
      if (found) return found;
    }
  }
  return null;
}

/** 递归查找节点 */
function findNode(
  nodes: LowCodeNode[],
  targetId: string,
): LowCodeNode | null {
  for (const node of nodes) {
    if (node.id === targetId) return node;
    if (node.children) {
      const found = findNode(node.children, targetId);
      if (found) return found;
    }
  }
  return null;
}

/** 深拷贝 Schema */
function cloneSchema(schema: LowCodeSchema): LowCodeSchema {
  return JSON.parse(JSON.stringify(schema));
}

/** 递归添加节点 */
function addNodeRecursive(
  nodes: LowCodeNode[],
  parentId: string,
  node: LowCodeNode,
  index: number,
): LowCodeNode[] {
  return nodes.map((n) => {
    if (n.id === parentId) {
      const children = [...(n.children || [])];
      children.splice(index, 0, node);
      return { ...n, children };
    }
    if (n.children) {
      return {
        ...n,
        children: addNodeRecursive(n.children, parentId, node, index),
      };
    }
    return n;
  });
}

/** 递归移动节点 */
function moveNodeRecursive(
  nodes: LowCodeNode[],
  nodeId: string,
  newParentId: string,
  index: number,
): LowCodeNode[] {
  // 先找到并移除节点
  let movedNode: LowCodeNode | null = null;
  const removeNode = (ns: LowCodeNode[]): LowCodeNode[] =>
    ns
      .map((n) => {
        if (n.id === nodeId) {
          movedNode = n;
          return null;
        }
        if (n.children) {
          return { ...n, children: removeNode(n.children) };
        }
        return n;
      })
      .filter(Boolean) as LowCodeNode[];

  let tree = removeNode(nodes);
  if (!movedNode) return nodes;

  // 再添加到新位置
  tree = addNodeRecursive(tree, newParentId, movedNode, index);
  return tree;
}

/** 递归更新节点属性 */
function updateNodePropsRecursive(
  nodes: LowCodeNode[],
  nodeId: string,
  props: Record<string, any>,
): LowCodeNode[] {
  return nodes.map((n) => {
    if (n.id === nodeId) {
      return { ...n, props: { ...n.props, ...props } };
    }
    if (n.children) {
      return {
        ...n,
        children: updateNodePropsRecursive(n.children, nodeId, props),
      };
    }
    return n;
  });
}

/** 递归更新节点事件处理器 */
function updateNodeEventsRecursive(
  nodes: LowCodeNode[],
  nodeId: string,
  events: EventHandler[],
): LowCodeNode[] {
  return nodes.map((n) => {
    if (n.id === nodeId) {
      return { ...n, events };
    }
    if (n.children) {
      return {
        ...n,
        children: updateNodeEventsRecursive(n.children, nodeId, events),
      };
    }
    return n;
  });
}

/** 递归更新节点数据绑定 */
function updateNodeDataBindingRecursive(
  nodes: LowCodeNode[],
  nodeId: string,
  propName: string,
  expression: string | null,
): LowCodeNode[] {
  return nodes.map((n) => {
    if (n.id === nodeId) {
      const existingBindings = n.dataBinding?.bindings ?? {};
      let bindings: Record<string, string>;
      if (expression === null) {
        // 移除绑定
        const { [propName]: _removed, ...rest } = existingBindings;
        bindings = rest;
      } else {
        bindings = { ...existingBindings, [propName]: expression };
      }
      const hasBindings = Object.keys(bindings).length > 0;
      return {
        ...n,
        dataBinding: hasBindings ? { ...n.dataBinding, bindings } : undefined,
      };
    }
    if (n.children) {
      return {
        ...n,
        children: updateNodeDataBindingRecursive(n.children, nodeId, propName, expression),
      };
    }
    return n;
  });
}

/** 递归删除节点 */
function removeNodeRecursive(
  nodes: LowCodeNode[],
  nodeId: string,
): LowCodeNode[] {
  return nodes
    .map((n) => {
      if (n.id === nodeId) return null;
      if (n.children) {
        return {
          ...n,
          children: removeNodeRecursive(n.children, nodeId),
        };
      }
      return n;
    })
    .filter(Boolean) as LowCodeNode[];
}

/** 推送快照到历史记录 */
function pushHistory(
  get: () => EditorStore,
  set: (partial: Partial<EditorStore>) => void,
  overrides: Partial<Pick<EditorStore, 'schema' | 'dataSources' | 'stateSchema'>> = {},
) {
  const state = get();
  const snapshot: HistoryEntry = {
    schema: cloneSchema(overrides.schema ?? state.schema),
    dataSources: JSON.parse(JSON.stringify(overrides.dataSources ?? state.dataSources)),
    stateSchema: JSON.parse(JSON.stringify(overrides.stateSchema ?? state.stateSchema)),
  };
  const newHistory = state.history.slice(0, state.historyIndex + 1);
  newHistory.push(snapshot);
  if (newHistory.length > MAX_HISTORY) newHistory.shift();
  set({
    ...overrides,
    history: newHistory,
    historyIndex: newHistory.length - 1,
  });
}

export const useEditorStore = create<EditorStore>()(persist(
  (set, get) => ({
  schema: cloneSchema(DEFAULT_SCHEMA),
  selectedNodeId: null,
  selectedNodeIds: [],
  history: [{ schema: cloneSchema(DEFAULT_SCHEMA), dataSources: [], stateSchema: {} }],
  historyIndex: 0,
  loading: false,
  pageId: null,
  savedSchema: cloneSchema(DEFAULT_SCHEMA),
  dataSources: [],
  stateSchema: {},

  setSchema: (schema) => {
    pushHistory(get, set as any, { schema });
  },

  setPageId: (id) => set({ pageId: id }),

  setLoading: (loading) => set({ loading }),

  selectNode: (nodeId) => set({
    selectedNodeId: nodeId,
    selectedNodeIds: nodeId ? [nodeId] : [],
  }),

  toggleNodeSelect: (nodeId) => {
    const { selectedNodeIds } = get();
    const idx = selectedNodeIds.indexOf(nodeId);
    let nextIds: string[];
    if (idx >= 0) {
      nextIds = selectedNodeIds.filter((id) => id !== nodeId);
    } else {
      nextIds = [...selectedNodeIds, nodeId];
    }
    set({
      selectedNodeIds: nextIds,
      selectedNodeId: nextIds[0] ?? null,
    });
  },

  selectAll: () => {
    const { schema } = get();
    const allIds = collectAllNodeIds(schema.children ?? []);
    set({
      selectedNodeIds: allIds,
      selectedNodeId: allIds[0] ?? null,
    });
  },

  clearSelection: () => set({
    selectedNodeIds: [],
    selectedNodeId: null,
  }),

  addNode: (node, parentId, index) => {
    const { schema } = get();
    const newChildren = addNodeRecursive(schema.children, parentId, node, index);
    const newSchema = { ...schema, children: newChildren };
    get().setSchema(newSchema);
  },

  addToRoot: (node, index) => {
    const { schema } = get();
    const newChildren = [...schema.children];
    newChildren.splice(index, 0, node);
    const newSchema = { ...schema, children: newChildren };
    get().setSchema(newSchema);
  },

  moveNode: (nodeId, newParentId, index) => {
    const { schema } = get();
    const newChildren = moveNodeRecursive(schema.children, nodeId, newParentId, index);
    const newSchema = { ...schema, children: newChildren };
    get().setSchema(newSchema);
  },

  updateNodeProps: (nodeId, props) => {
    const { schema } = get();
    const newChildren = updateNodePropsRecursive(schema.children, nodeId, props);
    const newSchema = { ...schema, children: newChildren };
    get().setSchema(newSchema);
  },

  updateNodeEvents: (nodeId, events) => {
    const { schema } = get();
    const newChildren = updateNodeEventsRecursive(schema.children, nodeId, events);
    const newSchema = { ...schema, children: newChildren };
    get().setSchema(newSchema);
  },

  updateNodeDataBinding: (nodeId, propName, expression) => {
    const { schema } = get();
    const newChildren = updateNodeDataBindingRecursive(schema.children, nodeId, propName, expression);
    const newSchema = { ...schema, children: newChildren };
    get().setSchema(newSchema);
  },

  removeNode: (nodeId) => {
    const { schema, selectedNodeId, selectedNodeIds } = get();
    const newChildren = removeNodeRecursive(schema.children, nodeId);
    const newSchema = { ...schema, children: newChildren };
    // 通过 setSchema 统一处理历史记录
    get().setSchema(newSchema);
    // 如果删除的是选中节点，清除选中状态
    const updates: Partial<EditorStore> = {};
    if (selectedNodeId === nodeId) {
      updates.selectedNodeId = null;
    }
    if (selectedNodeIds.includes(nodeId)) {
      updates.selectedNodeIds = selectedNodeIds.filter((id) => id !== nodeId);
    }
    if (Object.keys(updates).length > 0) {
      set(updates);
    }
  },

  addDataSource: (ds) => {
    const next = [...get().dataSources, ds];
    pushHistory(get, set as any, { dataSources: next });
  },

  updateDataSource: (id, updates) => {
    const next = get().dataSources.map((ds) =>
      ds.id === id ? { ...ds, ...updates } : ds,
    );
    pushHistory(get, set as any, { dataSources: next });
  },

  removeDataSource: (id) => {
    const next = get().dataSources.filter((ds) => ds.id !== id);
    pushHistory(get, set as any, { dataSources: next });
  },

  setStateSchema: (schema) => {
    pushHistory(get, set as any, { stateSchema: schema });
  },

  updateNodeBinding: (nodeId, propName, expression) => {
    const { schema } = get();
    const newChildren = updateNodeDataBindingRecursive(schema.children, nodeId, propName, expression);
    const newSchema = { ...schema, children: newChildren };
    get().setSchema(newSchema);
  },

  removeNodeBinding: (nodeId, propName) => {
    const { schema } = get();
    const newChildren = updateNodeDataBindingRecursive(schema.children, nodeId, propName, null);
    const newSchema = { ...schema, children: newChildren };
    get().setSchema(newSchema);
  },

  undo: () => {
    const { historyIndex, history } = get();
    if (historyIndex > 0) {
      const newIndex = historyIndex - 1;
      const entry = history[newIndex];
      set({
        schema: cloneSchema(entry.schema),
        dataSources: JSON.parse(JSON.stringify(entry.dataSources)),
        stateSchema: JSON.parse(JSON.stringify(entry.stateSchema)),
        historyIndex: newIndex,
        selectedNodeId: null,
        selectedNodeIds: [],
      });
    }
  },

  redo: () => {
    const { historyIndex, history } = get();
    if (historyIndex < history.length - 1) {
      const newIndex = historyIndex + 1;
      const entry = history[newIndex];
      set({
        schema: cloneSchema(entry.schema),
        dataSources: JSON.parse(JSON.stringify(entry.dataSources)),
        stateSchema: JSON.parse(JSON.stringify(entry.stateSchema)),
        historyIndex: newIndex,
        selectedNodeId: null,
        selectedNodeIds: [],
      });
    }
  },

  reset: () =>
    set({
      schema: cloneSchema(DEFAULT_SCHEMA),
      selectedNodeId: null,
      selectedNodeIds: [],
      history: [{ schema: cloneSchema(DEFAULT_SCHEMA), dataSources: [], stateSchema: {} }],
      historyIndex: 0,
      loading: false,
      pageId: null,
      savedSchema: cloneSchema(DEFAULT_SCHEMA),
      dataSources: [],
      stateSchema: {},
    }),

  markSaved: () => {
    set({ savedSchema: cloneSchema(get().schema) });
  },

  updateTheme: (theme) => {
    const { schema } = get();
    const newSchema = { ...schema, theme };
    get().setSchema(newSchema);
  },
}),
{
  name: 'lowcode-editor',
  partialize: (state) => ({
    schema: state.schema,
    dataSources: state.dataSources,
    stateSchema: state.stateSchema,
    history: state.history.slice(-20), // 只持久化最近 20 条历史
    historyIndex: Math.min(state.historyIndex, 19),
  }),
},
));
