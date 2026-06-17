# 低代码平台功能补齐实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use compose:subagent (recommended) or compose:execute to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 增强低代码平台的核心能力，包括表达式引擎、联动规则、表单联动和状态变量管理。

**Architecture:** 在现有表达式引擎基础上扩展内置函数和运算符；新增联动规则引擎和可视化配置面板；补全状态变量编辑UI。

**Tech Stack:** TypeScript, React, Zustand, Vitest

---

## 文件结构

### 新增文件
| 文件 | 职责 |
|------|------|
| `packages/shared/src/utils/expression-engine.ts` | 扩展现有表达式引擎 |
| `apps/admin/src/pages/lowcode/editor/components/StateVariablePanel.tsx` | 状态变量编辑面板 |
| `apps/admin/src/pages/lowcode/editor/components/L linkageRules.tsx` | 联动规则配置面板 |
| `packages/shared/src/__tests__/expression-engine.test.ts` | 表达式引擎测试 |

### 修改文件
| 文件 | 变更 |
|------|------|
| `packages/shared/src/types/lowcode.ts` | 新增 LinkageRule 类型 |
| `apps/admin/src/pages/lowcode/editor/store.ts` | 新增联动规则状态管理 |
| `apps/admin/src/pages/lowcode/editor/components/PropertyPanel.tsx` | 集成联动规则Tab |
| `apps/admin/src/pages/lowcode/editor/components/LayerPanel.tsx` | 添加状态变量Tab入口 |
| `apps/patient-miniapp/src/components/LowCodeRenderer/data-manager.ts` | 支持联动规则执行 |

---

## Task 1: 表达式引擎增强 - 数组方法

**Covers:** 表达式引擎增强

**Files:**
- Modify: `packages/shared/src/utils/expression-engine.ts:480-498`
- Test: `packages/shared/src/__tests__/expression-engine.test.ts`

- [ ] **Step 1: 添加数组方法测试**

```typescript
// 在 expression-engine.test.ts 末尾添加
describe('Array methods', () => {
  it('map transforms array elements', () => {
    expect(eval_('items.map(x => x * 2)', { items: [1, 2, 3] })).toEqual([2, 4, 6]);
  });

  it('filter selects matching elements', () => {
    expect(eval_('items.filter(x => x > 2)', { items: [1, 2, 3, 4] })).toEqual([3, 4]);
  });

  it('reduce accumulates values', () => {
    expect(eval_('items.reduce((acc, x) => acc + x, 0)', { items: [1, 2, 3] })).toBe(6);
  });

  it('find returns first match', () => {
    expect(eval_('items.find(x => x > 2)', { items: [1, 2, 3] })).toBe(3);
  });

  it('some checks if any element matches', () => {
    expect(eval_('items.some(x => x > 2)', { items: [1, 2, 3] })).toBe(true);
  });

  it('every checks if all elements match', () => {
    expect(eval_('items.every(x => x > 0)', { items: [1, 2, 3] })).toBe(true);
  });

  it('sort orders elements', () => {
    expect(eval_('items.sort()', { items: [3, 1, 2] })).toEqual([1, 2, 3]);
  });

  it('flat flattens nested arrays', () => {
    expect(eval_('items.flat()', { items: [[1, 2], [3, 4]] })).toEqual([1, 2, 3, 4]);
  });
});
```

- [ ] **Step 2: 运行测试验证失败**

Run: `cd packages/shared && npx vitest run src/__tests__/expression-engine.test.ts`

- [ ] **Step 3: 实现数组方法**

在 `expression-engine.ts` 的 `BUILT_IN_FUNCTIONS` 中添加：

```typescript
// 数组方法 - 作为高阶函数返回
map: (arr: any[], fn: (item: any, index: number) => any) => arr.map(fn),
filter: (arr: any[], fn: (item: any, index: number) => boolean) => arr.filter(fn),
reduce: (arr: any[], fn: (acc: any, item: any, index: number) => any, init: any) => arr.reduce(fn, init),
find: (arr: any[], fn: (item: any, index: number) => boolean) => arr.find(fn),
some: (arr: any[], fn: (item: any, index: number) => boolean) => arr.some(fn),
every: (arr: any[], fn: (item: any, index: number) => boolean) => arr.every(fn),
sort: (arr: any[], fn?: (a: any, b: any) => number) => [...arr].sort(fn),
flat: (arr: any[], depth: number = 1) => arr.flat(depth),
```

