# admin-ahooks-adoption — 自适应多智能体研究画布

> 协作模式：领域主导（Engineer 主导）
> 日期：2026-05-22
> 审查目标：apps/admin 端 ahooks hooks 替换机会与可抽象自定义 hooks

---

## 模式选择

**选定模式：** 领域主导（Engineer 主导）

**选择理由：** 核心是代码模式分析，需要深度扫描前端 hook 使用、状态管理、副作用处理。Engineer 主导深度代码扫描，PM/Designer 辅助识别业务/交互层面的复用机会。

---

## Round 1：事实层（只写事实，不评价）

### Engineer — 技术视角

**ahooks 引入情况：**
- ahooks 版本 `^3.9.7`，声明在 `apps/admin/package.json:30`
- 仅 1 处直接 import ahooks：`apps/admin/src/components/FormPage/index.tsx:14` -- `import { useUpdateEffect } from 'ahooks'`
- 1 处 import ahooks 类型定义：`apps/admin/src/hooks/useListRequest.ts:2` -- `import type { Options, Result } from 'ahooks/lib/useRequest/src/types'`
- useRequest 全部来自 `@umijs/max`（umi 内置 ahooks），非直接从 ahooks 导入

**原生 React Hooks 使用规模：**
- useState: ~809 处
- useEffect: ~236 处
- useCallback: ~213 处
- useMemo: ~152 处
- useRef: ~136 处
- useContext: 仅 2 处（SortableRow.tsx:58, department/index.tsx:73）

**重复代码模式 -- loading 状态管理：**
- 74 处 `const [loading, setLoading] = useState(false/true)` 模式
- 典型模式：`setLoading(true) -> try { await api... } catch { } finally { setLoading(false) }`，在 30+ 个文件中重复出现
- 涵盖：hooks 目录（useDict, useDataCache, useDoctors, useDepartments, useFormInitialValues, useStoreWithPermission）、组件（TenantSwitcher, NotificationButton, StoreSwitcher, ImageCropper, ImageUpload, MapLocationPicker）、页面（tenant, appointment, schedule, doctor, platform 等）

**重复代码模式 -- 弹窗/抽屉开关：**
- 70+ 个布尔开关状态声明，分布在约 40 个文件中
- 典型模式：`const [xxxOpen, setXxxOpen] = useState(false)` + `const [currentRecord, setCurrentRecord] = useState(null)`
- 最集中：`schedule/calendar/index.tsx` 有 7 个弹窗状态
- 其他高频：schedule/rule (4个), patient/detail (4个), user/detail (4个), store/index (3个), message/templates (3个)

**重复代码模式 -- debounce：**
- 2 处自实现 debounce 函数（useFormDraft.ts:54-71, useUniqueValidation.ts:47-64，代码完全相同）
- 3 处使用 lodash-es debounce（doctor/form.tsx:17, store/form.tsx:21, utils/proTable.ts:1）

**重复代码模式 -- localStorage 读写：**
- 20+ 个文件直接使用 localStorage.getItem/setItem/removeItem
- 主要键：hospital_current_store, hospital_current_tenant_id, dict_cache_*, form-draft-*, schedule_rule_form_guide_seen, schedule_calendar_view_mode 等
- 无使用 ahooks 的 useLocalStorageState

**重复代码模式 -- ResizeObserver/窗口尺寸：**
- 3 处手动 `new ResizeObserver()`（GanttTimeline, HorizontalTimeline, gantt/index）
- 1 处 window.addEventListener('resize', ...)（screen/index.tsx）
- 无使用 ahooks 的 useResizeObserver

**事件监听模式：**
- 6 处手动 addEventListener/removeEventListener（FullscreenButton, ResizableDivider, screen/index, visibilityAuth）
- 可用 ahooks 的 useEventListener 替代

**定时器模式：**
- 约 25 处 setTimeout/setInterval
- setInterval 轮询：NotificationButton (60s), online-users (2个), screen (2个), WechatLogin (2s)
- setTimeout 倒计时：PhoneLogin 验证码倒计时
- 可用 ahooks 的 useInterval/useTimeout 替代

