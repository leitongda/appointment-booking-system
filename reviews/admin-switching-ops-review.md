# appointment-booking-system — 自适应多智能体研究画布

> 协作模式：集中调度
> 日期：2026-04-02
> 审查目标：Admin 端各角色的租户切换、门店切换操作的优化空间分析

---

## 模式选择

**选定模式：** 集中调度

**选择理由：** 综合优化审查，涉及产品/UX/技术三方视角，无明确单一主导领域。集中调度模式可快速收敛且输出完整度最高。

---

## Round 1：事实层（只写事实，不评价）

### PM — 产品视角

**角色定义与权限范围：**
- 系统定义 5 种角色：SUPER_ADMIN（超级管理员）、PLATFORM_ADMIN（平台管理员）、TENANT_ADMIN（租户管理员）、STORE_ADMIN（门店管理员）、STORE_USER（门店用户）
- 来源：`apps/server/app/common/deps.py:254-260`

**各角色租户切换场景差异：**
- 租户列表 API 权限要求 `require_platform_admin()`，仅平台管理员可调用
- TenantSwitcher 组件始终渲染，无显式角色隐藏逻辑
- 租户列表 pageSize=100，缓存 TTL 5 分钟
- 来源：`apps/admin/src/components/TenantSwitcher/index.tsx:43-70`, `apps/server/app/modules/tenants/router.py:197-248`

**各角色门店切换场景差异：**
- 超级管理员：可查看所有门店，`canViewAllStores: true`，可切换到"全部门店"模式
- 门店管理员绑定多个门店时：`canViewAllStores: true`，可查看所有绑定门店
- 单门店用户：静态显示，无切换功能
- 来源：`apps/admin/src/components/HeaderActions/index.tsx:62-65`, `apps/server/app/modules/admin/helpers.py:47-57`

**管理员-门店绑定机制：**
- `admin_stores` 多对多关系表，含 `is_manager` 字段
- 创建管理员时，`current_store_id` 默认取绑定门店的第一个
- 来源：`apps/server/app/models/admin.py:18-26, 89-95`, `apps/server/app/modules/admin/service_admins.py:206-242`

**订阅计划与配额限制：**
- SubscriptionPlan 定义 max_stores、max_admins、max_doctors、max_appointments_per_month、max_storage_mb
- Tenant 模型可覆盖计划默认配额，`get_effective_max_xxx()` 方法优先使用覆盖值
- 来源：`apps/server/app/models/tenant.py:16-153`

### Designer — 用户视角

**切换器 UI 结构与交互：**
- 租户切换器：Popover + BankOutlined 图标，面板宽度 300px，名称最大宽度 120px
- 门店切换器：Popover + ShopOutlined/门店 Logo，面板宽度 280px，名称最大宽度 160px
- 两者的选中样式一致：蓝色背景 + 蓝色文字 + CheckOutlined 图标
- 两者排列顺序：租户切换器 → 门店切换器 → 刷新 → 通知 → 全屏
- 来源：`apps/admin/src/components/TenantSwitcher/index.tsx`, `apps/admin/src/components/HeaderActions/index.tsx`

**表单保护机制：**
- 门店切换有表单保护：路径匹配 `/create|edit` 时弹出确认框
- 租户切换无表单保护：直接执行切换，不检测表单状态
- 切换到"全部门店"有表单保护
- 来源：`apps/admin/src/components/HeaderActions/index.tsx:104-108, 162-184`

**切换操作步骤：**
- 租户切换：点击切换器 → 点击目标租户 → 页面刷新（1 次点击 + 自动刷新）
- 门店切换：点击切换器 → 点击目标门店 → API 调用 → 页面刷新（1 次点击 + 自动刷新）
- 切换过程有全屏遮罩层（白色半透明 + 毛玻璃 + Spin + 文字提示）

**跨 Tab 同步：**
- 监听 3 个 localStorage key：hospital_token、hospital_current_tenant_id、currentStore
- 3 种事件类型：auth-change、tenant-change、store-change
- 300ms 防抖间隔
- 所有跨 Tab 弹框配置为不可关闭（closable: false, maskClosable: false）
- 来源：`packages/shared/src/utils/crossTabSync.ts`, `apps/admin/src/app.tsx:154-212`

**门店管理功能区：**
- 4 个功能：签到二维码、诊费设置、复诊规则、编辑门店
- 基于权限动态过滤（store:list / store:update）
- 所有功能基于 currentStore?.id 操作
- 来源：`apps/admin/src/components/HeaderActions/index.tsx:219-261`

