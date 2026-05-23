# 患者端随访功能 — 自适应多智能体研究画布

> 协作模式：集中调度
> 日期：2026-05-23
> 审查目标：患者端随访功能设计与实现方案

---

## 模式选择

**选定模式：** 集中调度

**选择理由：** 患者端随访功能需求方向明确（患者查看自己的随访信息），跨职能决策点有限且可在 Team Lead 裁决中收敛。集中调度可快速产出可执行方案。

---

## Round 1：事实层（只写事实，不评价）

### PM — 产品视角

**产品定位：**
- 项目为全栈医院预约挂号系统，SaaS 多租户架构，支持多门店/分院/多科室/多医生排班预约
- 诊后随访模块已在 admin 端和 doctor 端完成实现（24 个 API 端点，3 个 Service 类）
- 患者端（H5 + 小程序）尚无随访功能入口和页面

**功能完成度：**
- 后端 API：24 个端点已实现，4 个端点支持 patient_id 筛选（`router.py:244,298,415,439`）
- API 客户端：`getPatientTasks` 和 `getPatientRecords` 方法已存在（`follow-up.ts:212,246`）
- admin 端：4 个页面已完成（plans/tasks/records/statistics）
- doctor 端：2 个页面已完成（tasks/records）
- 患者端 H5：0 个页面，0 条路由
- 患者端小程序：0 个页面

**目标用户线索：**
- 患者端 H5 使用 antd-mobile 5.34.0，UI 复杂度低，面向普通患者
- 患者端小程序使用 Taro 4 + NutUI，支持微信生态
- 认证层面：`get_current_user_or_admin` 允许患者 token 通过（`auth_deps.py:242-258`），走 User 表路径（`auth_unified.py:549-551`）
- Patient 模型与 User 模型通过 `user_id` FK 关联（`user.py:46`），一个 User 可拥有多个 Patient（家庭成员），`is_default` 标记默认就诊人

### Designer — 用户视角

**页面清单与结构：**
- 患者端 H5 共 22 条路由、28 个 .tsx 文件、6264 行代码
- 页面模块：home/department/doctor/booking/appointment/waitlist/records/profile/message/feedback/login/register/search/settings
- 无 follow-up 相关页面

**交互模式统计：**
- Loading：三种模式共存 — `Skeleton.Paragraph`（首页/详情页）、`useState(true)` + 条件渲染（列表页）、无显式 loading
- 空状态：统一使用 antd-mobile `Empty` 组件，判断条件 `items.length === 0 && !loading`
- 下拉刷新：`PullToRefresh` 组件包裹列表区域（appointment/records/waitlist/message）
- 上拉加载：`InfiniteScroll` 组件，`page` + `pageSize` + `hasMore` 状态管理
- 详情页：渐变色 Header + 卡片堆叠（appointment）、NavBar + 卡片列表（records）
- Tab 切换：`Tabs` 组件用于列表筛选（appointment/waitlist/message）

**组件一致性事实：**
- antd-mobile 组件引用约 144 次（NavBar/Toast/Empty/Dialog/Skeleton/Input/Form 等）
- 自定义 UI 组件引用约 56 次（Card/Button/SectionLabel/GradientText 等）
- 自定义组件位于 `components/ui/` 目录，业务组件位于 `components/` 目录

**响应式设计事实：**
- 使用 Tailwind CSS 3.4.19 进行布局
- antd-mobile 组件默认移动端适配

### Engineer — 技术视角

**存储层事实：**
- FollowUpTask 模型：`patient_id` FK -> patients.id, NOT NULL, indexed（`follow_up_task.py:22`）
- FollowUpRecord 模型：`patient_id` FK -> patients.id, NOT NULL, indexed（`follow_up_record.py:17`）
- Patient 模型：`user_id` FK -> users.id, NOT NULL（`user.py:46`），一个 User 可有多个 Patient
- FollowUpTask 复合索引：`(doctor_id, status, scheduled_date)`（`follow_up_task.py:12`）
- 无 `(patient_id, status, scheduled_date)` 复合索引