- [ ] **Step 4: 运行测试验证通过**

- [ ] **Step 5: Commit**

```bash
git add packages/shared/src/utils/expression-engine.ts packages/shared/src/__tests__/expression-engine.test.ts
git commit -m "feat(lowcode): add array methods to expression engine"
```

---

## Task 2: 表达式引擎增强 - 字符串方法

**Covers:** 表达式引擎增强

**Files:**
- Modify: `packages/shared/src/utils/expression-engine.ts:480-498`
- Test: `packages/shared/src/__tests__/expression-engine.test.ts`

- [ ] **Step 1: 添加字符串方法测试**

```typescript
describe('String methods', () => {
  it('trim removes whitespace', () => {
    expect(eval_("' hello '.trim()")).toBe('hello');
  });

  it('upper converts to uppercase', () => {
    expect(eval_("'hello'.upper()")).toBe('HELLO');
  });

  it('lower converts to lowercase', () => {
    expect(eval_("'HELLO'.lower()")).toBe('hello');
  });

  it('split splits string', () => {
    expect(eval_("'a,b,c'.split(',')")).toEqual(['a', 'b', 'c']);
  });

  it('replace substitutes text', () => {
    expect(eval_("'hello world'.replace('world', 'there')")).toBe('hello there');
  });

  it('slice extracts substring', () => {
    expect(eval_("'hello'.slice(1, 4)")).toBe('ell');
  });
});
```

- [ ] **Step 2: 运行测试验证失败**

- [ ] **Step 3: 实现字符串方法**

```typescript
// 字符串方法
trim: (s: string) => s.trim(),
upper: (s: string) => s.toUpperCase(),
lower: (s: string) => s.toLowerCase(),
split: (s: string, sep: string) => s.split(sep),
replace: (s: string, search: string, replacement: string) => s.replace(search, replacement),
slice: (s: string, start: number, end?: number) => s.slice(start, end),
```

- [ ] **Step 4: 运行测试验证通过**

- [ ] **Step 5: Commit**

```bash
git commit -m "feat(lowcode): add string methods to expression engine"
```

---

## Task 3: 表达式引擎增强 - 数学函数

**Covers:** 表达式引擎增强

**Files:**
- Modify: `packages/shared/src/utils/expression-engine.ts:480-498`
- Test: `packages/shared/src/__tests__/expression-engine.test.ts`

- [ ] **Step 1: 添加数学函数测试**

```typescript
describe('Math functions', () => {
  it('min returns minimum value', () => {
    expect(eval_('min(3, 1, 2)')).toBe(1);
  });

  it('max returns maximum value', () => {
    expect(eval_('max(3, 1, 2)')).toBe(3);
  });

  it('round rounds to nearest integer', () => {
    expect(eval_('round(3.7)')).toBe(4);
  });

  it('abs returns absolute value', () => {
    expect(eval_('abs(-5)')).toBe(5);
  });

  it('floor rounds down', () => {
    expect(eval_('floor(3.7)')).toBe(3);
  });

  it('ceil rounds up', () => {
    expect(eval_('ceil(3.2)')).toBe(4);
  });
});
```

- [ ] **Step 2: 运行测试验证失败**

- [ ] **Step 3: 实现数学函数**

```typescript
// 数学函数
min: (...args: number[]) => Math.min(...args),
max: (...args: number[]) => Math.max(...args),
round: (n: number) => Math.round(n),
abs: (n: number) => Math.abs(n),
floor: (n: number) => Math.floor(n),
ceil: (n: number) => Math.ceil(n),
```

- [ ] **Step 4: 运行测试验证通过**

- [ ] **Step 5: Commit**

```bash
git commit -m "feat(lowcode): add math functions to expression engine"
```

---

## Task 4: 表达式引擎增强 - 空值合并和可选链

**Covers:** 表达式引擎增强

**Files:**
- Modify: `packages/shared/src/utils/expression-engine.ts` (Parser 和 Evaluator)
- Test: `packages/shared/src/__tests__/expression-engine.test.ts`

- [ ] **Step 1: 添加运算符测试**

