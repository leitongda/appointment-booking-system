# 低代码平台架构评审画布

> 协作模式：领域主导（Engineer 主导）
> 执行深度：深度
> 风险升级因子：租户隔离、公共 API 契约、数据完整性
> 日期：2026-06-06
> 审查目标：低代码平台平台层/公共资产层/租户资产层的边界划分与租户解耦

---

## Phase 0 审批记录

**基础复杂度：** 深度（29+ 文件，6+ 模块，跨 6 个包/应用）
**风险升级因子：** 租户隔离、公共 API 契约、数据完整性
**最终深度：** 深度
**协作模式：** 领域主导（Engineer 主导）
**选定 Agent：**
- [Engineer]：加深版（架构师视角，深入分层边界设计）
- [PM]：精简版（聚焦模板市场治理、产品定位）
- [Designer]：精简版（聚焦编辑器体验、物料注册表交互）
- [评审组]：挑战者A + 挑战者B + 审计者（合并为 1 agent）
- [Engineer Lead]：交叉评审 + 综合裁决

**预估 Token：** ~250K-400K
**执行轮次：** Round 1-3（完整流程）
**跳过轮次：** 无
**自适应镜头：** 不适用（非轻量模式）

**用户批准：** 已批准（2026-06-06）

---

## Round 1：事实层（只写事实，不评价）

### Engineer - 技术架构视角

#### Schema 协议的分层边界

**F1.1** `LowCodeSchema` 类型定义（根节点）包含字段：`componentName`、`props`、`children`、`dataSources`、`theme`、`i18n`。
  来源：`packages/shared/src/types/lowcode.ts:129-139` | 证据级别: E1 | 置信度: High

**F1.2** `LowCodeNode` 类型定义包含字段：`id`、`componentName`、`props`、`children`、`dataBinding`、`api`、`events`、`loop`、`visible`、`dependOn`、`style`、`validationRules`、`animation`、`slots`。
  来源：`packages/shared/src/types/lowcode.ts:172-197` | 证据级别: E1 | 置信度: High

**F1.3** `tenantId` 字段仅存在于 `LowCodePage` 接口（第96行），不存在于 `LowCodeSchema` 或 `LowCodeNode` 类型定义中。Schema 本身不携带租户标识。
  来源：`packages/shared/src/types/lowcode.ts:94-106`（LowCodePage）；`packages/shared/src/types/lowcode.ts:129-197`（LowCodeSchema/LowCodeNode 无 tenantId） | 证据级别: E1 | 置信度: High

**F1.4** Schema 协议中不存在 `schema_version` 或版本号字段。版本管理通过独立的 `LowCodePageVersion` 模型实现。
  来源：`packages/shared/src/types/lowcode.ts`（全文无 schema_version）；`apps/server/app/models/lowcode_page_version.py:10-48` | 证据级别: E1 | 置信度: High

**F1.5** `LowCodePage` 服务端模型的 `schema_data` 字段为 `JSONB` 类型，直接存储 `LowCodeSchema` 的序列化 JSON。唯一约束 `uq_lowcode_pages_tenant_slug` 约束 `(tenant_id, slug)` 的唯一性。
  来源：`apps/server/app/models/lowcode_page.py:21,52` | 证据级别: E1 | 置信度: High

#### 编辑器状态与物料注册表的租户隔离

**F2.1** Zustand store 的 persist middleware 使用 key `'lowcode-editor'` 作为 localStorage 持久化标识，不包含任何租户标识。
  来源：`apps/admin/src/pages/lowcode/editor/store.ts:521` | 证据级别: E1 | 置信度: High

**F2.2** 物料注册表 `allMaterials` 由 5 个静态 import 的数组拼接而成，所有物料均来自编译时静态 import，无运行时动态加载机制。
  来源：`apps/admin/src/pages/lowcode/editor/materials/index.ts:3-17` | 证据级别: E1 | 置信度: High

**F2.3** `MaterialComponent` 类型定义不包含租户归属字段（无 `tenantId`、`source`、`isPublic`）。
  来源：`packages/shared/src/types/lowcode.ts:200-208` | 证据级别: E1 | 置信度: High

**F2.4** `businessMaterials` 定义了 4 个业务组件（BizAppointmentCard、BizDoctorCard、BizDepartmentPicker、BizTimeSlotPicker），与基础 UI 物料混合在同一注册表中。
  来源：`apps/admin/src/pages/lowcode/editor/materials/business.tsx:5-115` | 证据级别: E1 | 置信度: High

#### 渲染器的租户感知

**F3.1** 运行时渲染器 `LowCodeRenderer` 中无任何对 tenant 或 tenantId 的引用。渲染器本身不感知租户上下文。
  来源：`apps/patient-miniapp/src/components/LowCodeRenderer/index.tsx`（全文 grep `tenant` 无结果） | 证据级别: E1 | 置信度: High

**F3.2** `data-manager.ts` 中的 `requestApi` 函数通过 `Taro.getStorageSync('tenantCode')` 读取租户代码并注入 `X-Tenant-Code` header。租户标识从本地存储获取。
  来源：`apps/patient-miniapp/src/components/LowCodeRenderer/data-manager.ts:132-135` | 证据级别: E1 | 置信度: High