**响应式设计：**
- 代码中未发现明确的响应式断点处理
- 名称超出时使用省略号截断
- 来源：组件 less 文件

### Engineer — 技术视角

**前端请求拦截器：**
- X-Tenant-ID 从 localStorage `hospital_current_tenant_id` 读取，自动注入所有请求
- store_id 不在 header 中传递，后端通过数据库 `admins.current_store_id` 读取
- 来源：`apps/admin/src/utils/request.ts:76-81`

**后端租户上下文中间件：**
- 识别优先级：X-Tenant-ID Header > X-Tenant-Code Header > 子域名 > 路径前缀
- 使用 ContextVar 实现异步上下文隔离
- 每个请求开始时清除之前的上下文
- 平台管理员接口排除租户识别
- 来源：`apps/server/app/middleware/tenant_context.py:166-197`

**门店切换 API：**
- PUT /admin/me/current-store：更新数据库 `admin.current_store_id`
- 权限校验：`check_store_access()` 检查绑定门店列表
- 前端 localStorage `currentStore` 与数据库 `current_store_id` 双重存储
- 来源：`apps/server/app/modules/admin/router_auth_token.py:118-143`

**并发与竞态条件：**
- 前端使用 `switching` 状态标记防止重复点击
- 后端 ContextVar 自动隔离每个异步请求
- 快速连续切换时：前端有防护，后端有隔离
- 来源：`TenantSwitcher/index.tsx:106-115`, `HeaderActions/index.tsx:162-184`

**安全机制：**
- 租户越权防护：非超管用户的请求租户 ID 必须与账号租户一致
- 门店越权防护：check_store_access() 检查绑定门店列表
- Token 黑名单包含租户维度：`token:blacklist:{tenant_id}:{token_hash}`
- 会话隔离：`session:admin:{tenant_id}:{admin_id}`
- 租户状态校验：禁用(0)和欠费(2)状态阻止访问
- 来源：`apps/server/app/common/deps.py:277-293, 433-453`

**状态持久化：**
- localStorage 存储：hospital_token、hospital_current_tenant_id、currentStore
- 切换后统一执行 `window.location.reload()` 重新初始化应用状态
- 门店切换先调 API 更新数据库，再写 localStorage，再刷新页面
- 来源：各切换器组件

---

## Round 2：辩论层

### 交叉评论投票矩阵

#### 简化投票矩阵（集中调度模式）

| 议题 | 裁决者立场 | Critic 质询 | 最终裁决 |
|------|-----------|------------|---------|
| 租户切换缺少表单保护 | 认同，是疏忽 | 🚨 质询 1：租户切换无 API 确认的数据一致性风险 | P0：补齐表单保护 + API 验证 |
| 租户切换与门店切换架构不一致 | 认同，需要统一 | 质询 4：store_id 不在 header 传递 | P1：统一切换架构 |
| TenantSwitcher 对非平台管理员无意义 | 认同，需要角色控制 | 质询 8：始终渲染的冗余 | P0：按角色控制可见性 |
| canViewAllStores 语义混淆 | 认同，命名误导 | 质询 2：字段名的语义混淆 | P1：重命名 + 语义澄清 |
| 全量 reload 作为状态转换 | 认同，可靠但粗暴 | — | P2：渐进式替换 |
| 跨 Tab 同步弹框不可关闭 | 认同，阻断性过强 | 质询 5：同步的用户体验问题 | P1：提供"稍后刷新"选项 |
| 租户列表无搜索功能 | 认同，大量租户时体验差 | — | P0：添加搜索过滤 |
| 门店管理功能区与切换器耦合 | 认同，信息密度高 | — | P2：解耦功能区 |
| Token 多租户生命周期 | 当前无根本缺陷 | 🚨 质询 10：Token 黑名单租户维度 | 待定：需架构评审 |
| 响应式设计缺失 | 优先级低（后台系统） | 质询 6：响应式设计优先级被高估 | 不纳入行动计划 |

### 独到发现

1. **租户切换和门店切换采用了两种完全不同的架构模式**（前端主导 vs 前后端协作），这种不一致性在多角色系统中增加了维护成本和认知负担
2. **切换操作对"正在进行的操作"的保护粒度不一致**：门店切换保护表单页面，但租户切换不保护；两者都不保护非表单页面的内存状态（如列表筛选、分页位置）
3. **跨 Tab 同步的"强制刷新"模式**与多角色工作流存在冲突：超级管理员可能需要同时操作多个租户/门店的管理页面