```typescript
describe('Nullish coalescing and optional chaining', () => {
  it('?? returns right side if left is null/undefined', () => {
    expect(eval_('null ?? "default"')).toBe('default');
    expect(eval_('undefined ?? "default"')).toBe('default');
    expect(eval_('0 ?? "default"')).toBe(0);
    expect(eval_("'' ?? 'default'")).toBe('');
  });

  it('?. accesses property safely', () => {
    expect(eval_('obj?.name', { obj: { name: 'test' } })).toBe('test');
    expect(eval_('obj?.name', { obj: null })).toBeUndefined();
    expect(eval_('obj?.name', { obj: {} })).toBeUndefined();
  });

  it('?.[] accesses index safely', () => {
    expect(eval_('arr?.[0]', { arr: [1, 2, 3] })).toBe(1);
    expect(eval_('arr?.[0]', { arr: null })).toBeUndefined();
  });

  it('?.() calls method safely', () => {
    expect(eval_('obj?.toString()', { obj: 42 })).toBe('42');
    expect(eval_('obj?.toString()', { obj: null })).toBeUndefined();
  });
});
```

- [ ] **Step 2: 运行测试验证失败**

- [ ] **Step 3: 在 Parser 中添加新运算符**

需要修改 Parser 类：
1. 添加 `??` 为新 token 类型
2. 添加 `?.` 为可选链 token
3. 在 AST 节点类型中添加 `NullishCoalescing` 和 `OptionalChaining`

- [ ] **Step 4: 在 Evaluator 中实现**

```typescript
case 'NullishCoalescing': {
  const left = evaluate(node.left, ctx);
  return left ?? evaluate(node.right, ctx);
}
case 'OptionalChaining': {
  const obj = evaluate(node.object, ctx);
  if (obj == null) return undefined;
  return safeGet(obj, node.property);
}
```

- [ ] **Step 5: 运行测试验证通过**

- [ ] **Step 6: Commit**

```bash
git commit -m "feat(lowcode): add nullish coalescing and optional chaining operators"
```

---

## Task 5: 联动规则类型定义

**Covers:** 可视化联动规则面板, 表单联动值填充

**Files:**
- Modify: `packages/shared/src/types/lowcode.ts`

- [ ] **Step 1: 添加联动规则类型**

```typescript
// 在 lowcode.ts 末尾添加

/** 联动规则条件 */
export interface LinkageCondition {
  /** 源字段ID */
  sourceFieldId: string;
  /** 条件运算符 */
  operator: 'equals' | 'notEquals' | 'contains' | 'greaterThan' | 'lessThan' | 'isEmpty' | 'isNotEmpty';
  /** 比较值（可选，isEmpty/isNotEmpty 时不需要） */
  value?: any;
}

/** 联动规则动作 */
export interface LinkageAction {
  /** 动作类型 */
  type: 'setValue' | 'setVisible' | 'setDisabled' | 'setRequired' | 'setOptions';
  /** 目标字段ID */
  targetFieldId: string;
  /** 动作值（表达式或静态值） */
  value?: any;
}

/** 联动规则 */
export interface LinkageRule {
  /** 规则ID */
  id: string;
  /** 规则名称 */
  name: string;
  /** 条件列表（所有条件为 AND 关系） */
  conditions: LinkageCondition[];
  /** 动作列表（按顺序执行） */
  actions: LinkageAction[];
  /** 是否启用 */
  enabled: boolean;
}
```

- [ ] **Step 2: 在 LowCodeNode 中添加 linkageRules 字段**

```typescript
// 在 LowCodeNode 接口中添加
linkageRules?: LinkageRule[];
```

- [ ] **Step 3: Commit**

```bash
git commit -m "feat(lowcode): add linkage rule type definitions"
```

---

## Task 6: 状态变量编辑面板

**Covers:** 状态变量编辑面板

**Files:**
- Create: `apps/admin/src/pages/lowcode/editor/components/StateVariablePanel.tsx`
- Modify: `apps/admin/src/pages/lowcode/editor/components/LayerPanel.tsx`

- [ ] **Step 1: 创建 StateVariablePanel 组件**