**F3.3** 渲染器的组件映射（switch/case）覆盖 20+ 个组件名，映射中不含任何根据租户或订阅计划的条件分支。
  来源：`apps/patient-miniapp/src/components/LowCodeRenderer/index.tsx:354-693` | 证据级别: E1 | 置信度: High

**F3.4** 编辑器端渲染器使用 HTML 原生元素模拟 Taro 组件渲染，运行时端使用 Taro 组件。两者组件映射在 componentNames 列表上保持一致。
  来源：`apps/admin/src/pages/lowcode/editor/components/SchemaRenderer.tsx:154-878`；`apps/patient-miniapp/src/components/LowCodeRenderer/index.tsx:354-693` | 证据级别: E1 | 置信度: High

#### packages/codegen 的租户隔离

**F4.1** `COMPONENT_IMPORT_MAP` 包含 26 个组件映射，来源均为公共库或应用内路径。不存在平台公共组件与租户私有组件的区分机制。
  来源：`packages/codegen/src/generators/taro/page-generator.ts:45-81` | 证据级别: E1 | 置信度: High

**F4.2** `generatePage` 函数的 `GeneratePageOptions` 仅包含 `useHospitalApi` 和 `pageStyle`，不含租户标识。生成的代码头部注释不含租户标识。
  来源：`packages/codegen/src/generators/taro/page-generator.ts:33-38,906-910` | 证据级别: E1 | 置信度: High

**F4.3** `schema-analyzer.ts` 的校验规则中无租户相关校验。codegen 包本身不含租户权限检查。
  来源：`packages/codegen/src/analyzer/schema-analyzer.ts:301-379` | 证据级别: E1 | 置信度: High

#### 模板系统的三层边界

**F5.1** `LowCodeTemplate` 模型包含 `source_tenant_id`（来源租户ID）、`is_public`（是否公开到市场）、`is_official`（是否官方）三个字段。
  来源：`apps/server/app/models/lowcode_template.py:31-47` | 证据级别: E1 | 置信度: High

**F5.2** Fork 机制的数据流向：`fork_template()` 从 `LowCodeTemplate.schema_data` 复制到新创建的 `LowCodePage.schema_data`，新页面归属 `forked_by_tenant_id`。Fork 后的页面与原模板完全解耦。
  来源：`apps/server/app/modules/lowcode/template_service.py:288-340` | 证据级别: E1 | 置信度: High

**F5.3** 5 套样式模板通过 `templateMap` 硬编码在 `loader.ts` 中，通过编译时环境变量 `TARO_APP_TEMPLATE_CODE` 选择。不存在运行时根据租户动态加载不同模板集的机制。
  来源：`apps/miniapp-instance/src/templates/loader.ts:8-14,77-79` | 证据级别: E1 | 置信度: High

**F5.4** Shell 注册表包含 6 个页面类别的 26 个变体，全部为静态 import 映射，无租户归属标识。
  来源：`apps/miniapp-instance/src/shells/ShellRegistry.ts:12-57` | 证据级别: E1 | 置信度: High

**F5.5** `MiniappStyleTemplate` 类型中不存在租户可定制字段的定义；所有字段为平台定义的模板配置。
  来源：`apps/miniapp-instance/src/templates/types.ts:58-71` | 证据级别: E1 | 置信度: High

#### 功能门禁与订阅计划的绑定

**F6.1** `TenantFeatures` 中 lowcode 相关字段共 9 个：`lowcode_basic`(default=True)、`lowcode_advanced_components`、`lowcode_custom_components`、`lowcode_data_binding`、`lowcode_codegen`、`lowcode_marketplace`、`lowcode_publish_miniapp`、`lowcode_export_code`、`lowcode_max_pages`(int, default=5)。
  来源：`apps/server/app/modules/tenants/schemas.py:77-85` | 证据级别: E1 | 置信度: High

**F6.2** 功能开关读取优先级为三级覆盖：租户级覆盖 > 订阅计划默认 > 系统默认值。
  来源：`apps/server/app/common/feature_flags.py:15-67` | 证据级别: E1 | 置信度: High

**F6.3** 不存在"组件级"的订阅控制。`lowcode_advanced_components` 控制的是"含 dataBindings 的页面是否可发布"，而非控制单个组件的使用。
  来源：`apps/server/app/modules/lowcode/router.py:311-322` | 证据级别: E1 | 置信度: High

**F6.4** `lowcode_custom_components`、`lowcode_data_binding`、`lowcode_export_code` 三个功能开关在 TenantFeatures 中定义但未发现路由层的 enforce 调用。
  来源：`apps/server/app/modules/tenants/schemas.py:79,80,84`；`apps/server/app/modules/lowcode/router.py` 全文 grep 无命中 | 证据级别: E1 | 置信度: High

#### 三层边界的缺失与模糊地带