### Critic 质询

1. [Critic → 全体] 🚨 质询 1：租户切换无 API 确认的数据一致性风险
   - 论据：租户切换直接写 localStorage 再刷新，不经后端验证；门店切换先调 API
   - 要求回应：Engineer
   - 级别：🚨 关键
   - **裁决者回应**：确认事实。后端在每次请求中校验 tenant_id 一致性（deps.py:277-293），但存在 reload 后到首个 API 返回前的 UI 时间窗口风险。纳入 P1 行动计划。

2. [Critic → PM] 质询 2：canViewAllStores 语义混淆
   - 论据：字段名暗示"查看所有门店"，实际含义是"显示门店切换器/可看多个绑定门店"
   - 要求回应：PM
   - 级别：普通
   - **裁决者回应**：认同命名不当。纳入 P1。

3. [Critic → Designer] 质询 3：表单保护的不一致设计
   - 论据：租户切换破坏性更大却无保护，门店切换有保护
   - 要求回应：Designer
   - 级别：普通
   - **裁决者回应**：认同，是疏忽而非有意设计。纳入 P0。

4. [Critic → Engineer] 🚨 质询 4：store_id 不在 header 传递
   - 论据：每次请求通过数据库读取 current_store_id，可能存在性能瓶颈
   - 要求回应：Engineer
   - 级别：🚨 关键
   - **裁决者回应**：性能问题不存在（current_store_id 随 Admin 对象一次性加载），但前后端双重存储的一致性问题成立。纳入 P1。

5. [Critic → PM & Designer] 质询 5：跨 Tab 同步的用户体验问题
   - 论据：不可关闭弹框阻断性过强，无"拒绝同步"选项
   - 要求回应：PM & Designer
   - 级别：普通
   - **裁决者回应**：认同。纳入 P1。

6. [Critic → 全体] 质询 6：响应式设计的优先级被高估
   - 论据：Admin 后台系统典型场景是桌面端，无移动端访问频率数据
   - 要求回应：全体
   - 级别：普通
   - **裁决者回应**：认同。Admin 后台以桌面端为主，响应式不纳入行动计划。

7. [Critic → Engineer] 质询 7：SubscriptionPlan 配额检查在切换流程中的位置
   - 论据：切换操作是否检查配额限制？三方均未提及
   - 要求回应：Engineer
   - 级别：普通
   - **裁决者回应**：配额检查在 CRUD 操作层面生效（如创建门店时检查 max_stores），不在切换流程中。这是合理的设计——切换不应被配额阻断。

8. [Critic → PM] 质询 8：TenantSwitcher 始终渲染的冗余
   - 论据：非平台管理员看到的切换器是空白/报错/隐藏？
   - 要求回应：PM
   - 级别：普通
   - **裁决者回应**：API 403 后组件 catch error 并设空列表，切换器显示"选择租户"但无选项。用户体验混乱。纳入 P0。

9. [Critic → 全体] 质询 9：竞品对比标准缺失
   - 论据：所有发现基于内部代码审查，无外部参考
   - 要求回应：全体
   - 级别：普通
   - **裁决者回应**：认同。本审查以系统内部一致性为主要标准，竞品对比作为后续专项。

10. [Critic → Engineer] 🚨 质询 10：Token 黑名单租户维度的实际生效范围
    - 论据：多租户场景下 Token 生命周期不清晰
    - 要求回应：Engineer
    - 级别：🚨 关键
    - **裁决者回应**：Admin 的 tenant_id 是单值，Token 不含 tenant_id。切换租户不改变 Token。黑名单的租户维度主要用于隔离超管 logout 场景。无根本性缺陷，但需架构评审确认边界情况。纳入待定。

### 🚨 Critic 关键质询追踪

| # | 关键质询内容 | 回应摘要 | 回应是否充分 | 处置 |
|---|------------|---------|------------|------|
| 1 | 租户切换无 API 确认，数据一致性风险 | 后端每次请求校验 tenant_id，但存在 UI 时间窗口 | 是 | 纳入 P1 行动计划 |
| 2 | store_id 不在 header 传递，性能隐患 | 性能无问题（随 Admin 加载），但双重存储一致性成立 | 是 | 纳入 P1 行动计划 |
| 3 | Token 黑名单租户维度的实际生效范围 | Token 不含 tenant_id，黑名单租户维度用于超管隔离 | 部分 | 待定：需架构评审确认边界 |

