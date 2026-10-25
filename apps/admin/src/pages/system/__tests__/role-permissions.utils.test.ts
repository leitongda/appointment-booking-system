/**
 * role-permissions.utils 单测（openspec 4.3）
 *
 * 覆盖权限分类的核心推导与树操作纯函数：
 * - inferPermissionControlType：显式 controlType 优先，其余按 深度/子节点/末段语义推断
 * - normalizePermissionsTree：模块传播与 descendantCodes 完整性
 * - filterPermissionsTree：关键词/类型/仅看已选三维过滤 + 祖先保留
 * - 计数函数与高风险判定
 */
import { describe, expect, it } from 'vitest';
import type { Permission } from '@hospital/api';
import {
  codesByControlTypes,
  collectPermissionCodes,
  countCoveredModules,
  countSelectedByControlType,
  countVisibleByControlType,
  filterPermissionsTree,
  getAllKeys,
  inferPermissionControlType,
  isHighRiskPermission,
  normalizePermissionsTree,
  type PermissionControlType,
  type PermissionViewNode,
} from '../role-permissions.utils';

const p = (code: string, name: string, overrides: Partial<Permission> = {}): Permission => ({
  id: code,
  code,
  name,
  type: 'button',
  sort: 0,
  ...overrides,
});

/** 两个模块的样例树：
 * doctor（页面）→ doctor:list（接口）、doctor:update（操作）
 * system（页面）→ system:role（tab）→ system:role:delete（高风险操作）
 */
const SAMPLE: Permission[] = [
  p('doctor', '医生管理', { type: 'menu', children: [p('doctor:list', '医生列表'), p('doctor:update', '编辑医生')] }),
  p('system', '系统设置', {
    type: 'menu',
    children: [
      p('system:role', '角色管理', {
        children: [p('system:role:delete', '删除角色'), p('system:role:list', '角色列表')],
      }),
    ],
  }),
];

describe('inferPermissionControlType', () => {
  it('explicit controlType wins over inference', () => {
    expect(inferPermissionControlType(p('x', 'X', { controlType: 'api' }), 0)).toBe('api');
  });

  it('depth 0 is page', () => {
    expect(inferPermissionControlType(p('doctor', '医生'), 0)).toBe('page');
  });

  it('node with children is tab', () => {
    expect(inferPermissionControlType(p('system:role', '角色', { children: [p('a', 'A')] }), 1)).toBe('tab');
  });

  it('action segment wins over api segment', () => {
    // 'create' 在 ACTION_SEGMENTS，即使语义像接口也判为操作
    expect(inferPermissionControlType(p('doctor:create', '新增'), 2)).toBe('action');
  });

  it('api segments are classified as api', () => {
    for (const code of ['doctor:list', 'report:export', 'audit:history']) {
      expect(inferPermissionControlType(p(code, code), 2)).toBe('api');
    }
  });

  it('depth 1 or menu type falls back to tab', () => {
    expect(inferPermissionControlType(p('doctor:profile', '资料', { type: 'menu' }), 1)).toBe('tab');
  });

  it('everything else defaults to action', () => {
    expect(inferPermissionControlType(p('doctor:remark', '备注'), 2)).toBe('action');
  });
});

describe('normalizePermissionsTree', () => {
  const tree = normalizePermissionsTree(SAMPLE);

  it('propagates module code/name to descendants', () => {
    const roleNode = tree[1].children![0];
    expect(roleNode.moduleCode).toBe('system');
    expect(roleNode.children![0].moduleCode).toBe('system');
    expect(tree[0].children![0].moduleCode).toBe('doctor');
  });

  it('descendantCodes include self and all children codes', () => {
    expect(tree[1].descendantCodes).toEqual(['system', 'system:role', 'system:role:delete', 'system:role:list']);
  });

  it('classifies sample tree as expected', () => {
    expect(tree[1].controlType).toBe('page');
    expect(tree[1].children![0].controlType).toBe('tab');
    expect(tree[1].children![0].children![0].controlType).toBe('action');
    expect(tree[0].children![0].controlType).toBe('api');
  });
});