**F7.1** 代码库中不存在"平台层"、"公共资产层"、"租户资产层"的显式分层定义或注释。
  来源：全文 grep 无项目代码命中 | 证据级别: E1 | 置信度: High

**F7.2** `LowCodeSchema` 类型不包含任何租户隔离字段（无 `tenantId`、`version`、`scope`、`source`）。租户隔离完全依赖外层 `LowCodePage` 的 `tenant_id` 字段和数据库查询的 WHERE 条件。
  来源：`packages/shared/src/types/lowcode.ts:129-139` | 证据级别: E1 | 置信度: High

**F7.3** 物料注册表将基础 UI 物料和业务物料混合在同一数组中，`MaterialComponent` 类型中无 `scope`、`source`、`tenantId` 等字段区分物料归属。
  来源：`apps/admin/src/pages/lowcode/editor/materials/index.ts:11-17`；`packages/shared/src/types/lowcode.ts:200-208` | 证据级别: E1 | 置信度: High

**F7.4** 编辑器 Zustand store 的 localStorage key 为固定字符串 `'lowcode-editor'`，多个租户在同一浏览器上操作时会互相覆盖编辑状态。
  来源：`apps/admin/src/pages/lowcode/editor/store.ts:521` | 证据级别: E1 | 置信度: High

**F7.5** 模板 `create_template` 方法在创建模板时将 `source_tenant_id` 记录为创建租户的 ID，但模板被 Fork 后，新页面的 `schema_data` 与模板的 `schema_data` 完全解耦（无引用关系）。
  来源：`apps/server/app/modules/lowcode/template_service.py:158-223,288-340` | 证据级别: E1 | 置信度: High

---

### PM - 产品视角

#### 产品定位与功能完成度

**P1.1** 研究报告定义平台定位为"先内部验证，成熟后作为 SaaS 对外输出"。目标用户为"混合型 -- 运营人员做简单页面，开发人员处理复杂业务逻辑"。
  来源：`reviews/lowcode-miniapp-research.md:12-13` | 证据级别: E2 | 置信度: High

**P1.2** 项目 README 中未提及低代码平台作为系统组成部分。
  来源：`README.md:1-100` | 证据级别: E1 | 置信度: High

**P1.3** Phase 1-2 功能已全部落地（编辑器、35 个物料、数据绑定、代码生成、运行时渲染器）。Phase 3 部分落地（模板市场、版本管理、部署状态机 stub）。未落地：实际构建/上传/审核流水线、is_official 写入逻辑。
  来源：`apps/admin/src/pages/lowcode/` 全目录；`apps/server/app/modules/lowcode/` 全目录 | 证据级别: E1 | 置信度: High

#### 模板市场治理

**P2.1** `is_official` 字段在代码中无写入逻辑 -- 创建模板时未设置，更新模板时不在可更新字段中。仅在响应中输出。
  来源：`apps/server/app/modules/lowcode/template_service.py:158-265`；`apps/server/app/modules/lowcode/router_template.py:29-65` | 证据级别: E1 | 置信度: High

**P2.2** 代码中无模板审核流程端点（无 approve/reject/review 相关路由）。模板状态仅由 `status` 字段控制：0=禁用、1=正常。
  来源：`apps/server/app/modules/lowcode/router_template.py` 全文；`apps/server/app/models/lowcode_template.py:51` | 证据级别: E1 | 置信度: High

**P2.3** 模板创建时 `is_public` 默认为 `True`，直接上架市场，无审核中间步骤。
  来源：`apps/server/app/modules/lowcode/router_template.py:38` | 证据级别: E1 | 置信度: High

**P2.4** 前后端模板分类列表不一致：后端有"健康档案、排队叫号、科室导航、健康宣教、满意度调查"，前端有"临时挂号、问诊、公告通知、表单收集、落地页"。
  来源：`apps/server/app/modules/lowcode/router_template.py:149-158`；`apps/admin/src/pages/lowcode/marketplace/index.tsx:30-40` | 证据级别: E1 | 置信度: High

**P2.5** 模板列表为公开接口，无需认证即可浏览。
  来源：`apps/server/app/modules/lowcode/router_template.py:166-193` | 证据级别: E1 | 置信度: High

#### 功能开关与订阅控制

**P3.1** 9 个 lowcode_* 功能开关中，`lowcode_custom_components`、`lowcode_data_binding`、`lowcode_export_code` 三个在代码中未被任何路由端点使用。
  来源：`apps/server/app/modules/tenants/schemas.py:77-85`；`apps/server/app/modules/lowcode/router.py` 全文 grep | 证据级别: E1 | 置信度: High

**P3.2** 无组件级差异化控制：feature gate 仅检查布尔开关和页面配额，不检查组件使用。研究报告提及"租户可使用的组件集受订阅计划控制"，但代码中未找到对应实现。
  来源：`apps/server/app/modules/lowcode/feature_gate.py` 全文；`reviews/lowcode-miniapp-research.md:297` | 证据级别: E1+E2 | 置信度: High

#### 竞品对比

**P4.1** 研究报告对比了 7 个开源平台和 4 个商业平台。唯一可用的 Taro 低代码参考项目为 Designable（已停维）。
  来源：`reviews/lowcode-miniapp-research.md:92-444` | 证据级别: E2 | 置信度: High

