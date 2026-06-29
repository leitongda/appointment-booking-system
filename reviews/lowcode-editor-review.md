# hospital-admin-lowcode — 自适应多智能体研究画布

> 协作模式：领域主导（Designer 为 Lead）
> 日期：2026-06-27
> 审查目标：低代码平台编辑器 — 操作、布局、功能优化

---

## 模式选择

**选定模式：** 领域主导（Designer 为 Lead）

**选择理由：** 用户重点关注"操作"和"布局"，低代码编辑器是可视化工具，UX 是核心竞争力。Designer 加深版 prompt 可以深入分析编辑器的交互模式、操作流程、布局合理性。

---

## Round 1：事实层（只写事实，不评价）

### Designer — 用户视角（Lead 加深版）

**页面清单与结构：**
- 39 个源文件（37 .tsx/.ts + 2 .md）
- 页面：list.tsx（页面管理列表）、preview.tsx（预览）、layout.tsx（鉴权包装）、editor/index.tsx（编辑器主入口 733 行）
- 市场：marketplace/index.tsx、detail.tsx、ForkDialog.tsx、redirect.tsx
- 编辑器子模块：components/（Canvas、SchemaRenderer、PropertyPanel、ComponentPanel、LayerPanel、DataSourcePanel、EventConfig、LinkageRulesPanel、VersionHistory、DeployPanel、CodePreviewModal 等）、materials/（5 个分类文件 + snippets.ts）、utils/（tree.ts）、store.ts、constants.ts

**编辑器布局分析：**
- 三栏 IDE 布局：toolbarHeight=52px，leftPanelWidth=260px（固定），rightPanelWidth=320px（固定），canvas=flex:1
- 左侧面板：搜索 + 最近使用（8 项） + 5 个可折叠分类 + snippet 模板区，通过 `<Tabs>` 切换物料/图层/数据源
- 右侧面板：4 个 Tab（属性、样式、事件、高级）
- VersionHistory/DeployPanel/ShareDialog 使用 Drawer 弹出
- 图层面板和数据源面板是左侧面板 `<Tabs>` 中的 tab 页（非 Drawer）

**交互模式统计：**
- 7+ 键盘快捷键：Ctrl+Z/Ctrl+Shift+Z/Ctrl+S/Ctrl+C/Ctrl+V/Ctrl+D/Ctrl+A/Delete/ArrowUp/ArrowDown
- 拖拽：@dnd-kit/react，三种源类型（new-component、snippet、existing-node）
- 右键菜单：4 个操作（复制、删除、上移、下移）
- 选中：单选（蓝色实线边框）+ Shift 多选（紫色虚线边框）
- 自动保存：30 秒间隔，仅 isDirty 且已有 pageId 时触发
- 脏检查：beforeunload 原生弹窗 + history.block 路由拦截 Modal
- 画布缩放：4 档（50%/75%/100%/125%），Segmented 控件
- 设备预设：10 个机型 + 横竖屏切换 + DPR（1x/2x/3x）+ 自定义尺寸

**组件操作流程：**
- 添加：物料面板拖拽 → 画布放置 → 自动创建节点
- 选中：点击单选，Shift+点击多选，画布背景点击取消选中
- 编辑属性：右侧面板表单，支持 7 种控件类型 + 表达式模式 + i18n 标记
- 删除：属性面板头部删除按钮（Popconfirm）或 Delete 键
- 复制/粘贴/复制到：Ctrl+C/V/D
- 移动：图层面板上/下移按钮或拖拽重排
- 数据绑定：属性切换表达式模式 → 输入 {{表达式}} → 变量选择器自动补全
- 事件配置：5 种动作类型 + 条件触发 + 动作链排序
- 联动规则：7 种条件运算符 + 4 种动作

**空状态处理：**
- 画布空状态：虚线边框 + "拖组件到此处" 提示文本
- 无选中时右侧面板：显示主题配置面板

---

### PM — 产品视角（精简版）

**产品定位：**
- 基于拖拽的可视化页面搭建编辑器，面向运营人员无需编码搭建营销页、活动页、科室介绍页等
- JSON Schema 存储，运行时渲染器在 Admin H5 和患者小程序中动态展示

**功能完成度：**