**核心引擎事实：**
- `FollowUpTaskService.get_list()` 支持 `patient_id` 参数（`service.py:262,284-285`）
- `FollowUpRecordService.get_list()` 支持 `patient_id` 参数（`service.py:433,452-453`）
- Service 层已具备患者维度查询能力，无需修改

**API/协议事实：**
- 现有患者可用端点：`GET /tasks/patient/{patient_id}`（`router.py:298`）、`GET /records/patient/{patient_id}`（`router.py:439`）
- 缺少"从 token 自动获取当前患者的端点" — `GET /tasks/my` 仅取 `doctor_id`（`router.py:278`），对患者返回空
- 所有端点使用 `get_current_user_or_admin` 认证，患者 token 可通过
- **安全缺口**：现有端点不验证请求者身份与 URL 中 patient_id 的匹配关系 — 患者 A 可查患者 B 的数据

**安全机制事实：**
- 认证：JWT token，`hospital_token` key，`Authorization: Bearer` header
- 患者 token payload：`sub` = User.id，`type` = 非 "admin"/"doctor"，`role_type` = "user"
- `AccountInfo.to_dict()` 返回 `id`（User.id）、`role_type`、`nickname`，不含 `patient_id`
- 患者端 H5 自动注入 `store_id` 到 GET 请求（`patient-h5/request.ts:85-95`）

**依赖和模块耦合事实：**
- 患者端 H5 复用 `@hospital/api` 包（`package.json:14`），`followUpApi` 对象可直接使用
- 患者端小程序使用 `@hospital/api` 的 Taro 适配器
- Patient ↔ User 关系：`Patient.user_id` -> `User.id`（一对多）
- 需要通过 `User.id` → `Patient.id` 的映射才能使用现有 `getPatientTasks(patientId)` 方法

---

## Round 2：辩论层

### 交叉评论投票矩阵（简化版 — 集中调度模式）

| 议题 | 裁决者立场 | Critic 质询 | 最终裁决 |
|------|-----------|------------|---------|
| 患者端随访功能范围 | v1 只读查看，不含患者自提交 | 质询 1/5：需求未定义，核心交互遗漏 | 采纳 Critic 意见，明确定义为只读查看（v1），患者自提交归入 v2 |
| 安全缺口是阻断项 | 同意，新增端点而非修补现有端点 | 质询 3：Broken Access Control，合规风险 | 采纳，P0 优先级解决 |
| User→Patient 一对多处理 | v1 使用默认就诊人（is_default=True） | 质询 4：复杂度被低估 | 采纳，v1 简化处理，v2 支持切换就诊人 |
| "24 端点"表述误导 | 同意，需区分 admin/doctor 端点与患者可用端点 | 质询 2：管理层能力误报为用户层 | 采纳，实际患者安全可用端点为 0，需新增 |
| H5 vs 小程序差异化 | v1 仅 H5，小程序 v2 跟进 | 质询 7：未讨论差异化策略 | 采纳，分阶段实施 |
| 缺少复合索引 | 单列索引足够，患者数据量小 | 质询 8：未量化影响 | 不采纳，患者活跃任务 < 20 条，单列索引够用 |
| /tasks/overdue 全局访问 | 预存问题，非本次引入 | 质询 9：全局权限缺失 | 不在本次范围内修复，但记录为已知问题 |

### 独到发现

1. **User→Patient 映射是跨层问题**：后端（User.id → Patient.id 查询）、前端（就诊人选择器 UI）、产品（家庭成员随访数据归属）三个层面都需要处理。这不是单纯的"加个参数"问题。
2. **现有 followUpApi 方法设计面向 admin/doctor**：`getPatientTasks(patientId)` 要求调用方已知 patientId，但患者端需要的是"自动从 token 解析"的端点。API 客户端也需要新增方法。
3. **随访提醒与消息系统的集成点**：已有 Celery 定时任务 `send_follow_up_reminders` 创建 Message 记录（`tasks/follow_up_task.py`），患者端消息页面（`/message`）已实现。随访提醒可通过现有消息通道触达患者。

### 🚨 Critic 关键质询追踪