---

### Designer - 用户视角

#### 编辑器页面结构

**D1.1** 编辑器采用 Flex 三栏布局 (100vh 全屏)：顶部工具栏(48px) + 左侧面板(240px, 含物料/数据/图层三个 tab) + 中间画布 + 右侧属性面板。
  来源：`apps/admin/src/pages/lowcode/editor/index.tsx:478-677` | 证据级别: E1 | 置信度: High

**D1.2** 编辑器含 14 个组件文件：Canvas、SchemaRenderer、ComponentPanel、DataSourcePanel、LayerPanel、PropertyPanel、EventConfig、CodePreviewModal、DeployPanel、DeployStatus、VersionHistory、ShareDialog、PreviewQRCode、BuildLogViewer。
  来源：`apps/admin/src/pages/lowcode/editor/components/` 目录 | 证据级别: E1 | 置信度: High

#### 物料面板与组件分类

**D2.1** 5 个分类共 34 个物料组件：basic(6)、layout(3)、display(12)、form(9)、business(4)。加上 6 个 Snippet 模板。
  来源：`apps/admin/src/pages/lowcode/editor/materials/` 各文件 | 证据级别: E1 | 置信度: High

**D2.2** ComponentPanel 支持搜索（30 个组件的关键词映射）、最近使用（最多 8 个）、分类折叠列表、Snippet 面板。
  来源：`apps/admin/src/pages/lowcode/editor/components/ComponentPanel.tsx:179-309` | 证据级别: E1 | 置信度: High

#### 渲染器差异

**D3.1** 编辑器端支持 35 个组件（含 default fallback），运行时端 codegen 映射 35 个组件（3 Taro + 28 NutUI + 4 业务）。两端组件覆盖数量一致。
  来源：`apps/admin/src/pages/lowcode/editor/components/SchemaRenderer.tsx:134-878`；`packages/codegen/src/generators/taro/page-generator.ts:45-81` | 证据级别: E1 | 置信度: High

**D3.2** 编辑器端额外支持拖拽（DraggableNode/DroppableZone）和选中态高亮，运行时端不包含这些交互逻辑。
  来源：`apps/admin/src/pages/lowcode/editor/components/SchemaRenderer.tsx:21-77` | 证据级别: E1 | 置信度: High

#### Shell 变体系统

**D4.1** Shell 注册表定义了 6 个页面类别 x 多变体（总计 26 个），通过 React.lazy 动态导入。存在两套并行的注册机制（ShellRegistry.ts 和 registry.tsx）。
  来源：`apps/miniapp-instance/src/shells/ShellRegistry.ts:1-83`；`apps/miniapp-instance/src/shells/registry.tsx:1-29` | 证据级别: E1 | 置信度: High

**D4.2** 模板与 Shell 变体的绑定关系通过 `MiniappStyleTemplate.pageShells: Record<string, string>` 实现，键为页面路径，值为变体 ID。
  来源：`apps/miniapp-instance/src/templates/types.ts:66`；`apps/miniapp-instance/src/templates/modern-general.ts:31-38` | 证据级别: E1 | 置信度: High

#### 属性面板与事件配置

**D5.1** PropertyPanel 提供 10 个编辑区域：主题配置、组件信息、节点 ID、属性配置项（13 种输入类型中实际使用 7 种）、样式配置（8 属性）、条件渲染、动画效果、验证规则、循环渲染、事件配置。
  来源：`apps/admin/src/pages/lowcode/editor/components/PropertyPanel.tsx:770-1281` | 证据级别: E1 | 置信度: High

**D5.2** EventConfig 支持 4 种事件类型（onClick/onChange/onSubmit/onLoad）和 5 种动作类型（navigate/showToast/updateVariable/fetchApi/setData）。
  来源：`apps/admin/src/pages/lowcode/editor/components/EventConfig.tsx:36-50` | 证据级别: E1 | 置信度: High

---

### Round 1 质量门禁

- [x] 每条事实包含来源（文件路径:行号）
- [x] 每条事实标注证据级别（E1-E4）
- [x] 零评价性词汇
- [x] 覆盖所有调研维度（Schema 协议、编辑器、渲染器、codegen、模板系统、功能门禁）
- [x] 三个视角有高度交集

**结果：** 通过
**争议密度评估：** 高 -- 三个视角在"三层边界缺失"、"租户隔离不足"、"模板治理缺失"维度高度交集
**Round 2 决策：** 完整执行

---

## Round 2：辩论层

### Engineer Lead 交叉评审

**[Engineer -> PM] P2.1 is_official 无写入逻辑：+1，升级严重度**
`is_official` 确实从未被任何代码路径写入。`TemplateResponse` 对外暴露 `is_official: bool`，永远为 False，属于静默错误。严重度 P1。

**[Engineer -> PM] P2.2 无模板审核流程：+1，补充技术风险**
模板直接上架（`is_public` 默认 True），任何租户创建模板后立即对所有租户可见，无平台层面内容治理。严重度 P1。