---

## Round 3：共识层

### ✅ 共识项

1. **议题：租户切换缺少表单保护**
   **结论：** 租户切换破坏性（跨租户全量数据变更）大于门店切换（同租户内门店数据变更），但反而缺少表单保护。这是一个疏忽。
   **建议行动：** 在 TenantSwitcher 中复用 StoreSwitcher 的 `isOnFormPage()` + Modal.confirm 逻辑
   **成本估算：** 1h
   **优先级：** P0

2. **议题：TenantSwitcher 对非平台管理员显示无意义组件**
   **结论：** 非平台管理员看到"选择租户"但无法操作，造成用户困惑
   **建议行动：** 根据用户角色控制 TenantSwitcher 可见性（仅平台管理员/超级管理员可见）
   **成本估算：** 1h
   **优先级：** P0

3. **议题：租户列表无搜索/过滤功能**
   **结论：** pageSize=100 无搜索，当租户数量增长后，平台管理员难以快速定位目标租户
   **建议行动：** 在 TenantSwitcher 面板中添加 Search 输入框，支持按租户名称/编码过滤
   **成本估算：** 2h
   **优先级：** P0

4. **议题：租户切换与门店切换架构不一致**
   **结论：** 租户切换纯前端（localStorage → reload），门店切换前后端协作（API → localStorage → reload）。两种模式的可靠性、可审计性不同
   **建议行动：** 新增 `PUT /admin/me/current-tenant` API，租户切换经后端验证后再刷新；统一前后端协作模式
   **成本估算：** 4h
   **优先级：** P1

5. **议题：canViewAllStores 语义混淆**
   **结论：** 字段名暗示"查看所有门店"，实际含义是"可使用门店切换器"。STORE_ADMIN 绑定多门店时为 true，但并不能查看所有门店
   **建议行动：** 重命名为 `canSwitchStores` 或 `showStoreSwitcher`，同时更新前后端所有引用
   **成本估算：** 2h
   **优先级：** P1

6. **议题：跨 Tab 同步弹框阻断性过强**
   **结论：** 不可关闭弹框在多 Tab 工作场景下打断用户操作，且无法拒绝同步
   **建议行动：** 将 Modal.confirm 改为 Notification.notice，提供"立即刷新"和"忽略"两个选项；对于 auth-change（logout）保留强制弹框
   **成本估算：** 3h
   **优先级：** P1

7. **议题：localStorage key 命名不一致**
   **结论：** `hospital_current_tenant_id` 有 hospital_ 前缀，`currentStore` 无前缀
   **建议行动：** 统一为 `hospital_current_store`，更新所有引用（含跨 Tab 同步监听 key）
   **成本估算：** 1h
   **优先级：** P1

### ⚡ 分歧项

1. **议题：是否应替换 window.location.reload() 为 React 状态驱动的无刷新切换**
   **各方立场：**
   - PM：reload 可靠但体验粗暴，用户感知到"页面闪烁"
   - Designer：reload 导致所有内存状态丢失（筛选条件、分页位置、未保存的非表单数据）
   - Engineer：reload 是当前最安全的方案，无刷新切换需要处理大量状态清理逻辑
   **裁决：** 当前保持 reload 不变，作为 P2 规划渐进式替换。先从"租户/门店切换后记住当前页面路径"开始
   **决策依据：** 无刷新切换的工程量大且风险高（状态残留、缓存不一致），当前 reload 的可靠性价值高于体验优化

---

## 被低估的优势

1. **后端租户/门店越权防护体系完善** — deps.py 中的租户一致性校验 + 门店访问检查 + 租户状态校验形成了三层防护，即使前端 localStorage 被篡改也能有效阻断
2. **跨 Tab 同步机制的存在本身是加分项** — 很多 Admin 系统不处理多 Tab 状态同步，本项目通过 crossTabSync + 防抖 + 事件分类实现了基础同步能力
3. **切换过程的视觉反馈设计** — 全屏遮罩 + Spin + 文字提示的组合让用户明确知道"正在切换"，避免了用户在切换过程中误操作

---

## 行动计划（按 ROI 排序）

