import {describe, it, expect, beforeEach} from 'vitest';
import {useEditorStore} from '../store';
import type { ApiDataSource, EventHandler, LinkageRule, LowCodeSchema, LowCodeNode } from '@hospital/shared';

/** 测试用 Schema 树 */
const testSchema: LowCodeSchema = {
  componentName: 'Page',
  props: {},
  children: [
    { id: 'node-1', componentName: 'NutText', props: { text: 'Hello' }, children: [] },
    {
      id: 'node-2',
      componentName: 'NutView',
      props: {},
      children: [
        { id: 'node-3', componentName: 'NutButton', props: { text: 'Click' }, children: [] },
      ],
    },
  ],
};

/** 含多个同级子节点的 Schema */
const _multiChildSchema: LowCodeSchema = {
  componentName: 'Page',
  props: {},
  children: [
    { id: 'a', componentName: 'NutText', props: {}, children: [] },
    { id: 'b', componentName: 'NutText', props: {}, children: [] },
    { id: 'c', componentName: 'NutText', props: {}, children: [] },
  ],
};

/** 重置 store 到默认状态 */
function resetStore() {
  useEditorStore.setState({
    schema: { componentName: 'Page', props: {}, children: [] },
    selectedNodeId: null,
    selectedNodeIds: [],
    history: [{ schema: { componentName: 'Page', props: {}, children: [] }, dataSources: [], stateSchema: {} }],
    historyIndex: 0,
    loading: false,
    pageId: null,
    savedSchema: { componentName: 'Page', props: {}, children: [] },
    isDirty: false,
    dataSources: [],
    stateSchema: {},
  });
}