**[Engineer -> PM] P2.4 前后端模板分类不一致：+1，补充过滤风险**
前后端分类列表完全不一致。`list_templates` 用 `category == category` 精确匹配，前端传的 key 与后端存的值不一致会导致查询返回空结果。严重度 P1。

**[Engineer -> PM] P2.5 模板公开接口无需认证：+1，降级**
市场列表公开合理。但 `get_template` 详情中包含 `schema_data`，在公开接口中暴露完整 schema 定义（含内部 API URL），需关注。严重度 P2。

**[Engineer -> PM] P3.2 无组件级差异化控制：+1，补充架构影响**
`feature_gate.py` 仅有布尔开关和数量配额检查。`COMPONENT_IMPORT_MAP` 和物料注册表均为静态全量注册。若需组件级控制，需扩展 Schema 协议层。严重度 P1。

**[Engineer -> Designer] D2.1 物料分类：+1，补充归属缺失**
`MaterialComponent` 类型不包含 `scope`、`source`、`tenantId`、`planLevel` 字段，无法按租户或订阅计划过滤可用物料。

**[Engineer -> Designer] D4.1 Shell 双注册机制：+1**
两套机制并存增加维护成本。

### Engineer 交叉发现

**SF1: 模板删除缺少租户所有权校验 -- P0**
`delete_template` 仅检查权限，不校验租户所有权。租户 A 可删除租户 B 的模板。
来源：`router_template.py:348-366`; `template_service.py:270-283` | E1 | High

**SF2: `import_page` 缺少功能门禁和 schema 校验 -- P1**
未检查功能开关和页面配额，不校验 schema 内容，未限制文件大小。
来源：`router.py:264-298` | E1 | High

**SF3: `export_page` 导出不含租户标识 -- P1**
导出的 schema_data 可被导入到任何租户（SF2 确认导入不校验租户），形成跨租户数据泄漏链。
来源：`router.py:232-261` | E1 | High

**SF4: 编辑器 Zustand store 跨租户状态污染 -- P1**
localStorage key 固定，切换租户时前一租户的编辑状态（含敏感数据绑定配置）会覆盖。
来源：`editor/store.ts:521` | E1 | High

**SF5: `get_my_templates` 无分页上限保护 -- P2**
路由端点未设置 `page_size` 上限。
来源：`router_template.py:507-553` | E1 | Medium

**SF6: codegen `COMPONENT_IMPORT_MAP` 硬编码 -- P2**
业务组件以固定路径硬编码，无租户/计划过滤能力，扩展性受限。
来源：`page-generator.ts:33-81` | E1 | High

**SF7: `LowCodePageVersion` 无 schema 兼容性校验 -- P1**
版本创建为纯快照复制，不校验新版本 schema 兼容性。
来源：`template_service.py:386-432` | E1 | High

### 评审组质询

**[挑战者A] F7.4 localStorage 键冲突被高估：**
管理后台单租户使用场景下触发频率极低，丢失仅草稿暂态。建议降为 P2。

**[挑战者A] F6.4 三个功能开关未使用可能是设计取舍：**
`lowcode_custom_components` 对应未实现的功能，`lowcode_export_code` 与 `lowcode_codegen` 重复。建议保持但需 PM 澄清产品意图。

**[挑战者B] 租户隔离模型关键质询：**
Schema 层不携带 tenantId 是合理的分层设计（竞品做法一致）。F7.2 降为 P2。真正的风险在 F3.2（localStorage tenantCode）。

**[挑战者B] 产品阶段错位关键质询：**
评审隐含使用了 SaaS 标准。内部验证阶段下，模板审核缺失、is_official 缺失、公开接口均为可接受。P0/P1（安全/数据泄漏）不因阶段降低。

**[审计者] 模板公开接口安全关键质询：**
模板详情返回 schema_data（含内部 API URL），非认证用户可获取。需脱敏或要求认证。

**[审计者] 成本估算缺失：**
三方均未提供修复成本估算，Round 3 需补充。

### Round 2 质量门禁

- [x] 每个反驳附带理由
- [x] 评审组完成误报抑制检查
- [x] 评审组标记了 3 条关键质询
- [x] 交叉评论覆盖主要发现
- [x] 争议密度已计算

**结果：** 通过
**争议密度：** 高（3 条关键质询 + 7 个新发现）
**Round 3 决策：** 完整收敛

---

## Round 3：共识层

### 关键质询回应

**质询 1 [挑战者B]: Schema 层不携带 tenantId 是否真的是问题？**
裁决：挑战者 B 的论据成立。Schema 与 Page 的职责分离是合理的分层设计。租户隔离的核心在于 API 层的访问控制和数据查询的 WHERE 条件。F7.2 降级为 P2。保留 F3.2（localStorage tenantCode）为 P1。

**质询 2 [挑战者B]: 产品阶段错位 -- 内部验证 vs SaaS 就绪度**
裁决：采用双轨评估。P0/P1 发现基于代码实际行为（安全漏洞、数据泄漏、权限绕过），无论处于哪个阶段都必须修复。P2/P3 发现按 SaaS 就绪度排序，标注"待 SaaS 阶段"。