| 优先级 | 行动 | 成本 | 价值 | 负责 | 状态 |
|--------|------|------|------|------|------|
| P0 | 租户切换添加表单保护 | 1h | 高 | Designer | 已完成 |
| P0 | TenantSwitcher 按角色控制可见性 | 1h | 高 | PM + Engineer | 已完成 |
| P0 | 租户切换器添加搜索过滤 | 2h | 高 | Designer + Engineer | 已完成 |
| P1 | 统一租户切换架构（添加后端 API） | 4h | 高 | Engineer | 已完成 |
| P1 | 重命名 canViewAllStores | 2h | 中 | PM + Engineer | 已完成 |
| P1 | 跨 Tab 同步弹框改为非阻断式通知 | 3h | 高 | Designer + Engineer | 已完成 |
| P1 | 统一 localStorage key 命名 | 1h | 低 | Engineer | 已完成 |
| P2 | 渐进式替换 reload（先记住路径） | 4h | 中 | Engineer + Designer | 规划中 |
| P2 | 门店管理功能区与切换器解耦 | 4h | 中 | Designer | 规划中 |
| 待定 | Token 多租户生命周期架构评审 | — | 待定 | Engineer | 需用户确认 |

### P0：立即执行（高价值、低成本）

1. **租户切换添加表单保护** — 复用 StoreSwitcher 的 `isOnFormPage()` + Modal.confirm，在租户切换前检查表单状态。[成本：1h，负责：Designer]

2. **TenantSwitcher 按角色控制可见性** — 根据 `isSuperAdmin` 和 `isPlatformAdmin` 控制 TenantSwitcher 是否渲染，非平台管理员完全隐藏。[成本：1h，负责：PM + Engineer]

3. **租户切换器添加搜索过滤** — 在 Popover 面板中添加 Input.Search，支持按租户名称和编码实时过滤列表。[成本：2h，负责：Designer + Engineer]

### P1：本轮迭代（高价值、中等成本）

1. **统一租户切换架构** — 新增 `PUT /admin/me/current-tenant` API，租户切换经后端验证租户存在性和状态后再返回，前端收到成功响应后写 localStorage 并 reload。[成本：4h，负责：Engineer]

2. **重命名 canViewAllStores** — 后端 helpers.py + 前端 access.ts + HeaderActions 中统一重命名为 `canSwitchStores`，语义更准确。[成本：2h，负责：PM + Engineer]

3. **跨 Tab 同步改为非阻断式通知** — tenant-change 和 store-change 事件改为 Notification（右上角通知），提供"立即刷新"按钮；auth-change（logout）保留强制 Modal。[成本：3h，负责：Designer + Engineer]

4. **统一 localStorage key 命名** — `currentStore` → `hospital_current_store`，更新 crossTabSync 监听 key、StoreSwitcher 读写、app.tsx 引用。[成本：1h，负责：Engineer]

### P2：下个周期规划（中等价值、较高成本）

1. **渐进式替换 reload** — 第一阶段：切换后记住当前路径（排除 create/edit），reload 后自动导航回原页面。第二阶段：核心页面实现 React 状态驱动的无刷新切换。[成本：4h+，负责：Engineer + Designer]

2. **门店管理功能区解耦** — 将签到二维码、诊费设置、复诊规则、编辑门店从 StoreSwitcher Popover 中抽出，独立为侧边栏入口或当前页面的快捷操作栏。[成本：4h，负责：Designer]

### 待定：需用户确认

1. **Token 多租户生命周期架构评审** — Critic 指出 Token 黑名单的租户维度在超管多租户切换场景下的边界行为不清晰。需要确认：是否需要支持超管同时在多个 Tab 操作不同租户？如果是，当前的 Token 黑名单机制可能需要重新设计。[成本：待评估，负责：Engineer]

---

## 摘要

**使用模式：** 集中调度

**关键共识：**
- 7 项达成共识（3 项 P0 + 4 项 P1）

**关键分歧：**
- 1 项需要权衡（reload vs 无刷新切换）

**Top 3 P0 行动：**
1. 租户切换添加表单保护（1h） — 复用门店切换的保护逻辑
2. TenantSwitcher 按角色控制可见性（1h） — 非平台管理员隐藏
3. 租户切换器添加搜索过滤（2h） — 支持名称/编码搜索

**Critic 关键洞察：**
- 租户切换和门店切换采用了两种截然不同的架构模式（前端主导 vs 前后端协作），这种不一致性是多个优化点的根源
- Token 黑名单的租户维度设计在超管多租户场景下可能产生意外行为，需要专项评审

---

## 附录：模式切换日志

| 时间 | 从 | 到 | 原因 |
|------|-----|-----|------|
| — | — | — | 未切换模式 |