| 功能 | 状态 |
|------|------|
| 可视化画布拖拽编辑 | ✅ 已实现 |
| 组件属性面板配置 | ✅ 已实现（7 种控件 + 表达式 + i18n） |
| 数据源管理 | ✅ 已实现（API/Static/Mock + 测试连接） |
| 状态变量管理 | ✅ 已实现（5 种类型） |
| 事件配置 | ✅ 已实现（5 种动作 + 条件 + 链式） |
| 联动规则 | ✅ 已实现（7 种运算符 + 4 种动作） |
| 版本历史 | ✅ 已实现（列表 + 回滚） |
| 页面预览 | ✅ 已实现（3 种设备尺寸） |
| 模板市场 | ✅ 已实现（8 分类 + Fork + 收藏） |
| 页面发布/部署 | ✅ 已实现（完整流水线 + QR 码） |
| 代码生成 | ✅ 已实现（Taro + 原生） |

**支持的组件：** 38 个组件（5 分类）+ 6 个 snippet 模板

---

### Engineer — 技术视角（精简版）

**存储层：**
- Zustand store + persist 中间件，租户隔离 localStorage
- 持久化：schema、dataSources、stateSchema + 最近 20 条 history
- undo/redo：内存历史栈，MAX_HISTORY=30，JSON.parse(JSON.stringify(...)) 深拷贝快照
- isDirty：通过状态标志管理（setSchema 时设 true，markSaved 时设 false），非深比较

**核心引擎：**
- Schema 树：LowCodeSchema（根）→ LowCodeNode[]（子节点），支持 dataBinding/events/loop/visible/animation/slots/linkageRules
- 渲染引擎：SchemaRenderer 大型 switch 语句按 componentName 分发（约 30 个 case 分支），递归渲染，React.memo 优化
- 拖拽：@dnd-kit/react，computeInsertion() 计算插入位置，isDescendant 防循环放置
- 联动：事件系统 + 数据绑定 + 联动规则三种机制

**安全机制：**
- 预览页面：独立 PreviewNodeRenderer，无 iframe 隔离，与主应用共享 DOM/JS 上下文
- XSS：React 默认文本转义保护，img src 无 URL 校验
- 表达式仅做花括号匹配检查

**API 接口：** 28 个端点（CRUD + 版本管理 + 模板市场 + 部署流水线 + 预览 QR 码）

---

## Round 2：辩论层

### 交叉评论投票矩阵

| 议题 | Designer (Lead) | Critic 质询 | 最终裁决 |
|------|----------------|-------------|---------|
| 编辑器缺少应用内新手引导 | 确认：仅有 USER_GUIDE.md，无应用内引导 | ✅ 验证通过 | 共识 |
| 预览页面无 iframe 隔离 | 确认：共享 DOM/JS 上下文 | ✅ 验证通过，且 PreviewNodeRenderer 与 SchemaRenderer 存在代码重复 | 共识 |
| undo/redo 使用 JSON.stringify 深拷贝 | 确认：性能隐患 | ✅ 验证通过，每次 undo/redo 产生额外深拷贝 | 共识 |
| 属性面板右侧固定 320px 不可调整 | 确认：复杂组件属性多时空间不足 | 待定 | 共识 |
| 画布缩放仅 4 档且无自定义值 | 确认：无滑块连续缩放 | 待定 | 共识 |
| ~~图层/数据源均为 Drawer 形式~~ | ❌ Designer 修正：是左侧面板 Tabs 中的 tab 页，非 Drawer | Critic 纠正 | 已修正 |

### 独到发现（Critic 补充）

1. **无 ErrorBoundary**：SchemaRenderer 中无 try-catch 或 ErrorBoundary，组件渲染失败将导致整个编辑器白屏
2. **完全缺失 a11y**：零 ARIA 属性、零 role 属性、零 tabIndex，无法通过 Tab 键在面板间导航
3. **undo/redo + auto-save 逻辑缺陷**：undo 无条件设 isDirty=true，即使撤销到已保存状态，30 秒后 auto-save 会覆盖正确版本
4. **img src 无 URL 校验**：NutImage/NutAvatar/BizAppointmentCard/BizDoctorCard 直接使用 node.props.src，无 URL 白名单校验
5. **PreviewNodeRenderer 与 SchemaRenderer 代码重复**：两处渲染逻辑几乎完全相同，bug 修复需同步两处
6. **无 Schema 级别导入/导出**：仅有节点级复制粘贴，无法导出整个页面 JSON

### Critic 质询

1. [Critic → Designer] 图层/数据源面板是 Drawer 还是 Tab？
   - 论据：代码显示 LayerPanel 和 DataSourcePanel 嵌入在左侧面板 `<Tabs>` 中
   - 要求回应：修正描述
   - 级别：普通 → ✅ 已修正

2. [Critic → Engineer] isDirty 是否通过 JSON.stringify 深比较？
   - 论据：代码中 isDirty 通过状态标志管理，非深比较
   - 要求回应：修正描述
   - 级别：普通 → ✅ 已修正