**质询 3 [审计者]: 模板公开接口的安全边界**
裁决：`get_template` 详情返回 `schema_data`（含内部 API URL），构成信息泄露风险。P1，需脱敏或要求认证。

### 共识项

1. **议题：模板删除缺少租户所有权校验**
   结论：P0 安全漏洞，必须立即修复
   严重度定义匹配：跨租户数据破坏，任何拥有模板删除权限的租户均可删除其他租户的模板
   影响声明：所有租户的模板资产安全
   证据级别：E1 | 来源：`router_template.py:348-366`; `template_service.py:270-283` | 置信度：High
   工程成本：Low（2 小时） -- 在 `delete_template` 方法中增加 `tenant_id` 参数校验
   风险降低：High -- 消除跨租户数据破坏风险
   杠杆率：High/Low = 最高
   负责：Engineer

2. **议题：import_page 绕过功能门禁和 schema 校验**
   结论：P1 安全/稳定性风险
   影响声明：租户可通过导入绕过页面配额限制和功能开关控制
   证据级别：E1 | 来源：`router.py:264-298` | 置信度：High
   工程成本：Medium（4 小时） -- 补充 enforce_feature + enforce_page_limit + schema 校验
   风险降低：High
   杠杆率：High/Medium = 高
   负责：Engineer

3. **议题：export/import 组合形成跨租户数据泄漏链**
   结论：P1 数据泄漏风险
   影响声明：租户 A 导出的含内部 API 配置的 schema 可被导入到租户 B
   证据级别：E1 | 来源：`router.py:232-298` | 置信度：High
   工程成本：Medium（4 小时） -- 在 import 时注入 tenant_id，或在 export 时脱敏
   风险降低：High
   杠杆率：High/Medium = 高
   负责：Engineer

4. **议题：编辑器 Zustand store 跨租户状态污染**
   结论：P1 运行时缺陷（结合数据泄漏路径）
   影响声明：敏感数据绑定配置可通过 localStorage 跨租户泄漏
   证据级别：E1 | 来源：`editor/store.ts:521` | 置信度：High
   工程成本：Low（1 小时） -- localStorage key 拼接 tenantId
   风险降低：Medium
   杠杆率：Medium/Low = 高
   负责：Designer + Engineer

5. **议题：模板详情公开接口暴露 schema_data**
   结论：P1 信息泄露风险
   影响声明：非认证用户可获取模板中绑定的内部 API 端点信息
   证据级别：E1 | 来源：`router_template.py:201-218`; `template_service.py:142` | 置信度：High
   工程成本：Low（2 小时） -- 在公开详情接口中脱敏 dataSources 或要求认证
   风险降低：High
   杠杆率：High/Low = 最高
   负责：Engineer

6. **议题：版本快照无 schema 兼容性校验**
   结论：P1 数据完整性风险
   影响声明：无效 schema 可被标记为"已发布"
   证据级别：E1 | 来源：`template_service.py:386-432` | 置信度：High
   工程成本：Medium（4 小时） -- 在 create_version 中调用 analyzeSchema 校验
   风险降低：Medium
   杠杆率：Medium/Medium = 中
   负责：Engineer

7. **议题：is_official 字段无写入逻辑**
   结论：P1 数据完整性（静默错误）
   影响声明：所有模板永远被标记为非官方，前端 UI 依赖此字段展示"官方"标签时显示错误
   证据级别：E1 | 来源：`template_service.py:158-265` | 置信度：High
   工程成本：Low（2 小时） -- 在平台管理员端点中增加 is_official 设置能力
   风险降低：Medium
   杠杆率：Medium/Low = 高
   负责：PM + Engineer

8. **议题：前后端模板分类不一致**
   结论：P1 功能缺陷
   影响声明：前端提交的分类值在后端无法匹配，查询可能返回空结果
   证据级别：E1 | 来源：`router_template.py:149-158`; `marketplace/index.tsx:30-40` | 置信度：High
   工程成本：Low（2 小时） -- 统一分类列表
   风险降低：Medium
   杠杆率：Medium/Low = 高
   负责：PM + Engineer

9. **议题：模板直接上架无审核流程**
   结论：P1（SaaS 阶段必须修复），内部验证阶段暂可接受
   影响声明：SaaS 化后任何租户创建的模板立即对所有租户可见
   证据级别：E1 | 来源：`router_template.py:38`; `router_template.py` 全文无 approve/reject | 置信度：High
   工程成本：High（16 小时） -- 新增审核状态机 + 审核端点 + 列表过滤逻辑修改
   风险降低：High（SaaS 阶段）
   杠杆率：High/High = 中
   负责：Engineer

10. **议题：无组件级差异化控制**
    结论：P1（SaaS 阶段必须实现）
    影响声明：无法按订阅计划控制租户可用的组件集合
    证据级别：E1+E2 | 来源：`feature_gate.py` 全文; `lowcode-miniapp-research.md:297` | 置信度：High
    工程成本：High（24 小时） -- Schema 协议扩展 + 物料注册表 scope 字段 + 编辑器过滤 + codegen 过滤
    风险降低：High（SaaS 阶段）
    杠杆率：High/High = 中
    负责：Engineer

