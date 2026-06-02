# 低代码 Phase 2 研究报告：数据绑定 + 代码生成

> 研究日期: 2026-06-02
> 研究范围: 数据绑定架构、表达式引擎、代码生成方案、实施计划

---

## 一、数据绑定模块

### 1.1 行业方案研究

**amis (百度)** — 最成熟的数据源模型：
- 声明式 API 配置：`url`、`method`、`headers`、`data`（请求参数）、`dataField`（响应映射）
- `${variable}` 模板语法：所有 props 值支持 `${expression}` 插值
- Service 组件：执行 API 请求后将结果注入子组件数据域
- 数据作用域链：Page > Service > 子组件形成层级数据域

**Formily (阿里巴巴)** — 表单场景：
- JSON Schema 驱动，`x-reactions` 声明响应式联动
- `$self` / `$form` 上下文实现字段间联动
- 响应式字段管理，字段级独立更新

### 1.2 推荐方案：层级数据域 + 表达式引用

**变量作用域链：**
```
PageContext
  ├── pageParams      -- 路由参数
  ├── api.{id}        -- API 数据源结果
  ├── formData        -- 表单组件值
  └── {varName}       -- 用户自定义变量

ComponentContext (继承 PageContext)
  └── item / index    -- 循环渲染的当前项和索引
```

### 1.3 表达式引擎：分层设计

| 层次 | 语法 | 示例 | 引擎 |
|------|------|------|------|
| L0 字面量 | 静态值 | `"hello"`, `123` | 无需引擎 |
| L1 变量引用 | `${path}` | `${api.departments.items[0].name}` | 模板引擎 |
| L2 简单运算 | `${expr}` | `${formData.age >= 18}` | 模板引擎 |
| L3 函数/管道 | `${expr \| fn}` | `${items \| filter(name ~ keyword)}` | JSONata |

**推荐**：简单场景用 `${}` 模板语法（覆盖 80%），复杂场景用 JSONata（覆盖 20%）。

### 1.4 增强后的 LowCodeNode Schema

```typescript
/** API 数据源配置 */
export interface ApiDataSource {
  id: string;
  method: 'GET' | 'POST' | 'PUT' | 'DELETE';
  url: string;
  headers?: Record<string, string>;
  params?: Record<string, any>;
  dataPath?: string;
  pollingInterval?: number;
  manual?: boolean;
}

/** 事件处理器配置 */
export interface EventHandler {
  event: 'onClick' | 'onChange' | 'onSubmit' | 'onLoad';
  actions: EventAction[];
}

/** 事件动作 */
export interface EventAction {
  type: 'setData' | 'fetchApi' | 'navigate' | 'showToast' | 'updateVariable';
  payload: Record<string, any>;
}

/** 循环渲染配置 */
export interface LoopConfig {
  dataSource: string;
  itemName?: string;
  indexName?: string;
}

/** 增强后的 LowCodeNode */
export interface LowCodeNode {
  id: string;
  componentName: string;
  props: Record<string, any>;
  children?: LowCodeNode[];
  api?: ApiDataSource;
  dataBinding?: Record<string, string>;
  events?: EventHandler[];
  loop?: LoopConfig;
  visible?: string;
  dependOn?: string[];
}
```

### 1.5 运行时架构

```
Schema JSON → Parser → Runtime Engine → DataSource Manager
                                    ↓
                    Variable Store ← Expression Evaluator
                                    ↓
                              Renderer (Taro/React)
```

---

## 二、代码生成模块

### 2.1 核心结论

**无现成的 Schema-to-Taro 代码生成项目可复用**，需自建。

### 2.2 技术路线对比

| 维度 | 模板字符串 | AST 编程式 (Babel) |
|------|-----------|-------------------|
| 实现复杂度 | 低 | 中高 |
| 输出正确性 | 不保证 | 形式正确 |
| 格式控制 | 差 | 好 (@babel/generator) |
| 适用场景 | 简单页面 (< 5 组件) | 复杂页面 (任意嵌套) |

**推荐**：AST 编程式，理由：
- Schema 支持 10 层嵌套 + 条件/列表渲染
- Babel 生态成熟，`@babel/types` + `@babel/generator` 是事实标准

### 2.3 双模式输出架构