```tsx
// apps/admin/src/pages/lowcode/editor/components/StateVariablePanel.tsx
import React, { useState } from 'react';
import { Button, Input, Select, Space, Card, Popconfirm, message } from 'antd';
import { PlusOutlined, DeleteOutlined, EditOutlined } from '@ant-design/icons';
import { useEditorStore } from '../store';

interface StateVariable {
  type: string;
  defaultValue: any;
  label: string;
}

const TYPE_OPTIONS = [
  { label: '字符串', value: 'string' },
  { label: '数字', value: 'number' },
  { label: '布尔', value: 'boolean' },
  { label: '数组', value: 'array' },
  { label: '对象', value: 'object' },
];

export const StateVariablePanel: React.FC = () => {
  const { stateSchema, setStateSchema } = useEditorStore();
  const [editingKey, setEditingKey] = useState<string | null>(null);
  const [newKey, setNewKey] = useState('');
  const [newLabel, setNewLabel] = useState('');
  const [newType, setNewType] = useState('string');
  const [newValue, setNewValue] = useState('');

  const variables = Object.entries(stateSchema || {});

  const handleAdd = () => {
    if (!newKey.trim()) {
      message.warning('请输入变量名');
      return;
    }
    if (stateSchema?.[newKey]) {
      message.warning('变量名已存在');
      return;
    }

    const parsedValue = parseValueByType(newValue, newType);
    setStateSchema({
      ...stateSchema,
      [newKey]: {
        type: newType,
        defaultValue: parsedValue,
        label: newLabel || newKey,
      },
    });
    setNewKey('');
    setNewLabel('');
    setNewValue('');
    message.success('添加成功');
  };

  const handleDelete = (key: string) => {
    const { [key]: _, ...rest } = stateSchema || {};
    setStateSchema(rest);
    message.success('删除成功');
  };

  const handleUpdate = (key: string, updates: Partial<StateVariable>) => {
    setStateSchema({
      ...stateSchema,
      [key]: {
        ...stateSchema![key],
        ...updates,
      },
    });
  };

  const parseValueByType = (value: string, type: string): any => {
    if (!value) {
      switch (type) {
        case 'string': return '';
        case 'number': return 0;
        case 'boolean': return false;
        case 'array': return [];
        case 'object': return {};
        default: return '';
      }
    }
    try {
      return JSON.parse(value);
    } catch {
      return value;
    }
  };

  return (
    <div style={{ padding: 12 }}>
      <div style={{ marginBottom: 12, fontWeight: 600 }}>状态变量</div>
      
      {/* 现有变量列表 */}
      {variables.map(([key, variable]) => (
        <Card key={key} size="small" style={{ marginBottom: 8 }}>
          {editingKey === key ? (
            <Space direction="vertical" style={{ width: '100%' }}>
              <Input
                size="small"
                placeholder="显示名称"
                value={variable.label}
                onChange={(e) => handleUpdate(key, { label: e.target.value })}
              />
              <Select
                size="small"
                style={{ width: '100%' }}
                value={variable.type}
                options={TYPE_OPTIONS}
                onChange={(v) => handleUpdate(key, { type: v })}
              />
              <Input
                size="small"
                placeholder="默认值 (JSON)"
                value={JSON.stringify(variable.defaultValue)}
                onChange={(e) => handleUpdate(key, { 
                  defaultValue: parseValueByType(e.target.value, variable.type) 
                })}
              />
              <Button size="small" onClick={() => setEditingKey(null)}>
                完成
              </Button>
            </Space>
          ) : (
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <div style={{ fontWeight: 500 }}>{variable.label || key}</div>
                <div style={{ fontSize: 12, color: '#999' }}>
                  {key} · {variable.type}
                </div>
              </div>
              <Space>
                <EditOutlined 
                  style={{ cursor: 'pointer' }} 
                  onClick={() => setEditingKey(key)} 
                />
                <Popconfirm title="确定删除？" onConfirm={() => handleDelete(key)}>
                  <DeleteOutlined style={{ cursor: 'pointer', color: '#ff4d4f' }} />
                </Popconfirm>
              </Space>
            </div>
          )}
        </Card>
      ))}

      {/* 添加新变量 */}
      <Card size="small" style={{ marginTop: 12, borderStyle: 'dashed' }}>
        <Space direction="vertical" style={{ width: '100%' }}>
          <Input
            size="small"
            placeholder="变量名 (英文)"
            value={newKey}
            onChange={(e) => setNewKey(e.target.value)}
          />
          <Input
            size="small"
            placeholder="显示名称"
            value={newLabel}
            onChange={(e) => setNewLabel(e.target.value)}
          />
          <Select
            size="small"
            style={{ width: '100%' }}
            value={newType}
            options={TYPE_OPTIONS}
            onChange={setNewType}
          />
          <Input
            size="small"
            placeholder="默认值 (JSON)"
            value={newValue}
            onChange={(e) => setNewValue(e.target.value)}
          />
          <Button
            type="primary"
            size="small"
            icon={<PlusOutlined />}
            onClick={handleAdd}
            block
          >
            添加变量
          </Button>
        </Space>
      </Card>
    </div>
  );
};
```