3. [Critic → 全体] undo/redo + auto-save 存在数据丢失风险
   - 论据：undo 设 isDirty=true → 30 秒后 auto-save 覆盖正确版本
   - 要求回应：评估严重性并提出修复方案
   - 级别：🚨 关键 → 纳入行动计划

### 🚨 Critic 关键质询追踪

| # | 关键质询内容 | 三方回应摘要 | 回应是否充分 | 处置 |
|---|------------|------------|------------|------|
| 1 | undo/redo + auto-save 数据丢失风险 | Team Lead 确认：真实风险，需要在 undo/redo 时比较 historyEntry 与 savedSchema | 是 | 纳入计划 P0 |

---

## Round 3：共识层

### ✅ 共识项

1. **议题：** 编辑器缺少应用内新手引导
   **结论：** USER_GUIDE.md 存在但未被引用，无应用内引导 Tour、Tooltip 提示或交互式教程
   **建议行动：** 添加首次使用的引导 Tour（基于 GuidedTour 组件），覆盖画布操作、属性配置、数据绑定核心流程
   **成本估算：** 3-5 天
   **负责角色：** Designer + Engineer

2. **议题：** 预览页面无 iframe 隔离 + 与 SchemaRenderer 代码重复
   **结论：** 预览渲染器与编辑器渲染器存在大量重复代码，且无沙箱隔离
   **建议行动：** 提取共享渲染组件，预览页面使用 iframe 隔离
   **成本估算：** 3-5 天
   **负责角色：** Engineer

3. **议题：** undo/redo + auto-save 数据丢失风险
   **结论：** undo 无条件设 isDirty=true，auto-save 会覆盖正确版本
   **建议行动：** undo/redo 后比较当前 schema 与 savedSchema，仅在不同时设 isDirty=true
   **成本估算：** 0.5-1 天
   **负责角色：** Engineer

4. **议题：** 无 ErrorBoundary，组件渲染失败导致白屏
   **结论：** SchemaRenderer 无错误边界保护
   **建议行动：** 在 NodeRenderer 层级添加 ErrorBoundary，渲染失败时显示红色占位符
   **成本估算：** 1-2 天
   **负责角色：** Engineer

5. **议题：** 完全缺失 a11y
   **结论：** 零 ARIA 属性，无法通过键盘在面板间导航
   **建议行动：** 为关键交互区域添加 aria-label、role、tabIndex，支持 Tab 键导航
   **成本估算：** 2-3 天
   **负责角色：** Designer + Engineer

6. **议题：** 画布缩放仅 4 档
   **结论：** 50/75/100/125 四档，无滑块连续缩放
   **建议行动：** 替换为 Slider 组件，支持 25%-200% 连续缩放 + 自定义输入
   **成本估算：** 0.5 天
   **负责角色：** Engineer

7. **议题：** 属性面板固定 320px 不可调整
   **结论：** 复杂组件属性多时空间不足
   **建议行动：** 添加 ResizableDivider 支持拖拽调整宽度，记忆用户偏好
   **成本估算：** 1 天
   **负责角色：** Engineer

8. **议题：** undo/redo JSON.stringify 性能隐患
   **结论：** 每次 mutation 触发 3 次完整树序列化，大页面可能卡顿
   **建议行动：** 引入 Immer 替代 JSON.stringify，或使用 structural sharing
   **成本估算：** 2-3 天
   **负责角色：** Engineer

9. **议题：** img src 无 URL 校验
   **结论：** 直接使用 node.props.src，无白名单校验
   **建议行动：** 添加 URL 校验函数，限制 http/https 协议，可选白名单域名
   **成本估算：** 0.5 天
   **负责角色：** Engineer

10. **议题：** 无 snippet 自定义能力
    **结论：** 6 个预置 snippet，用户无法保存自定义组合
    **建议行动：** 添加"保存为 snippet"功能，支持用户将选中组件树保存为自定义模板
    **成本估算：** 2-3 天
    **负责角色：** PM + Engineer

### ⚡ 分歧项

1. **议题：** 是否需要添加 Schema 级别导入/导出
   **各方立场：**
   - PM：有价值，支持跨环境迁移和备份
   - Designer：增加操作复杂度，需要谨慎设计入口
   - Engineer：API 层已有 exportPage/importPage，前端只需 UI
   **裁决/建议：** 纳入 P2，利用现有 API 添加导出按钮和导入入口
   **决策依据：** API 已就绪，前端工作量小，但优先级低于核心体验优化

---

## 被低估的优势