```
LowCodeNode Schema
        |
  +-----+-----+
  |           |
[Taro 源码]  [运行时渲染]
  |           |
Schema → Babel AST    Schema JSON 直接存储
→ @babel/generator    → LowCodeRenderer 解释
→ .tsx + .scss        → NutUI 组件树
  |
Taro 编译管线
→ WXML + WXSS + JS
```

### 2.4 Taro 源码生成示例

**输入 Schema：**
```json
{
  "componentName": "Page",
  "props": { "navigationBarTitleText": "预约挂号" },
  "children": [
    {
      "componentName": "NutCard",
      "props": { "title": "选择科室" },
      "children": [
        { "componentName": "NutText", "props": { "text": "${api.departments[0].name}" } }
      ]
    }
  ],
  "dataSources": [
    { "id": "departments", "url": "/api/departments", "method": "GET" }
  ]
}
```

**生成的 TSX：**
```tsx
import { View, Text } from '@tarojs/components';
import { Card } from '@tarojs/nutui-react-taro';
import { useState, useEffect } from 'react';
import { request } from '@tarojs/taro';

export default function DepartmentPage() {
  const [departments, setDepartments] = useState([]);

  useEffect(() => {
    request({ url: '/api/departments', method: 'GET' })
      .then((res) => setDepartments(res.data));
  }, []);

  return (
    <View className="page-department">
      <Card title="选择科室">
        <Text>{departments[0]?.name}</Text>
      </Card>
    </View>
  );
}
```

### 2.5 组件映射表

| Schema componentName | Taro 导入 | JSX 标签名 |
|---------------------|-----------|-----------|
| Page | @tarojs/components | View |
| NutText | @tarojs/components | Text |
| NutImage | @tarojs/components | Image |
| NutButton | @tarojs/components | Button |
| NutInput | @tarojs/components | Input |
| NutCell | @tarojs/nutui-react-taro | Cell |
| NutCard | @tarojs/nutui-react-taro | Card |
| NutSwiper | @tarojs/components | Swiper |
| NutRow/NutCol | @tarojs/components | View (flex) |

---

## 三、实施计划

### Sprint 1: 表达式引擎 + 类型定义 (1.5 周)

| 任务 | 文件 | 工作量 |
|------|------|--------|
| 表达式解析器 + 求值器 | `packages/shared/src/utils/expression-engine.ts` | 3d |
| 表达式引擎测试 | `packages/shared/src/__tests__/expression-engine.test.ts` | 1d |
| 增强 TypeScript 类型 | `packages/shared/src/types/lowcode.ts` | 1d |
| Schema 校验增强 | `apps/server/app/schemas/lowcode.py` | 1d |

### Sprint 2: 运行时数据管理器 (2 周)

| 任务 | 文件 | 工作量 |
|------|------|--------|
| `useDataManager` hook | `apps/patient-miniapp/src/components/LowCodeRenderer/data-manager.ts` | 3d |
| DataProvider context | `apps/patient-miniapp/src/components/LowCodeRenderer/DataProvider.tsx` | 2d |
| 增强 LowCodeRenderer | `apps/patient-miniapp/src/components/LowCodeRenderer/index.tsx` | 2d |
| 条件渲染支持 | 同上 | 1d |
| 列表渲染支持 | 同上 | 1d |
| 后端数据源测试端点 | `apps/server/app/modules/lowcode/router.py` | 1d |

### Sprint 3: 编辑器 UI 数据绑定 (2 周)

| 任务 | 文件 | 工作量 |
|------|------|--------|
| DataSourcePanel 组件 | `apps/admin/src/pages/lowcode/editor/components/DataSourcePanel.tsx` | 3d |
| EventConfig 组件 | `apps/admin/src/pages/lowcode/editor/components/EventConfig.tsx` | 2d |
| PropertyPanel 绑定 UI | `apps/admin/src/pages/lowcode/editor/components/PropertyPanel.tsx` | 2d |
| 编辑器 store 扩展 | `apps/admin/src/pages/lowcode/editor/store.ts` | 1d |
| ExpressionInput 组件 | `apps/admin/src/pages/lowcode/editor/components/ExpressionInput.tsx` | 1.5d |

### Sprint 4: Taro 代码生成器 (2.5 周)