- [ ] **Step 2: 在 LayerPanel 中添加状态变量 Tab**

修改 `LayerPanel.tsx`，添加新的 Tab：

```tsx
// 在 LayerPanel.tsx 的 Tabs 组件中添加新 Tab
<Tabs.TabPane tab="状态变量" key="state">
  <StateVariablePanel />
</Tabs.TabPane>
```

- [ ] **Step 3: 运行开发服务器验证 UI**

Run: `pnpm dev:admin`

- [ ] **Step 4: Commit**

```bash
git commit -m "feat(lowcode): add state variable editor panel"
```

---

## Task 7: 联动规则配置面板

**Covers:** 可视化联动规则面板

**Files:**
- Create: `apps/admin/src/pages/lowcode/editor/components/LinkageRulesPanel.tsx`
- Modify: `apps/admin/src/pages/lowcode/editor/components/PropertyPanel.tsx`

- [ ] **Step 1: 创建 LinkageRulesPanel 组件**

```tsx
// apps/admin/src/pages/lowcode/editor/components/LinkageRulesPanel.tsx
import React, { useState } from 'react';
import { Button, Input, Select, Space, Card, Switch, Popconfirm, message } from 'antd';
import { PlusOutlined, DeleteOutlined } from '@ant-design/icons';
import { useEditorStore } from '../store';
import { LinkageRule, LinkageCondition, LinkageAction } from '@hospital/shared/types/lowcode';

const OPERATORS = [
  { label: '等于', value: 'equals' },
  { label: '不等于', value: 'notEquals' },
  { label: '包含', value: 'contains' },
  { label: '大于', value: 'greaterThan' },
  { label: '小于', value: 'lessThan' },
  { label: '为空', value: 'isEmpty' },
  { label: '不为空', value: 'isNotEmpty' },
];

const ACTION_TYPES = [
  { label: '设置值', value: 'setValue' },
  { label: '显示/隐藏', value: 'setVisible' },
  { label: '启用/禁用', value: 'setDisabled' },
  { label: '必填/非必填', value: 'setRequired' },
];

export const LinkageRulesPanel: React.FC = () => {
  const { selectedNodeId, schema, updateNodeLinkageRules } = useEditorStore();
  const [editingRuleId, setEditingRuleId] = useState<string | null>(null);

  // 获取当前选中节点的联动规则
  const selectedNode = findNodeById(schema?.children || [], selectedNodeId);
  const rules: LinkageRule[] = selectedNode?.linkageRules || [];

  // 获取页面中所有可绑定的字段节点
  const allFields = getAllFieldNodes(schema?.children || []);

  const handleAddRule = () => {
    const newRule: LinkageRule = {
      id: `rule_${Date.now()}`,
      name: `联动规则 ${rules.length + 1}`,
      conditions: [],
      actions: [],
      enabled: true,
    };
    updateNodeLinkageRules(selectedNodeId, [...rules, newRule]);
    setEditingRuleId(newRule.id);
  };

  const handleDeleteRule = (ruleId: string) => {
    updateNodeLinkageRules(
      selectedNodeId,
      rules.filter((r) => r.id !== ruleId)
    );
  };

  const handleToggleRule = (ruleId: string, enabled: boolean) => {
    updateNodeLinkageRules(
      selectedNodeId,
      rules.map((r) => (r.id === ruleId ? { ...r, enabled } : r))
    );
  };

  const handleUpdateCondition = (
    ruleId: string,
    condIndex: number,
    updates: Partial<LinkageCondition>
  ) => {
    updateNodeLinkageRules(
      selectedNodeId,
      rules.map((r) => {
        if (r.id !== ruleId) return r;
        const newConditions = [...r.conditions];
        newConditions[condIndex] = { ...newConditions[condIndex], ...updates };
        return { ...r, conditions: newConditions };
      })
    );
  };

  const handleAddCondition = (ruleId: string) => {
    updateNodeLinkageRules(
      selectedNodeId,
      rules.map((r) => {
        if (r.id !== ruleId) return r;
        return {
          ...r,
          conditions: [
            ...r.conditions,
            { sourceFieldId: '', operator: 'equals', value: '' },
          ],
        };
      })
    );
  };

  const handleUpdateAction = (
    ruleId: string,
    actionIndex: number,
    updates: Partial<LinkageAction>
  ) => {
    updateNodeLinkageRules(
      selectedNodeId,
      rules.map((r) => {
        if (r.id !== ruleId) return r;
        const newActions = [...r.actions];
        newActions[actionIndex] = { ...newActions[actionIndex], ...updates };
        return { ...r, actions: newActions };
      })
    );
  };

  const handleAddAction = (ruleId: string) => {
    updateNodeLinkageRules(
      selectedNodeId,
      rules.map((r) => {
        if (r.id !== ruleId) return r;
        return {
          ...r,
          actions: [
            ...r.actions,
            { type: 'setValue', targetFieldId: '', value: '' },
          ],
        };
      })
    );
  };

  if (!selectedNodeId) {
    return (
      <div style={{ padding: 12, color: '#999', textAlign: 'center' }}>
        请先选择一个组件
      </div>
    );
  }

  return (
    <div style={{ padding: 12 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 12 }}>
        <span style={{ fontWeight: 600 }}>联动规则</span>
        <Button size="small" icon={<PlusOutlined />} onClick={handleAddRule}>
          添加规则
        </Button>
      </div>

      {rules.length === 0 && (
        <div style={{ color: '#999', textAlign: 'center', padding: 20 }}>
          暂无联动规则
        </div>
      )}

      {rules.map((rule) => (
        <Card
          key={rule.id}
          size="small"
          style={{ marginBottom: 8 }}
          title={
            <Space>
              <Switch
                size="small"
                checked={rule.enabled}
                onChange={(v) => handleToggleRule(rule.id, v)}
              />
              <span>{rule.name}</span>
            </Space>
          }
          extra={
            <Popconfirm title="确定删除？" onConfirm={() => handleDeleteRule(rule.id)}>
              <DeleteOutlined style={{ cursor: 'pointer', color: '#ff4d4f' }} />
            </Popconfirm>
          }
        >
          {/* 条件配置 */}
          <div style={{ marginBottom: 8 }}>
            <div style={{ fontSize: 12, color: '#666', marginBottom: 4 }}>当</div>
            {rule.conditions.map((cond, i) => (
              <Space key={i} style={{ marginBottom: 4, display: 'flex' }}>
                <Select
                  size="small"
                  style={{ width: 120 }}
                  placeholder="字段"
                  value={cond.sourceFieldId || undefined}
                  options={allFields.map((f) => ({ label: f.label, value: f.id }))}
                  onChange={(v) => handleUpdateCondition(rule.id, i, { sourceFieldId: v })}
                />
                <Select
                  size="small"
                  style={{ width: 80 }}
                  value={cond.operator}
                  options={OPERATORS}
                  onChange={(v) => handleUpdateCondition(rule.id, i, { operator: v })}
                />
                {!['isEmpty', 'isNotEmpty'].includes(cond.operator) && (
                  <Input
                    size="small"
                    style={{ width: 80 }}
                    placeholder="值"
                    value={cond.value}
                    onChange={(e) => handleUpdateCondition(rule.id, i, { value: e.target.value })}
                  />
                )}
              </Space>
            ))}
            <Button size="small" type="link" onClick={() => handleAddCondition(rule.id)}>
              + 添加条件
            </Button>
          </div>

          {/* 动作配置 */}
          <div>
            <div style={{ fontSize: 12, color: '#666', marginBottom: 4 }}>则</div>
            {rule.actions.map((action, i) => (
              <Space key={i} style={{ marginBottom: 4, display: 'flex' }}>
                <Select
                  size="small"
                  style={{ width: 100 }}
                  value={action.type}
                  options={ACTION_TYPES}
                  onChange={(v) => handleUpdateAction(rule.id, i, { type: v })}
                />
                <Select
                  size="small"
                  style={{ width: 120 }}
                  placeholder="目标字段"
                  value={action.targetFieldId || undefined}
                  options={allFields.map((f) => ({ label: f.label, value: f.id }))}
                  onChange={(v) => handleUpdateAction(rule.id, i, { targetFieldId: v })}
                />
                {action.type === 'setValue' && (
                  <Input
                    size="small"
                    style={{ width: 80 }}
                    placeholder="值"
                    value={action.value}
                    onChange={(e) => handleUpdateAction(rule.id, i, { value: e.target.value })}
                  />
                )}
              </Space>
            ))}
            <Button size="small" type="link" onClick={() => handleAddAction(rule.id)}>
              + 添加动作
            </Button>
          </div>
        </Card>
      ))}
    </div>
  );
};

// 辅助函数
function findNodeById(nodes: any[], id: string | null): any {
  if (!id) return null;
  for (const node of nodes) {
    if (node.id === id) return node;
    if (node.children) {
      const found = findNodeById(node.children, id);
      if (found) return found;
    }
  }
  return null;
}

function getAllFieldNodes(nodes: any[]): { id: string; label: string }[] {
  const fields: { id: string; label: string }[] = [];
  const traverse = (items: any[]) => {
    for (const node of items) {
      if (node.componentName?.startsWith('Nut')) {
        fields.push({
          id: node.id,
          label: node.props?.placeholder || node.props?.text || node.componentName,
        });
      }
      if (node.children) traverse(node.children);
    }
  };
  traverse(nodes);
  return fields;
}
```