| # | 关键质询内容 | 三方回应摘要 | 回应是否充分 | 处置 |
|---|------------|------------|------------|------|
| 1 | 需求未定义却声称明确 | Team Lead 裁决：定义 v1 用户故事为"患者查看自己的随访任务和记录（只读）"，v2 患者自提交 | 是 | 纳入计划 |
| 3 | 安全缺口是阻断项（Broken Access Control） | Team Lead 裁决：新增 `/follow-up/my-tasks` 和 `/follow-up/my-records` 端点，从 token 自动解析 User.id → Patient.id，内置权限校验 | 是 | 纳入计划（P0） |

### Critic 质询

1. [Critic → 全体] 质询 1：PM 声称"需求明确"但未定义用户故事
   - 论据：患者是只读查看还是需要提交？家庭成员数据如何处理？
   - 要求回应：PM
   - 级别：🚨 关键
   - **裁决回应**：v1 定义为只读查看。用户故事：(1) 患者查看"我的待办随访"列表（按状态筛选）；(2) 查看随访任务详情（医生、科室、计划日期、当前状态）；(3) 查看已完成的随访记录（医生反馈、患者状况评估）。家庭成员：v1 使用默认就诊人（is_default=True），v2 支持切换。

2. [Critic → 全体] 质询 2：24 个端点表述误导
   - 论据：实际患者安全可用端点为 0
   - 要求回应：PM
   - 级别：普通
   - **裁决回应**：同意。患者端需要新增 2 个专用端点。

3. [Critic → 全体] 质询 3：安全缺口是阻断项
   - 论据：OWASP A01:2021 Broken Access Control，医疗数据合规风险
   - 要求回应：Engineer + PM
   - 级别：🚨 关键
   - **裁决回应**：新增端点内置权限校验，从 token 的 User.id 查询关联 Patient.id，不暴露 patient_id 给前端 URL。

4. [Critic → 全体] 质询 4：User→Patient 一对多复杂度
   - 论据：需要 2 次串行请求 + 就诊人选择器 UI
   - 要求回应：PM + Designer + Engineer
   - 级别：普通
   - **裁决回应**：v1 简化 — 使用默认就诊人，后端一次查询 `Patient.query.filter_by(user_id=user_id, is_default=True)`。v2 支持就诊人切换。

5. [Critic → 全体] 质询 5：遗漏核心交互——记录提交
   - 论据：随访本质是双向的
   - 要求回应：Designer
   - 级别：普通
   - **裁决回应**：v1 只读。患者自提交（血压/血糖/症状反馈）归入 v2，需要表单设计 + 数据校验 + 文件上传。

6. [Critic → 全体] 质询 6：撤回（数字一致）

7. [Critic → 全体] 质询 7：H5 vs 小程序差异化
   - 论据：小程序有订阅消息能力，H5 没有
   - 要求回应：PM + Designer
   - 级别：普通
   - **裁决回应**：v1 仅 H5。小程序 v2 跟进，利用微信订阅消息推送随访提醒。

8. [Critic → 全体] 质询 8：复合索引影响未量化
   - 论据：患者数据量小，单列索引可能够用
   - 要求回应：Engineer
   - 级别：普通
   - **裁决回应**：不采纳。患者活跃任务 < 20 条，单列 patient_id 索引足够。

9. [Critic → 全体] 质询 9：/tasks/overdue 全局访问
   - 论据：跨角色权限缺失
   - 要求回应：Engineer
   - 级别：普通
   - **裁决回应**：预存问题，非本次引入。记录为已知技术债，不在本次修复。

10. [Critic → 全体] 质询 10：集中调度依据不成立
    - 论据：多个问题需要跨职能决策
    - 要求回应：PM
    - 级别：普通
    - **裁决回应**：部分同意。决策点在 Team Lead 裁决中已收敛，不构成切换模式的理由。

---

## Round 3：共识层

### ✅ 共识项