| 任务 | 文件 | 工作量 |
|------|------|--------|
| Schema 分析器 | `packages/codegen/src/analyzer/schema-analyzer.ts` | 2d |
| 组件解析器 | `packages/codegen/src/analyzer/component-resolver.ts` | 1d |
| 数据流分析器 | `packages/codegen/src/analyzer/data-flow-analyzer.ts` | 2d |
| Taro 页面生成器 | `packages/codegen/src/generators/taro/page-generator.ts` | 3d |
| Taro 组件生成器 | `packages/codegen/src/generators/taro/component-generator.ts` | 2d |
| State + Hooks 生成器 | `packages/codegen/src/generators/taro/state-generator.ts` | 2d |
| Import 收集器 | `packages/codegen/src/generators/taro/import-generator.ts` | 1d |
| 样式生成器 | `packages/codegen/src/generators/taro/style-generator.ts` | 1d |
| Codegen 服务 (Python) | `apps/server/app/modules/lowcode/codegen_service.py` | 2d |

### Sprint 5: 原生生成器 + 集成 (1.5 周)

| 任务 | 文件 | 工作量 |
|------|------|--------|
| WXML 模板映射 | `packages/codegen/src/generators/native/wxml-generator.ts` | 2d |
| WXSS 样式生成器 | `packages/codegen/src/generators/native/wxss-generator.ts` | 1d |
| 页面 JS 逻辑生成器 | `packages/codegen/src/generators/native/js-generator.ts` | 2d |
| 下载端点 (tar.gz) | `apps/server/app/modules/lowcode/router.py` | 1d |
| 编辑器代码预览 Modal | `apps/admin/src/pages/lowcode/editor/components/CodePreviewModal.tsx` | 1.5d |

---

## 四、总工作量估算

| Sprint | 周期 | 累计 |
|--------|------|------|
| Sprint 1: 表达式引擎 + 类型 | 1.5 周 | 1.5 周 |
| Sprint 2: 运行时数据管理器 | 2 周 | 3.5 周 |
| Sprint 3: 编辑器 UI | 2 周 | 5.5 周 |
| Sprint 4: Taro 代码生成器 | 2.5 周 | 8 周 |
| Sprint 5: 原生生成器 + 集成 | 1.5 周 | 9.5 周 |
| **合计** | **~9.5 周 (1 人)** | |

2 人团队：~5.5 周（一人负责数据绑定运行时 + 编辑器，一人负责代码生成）

---

## 五、关键文件清单

### 新建文件 (36 个)

**共享类型和工具：**
- `packages/shared/src/utils/expression-engine.ts`
- `packages/shared/src/__tests__/expression-engine.test.ts`

**代码生成包：**
- `packages/codegen/` (完整包结构，24 个文件)

**编辑器 UI：**
- `apps/admin/src/pages/lowcode/editor/components/DataSourcePanel.tsx`
- `apps/admin/src/pages/lowcode/editor/components/EventConfig.tsx`
- `apps/admin/src/pages/lowcode/editor/components/ExpressionInput.tsx`
- `apps/admin/src/pages/lowcode/editor/components/CodePreviewModal.tsx`

**运行时：**
- `apps/patient-miniapp/src/components/LowCodeRenderer/data-manager.ts`
- `apps/patient-miniapp/src/components/LowCodeRenderer/DataProvider.tsx`

**后端：**
- `apps/server/app/modules/lowcode/codegen_service.py`

### 修改文件 (8 个)

- `packages/shared/src/types/lowcode.ts` — 增强类型定义
- `packages/api/src/modules/lowcode.ts` — 新增 API 方法
- `apps/server/app/schemas/lowcode.py` — Schema 校验增强
- `apps/server/app/modules/lowcode/router.py` — 新增端点
- `apps/server/app/modules/lowcode/service.py` — 新增方法
- `apps/admin/src/pages/lowcode/editor/store.ts` — 数据源管理
- `apps/admin/src/pages/lowcode/editor/components/PropertyPanel.tsx` — 绑定 UI
- `apps/patient-miniapp/src/components/LowCodeRenderer/index.tsx` — 运行时改造

---

*报告基于 amis (百度)、Formily (阿里)、lowcode-engine (阿里)、H5-Dooring 等开源项目研究及行业经验综合分析。*