**详情页共同模式：**
- 6 个详情页遵循 `useParams() + useState(loading) + useEffect(() => { fetchDetail() }, [id])` 模式
- 位置：appointment/detail, tenant/detail, doctor/detail, user/detail, patient/detail, approval/instances/detail

**已有自定义 hooks（apps/admin/src/hooks/，共 15 个文件）：**
- useListPage: ~20 个列表页使用
- useListRequest/usePaginatedRequest: 1 个页面直接使用
- useFormSubmit: 8 个表单页使用
- useFormInitialValues: 8 个表单页使用
- useFormDraft: 0 个页面使用
- useDict/useDictBatch: ~20 个页面使用
- useDataCache: 0 个页面直接 import
- useDepartments: 6 个页面使用
- useDoctors: 6 个页面使用
- useStoreWithPermission: 8 个页面使用
- useResponsive/useTableConfig/useModalConfig: 1 个页面直接 import
- useRetry: 0 个页面直接 import
- useUniqueValidation: 0 个页面直接 import

**弹窗表单共同模式：**
- 典型：open 状态 + currentRecord 状态 + 打开设置 record + 关闭清空 + 提交后 reload 列表
- 约 10+ 处 `const [currentRecord, setCurrentRecord] = useState(null)`

**actionRef 模式：**
- 26 处 `actionRef = useRef<ActionType>()` 声明，分布在列表页中

**数据请求模式：**
- ProTable request prop 模式：28 个文件使用 createListRequest，约 28 个文件内联 async request 函数
- useRequest 直接使用：仅 3 个文件（useListRequest.ts, notification-logs.tsx, notification-quota.tsx）
- 4 处直接使用 fetch()（ImportExport, MapLocationPicker）

**未使用已有 hooks 的表单页（自行管理 loading/data/submit）：**
- tenant/form.tsx, tenant/plan-form.tsx, doctor/form.tsx, doctor/booking-setting-form.tsx, schedule/rule/form.tsx, store/form.tsx, message/form.tsx, system/rule-set-form.tsx, system/role-permissions.tsx, platform/platform-announcement-form.tsx

### PM — 产品视角

**页面清单与业务域：**
- 28 个子目录 + 1 个根级文件，144 个 TSX/TS 文件
- 文件数最多：排班管理 (35), 系统设置 (30), 医生管理 (11), 小程序平台 (9), 内容管理 (6), 仪表盘 (6), 租户管理 (5), 门店管理 (5)

**业务逻辑复用线索：**
- Popconfirm 组件：35 个文件中 141 处引用，几乎覆盖所有列表页操作列
- Modal.confirm：15 处，用于需要额外输入的确认操作（如取消预约带原因）
- 启用/禁用开关：6 个文件使用 Switch 组件 + checkedChildren="启用" unCheckedChildren="禁用"
- 审批操作：2 个独立审批中心页面 + 3 个业务页面内审批操作，统一模式：handleApprove/handleReject + 审批备注弹窗
- 导出功能：3 处已实现（tenant/detail, schedule/statistics, schedule/calendar），2 处占位未实现
- 批量操作：5 个文件使用 rowSelection + selectedRowKeys + 批量操作按钮
- 状态变更操作：停诊/恢复、发布/撤回、租户激活/停用、预约状态变更等统一模式

**数据获取模式：**
- ProTable + createListRequest：28 个文件
- ProTable + 内联 request：约 28 个文件
- useListPage hook：29 个文件
- useEffect + 手动请求：82 处
- useRequest 直接使用：仅 2 个文件

### Designer — 交互视角

**Modal/Drawer 使用统计：**
- ModalForm (ProComponents): 32 处
- Modal (Ant Design): 30 处
- Modal.confirm (命令式): 28 处
- Popconfirm (轻量确认): 55 处
- Drawer: 19 处
- 所有 Modal/Drawer 均使用受控 open/visible 属性，未发现 useModal hook 模式