1. **议题：v1 功能范围 — 只读查看**
   **结论：** 患者端随访 v1 为只读模式，患者查看自己的待办任务和已完成记录。患者自提交（血压/血糖等）归入 v2。
   **建议行动：** 新建 2 个后端端点 + 2 个前端页面 + 1 个 profile 入口
   **成本估算：** 16h（后端 4h + 前端 10h + 联调 2h）
   **优先级：** P0

2. **议题：安全方案 — 新增患者专用端点**
   **结论：** 不复用现有 `/tasks/patient/{patient_id}` 端点（无权限校验）。新增 `/follow-up/my-tasks` 和 `/follow-up/my-records` 端点，从 token 自动解析 User.id → Patient.id，内置权限校验。
   **建议行动：** router.py 新增 2 个端点，service 层无需修改（已有 patient_id 参数）
   **成本估算：** 4h（含安全校验逻辑）
   **优先级：** P0

3. **议题：User→Patient 映射 — v1 使用默认就诊人**
   **结论：** 后端查询 `Patient.query.filter_by(user_id=user_id, tenant_id=tenant_id, is_default=True)`。若无默认就诊人，返回空结果并提示"请先添加就诊人"。
   **建议行动：** 后端端点内置映射逻辑，前端无需就诊人选择器
   **成本估算：** 1h（包含在端点开发中）
   **优先级：** P0

4. **议题：前端页面 — 任务列表 + 记录列表 + 详情**
   **结论：** 新建 `follow-up/tasks.tsx`（任务列表）、`follow-up/records.tsx`（记录列表）、`follow-up/task-detail.tsx`（任务详情含关联记录）。复用现有交互模式（PullToRefresh + InfiniteScroll + Empty + Skeleton）。
   **建议行动：** 参照 records 页面和 appointment 页面的模式开发
   **成本估算：** 10h（3 个页面 + 路由配置 + profile 入口）
   **优先级：** P0

5. **议题：API 客户端新增方法**
   **结论：** 在 `packages/api/src/modules/follow-up.ts` 新增 `getMyTasks()` 和 `getMyRecords()` 方法，无需 patientId 参数（后端从 token 解析）。
   **建议行动：** 新增 2 个 API 方法 + 对应类型
   **成本估算：** 1h
   **优先级：** P0

### ⚡ 分歧项

1. **议题：是否需要复合索引 `(patient_id, status, scheduled_date)`**
   **各方立场：**
   - Engineer：Round 1 提出缺少索引
   - Critic：质疑未量化影响
   - Team Lead：患者数据量小（< 20 条活跃任务），单列索引足够
   **裁决：** 不添加。单列 patient_id 索引已有，数据量不需要复合索引。
   **决策依据：** 患者维度数据量远小于医生维度，过度索引增加写入开销。

---

## 被低估的优势

1. **消息系统已就绪**：Celery 任务 `send_follow_up_reminders` 已创建 Message 记录（`tasks/follow_up_task.py`），患者端消息页面（`/message`）已实现。随访提醒可通过现有消息通道零成本触达患者。
2. **Service 层已支持 patient_id 查询**：`FollowUpTaskService.get_list()` 和 `FollowUpRecordService.get_list()` 均接受 patient_id 参数，新增端点只需在 router 层调用现有 service 方法。
3. **@hospital/api 复用**：患者端 H5 已配置 `@hospital/api` 包，新增 API 方法后可直接使用，无需额外配置。

---

## 行动计划（按 ROI 排序）

| 优先级 | 行动 | 成本 | 价值 | 负责 | 状态 |
|--------|------|------|------|------|------|
| P0 | 后端：新增 `/follow-up/my-tasks` 和 `/follow-up/my-records` 端点（含安全校验 + User→Patient 映射） | 4h | 高 | Engineer | |
| P0 | API 客户端：新增 `getMyTasks()` / `getMyRecords()` 方法 | 1h | 高 | Engineer | |
| P0 | 前端 H5：任务列表页 `follow-up/tasks.tsx` | 4h | 高 | Engineer | |
| P0 | 前端 H5：记录列表页 `follow-up/records.tsx` | 3h | 高 | Engineer | |
| P0 | 前端 H5：任务详情页 `follow-up/task-detail.tsx` | 3h | 高 | Engineer | |
| P0 | 前端 H5：路由配置 + profile 入口 + 首页快捷入口 | 1h | 高 | Engineer | |
| P1 | 已知技术债：`/tasks/overdue` 端点缺少权限校验 | 2h | 中 | Engineer | |
| P2 | 患者端小程序跟进随访页面 | 8h | 中 | Engineer | |
| P2 | 患者自提交随访记录（血压/血糖/症状） | 16h | 高 | PM + Designer + Engineer | |
| P2 | 就诊人切换支持（查看家庭成员随访数据） | 8h | 中 | PM + Engineer | |