describe('useEditorStore', () => {
  beforeEach(() => {
    resetStore();
  });

  describe('setSchema', () => {
    it('should set the schema', () => {
      useEditorStore.getState().setSchema(testSchema);
      expect(useEditorStore.getState().schema).toEqual(testSchema);
    });

    it('should push to history', () => {
      useEditorStore.getState().setSchema(testSchema);
      const state = useEditorStore.getState();
      expect(state.history).toHaveLength(2);
      expect(state.historyIndex).toBe(1);
      expect(state.history[1].schema).toEqual(testSchema);
    });

    it('should truncate future history when setting schema after undo', () => {
      useEditorStore.getState().setSchema(testSchema);
      useEditorStore.getState().undo();

      const newSchema: LowCodeSchema = {
        componentName: 'Page',
        props: {},
        children: [{ id: 'node-new', componentName: 'NutText', props: { text: 'X' }, children: [] }],
      };
      useEditorStore.getState().setSchema(newSchema);

      const state = useEditorStore.getState();
      expect(state.history).toHaveLength(2);
      expect(state.historyIndex).toBe(1);
      expect(state.schema).toEqual(newSchema);
    });
  });

  describe('addNode', () => {
    it('should add a node to a parent with empty children', () => {
      useEditorStore.setState({ schema: testSchema });

      const newNode: LowCodeNode = { id: 'node-4', componentName: 'NutText', props: { text: 'World' }, children: [] };
      useEditorStore.getState().addNode(newNode, 'node-1', 0);

      const state = useEditorStore.getState();
      const parent = state.schema.children.find((c) => c.id === 'node-1');
      expect(parent).toBeDefined();
      expect(parent!.children).toHaveLength(1);
      expect(parent!.children![0].id).toBe('node-4');
      expect(parent!.children![0].props.text).toBe('World');
    });

    it('should add a node to a parent that already has children', () => {
      useEditorStore.setState({ schema: testSchema });

      const newNode: LowCodeNode = { id: 'node-4', componentName: 'NutText', props: {}, children: [] };
      useEditorStore.getState().addNode(newNode, 'node-2', 0);

      const state = useEditorStore.getState();
      const parent = state.schema.children.find((c) => c.id === 'node-2');
      expect(parent!.children).toHaveLength(2);
      expect(parent!.children![0].id).toBe('node-4');
      expect(parent!.children![1].id).toBe('node-3');
    });

    it('should insert at the beginning (index 0) of parent children', () => {
      useEditorStore.setState({ schema: testSchema });

      const newNode: LowCodeNode = { id: 'node-first', componentName: 'NutText', props: {}, children: [] };
      useEditorStore.getState().addNode(newNode, 'node-2', 0);

      const state = useEditorStore.getState();
      const parent = state.schema.children.find((c) => c.id === 'node-2');
      expect(parent!.children![0].id).toBe('node-first');
      expect(parent!.children![1].id).toBe('node-3');
    });

    it('should insert at the end (index = children.length) of parent children', () => {
      useEditorStore.setState({ schema: testSchema });

      const newNode: LowCodeNode = { id: 'node-last', componentName: 'NutText', props: {}, children: [] };
      useEditorStore.getState().addNode(newNode, 'node-2', 1);

      const state = useEditorStore.getState();
      const parent = state.schema.children.find((c) => c.id === 'node-2');
      expect(parent!.children).toHaveLength(2);
      expect(parent!.children![0].id).toBe('node-3');
      expect(parent!.children![1].id).toBe('node-last');
    });

    it('should insert at a middle index', () => {
      const schema3: LowCodeSchema = {
        componentName: 'Page',
        props: {},
        children: [
          { id: 'p', componentName: 'NutView', props: {}, children: [
            { id: 'c1', componentName: 'NutText', props: {}, children: [] },
            { id: 'c2', componentName: 'NutText', props: {}, children: [] },
            { id: 'c3', componentName: 'NutText', props: {}, children: [] },
          ]},
        ],
      };
      useEditorStore.setState({ schema: schema3 });

      const newNode: LowCodeNode = { id: 'c-mid', componentName: 'NutText', props: {}, children: [] };
      useEditorStore.getState().addNode(newNode, 'p', 1);

      const state = useEditorStore.getState();
      const parent = state.schema.children[0];
      expect(parent.children!.map((c) => c.id)).toEqual(['c1', 'c-mid', 'c2', 'c3']);
    });

    it('should push to history', () => {
      useEditorStore.setState({ schema: testSchema });

      const newNode: LowCodeNode = { id: 'node-4', componentName: 'NutText', props: {}, children: [] };
      useEditorStore.getState().addNode(newNode, 'node-1', 0);

      expect(useEditorStore.getState().historyIndex).toBeGreaterThan(0);
    });

    it('should add a node with its own children subtree', () => {
      useEditorStore.setState({ schema: testSchema });

      const subtree: LowCodeNode = {
        id: 'subtree',
        componentName: 'NutView',
        props: {},
        children: [
          { id: 'sub-child', componentName: 'NutText', props: { text: 'nested' }, children: [] },
        ],
      };
      useEditorStore.getState().addNode(subtree, 'node-1', 0);

      const state = useEditorStore.getState();
      const parent = state.schema.children.find((c) => c.id === 'node-1');
      expect(parent!.children).toHaveLength(1);
      expect(parent!.children![0].id).toBe('subtree');
      expect(parent!.children![0].children).toHaveLength(1);
      expect(parent!.children![0].children![0].id).toBe('sub-child');
    });

    it('should not mutate the original schema', () => {
      useEditorStore.setState({ schema: testSchema });
      const originalChildren = useEditorStore.getState().schema.children;

      const newNode: LowCodeNode = { id: 'node-mutate-test', componentName: 'NutText', props: {}, children: [] };
      useEditorStore.getState().addNode(newNode, 'node-1', 0);

      // Original reference should not be changed (setSchema clones)
      expect(originalChildren).toHaveLength(2);
      expect(useEditorStore.getState().schema.children).toHaveLength(2); // still 2 top-level
    });
  });

  describe('moveNode', () => {
    it('should move a node from one parent to another', () => {
      useEditorStore.setState({ schema: testSchema });

      useEditorStore.getState().moveNode('node-3', 'node-1', 0);

      const state = useEditorStore.getState();
      const sourceParent = state.schema.children.find((c) => c.id === 'node-2');
      const targetParent = state.schema.children.find((c) => c.id === 'node-1');

      expect(sourceParent!.children).toHaveLength(0);
      expect(targetParent!.children).toHaveLength(1);
      expect(targetParent!.children![0].id).toBe('node-3');
    });

    it('should preserve moved node data', () => {
      useEditorStore.setState({ schema: testSchema });

      useEditorStore.getState().moveNode('node-3', 'node-1', 0);

      const state = useEditorStore.getState();
      const movedNode = state.schema.children
        .find((c) => c.id === 'node-1')!
        .children![0];
      expect(movedNode.componentName).toBe('NutButton');
      expect(movedNode.props.text).toBe('Click');
    });

    it('should reorder within the same parent using a valid parent id', () => {
      const parentSchema: LowCodeSchema = {
        componentName: 'Page',
        props: {},
        children: [
          {
            id: 'container',
            componentName: 'NutView',
            props: {},
            children: [
              { id: 'x', componentName: 'NutText', props: {}, children: [] },
              { id: 'y', componentName: 'NutText', props: {}, children: [] },
              { id: 'z', componentName: 'NutText', props: {}, children: [] },
            ],
          },
        ],
      };
      useEditorStore.setState({ schema: parentSchema });

      // Move 'x' from index 0 to index 2 (end) within 'container'
      useEditorStore.getState().moveNode('x', 'container', 2);

      const state = useEditorStore.getState();
      const container = state.schema.children[0];
      expect(container.children!.map((c) => c.id)).toEqual(['y', 'z', 'x']);
    });

    it('should reorder within the same parent (move last to first)', () => {
      const parentSchema: LowCodeSchema = {
        componentName: 'Page',
        props: {},
        children: [
          {
            id: 'container',
            componentName: 'NutView',
            props: {},
            children: [
              { id: 'x', componentName: 'NutText', props: {}, children: [] },
              { id: 'y', componentName: 'NutText', props: {}, children: [] },
              { id: 'z', componentName: 'NutText', props: {}, children: [] },
            ],
          },
        ],
      };
      useEditorStore.setState({ schema: parentSchema });

      // Move 'z' from index 2 to index 0 (beginning) within 'container'
      useEditorStore.getState().moveNode('z', 'container', 0);

      const state = useEditorStore.getState();
      const container = state.schema.children[0];
      expect(container.children!.map((c) => c.id)).toEqual(['z', 'x', 'y']);
    });

    it('should preserve children of moved node', () => {
      const schema: LowCodeSchema = {
        componentName: 'Page',
        props: {},
        children: [
          { id: 'src', componentName: 'NutView', props: {}, children: [
            { id: 'movable', componentName: 'NutView', props: {}, children: [
              { id: 'grandchild', componentName: 'NutText', props: { text: 'deep' }, children: [] },
            ]},
          ]},
          { id: 'dst', componentName: 'NutView', props: {}, children: [] },
        ],
      };
      useEditorStore.setState({ schema });

      useEditorStore.getState().moveNode('movable', 'dst', 0);

      const state = useEditorStore.getState();
      const src = state.schema.children.find((c) => c.id === 'src');
      const dst = state.schema.children.find((c) => c.id === 'dst');

      expect(src!.children).toHaveLength(0);
      expect(dst!.children).toHaveLength(1);
      expect(dst!.children![0].id).toBe('movable');
      expect(dst!.children![0].children).toHaveLength(1);
      expect(dst!.children![0].children![0].id).toBe('grandchild');
    });

    it('should push to history', () => {
      useEditorStore.setState({ schema: testSchema });

      useEditorStore.getState().moveNode('node-3', 'node-1', 0);

      expect(useEditorStore.getState().historyIndex).toBeGreaterThan(0);
    });

    it('should not affect other nodes during move', () => {
      useEditorStore.setState({ schema: testSchema });

      useEditorStore.getState().moveNode('node-3', 'node-1', 0);

      const state = useEditorStore.getState();
      const node1 = state.schema.children.find((c) => c.id === 'node-1');
      expect(node1!.props).toEqual({ text: 'Hello' });
      expect(node1!.componentName).toBe('NutText');
    });
  });

  describe('updateNodeProps', () => {
    it('should update props of a specific node', () => {
      useEditorStore.setState({ schema: testSchema });

      useEditorStore.getState().updateNodeProps('node-1', { text: 'Updated', fontSize: 16 });

      const state = useEditorStore.getState();
      const node = state.schema.children.find((c) => c.id === 'node-1');
      expect(node!.props.text).toBe('Updated');
      expect(node!.props.fontSize).toBe(16);
    });

    it('should not affect other nodes', () => {
      useEditorStore.setState({ schema: testSchema });

      useEditorStore.getState().updateNodeProps('node-1', { text: 'Changed' });

      const state = useEditorStore.getState();
      const otherNode = state.schema.children.find((c) => c.id === 'node-2');
      expect(otherNode!.props).toEqual({});
    });

    it('should work on deeply nested nodes (2 levels)', () => {
      useEditorStore.setState({ schema: testSchema });

      useEditorStore.getState().updateNodeProps('node-3', { text: 'New Click' });

      const state = useEditorStore.getState();
      const nested = state.schema.children
        .find((c) => c.id === 'node-2')!
        .children!.find((c) => c.id === 'node-3');
      expect(nested!.props.text).toBe('New Click');
    });

    it('should work on 3+ levels deep nodes', () => {
      const deepSchema: LowCodeSchema = {
        componentName: 'Page',
        props: {},
        children: [
          {
            id: 'level1',
            componentName: 'NutView',
            props: {},
            children: [
              {
                id: 'level2',
                componentName: 'NutView',
                props: {},
                children: [
                  { id: 'level3', componentName: 'NutText', props: { text: 'deep' }, children: [] },
                ],
              },
            ],
          },
        ],
      };
      useEditorStore.setState({ schema: deepSchema });

      useEditorStore.getState().updateNodeProps('level3', { text: 'updated deep', color: 'red' });

      const state = useEditorStore.getState();
      const level3 = state.schema.children[0].children![0].children![0];
      expect(level3.id).toBe('level3');
      expect(level3.props.text).toBe('updated deep');
      expect(level3.props.color).toBe('red');
    });

    it('should merge props without removing existing ones', () => {
      useEditorStore.setState({ schema: testSchema });

      useEditorStore.getState().updateNodeProps('node-1', { color: 'blue' });

      const state = useEditorStore.getState();
      const node = state.schema.children.find((c) => c.id === 'node-1');
      expect(node!.props.text).toBe('Hello');
      expect(node!.props.color).toBe('blue');
    });

    it('should overwrite existing prop values', () => {
      useEditorStore.setState({ schema: testSchema });

      useEditorStore.getState().updateNodeProps('node-1', { text: 'Overwritten' });

      const state = useEditorStore.getState();
      const node = state.schema.children.find((c) => c.id === 'node-1');
      expect(node!.props.text).toBe('Overwritten');
    });

    it('should push to history', () => {
      useEditorStore.setState({ schema: testSchema });

      useEditorStore.getState().updateNodeProps('node-1', { text: 'X' });

      expect(useEditorStore.getState().historyIndex).toBeGreaterThan(0);
    });

    it('should not affect parent or sibling nodes', () => {
      useEditorStore.setState({ schema: testSchema });

      useEditorStore.getState().updateNodeProps('node-3', { text: 'Changed' });

      const state = useEditorStore.getState();
      const parent = state.schema.children.find((c) => c.id === 'node-2');
      expect(parent!.props).toEqual({});
      const sibling = state.schema.children.find((c) => c.id === 'node-1');
      expect(sibling!.props.text).toBe('Hello');
    });
  });

  describe('removeNode', () => {
    it('should remove a top-level node', () => {
      useEditorStore.setState({ schema: testSchema });

      useEditorStore.getState().removeNode('node-1');

      const state = useEditorStore.getState();
      expect(state.schema.children.find((c) => c.id === 'node-1')).toBeUndefined();
      expect(state.schema.children).toHaveLength(1);
    });

    it('should remove a deeply nested node', () => {
      useEditorStore.setState({ schema: testSchema });

      useEditorStore.getState().removeNode('node-3');

      const state = useEditorStore.getState();
      const parent = state.schema.children.find((c) => c.id === 'node-2');
      expect(parent!.children).toHaveLength(0);
    });

    it('should clear selection if the removed node was selected (top-level)', () => {
      useEditorStore.setState({ schema: testSchema, selectedNodeId: 'node-1' });

      useEditorStore.getState().removeNode('node-1');

      expect(useEditorStore.getState().selectedNodeId).toBeNull();
    });

    it('should clear selection when removing a deeply nested selected node', () => {
      useEditorStore.setState({ schema: testSchema, selectedNodeId: 'node-3' });

      useEditorStore.getState().removeNode('node-3');

      const state = useEditorStore.getState();
      expect(state.selectedNodeId).toBeNull();
      const parent = state.schema.children.find((c) => c.id === 'node-2');
      expect(parent!.children).toHaveLength(0);
    });

    it('should keep selection if a different node was selected', () => {
      useEditorStore.setState({ schema: testSchema, selectedNodeId: 'node-2' });

      useEditorStore.getState().removeNode('node-1');

      expect(useEditorStore.getState().selectedNodeId).toBe('node-2');
    });

    it('should keep selection when removing a node unrelated to the selected nested node', () => {
      useEditorStore.setState({ schema: testSchema, selectedNodeId: 'node-3' });

      useEditorStore.getState().removeNode('node-1');

      expect(useEditorStore.getState().selectedNodeId).toBe('node-3');
    });

    it('should not affect parent node properties when removing a child', () => {
      useEditorStore.setState({ schema: testSchema });

      useEditorStore.getState().removeNode('node-3');

      const state = useEditorStore.getState();
      const parent = state.schema.children.find((c) => c.id === 'node-2');
      expect(parent!.componentName).toBe('NutView');
      expect(parent!.props).toEqual({});
    });

    it('should push to history', () => {
      useEditorStore.setState({ schema: testSchema });

      useEditorStore.getState().removeNode('node-1');

      expect(useEditorStore.getState().historyIndex).toBeGreaterThan(0);
    });
  });

  describe('selectNode', () => {
    it('should set the selected node ID', () => {
      useEditorStore.getState().selectNode('node-1');
      expect(useEditorStore.getState().selectedNodeId).toBe('node-1');
      expect(useEditorStore.getState().selectedNodeIds).toEqual(['node-1']);
    });

    it('should clear selection when null is passed', () => {
      useEditorStore.setState({ selectedNodeId: 'node-1', selectedNodeIds: ['node-1'] });
      useEditorStore.getState().selectNode(null);
      expect(useEditorStore.getState().selectedNodeId).toBeNull();
      expect(useEditorStore.getState().selectedNodeIds).toEqual([]);
    });
  });

  describe('multi selection', () => {
    it('should toggle selected nodes and keep first selected as active', () => {
      useEditorStore.getState().toggleNodeSelect('node-1');
      useEditorStore.getState().toggleNodeSelect('node-2');

      expect(useEditorStore.getState().selectedNodeIds).toEqual(['node-1', 'node-2']);
      expect(useEditorStore.getState().selectedNodeId).toBe('node-1');

      useEditorStore.getState().toggleNodeSelect('node-1');

      expect(useEditorStore.getState().selectedNodeIds).toEqual(['node-2']);
      expect(useEditorStore.getState().selectedNodeId).toBe('node-2');
    });

    it('should select all nodes across nested schema levels', () => {
      useEditorStore.setState({ schema: testSchema });

      useEditorStore.getState().selectAll();

      expect(useEditorStore.getState().selectedNodeIds).toEqual(['node-1', 'node-2', 'node-3']);
      expect(useEditorStore.getState().selectedNodeId).toBe('node-1');
    });

    it('should clear all selected nodes', () => {
      useEditorStore.setState({ selectedNodeId: 'node-1', selectedNodeIds: ['node-1', 'node-2'] });

      useEditorStore.getState().clearSelection();

      expect(useEditorStore.getState().selectedNodeId).toBeNull();
      expect(useEditorStore.getState().selectedNodeIds).toEqual([]);
    });
  });

  describe('node events and data binding', () => {
    it('should update event handlers on a node', () => {
      useEditorStore.setState({ schema: testSchema });
      const events: EventHandler[] = [
        { event: 'onClick', actions: [{ type: 'showToast', payload: { message: 'ok' } }] },
      ];

      useEditorStore.getState().updateNodeEvents('node-3', events);

      const node = useEditorStore.getState().schema.children[1].children![0];
      expect(node.events).toEqual(events);
    });

    it('should add and merge node data bindings', () => {
      useEditorStore.setState({ schema: testSchema });

      useEditorStore.getState().updateNodeDataBinding('node-1', 'text', '{{state.title}}');
      useEditorStore.getState().updateNodeBinding('node-1', 'color', '{{state.color}}');

      const node = useEditorStore.getState().schema.children[0];
      expect(node.dataBinding?.bindings).toEqual({
        text: '{{state.title}}',
        color: '{{state.color}}',
      });
    });

    it('should remove one binding and clear dataBinding when the last binding is removed', () => {
      useEditorStore.setState({ schema: testSchema });
      useEditorStore.getState().updateNodeDataBinding('node-1', 'text', '{{state.title}}');
      useEditorStore.getState().updateNodeDataBinding('node-1', 'color', '{{state.color}}');

      useEditorStore.getState().removeNodeBinding('node-1', 'text');

      let node = useEditorStore.getState().schema.children[0];
      expect(node.dataBinding?.bindings).toEqual({ color: '{{state.color}}' });

      useEditorStore.getState().removeNodeBinding('node-1', 'color');

      node = useEditorStore.getState().schema.children[0];
      expect(node.dataBinding).toBeUndefined();
    });
  });

  describe('dataSources', () => {
    const apiSource: ApiDataSource = {
      id: 'users',
      name: '用户列表',
      type: 'api',
      method: 'GET',
      url: '/api/v1/users',
      dataPath: 'data.items',
    };

    it('should add, update and remove page data sources', () => {
      useEditorStore.getState().addDataSource(apiSource);
      expect(useEditorStore.getState().dataSources).toEqual([apiSource]);

      useEditorStore.getState().updateDataSource('users', {
        method: 'POST',
        params: { status: 1 },
      });

      expect(useEditorStore.getState().dataSources[0]).toMatchObject({
        id: 'users',
        method: 'POST',
        params: { status: 1 },
      });

      useEditorStore.getState().removeDataSource('users');
      expect(useEditorStore.getState().dataSources).toEqual([]);
    });

    it('should include data sources in undo and redo history', () => {
      useEditorStore.getState().addDataSource(apiSource);
      expect(useEditorStore.getState().dataSources).toHaveLength(1);

      useEditorStore.getState().undo();
      expect(useEditorStore.getState().dataSources).toEqual([]);

      useEditorStore.getState().redo();
      expect(useEditorStore.getState().dataSources).toEqual([apiSource]);
    });
  });

  describe('stateSchema', () => {
    it('should set state variables with parsed default values', () => {
      const schema = {
        title: { type: 'string', defaultValue: '首页', label: '标题' },
        count: { type: 'number', defaultValue: 0, label: '计数' },
        filters: { type: 'array', defaultValue: ['active'], label: '筛选条件' },
      };

      useEditorStore.getState().setStateSchema(schema);

      expect(useEditorStore.getState().stateSchema).toEqual(schema);
    });

    it('should include state variables in undo and redo history', () => {
      const schema = {
        visible: { type: 'boolean', defaultValue: true, label: '是否显示' },
      };

      useEditorStore.getState().setStateSchema(schema);
      expect(useEditorStore.getState().stateSchema).toEqual(schema);

      useEditorStore.getState().undo();
      expect(useEditorStore.getState().stateSchema).toEqual({});

      useEditorStore.getState().redo();
      expect(useEditorStore.getState().stateSchema).toEqual(schema);
    });
  });

  describe('linkage rules', () => {
    const rules: LinkageRule[] = [
      {
        id: 'rule-1',
        name: '选择套餐后设置价格',
        enabled: true,
        conditions: [{ sourceFieldId: 'node-3', operator: 'equals', value: 'vip' }],
        actions: [{ type: 'setValue', targetFieldId: 'node-1', value: '199' }],
      },
    ];

    it('should update linkage rules for a selected node', () => {
      useEditorStore.setState({ schema: testSchema });

      useEditorStore.getState().updateNodeLinkageRules('node-1', rules);

      expect(useEditorStore.getState().schema.children[0].linkageRules).toEqual(rules);
    });

    it('should ignore linkage rule updates without a target node id', () => {
      useEditorStore.setState({ schema: testSchema });

      useEditorStore.getState().updateNodeLinkageRules(null, rules);

      expect(useEditorStore.getState().schema).toEqual(testSchema);
      expect(useEditorStore.getState().historyIndex).toBe(0);
    });
  });

  describe('undo', () => {
    it('should revert to previous schema state', () => {
      useEditorStore.getState().setSchema(testSchema);
      useEditorStore.getState().undo();

      expect(useEditorStore.getState().schema).toEqual({ componentName: 'Page', props: {}, children: [] });
    });

    it('should update historyIndex', () => {
      useEditorStore.getState().setSchema(testSchema);
      useEditorStore.getState().undo();

      expect(useEditorStore.getState().historyIndex).toBe(0);
    });

    it('should clear selection', () => {
      useEditorStore.setState({ selectedNodeId: 'node-1' });
      useEditorStore.getState().setSchema(testSchema);
      useEditorStore.getState().undo();

      expect(useEditorStore.getState().selectedNodeId).toBeNull();
    });

    it('should not go below index 0', () => {
      useEditorStore.getState().undo();
      expect(useEditorStore.getState().historyIndex).toBe(0);
    });
  });

  describe('redo', () => {
    it('should advance to next schema state', () => {
      useEditorStore.getState().setSchema(testSchema);
      useEditorStore.getState().undo();
      useEditorStore.getState().redo();

      expect(useEditorStore.getState().schema).toEqual(testSchema);
    });

    it('should update historyIndex', () => {
      useEditorStore.getState().setSchema(testSchema);
      useEditorStore.getState().undo();
      useEditorStore.getState().redo();

      expect(useEditorStore.getState().historyIndex).toBe(1);
    });

    it('should clear selection', () => {
      useEditorStore.setState({ selectedNodeId: 'node-1' });
      useEditorStore.getState().setSchema(testSchema);
      useEditorStore.getState().undo();
      useEditorStore.getState().redo();

      expect(useEditorStore.getState().selectedNodeId).toBeNull();
    });

    it('should not go beyond history length', () => {
      useEditorStore.getState().redo();
      expect(useEditorStore.getState().historyIndex).toBe(0);
    });

    it('should work with multiple undo/redo cycles via setSchema', () => {
      const schema2: LowCodeSchema = {
        componentName: 'Page',
        props: {},
        children: [{ id: 'n2', componentName: 'NutText', props: {}, children: [] }],
      };
      const schema3: LowCodeSchema = {
        componentName: 'Page',
        props: {},
        children: [{ id: 'n3', componentName: 'NutText', props: {}, children: [] }],
      };

      useEditorStore.getState().setSchema(testSchema);
      useEditorStore.getState().setSchema(schema2);
      useEditorStore.getState().setSchema(schema3);

      useEditorStore.getState().undo();
      expect(useEditorStore.getState().schema).toEqual(schema2);

      useEditorStore.getState().undo();
      expect(useEditorStore.getState().schema).toEqual(testSchema);

      useEditorStore.getState().redo();
      expect(useEditorStore.getState().schema).toEqual(schema2);

      useEditorStore.getState().redo();
      expect(useEditorStore.getState().schema).toEqual(schema3);
    });

    it('should undo/redo across multiple operations (add, remove)', () => {
      useEditorStore.getState().setSchema(testSchema);

      // Operation 1: add a node to node-1
      useEditorStore.getState().addNode({ id: 'added', componentName: 'NutText', props: {}, children: [] }, 'node-1', 0);
      const node1AfterAdd = useEditorStore.getState().schema.children.find((c) => c.id === 'node-1');
      expect(node1AfterAdd!.children![0].id).toBe('added');

      // Operation 2: remove node-1
      useEditorStore.getState().removeNode('node-1');
      expect(useEditorStore.getState().schema.children.find((c) => c.id === 'node-1')).toBeUndefined();

      // Undo remove -> node-1 back with 'added' child
      useEditorStore.getState().undo();
      const node1Restored = useEditorStore.getState().schema.children.find((c) => c.id === 'node-1');
      expect(node1Restored).toBeDefined();

      // Undo add -> back to original testSchema (node-1 has empty children)
      useEditorStore.getState().undo();
      const node1Original = useEditorStore.getState().schema.children.find((c) => c.id === 'node-1');
      expect(node1Original).toBeDefined();
      expect(node1Original!.children).toHaveLength(0);

      // Redo add
      useEditorStore.getState().redo();
      const node1Redo = useEditorStore.getState().schema.children.find((c) => c.id === 'node-1');
      expect(node1Redo!.children![0].id).toBe('added');

      // Redo remove
      useEditorStore.getState().redo();
      expect(useEditorStore.getState().schema.children.find((c) => c.id === 'node-1')).toBeUndefined();
    });

    it('should replace the redo branch when making new changes after undo', () => {
      const s1: LowCodeSchema = {
        componentName: 'Page',
        props: {},
        children: [{ id: 's1', componentName: 'NutText', props: {}, children: [] }],
      };
      const s2: LowCodeSchema = {
        componentName: 'Page',
        props: {},
        children: [{ id: 's2', componentName: 'NutText', props: {}, children: [] }],
      };
      const s3: LowCodeSchema = {
        componentName: 'Page',
        props: {},
        children: [{ id: 's3', componentName: 'NutText', props: {}, children: [] }],
      };

      useEditorStore.getState().setSchema(s1);
      useEditorStore.getState().setSchema(s2);
      useEditorStore.getState().undo(); // back to s1
      useEditorStore.getState().setSchema(s3); // truncate s2 from history

      const state = useEditorStore.getState();
      expect(state.history).toHaveLength(3); // [default, s1, s3]
      expect(state.historyIndex).toBe(2);
      expect(state.schema).toEqual(s3);
    });

    it('should clear selection on every undo', () => {
      useEditorStore.getState().setSchema(testSchema);
      useEditorStore.setState({ selectedNodeId: 'node-1' });
      useEditorStore.getState().undo();
      expect(useEditorStore.getState().selectedNodeId).toBeNull();

      // Set again, undo again
      useEditorStore.getState().setSchema(testSchema);
      useEditorStore.setState({ selectedNodeId: 'node-2' });
      useEditorStore.getState().undo();
      expect(useEditorStore.getState().selectedNodeId).toBeNull();
    });

    it('should clear selection on every redo', () => {
      useEditorStore.getState().setSchema(testSchema);
      useEditorStore.getState().setSchema({ componentName: 'Page', props: {}, children: [{ id: 'x', componentName: 'NutText', props: {}, children: [] }] });
      useEditorStore.getState().undo();
      useEditorStore.setState({ selectedNodeId: 'x' });
      useEditorStore.getState().redo();
      expect(useEditorStore.getState().selectedNodeId).toBeNull();
    });
  });

  describe('history limit', () => {
    it('should cap history at MAX_HISTORY (30) entries', () => {
      for (let i = 0; i < 35; i++) {
        const s: LowCodeSchema = {
          componentName: 'Page',
          props: {},
          children: [{ id: `n-${i}`, componentName: 'NutText', props: { text: `${i}` }, children: [] }],
        };
        useEditorStore.getState().setSchema(s);
      }

      const state = useEditorStore.getState();
      expect(state.history.length).toBeLessThanOrEqual(30);
      expect(state.historyIndex).toBe(state.history.length - 1);
      expect(state.schema.children[0].id).toBe('n-34');
    });

    it('should drop the oldest entries when limit is exceeded', () => {
      // Push 29 entries (total = 30 including initial default)
      for (let i = 0; i < 29; i++) {
        const s: LowCodeSchema = {
          componentName: 'Page',
          props: {},
          children: [{ id: `n-${i}`, componentName: 'NutText', props: {}, children: [] }],
        };
        useEditorStore.getState().setSchema(s);
      }

      expect(useEditorStore.getState().history).toHaveLength(30);

      // Push one more -> drops the first entry (default with empty children)
      useEditorStore.getState().setSchema({
        componentName: 'Page',
        props: {},
        children: [{ id: 'n-overflow', componentName: 'NutText', props: {}, children: [] }],
      });

      const state = useEditorStore.getState();
      expect(state.history.length).toBe(30);
      // The oldest entry should now be n-0 (default was dropped)
      expect(state.history[0].schema.children[0].id).toBe('n-0');
    });

    it('should keep the most recent entry after exceeding limit', () => {
      for (let i = 0; i < 40; i++) {
        const s: LowCodeSchema = {
          componentName: 'Page',
          props: {},
          children: [{ id: `n-${i}`, componentName: 'NutText', props: {}, children: [] }],
        };
        useEditorStore.getState().setSchema(s);
      }

      const state = useEditorStore.getState();
      expect(state.schema.children[0].id).toBe('n-39');
      expect(state.historyIndex).toBe(state.history.length - 1);
    });
  });

  describe('reset', () => {
    it('should clear all state to defaults', () => {
      useEditorStore.setState({ loading: true, pageId: 'page-123', dataSources: [{ id: 'x', type: 'api', method: 'GET', url: '/x' }] });
      useEditorStore.getState().setSchema(testSchema);
      useEditorStore.getState().selectNode('node-1');
      useEditorStore.getState().setStateSchema({ title: { type: 'string', defaultValue: '', label: '标题' } });

      useEditorStore.getState().reset();

      const state = useEditorStore.getState();
      expect(state.schema.children).toEqual([]);
      expect(state.selectedNodeId).toBeNull();
      expect(state.history).toHaveLength(1);
      expect(state.historyIndex).toBe(0);
      expect(state.loading).toBe(false);
      expect(state.pageId).toBeNull();
      expect(state.isDirty).toBe(false);
      expect(state.dataSources).toEqual([]);
      expect(state.stateSchema).toEqual({});
    });

    it('should reset savedSchema to default', () => {
      useEditorStore.getState().setSchema(testSchema);
      useEditorStore.getState().markSaved();

      useEditorStore.getState().reset();

      expect(useEditorStore.getState().savedSchema.children).toEqual([]);
    });

    it('should mark current schema as saved and clear dirty state', () => {
      useEditorStore.getState().setSchema(testSchema);
      expect(useEditorStore.getState().isDirty).toBe(true);

      useEditorStore.getState().markSaved();

      expect(useEditorStore.getState().savedSchema).toEqual(testSchema);
      expect(useEditorStore.getState().isDirty).toBe(false);
    });
  });
});