describe('getAllKeys / collectPermissionCodes', () => {
  it('flatten full tree depth-first', () => {
    const expected = [
      'doctor', 'doctor:list', 'doctor:update',
      'system', 'system:role', 'system:role:delete', 'system:role:list',
    ];
    expect(getAllKeys(SAMPLE)).toEqual(expected);
    expect(collectPermissionCodes(normalizePermissionsTree(SAMPLE))).toEqual(expected);
  });
});

const viewNode = (code: string, controlType: PermissionControlType): PermissionViewNode =>
  // p() 的 children 是 Permission[]，与 ViewNode 的 children 协变不兼容，直接断言
  ({ ...p(code, code), depth: 2, moduleCode: 'x', moduleName: 'x', controlType, descendantCodes: [] }) as PermissionViewNode;

describe('filterPermissionsTree', () => {
  const tree = normalizePermissionsTree(SAMPLE);
  const noFilter = {
    keyword: '',
    controlTypes: ['page', 'tab', 'action', 'api'] as PermissionControlType[],
    checkedKeys: new Set<string>(),
    onlySelected: false,
  };

  it('keyword matches name (case-insensitive)', () => {
    const result = filterPermissionsTree(tree, { ...noFilter, keyword: '角色' });
    expect(getAllKeys(result)).toEqual(['system', 'system:role', 'system:role:delete', 'system:role:list']);
  });

  it('keyword matches code', () => {
    const result = filterPermissionsTree(tree, { ...noFilter, keyword: 'doctor:list' });
    expect(getAllKeys(result)).toEqual(['doctor', 'doctor:list']);
  });

  it('type filter keeps ancestors of matching descendants', () => {
    const result = filterPermissionsTree(tree, { ...noFilter, controlTypes: ['action'] });
    // 只剩 action 节点（doctor:update / system:role:delete），父级路径保留用于展示
    expect(getAllKeys(result)).toEqual(['doctor', 'doctor:update', 'system', 'system:role', 'system:role:delete']);
  });

  it('onlySelected keeps ancestors of selected descendants', () => {
    const result = filterPermissionsTree(tree, {
      ...noFilter,
      checkedKeys: new Set(['system:role:delete']),
      onlySelected: true,
    });
    expect(getAllKeys(result)).toEqual(['system', 'system:role', 'system:role:delete']);
  });

  it('recomputes descendantCodes after filtering', () => {
    const result = filterPermissionsTree(tree, { ...noFilter, checkedKeys: new Set(['doctor:update']), onlySelected: true });
    expect(result[0].descendantCodes).toEqual(['doctor', 'doctor:update']);
  });
});

describe('counting helpers', () => {
  const tree = normalizePermissionsTree(SAMPLE);

  it('countVisibleByControlType counts all nodes', () => {
    expect(countVisibleByControlType(tree)).toEqual({ page: 2, tab: 1, action: 2, api: 2 });
  });

  it('countSelectedByControlType counts only checked', () => {
    const summary = countSelectedByControlType(tree, new Set(['doctor', 'doctor:list', 'system:role:delete']));
    expect(summary).toEqual({ page: 1, tab: 0, action: 1, api: 1 });
  });

  it('countCoveredModules counts modules with any checked descendant', () => {
    expect(countCoveredModules(tree, new Set(['doctor:update']))).toBe(1);
    expect(countCoveredModules(tree, new Set(['system:role:delete', 'doctor:list']))).toBe(2);
    expect(countCoveredModules(tree, new Set())).toBe(0);
  });

  it('codesByControlTypes collects codes of the given types only', () => {
    expect(codesByControlTypes(tree, ['page', 'tab'])).toEqual(['doctor', 'system', 'system:role']);
    expect(codesByControlTypes(tree, ['action'])).toEqual(['doctor:update', 'system:role:delete']);
    expect(codesByControlTypes(tree, ['api'])).toEqual(['doctor:list', 'system:role:list']);
    expect(codesByControlTypes(tree, [])).toEqual([]);
  });
});

describe('isHighRiskPermission', () => {
  it('flags delete / refund / reset-password / permission / kick / status suffixes', () => {
    for (const code of ['system:role:delete', 'payment:refund', 'system:user:reset-password', 'system:role:permission', 'admin:kick', 'order:status']) {
      expect(isHighRiskPermission(viewNode(code, 'action'))).toBe(true);
    }
  });

  it('does not flag regular operations', () => {
    expect(isHighRiskPermission(viewNode('doctor:update', 'action'))).toBe(false);
  });
});