**Loading 展示方式：**
- Spin 组件：约 70 处（`<Spin spinning={loading}>`）
- 自定义 ListPageSkeleton：8 处使用
- Card loading 属性：多个表单页面
- Button loading 属性：提交按钮

**空状态处理：**
- `<Empty>` 组件约 60 处
- 统一使用 `description="暂无xxx"` 模式

**表单校验方式：**
- 几乎所有表单使用 `rules={[{ required: true, message: '...' }]}` 模式
- 已有 formValidators.ts 工具函数提供复用校验规则
- form.validateFields() 手动校验约 8 处

**状态管理模式：**
- URL 参数传递（useParams/useSearchParams）：主要页面间传递方式
- 全局状态 useModel('@@initialState')：38 处
- Context API：仅 2 处 UI 层部 Context
- Props drilling：子组件通过 props 接收回调和数据

**弹窗/抽屉数据交互模式：**
- 模式 A（最常见）：父组件管理 open + currentRecord 状态
- 模式 B：ModalForm 自带表单生命周期
- 模式 C：命令式 Modal.confirm

**级联选择模式：**
- 门店->科室->医生 三级级联：schedule/custom-form, schedule/rule/form, schedule/rule/index, schedule/gantt, schedule/detail
- 门店->医生 二级级联：schedule/rest-day-form, schedule/suspension
- useDict 字典数据 hook：37 处使用，带 localStorage 缓存

**重复交互模式：**
- "搜索表单 + 列表 + 分页"：60 个 ProTable 使用
- "点击行打开详情/编辑弹窗"：约 20 处
- "批量操作"：5 个文件
- "级联选择"：8+ 个文件

---

## Round 2：辩论层

### 交叉评论投票矩阵

#### 简化投票矩阵（领域主导模式）

| 议题 | Engineer 立场 | Critic 质询 | 最终裁决 |
|------|-------------|------------|---------|
| useRequest 替代 74 处 loading | ~50 处可替代，分 A/B/C 三类 | 数字膨胀，实际 20-30 处 | 裁决：20-30 处 A 类可直接替代，B 类用已有 hook 覆盖 |
| useToggle 替代弹窗开关 | ROI 太低，不建议 | 收益极小，95% 是显式设置非 toggle | 裁决：不采用 useToggle，可选 useModalWithRecord |
| ahooks 双实例风险 | 未提及 | @umijs/max 内置 vs 独立声明可能双实例 | 裁决：需验证，优先级提升至 P0 |
| debounce 迁移行为差异 | 统一替换可行 | trailing/leading 默认值、cancel 行为需确认 | 裁决：迁移前逐个审计选项 |
| 5 个零使用 hooks | useDataCache/useRetry 废弃，其余保留 | 团队"写了不用"的文化问题 | 裁决：废弃 2 个 + 重设计 1 个 + 文档推广 |
| bundle size 影响 | 未分析 | useRequest 是最重 hook，可能 dead weight | 裁决：渐进采用，不全面替换 |
| 优先级区分 | 按 ROI 排序 | 应按"用户体验 vs 开发体验 vs 代码整洁"分层 | 裁决：采纳三档分类 |

### 独到发现

1. **createListRequest 与 useListRequest 功能重叠** -- 两者都提供重试/防抖/loading 延迟，使用场景不同但文档未说明，易致开发者困惑
2. **4 处直接 fetch() 绕过项目 HTTP 客户端** -- ImportExport 和 MapLocationPicker 绕过了 axios 拦截器、错误处理、token 注入，存在安全隐患
3. **formValidators.ts 推广不足** -- 已有复用校验规则但 8 个表单页仍内联校验逻辑
4. **useDict 与 useDataCache 缓存机制重叠** -- useDict 用 localStorage 持久化，useDataCache 用内存 Map，两套机制并存

### Critic 质询

