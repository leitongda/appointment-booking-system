# 低代码平台 — 小程序生成优先级计划

## 短期目标

让低代码编辑器搭建的页面能够成功生成可运行的微信小程序代码。

## Top 10 高优先级事项

### #1 [P0-阻塞] 修复 codegen 包构建脚本

**问题**: `packages/codegen/package.json` 没有 `build` 脚本，`dist/index.js` 不存在，`codegen_service.py` 的 subprocess 调用链路完全断裂。

**修复**:
- `packages/codegen/package.json` 添加 `"build": "tsc"` 脚本
- 添加 `tsconfig.json`（如不存在）
- 确认 `codegen_service.py` 的路径指向正确

**影响**: 不修复则 Taro 代码生成完全无法工作。

---

### #2 [P0-阻塞] 修复 Native 生成器调用链路

**问题**: `codegen_service.py` 的 `_NODEJS_WRAPPER` 中 target=native 分支使用内联的简陋 `generateWxml()`（~130 行），完全忽略了 `packages/codegen/src/generators/native/wxml-generator.ts`（639 行，功能完整）。

**内联实现的缺陷**:
- 不支持 `dataBinding`（节点的数据绑定完全被忽略）
- 不支持 `loop` 渲染（wx:for 不生成）
- 不支持 `visible` 条件渲染
- 不支持事件绑定（event handlers 为空）
- `.wxss` 只有基础样式

**修复**:
- `_NODEJS_WRAPPER` 的 target=native 分支改为 require 并调用 `wxml-generator.ts` 的 `generateWxmlPage()`
- 或将内联实现替换为对独立模块的调用

**影响**: 不修复则原生小程序代码生成不可用。

---

### #3 [P1-高] 补齐 10 个缺失组件的三端映射

**问题**: 30 个物料中有 10 个在三端（SchemaRenderer / Taro / Native）完全缺失：

| 组件 | 分类 | 缺失层 |
|------|------|--------|
| NutSearchBar | basic | 三端全缺 |
| NutNavBar | basic | 三端全缺 |
| NutIcon | display | 三端全缺 |
| NutTag | display | 三端全缺 |
| NutAvatar | display | 三端全缺 |
| NutBadge | display | 三端全缺 |
| NutProgress | display | 三端全缺 |
| NutCheckbox | form | 三端全缺 |
| NutRadio | form | 三端全缺 |
| NutDatePicker | form | 三端全缺 |
| NutCalendar | form | 三端全缺 |

**修复**: 为每个组件添加：
1. `SchemaRenderer.tsx` 中的 HTML 模拟渲染（编辑器可视化）
2. `COMPONENT_IMPORT_MAP` 中的 Taro/NutUI import 映射
3. `COMPONENT_WXML_MAP` 中的原生标签映射

**影响**: 补齐后组件覆盖率从 63% 提升到 100%。

---

### #4 [P1-高] 消除 deploy_service.py 重复 stub

**问题**: `deploy_service.py` 的 4 个阶段方法全部是 stub（返回假数据），实际部署完全由 Celery 任务链 (`lowcode_deploy_task.py`) 驱动。两套并行逻辑造成维护负担。

**修复**:
- 删除 `deploy_service.py` 中的 stub 阶段方法
- 统一由 Celery 任务链驱动部署
- `trigger_deploy()` 直接调用 Celery 任务

**影响**: 消除代码重复，降低维护成本。

---

### #5 [P1-高] 提取 _NODEJS_WRAPPER 到独立文件

**问题**: `codegen_service.py` 中内嵌 319 行 JS 字符串作为 Node.js 包装脚本，难以维护和测试。

**修复**:
- 提取为 `packages/codegen/src/cli-wrapper.js`（或 `.ts`）
- `codegen_service.py` 直接执行该文件，不再动态生成临时脚本

**影响**: 代码可维护性提升，为后续优化（常驻进程、缓存）打基础。

---

### #6 [P2-中] 优化代码生成性能（常驻 Node 进程）