- [ ] **Step 2: 在 PropertyPanel 中集成**

在 PropertyPanel 中添加联动规则 Tab：

```tsx
import { LinkageRulesPanel } from './LinkageRulesPanel';

// 在 Tabs 组件中添加
<Tabs.TabPane tab="联动规则" key="linkage">
  <LinkageRulesPanel />
</Tabs.TabPane>
```

- [ ] **Step 3: 在 Store 中添加 updateNodeLinkageRules**

```typescript
// 在 store.ts 中添加
updateNodeLinkageRules: (nodeId: string | null, rules: LinkageRule[]) => {
  if (!nodeId) return;
  const newSchema = produce(get().schema, (draft) => {
    const node = findNodeInDraft(draft.children, nodeId);
    if (node) {
      node.linkageRules = rules;
    }
  });
  set({ schema: newSchema });
  get().pushHistory();
},
```

- [ ] **Step 4: 运行开发服务器验证 UI**

- [ ] **Step 5: Commit**

```bash
git commit -m "feat(lowcode): add linkage rules configuration panel"
```

---

## Task 8: 联动规则运行时执行

**Covers:** 可视化联动规则面板, 表单联动值填充

**Files:**
- Modify: `apps/patient-miniapp/src/components/LowCodeRenderer/data-manager.ts`