1. **[Critic -> 全体] 质询 1：74 处 loading 数字膨胀**
   - 论据：按钮 loading、表单初始值加载、字典缓存类 loading 不适合 useRequest
   - 级别：普通

2. **[Critic -> 全体] 质询 2：useToggle 收益-成本比被高估**
   - 论据：95% 操作是显式 setXxxOpen(true/false)，toggle 方法几乎不被调用
   - 级别：普通

3. **[Critic -> 全体] 质询 3：ahooks 双实例风险**
   - 论据：@umijs/max re-export useRequest + 独立声明 ahooks ^3.9.7，可能两个实例
   - 级别：🚨 关键

4. **[Critic -> 全体] 质询 4：debounce 迁移行为差异**
   - 论据：自实现 trailing-only vs ahooks 默认 trailing，lodash 可配 leading/maxWait
   - 级别：普通

5. **[Critic -> 全体] 质询 5：5 个高质量 hooks 零使用率根因**
   - 论据：代码质量高、文档完整，零使用率说明是流程/沟通问题
   - 级别：🚨 关键

6. **[Critic -> 全体] 质询 6：bundle size 影响未评估**
   - 论据：useRequest 是最重 hook，全面替换后 dead weight 问题
   - 级别：普通

7. **[Critic -> 全体] 质询 7：替换优先级未按受益者分层**
   - 论据：应区分用户体验提升 / 开发者体验提升 / 代码整洁度提升
   - 级别：普通

### Critic 关键质询追踪

| # | 关键质询内容 | 回应 | 回应是否充分 | 处置 |
|---|------------|------|------------|------|
| 3 | ahooks 双实例风险 | 已验证：无运行时双实例风险。@umijs/max 通过 @ahooksjs/use-request@2.8.15 提供 useRequest，ahooks@3.9.7 仅被 FormPage 的 useUpdateEffect 使用。但存在类型不匹配风险（useListRequest.ts 从 ahooks 导入类型约束 @umijs/max 的运行时） | 充分 | 纳入 P0 行动（修复类型导入） |
| 5 | 5 个 hooks 零使用率 | useDataCache/useRetry 与已有设施重叠应废弃；useUniqueValidation 接口过于简单；useFormDraft/usePaginatedRequest 保留但暂不推广 | 充分 | 纳入 P0 行动 |

---

## Round 3：共识层

### 共识项

1. **废弃 useDataCache 和 useRetry** -- 与 useListRequest/createListRequest 功能重叠，保留会造成混淆
2. **消除重复自实现 debounce** -- useFormDraft.ts 和 useUniqueValidation.ts 中完全相同的 18 行 debounce 代码
3. **统一 ProTable request 模式** -- 13 个"不知道 createListRequest 存在"的内联 request 页面可直接迁移
4. **详情页抽取 useDetail hook** -- 6 个详情页的 useParams+loading+useEffect 模式高度相似
5. **抽取 useExport hook** -- 3 处导出功能遵循相同模式（调 API 拿 blob -> 创建 a 标签 -> 下载）
6. **抽取 useCascadingSelect hook** -- 8+ 个文件的门店->科室->医生级联选择逻辑
7. **setInterval 轮询迁移到 ahooks useInterval** -- 10 处轮询场景，自动清理避免内存泄漏
8. **散落的 localStorage 直接使用统一** -- 8 处未封装的 localStorage 调用
9. **4 处直接 fetch() 迁移到项目 HTTP 客户端** -- 安全隐患需修复
10. **formValidators.ts 推广** -- 8 个表单页内联校验规则可迁移

### 分歧项

1. **useToggle 替代弹窗开关** -- Engineer 认为 ROI 太低（每处仅减少 2 行），Critic 同意。分歧在于是否值得为代码一致性做低 ROI 替换。裁决：不采用。
2. **useRequest 全面替代 loading 管理** -- Engineer 评估 50 处可替代，Critic 认为 20-30 处。分歧在于 B 类（表单提交）是否适合 useRequest manual 模式。裁决：B 类优先用已有 useFormSubmit 覆盖，不引入 useRequest manual 模式。
3. **useLocalStorageState 替代 localStorage** -- 20+ 处中 12 处已封装在 hooks 中，8 处散落。分歧在于 ahooks useLocalStorageState 的跨标签页同步功能是否需要。裁决：admin 后台单标签页场景，用简单封装即可，不引入 useLocalStorageState。