**问题**: 每次代码生成都创建临时文件 + 启动新 Node 进程，编辑器预览场景下开销显著。

**修复**:
- 启动常驻 Node 进程（或 WebSocket 服务）
- 通过 stdin/stdout 持续通信，避免反复 fork
- 或将 codegen 逻辑改为 Python 直接调用（codegen 包只有 4 个源文件）

**影响**: 预览响应速度提升 5-10 倍。

---

### #7 [P2-中] 加固数据绑定表达式校验

**问题**: `resolveExpression()` 中 `api.xxx` / `dataSource.xxx` / `ds.xxx` 三种前缀都映射到 `apiData.xxx`，但不校验数据源是否存在。引用不存在的数据源会生成运行时 ReferenceError。

**修复**:
- 在 Schema 分析阶段校验所有 dataBinding 表达式引用的数据源是否存在
- 缺失时在 warnings 中报告，而非生成会崩溃的代码

**影响**: 减少生成代码的运行时错误。

---

### #8 [P2-中] 增加 Taro 构建缓存

**问题**: `_run_taro_build()` 每次在全新临时目录执行 `npx taro build --type weapp`，无缓存机制。

**修复**:
- 缓存 `node_modules` 层（复用 node_modules，只更新源码）
- 利用 Taro 的增量编译能力
- 或使用 Docker 镜像预装依赖

**影响**: 构建时间从 30 分钟级别降至 5-10 分钟。

---

### #9 [P2-中] 建立物料注册表（消除 switch-case）

**问题**: SchemaRenderer 用 switch-case 硬编码 20 个组件的渲染，新增组件需改两处。

**修复**:
- 建立 `materialRegistry`（Map<componentName, { editorComponent, isContainer }>)
- SchemaRenderer 改为 `componentMap[node.componentName]` 动态查找
- 新增组件只需注册，不改渲染器

**影响**: 为后续业务物料扩展和动态注册打基础。

---

### #10 [P3-低] 补充 codegen 单元测试

**问题**: `taro-generator.test.ts` 有 10 个用例，但缺少 Native 生成器和 Schema 分析器的测试。

**修复**:
- 为 `wxml-generator.ts` 补充测试（dataBinding、loop、visible、事件绑定）
- 为 `schema-analyzer.ts` 补充测试（依赖图构建、警告生成）

**影响**: 代码生成质量保障。

---

## 与之前计划的关系

之前写的 Phase 1-4 计划侧重物料管理的可扩展性（动态注册表、Formily、业务物料、物料市场）。

本计划侧重**让小程序生成链路跑通**，是 Phase 1-4 的前置条件。建议执行顺序：

```
#1 codegen 构建修复 ─┐
#2 Native 生成器修复 ─┤─→ 链路跑通
#3 补齐 10 个组件 ───┘
     │
     v
#4 消除 stub ─┐
#5 提取 wrapper ─┤─→ 代码质量
#6 常驻进程 ────┘
     │
     v
#7 表达式校验 ─┐
#8 构建缓存 ────┤─→ 性能与健壮性
#9 注册表 ──────┘
     │
     v
#10 测试 ──→ 质量保障
```

## 文件变更清单

| 操作 | 文件 |
|------|------|
| 修改 | `packages/codegen/package.json`（添加 build 脚本） |
| 修改 | `apps/server/app/modules/lowcode/codegen_service.py`（修复 Native 路径 + 提取 wrapper） |
| 修改 | `apps/server/app/modules/lowcode/deploy_service.py`（删除 stub） |
| 修改 | `apps/admin/src/pages/lowcode/editor/components/SchemaRenderer.tsx`（补齐 10 组件 + 注册表） |
| 新建 | `apps/admin/src/pages/lowcode/editor/materials/registry.ts`（物料注册表） |
| 修改 | `packages/codegen/src/generators/page-generator.ts`（表达式校验） |
| 新建 | `packages/codegen/src/__tests__/wxml-generator.test.ts` |
| 新建 | `packages/codegen/src/__tests__/schema-analyzer.test.ts` |