### 分歧项

1. **议题：Schema 不含 tenantId 是否构成缺陷**
   各方立场：
   - Engineer：F7.2 降级为 P2，资源级隔离是合理设计
   - 挑战者B：+1 Engineer，Schema 不应冗余租户标识
   - 审计者：需要 Engineer 明确租户隔离模型
   裁决：P2 观察项，不作为缺陷
   决策依据：竞品做法一致，租户隔离依赖 API 层而非 Schema 层

2. **议题：编辑器 localStorage 键冲突的严重度**
   各方立场：
   - Engineer：P1（结合数据泄漏路径）
   - 挑战者A：P2（B 端单用户场景，触发频率极低）
   裁决：P1，因为数据泄漏路径确实存在（SF4）
   决策依据：安全评估应基于最坏情况而非最常见情况

### Open Risks

1. **风险描述：** 三个未使用的功能开关（`lowcode_custom_components`、`lowcode_data_binding`、`lowcode_export_code`）的产品意图不明确
   分歧方：PM vs Engineer
   争议核心：是"渐进式实现策略"还是"遗漏"？
   已有证据：F6.4（E1 确认未使用）
   建议：需 PM 澄清三个开关各自的产品语义后再定优先级

2. **风险描述：** Shell 双注册机制的调用关系未验证
   分歧方：Designer vs Engineer
   争议核心：`ShellRegistry.ts` 和 `registry.tsx` 是否在同一运行时路径中并行生效？
   已有证据：D4.1（E1 确认两个文件存在）
   建议：需 Engineer 补充调用关系分析

---

## 被低估的优势

1. Schema 与 Page 的职责分离是合理的分层设计，与竞品做法一致
2. Fork 后解耦（F5.2）是避免跨租户数据耦合的正确设计决策
3. 两端组件覆盖数量一致（35 个），编辑器预览与运行时的映射保持同步
4. 功能门禁三级覆盖机制（租户 > 订阅计划 > 系统默认）架构清晰
5. 表达式引擎无 eval/Function，安全设计到位

---

## 行动计划（按杠杆率排序）

| 优先级 | 行动 | 严重度 | 杠杆率 | 工程成本 | 风险降低 | 负责 | 状态 |
|--------|------|--------|--------|---------|---------|------|------|
| P0 | 模板删除增加租户所有权校验 | P0 | 最高 | Low (2h) | High | Engineer | 待修复 |
| P1 | 模板公开详情接口脱敏/认证 | P1 | 最高 | Low (2h) | High | Engineer | 待修复 |
| P1 | import_page 补充功能门禁+schema 校验 | P1 | 高 | Medium (4h) | High | Engineer | 待修复 |
| P1 | export/import 增加租户标识注入 | P1 | 高 | Medium (4h) | High | Engineer | 待修复 |
| P1 | 编辑器 store key 拼接 tenantId | P1 | 高 | Low (1h) | Medium | Designer+Engineer | 待修复 |
| P1 | is_official 增加写入逻辑 | P1 | 高 | Low (2h) | Medium | PM+Engineer | 待修复 |
| P1 | 前后端模板分类统一 | P1 | 高 | Low (2h) | Medium | PM+Engineer | 待修复 |
| P1 | 版本快照增加 schema 兼容性校验 | P1 | 中 | Medium (4h) | Medium | Engineer | 待修复 |
| P1 | 模板审核流程（SaaS 阶段） | P1 | 中 | High (16h) | High | Engineer | 待 SaaS |
| P1 | 组件级差异化控制（SaaS 阶段） | P1 | 中 | High (24h) | High | Engineer | 待 SaaS |
| P2 | get_my_templates 增加分页上限 | P2 | 中 | Low (1h) | Low | Engineer | 待修复 |
| P2 | codegen COMPONENT_IMPORT_MAP 可配置化 | P2 | 中 | Medium (4h) | Low | Engineer | 待 SaaS |
| P2 | localStorage tenantCode 改用安全存储 | P2 | 中 | Medium (4h) | Medium | Engineer | 待评估 |
| Open Risk | 三个未使用功能开关的产品意图 | - | - | - | - | PM | 待确认 |
| Open Risk | Shell 双注册机制调用关系 | - | - | - | - | Engineer | 待分析 |

### P0：立即执行

1. **行动：** 在 `delete_template` 方法中增加 `tenant_id` 参数，校验当前租户是否为模板的 `source_tenant_id`
   **影响声明：** 消除租户 A 删除租户 B 模板的跨租户数据破坏风险
   **证据：** E1 | `router_template.py:348-366`; `template_service.py:270-283` | High
   **杠杆率：** 最高
   **预估工时：** 2 小时
   **负责：** Engineer

### P1：本轮迭代