---

## 被低估的优势

1. **已有 useListPage hook 的覆盖范围** -- ~20 个列表页已使用，封装了 handleAction/handleDelete/reload，但团队未充分推广到剩余 ~20 个列表页
2. **createListRequest 工具函数的成熟度** -- 已提供参数转换、重试、防抖、loading 延迟，但 13 个页面不知道其存在
3. **formValidators.ts 的校验规则复用** -- 已提供 phoneRules/emailRules/passwordRules 等，但推广不足

---

## 行动计划（按 ROI 排序）

| 优先级 | 行动 | 成本 | 价值 | 负责 | 状态 |
|--------|------|------|------|------|------|
| P0 | 验证 ahooks 双实例风险 | 1h | 消除技术隐患 | Engineer | |
| P0 | 废弃 useDataCache/useRetry + 更新文档 | 2h | 消除代码混淆 | Engineer | |
| P0 | 消除重复自实现 debounce | 1h | 消除重复代码 | Engineer | |
| P0 | 4 处 fetch() 迁移到项目 HTTP 客户端 | 2h | 安全+一致性 | Engineer | |
| P1 | 抽取 useDetail hook + 6 处迁移 | 10h | 减少详情页重复代码 | Engineer | |
| P1 | 抽取 useExport hook + 3 处迁移 | 3.5h | 统一导出逻辑 | Engineer | |
| P1 | 13 个内联 request 迁移到 createListRequest | 4.3h | 统一 ProTable 模式 | Engineer | |
| P1 | 10 处 setInterval 迁移到 useInterval | 5h | 自动清理+代码简洁 | Engineer | |
| P1 | formValidators.ts 推广到 8 个表单页 | 2.7h | 校验规则复用 | Engineer | |
| P2 | 抽取 useCascadingSelect hook + 8 处迁移 | 12h | 级联选择统一 | Engineer | |
| P2 | 散落 localStorage 统一封装 | 4h | 一致性 | Engineer | |
| P2 | 重设计 useUniqueValidation hook | 3h | 唯一性校验复用 | Engineer | |
| 待定 | useRequest 替代 A 类 loading (20-30 处) | 15h | 减少样板代码 | Engineer | 需确认 ahooks 双实例后再推进 |
| 待定 | useModalWithRecord hook (25 处) | 15.5h | 弹窗状态标准化 | Engineer | ROI 边际，需评估 |

### P0：立即执行（高价值、低成本）

1. **验证 ahooks 双实例风险**（1h）
   - 检查 @umijs/max 的 dist 产物是否内联了 ahooks 代码
   - 确认从 'ahooks' 和 '@umijs/max' 导入的 useRequest 是否是同一实例
   - 如果是双实例，需要将所有 `import { useRequest } from '@umijs/max'` 统一为 `import { useRequest } from 'ahooks'`

2. **废弃 useDataCache/useRetry**（2h）
   - 删除 `apps/admin/src/hooks/useDataCache.ts` 和 `apps/admin/src/hooks/useRetry.ts`
   - 更新 hooks 目录的 README 文档
   - 确认无其他文件引用（已确认 0 个页面使用）

3. **消除重复自实现 debounce**（1h）
   - `useFormDraft.ts:54-71` 和 `useUniqueValidation.ts:47-64` 中完全相同的 debounce 函数
   - 提取为共享的 `utils/debounce.ts` 工具函数，或替换为 ahooks `useDebounceFn`