- [ ] **Step 1: 实现联动规则执行器**

```typescript
// 在 data-manager.ts 中添加

import { LinkageRule, LinkageCondition, LinkageAction } from '@hospital/shared/types/lowcode';

/** 评估联动规则条件 */
function evaluateLinkageCondition(
  condition: LinkageCondition,
  context: Record<string, any>
): boolean {
  const sourceValue = context[condition.sourceFieldId];
  
  switch (condition.operator) {
    case 'equals':
      return sourceValue === condition.value;
    case 'notEquals':
      return sourceValue !== condition.value;
    case 'contains':
      return String(sourceValue).includes(String(condition.value));
    case 'greaterThan':
      return Number(sourceValue) > Number(condition.value);
    case 'lessThan':
      return Number(sourceValue) < Number(condition.value);
    case 'isEmpty':
      return sourceValue == null || sourceValue === '';
    case 'isNotEmpty':
      return sourceValue != null && sourceValue !== '';
    default:
      return false;
  }
}

/** 执行联动规则动作 */
function executeLinkageAction(
  action: LinkageAction,
  context: Record<string, any>,
  updateContext: (updates: Record<string, any>) => void
): void {
  const updates: Record<string, any> = {};
  
  switch (action.type) {
    case 'setValue':
      updates[action.targetFieldId] = action.value;
      break;
    case 'setVisible':
      updates[`${action.targetFieldId}_visible`] = action.value === 'true' || action.value === true;
      break;
    case 'setDisabled':
      updates[`${action.targetFieldId}_disabled`] = action.value === 'true' || action.value === true;
      break;
    case 'setRequired':
      updates[`${action.targetFieldId}_required`] = action.value === 'true' || action.value === true;
      break;
  }
  
  updateContext(updates);
}

/** 执行节点的所有联动规则 */
export function executeLinkageRules(
  nodeId: string,
  rules: LinkageRule[],
  context: Record<string, any>,
  updateContext: (updates: Record<string, any>) => void
): void {
  for (const rule of rules) {
    if (!rule.enabled) continue;
    
    // 检查所有条件（AND 关系）
    const allConditionsMet = rule.conditions.every((cond) =>
      evaluateLinkageCondition(cond, context)
    );
    
    if (allConditionsMet) {
      // 执行所有动作
      for (const action of rule.actions) {
        executeLinkageAction(action, context, updateContext);
      }
    }
  }
}
```