1. **行动：** 模板详情公开接口脱敏 -- 在 `get_template` 中对非认证请求过滤 dataSources 字段，或要求认证
   **影响声明：** 防止非认证用户获取内部 API 端点信息
   **证据：** E1 | `router_template.py:201-218` | High
   **杠杆率：** 最高 | 预估工时：2 小时 | 负责：Engineer

2. **行动：** `import_page` 补充 `enforce_feature("lowcode_basic")` + `enforce_page_limit()` + schema 内容校验
   **影响声明：** 防止通过导入绕过功能门禁和配额限制
   **证据：** E1 | `router.py:264-298` | High
   **杠杆率：** 高 | 预估工时：4 小时 | 负责：Engineer

3. **行动：** export/import 增加租户标识 -- export 时注入 tenant_id 到导出数据，import 时校验 tenant_id 匹配
   **影响声明：** 阻断跨租户数据泄漏链
   **证据：** E1 | `router.py:232-298` | High
   **杠杆率：** 高 | 预估工时：4 小时 | 负责：Engineer

4. **行动：** 编辑器 store localStorage key 改为 `lowcode-editor-${tenantId}`
   **影响声明：** 消除跨租户编辑状态污染和数据泄漏路径
   **证据：** E1 | `editor/store.ts:521` | High
   **杠杆率：** 高 | 预估工时：1 小时 | 负责：Designer + Engineer

5. **行动：** 在平台管理员端点中增加 `is_official` 设置能力
   **影响声明：** 消除"官方"标签永远为 False 的静默错误
   **证据：** E1 | `template_service.py:158-265` | High
   **杠杆率：** 高 | 预估工时：2 小时 | 负责：PM + Engineer

6. **行动：** 统一前后端模板分类列表，或让前端从后端 `get_template_categories` 接口动态获取
   **影响声明：** 消除分类不匹配导致的模板查询空结果
   **证据：** E1 | `router_template.py:149-158`; `marketplace/index.tsx:30-40` | High
   **杠杆率：** 高 | 预估工时：2 小时 | 负责：PM + Engineer

7. **行动：** 在 `create_version` 中调用 `analyzeSchema` 校验 schema 兼容性
   **影响声明：** 防止无效 schema 被标记为"已发布"
   **证据：** E1 | `template_service.py:386-432` | High
   **杠杆率：** 中 | 预估工时：4 小时 | 负责：Engineer

### P2：下个周期规划（SaaS 阶段）

1. **行动：** 实现模板审核流程（状态机：draft -> pending_review -> approved/rejected）
   **杠杆率：** 中 | 预估工时：16 小时 | 负责：Engineer

2. **行动：** 实现组件级差异化控制（Schema 协议扩展 + 物料 scope 字段 + 过滤逻辑）
   **杠杆率：** 中 | 预估工时：24 小时 | 负责：Engineer

3. **行动：** `get_my_templates` 增加 page_size 上限约束
   **杠杆率：** 中 | 预估工时：1 小时 | 负责：Engineer

4. **行动：** codegen `COMPONENT_IMPORT_MAP` 改为可配置结构
   **杠杆率：** 中 | 预估工时：4 小时 | 负责：Engineer

5. **行动：** 评估 localStorage tenantCode 改用 HttpOnly cookie 或服务端 session
   **杠杆率：** 中 | 预估工时：4 小时 | 负责：Engineer

### P3：仅记录

1. 编辑器端与运行时端使用不同组件库（HTML vs Taro）-- 已确认的架构设计决策，非缺陷
2. Shell 双注册机制待调用关系分析后定性
3. 三个未使用功能开关待 PM 澄清产品意图

### Open Risks

1. 三个未使用功能开关（`lowcode_custom_components`、`lowcode_data_binding`、`lowcode_export_code`）的产品意图不明确 -- 待 PM 确认
2. Shell 双注册机制（`ShellRegistry.ts` vs `registry.tsx`）的调用关系待分析

### 待定：需用户确认

1. 当前评审基准确认：按"内部验证完成度"还是"SaaS 就绪度"评估？（影响 P2/P3 的排序）
2. 模板详情公开接口的脱敏策略：过滤 dataSources 字段 vs 要求认证？
3. is_official 的设置方式：平台管理员手动设置 vs 官方模板自动标记？

---

## 摘要

**使用模式：** 领域主导（Engineer 主导）
**执行深度：** 深度
**风险升级：** 租户隔离、公共 API 契约、数据完整性

**关键共识：** 10 项
**关键分歧：** 2 项（Schema tenantId 争议、编辑器 store 严重度争议）
**Open Risks：** 2 项

**Top 3 P0/P1 行动（按杠杆率）：**
1. [杠杆率最高] 模板删除增加租户所有权校验（P0, 2h）
2. [杠杆率最高] 模板公开详情接口脱敏/认证（P1, 2h）
3. [杠杆率高] import_page 补充功能门禁+schema 校验（P1, 4h）

**评审组关键洞察：**
- 租户隔离的核心在于 API 层访问控制，而非 Schema 自描述
- 产品阶段错位导致部分发现被系统性高估，P0/P1 修复不因阶段降低
- 模板公开接口暴露 schema_data 是三方遗漏的安全风险