### P0：立即执行（高价值、低成本）

1. **后端新增患者专用端点**（4h）
   - `GET /follow-up/my-tasks`：从 token 解析 User.id → 查询默认 Patient.id → 调用 `FollowUpTaskService.get_list(patient_id=...)` → 返回结果
   - `GET /follow-up/my-records`：同上逻辑，调用 `FollowUpRecordService.get_list(patient_id=...)`
   - 安全校验：若 User 无关联 Patient，返回空结果 + 提示信息
   - 路由放于 `/tasks/my` 和 `/records/my` 之前（避免路径冲突）

2. **API 客户端新增方法**（1h）
   - `getMyTasks(params?)` → `GET /follow-up/tasks/my-patient`
   - `getMyRecords(params?)` → `GET /follow-up/records/my-patient`
   - 新增 `FollowUpMyTasksParams` / `FollowUpMyRecordsParams` 类型

3. **前端 H5 — 任务列表页**（4h）
   - 路径：`/follow-up/tasks`
   - 交互：PullToRefresh + InfiniteScroll + Tabs（全部/待办/已完成/已跳过）+ Empty
   - 列表项：任务编号、医生、科室、计划日期、状态 Tag
   - 点击跳转详情

4. **前端 H5 — 记录列表页**（3h）
   - 路径：`/follow-up/records`
   - 交互：PullToRefresh + InfiniteScroll + Empty
   - 列表项：医生、随访日期、患者状况 Tag、内容摘要

5. **前端 H5 — 任务详情页**（3h）
   - 路径：`/follow-up/tasks/:id`
   - 布局：NavBar + 卡片堆叠（参照 appointment/detail.tsx 模式）
   - 内容：任务信息卡片 + 关联随访记录列表

6. **路由配置 + 入口**（1h）
   - `.umirc.ts` 新增 follow-up 路由组
   - `profile/index.tsx` 的 menuItems 新增"我的随访"入口
   - `home/index.tsx` 首页菜单新增随访快捷入口（可选）

### P1：本轮迭代

1. **修复 /tasks/overdue 权限问题**（2h）
   - 添加 tenant_id 筛选（利用 middleware 的 ContextVar）
   - 或限制为 admin 角色专用

### P2：下个周期规划

1. 患者端小程序跟进随访页面（8h）
2. 患者自提交随访记录功能（16h）
3. 就诊人切换支持（8h）

---

## 摘要

**使用模式：** 集中调度

**关键共识：**
- 5 项达成共识（功能范围、安全方案、User→Patient 映射、前端页面、API 客户端）

**关键分歧：**
- 1 项（复合索引），已裁决为不添加

**Top 3 P0 行动：**
1. 后端新增 `/follow-up/my-tasks` 和 `/follow-up/my-records` 端点（含安全校验）— 4h
2. 前端 H5 新增任务列表 + 记录列表 + 详情 3 个页面 — 10h
3. API 客户端新增 `getMyTasks` / `getMyRecords` 方法 — 1h

**Critic 关键洞察：**
- 安全缺口（Broken Access Control）是阻断项，必须在 UI 开发前解决 — 已通过新增专用端点方案覆盖
- 需求定义是逻辑起点 — 已明确定义 v1 只读 + 默认就诊人的用户故事

**总成本估算：** 16h（P0 全部项）

---

## 附录：模式切换日志

| 时间 | 从 | 到 | 原因 |
|------|-----|-----|------|
| 无切换 | | | |