- [ ] **Step 2: 在事件处理中集成联动规则**

```typescript
// 在处理 onChange 事件时调用联动规则
if (node.linkageRules?.length) {
  executeLinkageRules(node.id, node.linkageRules, currentState, updateState);
}
```

- [ ] **Step 3: 运行测试验证**

- [ ] **Step 4: Commit**

```bash
git commit -m "feat(lowcode): implement linkage rules runtime execution"
```

---

## Task 9: 端到端测试

**Covers:** 所有功能

**Files:**
- Test: `apps/admin/e2e/lowcode-features.spec.ts`

- [ ] **Step 1: 编写表达式引擎 E2E 测试**

```typescript
// apps/admin/e2e/lowcode-features.spec.ts
import { test, expect } from '@playwright/test';

test.describe('Lowcode Feature Enhancement', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/lowcode/editor/test-page');
  });

  test('expression engine supports array methods', async ({ page }) => {
    // 测试 map/filter 等数组方法
    const result = await page.evaluate(() => {
      const { evaluateExpression } = require('@hospital/shared/utils/expression-engine');
      return evaluateExpression('items.map(x => x * 2)', { items: [1, 2, 3] });
    });
    expect(result).toEqual([2, 4, 6]);
  });

  test('state variable panel adds variables', async ({ page }) => {
    // 点击状态变量 Tab
    await page.click('text=状态变量');
    
    // 填写变量信息
    await page.fill('input[placeholder="变量名"]', 'userName');
    await page.fill('input[placeholder="显示名称"]', '用户名');
    
    // 点击添加
    await page.click('button:has-text("添加变量")');
    
    // 验证添加成功
    await expect(page.locator('text=用户名')).toBeVisible();
  });

  test('linkage rules can be configured', async ({ page }) => {
    // 选择一个输入框组件
    await page.click('[data-testid="node-NutInput-1"]');
    
    // 切换到联动规则 Tab
    await page.click('text=联动规则');
    
    // 添加规则
    await page.click('button:has-text("添加规则")');
    
    // 验证规则卡片出现
    await expect(page.locator('text=联动规则 1')).toBeVisible();
  });
});
```

- [ ] **Step 2: 运行 E2E 测试**

Run: `pnpm test:e2e`

- [ ] **Step 3: Commit**

```bash
git commit -m "test(lowcode): add e2e tests for feature enhancements"
```

---

## 执行顺序

1. **Task 1-4**: 表达式引擎增强（相互独立，可并行）
2. **Task 5**: 类型定义（依赖 Task 1-4 的类型）
3. **Task 6**: 状态变量面板（独立）
4. **Task 7**: 联动规则面板（依赖 Task 5）
5. **Task 8**: 联动规则运行时（依赖 Task 7）
6. **Task 9**: E2E 测试（依赖所有功能完成）

---

## 注意事项

1. **表达式引擎**需要在沙箱中执行，避免安全风险
2. **联动规则**复用现有事件系统，不引入新的状态管理
3. **状态变量**的类型信息在运行时暂不强制校验，保持灵活性
4. **UI 组件**遵循现有 Ant Design 风格