4. **4 处 fetch() 迁移到项目 HTTP 客户端**（2h）
   - `ImportExport/index.tsx:77,120` -- 文件导出/模板下载
   - `MapLocationPicker/index.tsx:51,76` -- POI 搜索/逆地理编码
   - 统一使用项目的 request 实例，获得 token 注入、错误处理、拦截器能力

### P1：本轮迭代（高价值、中等成本）

1. **抽取 useDetail hook**（10h）
   - 支持 useParams 获取 id + useRequest 加载数据 + loading/error 状态
   - 支持并行加载（Promise.all）和级联加载
   - 迁移 6 个详情页：appointment/detail, tenant/detail, doctor/detail, user/detail, patient/detail, approval/instances/detail

2. **抽取 useExport hook**（3.5h）
   - 封装"调 API 拿 blob -> 创建临时 a 标签 -> 触发下载"模式
   - 迁移 3 处：tenant/detail, schedule/statistics, schedule/calendar

3. **13 个内联 request 迁移到 createListRequest**（4.3h）
   - 这些页面不知道 createListRequest 的存在，直接手写了 request 函数
   - 每处迁移约 20 分钟

4. **10 处 setInterval 迁移到 ahooks useInterval**（5h）
   - NotificationButton (60s), online-users (2个), screen (2个), WechatLogin (2s) 等
   - useInterval 自动处理组件卸载时的 clearInterval

5. **formValidators.ts 推广**（2.7h）
   - 8 个表单页仍内联校验规则，可迁移到已有的 phoneRules/emailRules/stringLengthRules 等

### P2：下个周期规划（中等价值、较高成本）

1. **抽取 useCascadingSelect hook**（12h）
   - 门店->科室->医生级联选择，支持自定义过滤器
   - 8+ 个文件迁移

2. **散落 localStorage 统一封装**（4h）
   - 8 处未封装的 localStorage 直接调用

3. **重设计 useUniqueValidation hook**（3h）
   - 当前接口过于简单，无法覆盖 doctor/form 和 store/form 的复杂唯一性验证需求

### 待定：需用户确认

1. **useRequest 替代 A 类 loading 状态**（15h）
   - 20-30 处简单的"调 API -> 设 loading -> 设 data"模式
   - 需先确认 ahooks 双实例问题已解决
   - 渐进式迁移，不需要一次性完成

2. **useModalWithRecord hook**（15.5h）
   - 25 处"开关 + currentRecord"模式
   - 每处仅减少 2 行代码，ROI 边际

---

## 摘要

**使用模式：** 领域主导（Engineer 主导）

**关键共识：** 10 项
- 废弃 useDataCache/useRetry、消除重复 debounce、统一 ProTable request、抽取 useDetail/useExport/useCascadingSelect hooks、setInterval 迁移、localStorage 统一、fetch() 迁移、formValidators 推广

**关键分歧：** 3 项
- useToggle 采用（裁决：不采用）、useRequest 全面替代范围（裁决：仅 A 类 20-30 处）、useLocalStorageState 采用（裁决：不引入）

**Top 3 P0 行动：**
1. 验证 ahooks 双实例风险（1h）-- 技术前提，不确认则后续迁移可能无效
2. 废弃 useDataCache/useRetry + 消除重复 debounce（3h）-- 立即消除代码冗余和混淆
3. 4 处 fetch() 迁移到项目 HTTP 客户端（2h）-- 安全+一致性修复

**Critic 关键洞察：**
- ahooks 双实例风险是所有迁移工作的技术前提，必须先验证
- 5 个零使用 hooks 反映的是团队流程问题（写了不用），而非工具问题，单纯引入 ahooks 不能解决采用率问题
- 替换工作应按"用户体验 > 开发者体验 > 代码整洁"三档排优先级，避免在低收益项上浪费时间

**总成本估算：**
- P0：6h（立即执行）
- P1：25.5h（本轮迭代）
- P2：19h（下周期规划）
- 待定：30.5h（需用户确认）

---

## 附录：模式切换日志

| 时间 | 从 | 到 | 原因 |
|------|-----|-----|------|
| | | | |