1. **设备预设覆盖全面**：10 个主流机型 + 横竖屏 + DPR，远超同类低代码工具
2. **snippet 模板**：6 个预置组合模板是快速搭建的利器
3. **完整的部署流水线**：从构建到审核到发布的完整链路，含 QR 码预览
4. **表达式系统**：支持 mustache 语法 + 变量选择器 + i18n 标记，功能完备
5. **租户隔离存储**：localStorage key 追加 tenantId，多租户场景安全

---

## 行动计划（按 ROI 排序）

| 优先级 | 行动 | 成本 | 价值 | 负责 | 状态 |
|--------|------|------|------|------|------|
| P0 | 修复 undo/redo + auto-save 数据丢失风险 | 0.5-1 天 | 高 | Engineer | 待开始 |
| P0 | 添加 ErrorBoundary 防止组件渲染失败白屏 | 1-2 天 | 高 | Engineer | 待开始 |
| P0 | img src URL 校验 | 0.5 天 | 高 | Engineer | 待开始 |
| P1 | 画布缩放改为 Slider 连续缩放 | 0.5 天 | 中 | Engineer | 待开始 |
| P1 | 属性面板可拖拽调整宽度 | 1 天 | 中 | Engineer | 待开始 |
| P1 | 添加首次使用引导 Tour | 3-5 天 | 高 | Designer + Engineer | 待开始 |
| P1 | 提取共享渲染组件 + 预览 iframe 隔离 | 3-5 天 | 高 | Engineer | 待开始 |
| P2 | a11y 基础支持（ARIA + Tab 导航） | 2-3 天 | 中 | Designer + Engineer | 待开始 |
| P2 | undo/redo 性能优化（Immer） | 2-3 天 | 中 | Engineer | 待开始 |
| P2 | 自定义 snippet 保存功能 | 2-3 天 | 中 | PM + Engineer | 待开始 |
| P2 | Schema 级别导入/导出 UI | 1 天 | 低 | Engineer | 待定 |

### P0：立即执行（高价值、低成本）

1. **修复 undo/redo + auto-save 数据丢失风险** — 0.5-1 天
   - 方案：`undo()`/`redo()` 后，通过 `JSON.stringify(currentSchema) === JSON.stringify(savedSchema)` 判断是否与已保存版本一致，一致则设 `isDirty=false`
   - 优化：可用 hash 比较替代完整字符串比较

2. **添加 ErrorBoundary** — 1-2 天
   - 方案：创建 `NodeErrorBoundary` 组件包装 `NodeRenderer`，渲染失败时显示红色虚线占位符 + 组件名 + 错误信息
   - 参考：admin 端已有 ErrorBoundary 需求（上一轮评审发现）

3. **img src URL 校验** — 0.5 天
   - 方案：创建 `isValidImageUrl()` 工具函数，限制 http/https/data 协议，拒绝 javascript: 等危险协议

### P1：本轮迭代（高价值、中等成本）

4. **画布缩放改为 Slider** — 0.5 天
5. **属性面板可拖拽调整宽度** — 1 天（复用已有的 ResizableDivider 组件）
6. **添加首次使用引导 Tour** — 3-5 天（复用已有的 GuidedTour 组件）
7. **提取共享渲染组件 + 预览 iframe 隔离** — 3-5 天

### P2：下个周期规划（中等价值、较高成本）

8. **a11y 基础支持** — 2-3 天
9. **undo/redo 性能优化（Immer）** — 2-3 天
10. **自定义 snippet 保存** — 2-3 天

### 待定：需用户确认

1. **Schema 级别导入/导出 UI** — 1 天（API 已就绪，需确认产品需求）

---

## 摘要

**使用模式：** 领域主导（Designer 为 Lead）

**关键共识：** 10 项达成共识
**关键分歧：** 1 项（Schema 导入/导出优先级）

**Top 3 P0 行动：**
1. 🔴 修复 undo/redo + auto-save 数据丢失风险（0.5-1 天）— Critic 发现的关键缺陷
2. 🔴 添加 ErrorBoundary 防止组件渲染失败白屏（1-2 天）— Critic 发现的盲点
3. 🔴 img src URL 校验（0.5 天）— 安全防护

**Critic 关键洞察：**
- undo/redo + auto-save 存在数据丢失风险，三个角色均未识别（最关键发现）
- 编辑器完全缺失 a11y，零 ARIA 属性
- 预览页面与编辑器存在大量渲染代码重复
- SchemaRenderer 无 ErrorBoundary 保护

**修正记录：**
- Designer 修正：图层/数据源面板是左侧面板 Tabs 中的 tab 页，非 Drawer
- Engineer 修正：isDirty 通过状态标志管理，非 JSON.stringify 深比较

---

## 附录：模式切换日志

| 时间 | 从 | 到 | 原因 |
|------|-----|-----|------|
| - | - | - | 未发生模式切换 |
