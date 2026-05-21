# appointment-booking-system — 自适应多智能体研究画布

> 协作模式：集中调度
> 日期：2026-05-21
> 审查目标：Admin 前端未接入后端接口的实施规划

---

## 模式选择

**选定模式：** 集中调度

**选择理由：** 综合项目评审，无明确主导领域深入需求。集中调度可快速收敛且输出完整度最高，Team Lead 直接裁决效率最佳。

---

## Round 1：事实层（只写事实，不评价）

### PM — 产品视角

**产品定位：**
- SaaS 多租户医院预约挂号系统，支持多门店/分院、多科室、多医生排班预约
- 目标用户：平台管理员（超管）、门店管理员、门店员工
- 已有 25 个页面目录、130 个 tsx 文件、10 个路由模块

**功能完成度：**
- 后端 50 个 router.py 文件，注册 67 条路由
- admin 前端已接入约 35 个模块（含部分端点接入）
- 完全缺失的非用户端模块：8-10 个
- 用户端专属模块（无需 admin 页面）：3 个（user_favorites, notification_preferences, doctor_portal）

**已实现但 admin 未接入的后端模块清单：**

| 后端模块 | 路由前缀 | 端点数 | 权限要求 | admin 状态 |
|---------|---------|--------|---------|-----------|
| platform_announcements | /platform-announcements | 7 | require_platform_admin | 无页面、无路由、无 API 模块 |
| support_tickets | /support-tickets | 9 | require_permission 细粒度 | 无页面、无路由、无 API 模块 |
| backup | /backup/{tenant_id}/* | 3 | require_platform_admin | 无页面、无路由、无 API 模块 |
| analytics | /analytics/* | 5 | get_current_admin | 无页面、无路由、无 API 模块 |
| unified_message | /unified-messages | 2 个发送端点未接入 | message:send | 已有模板/规则页面，发送功能缺失 |
| websocket | /ws/* | 3 | - | 无页面（实时通知） |
| tenants | /tenants | 12 个端点未接入 | 多种 | 已有基础页面，缺标签/迁移/密码策略/使用趋势 |
| schedules | /schedules | 4 个发布/撤回端点未接入 | - | 已有排班页面，缺发布/撤回/冲突检测 |
| data import/export | /data/* | 14 个端点未接入 | - | 仅排班导入导出有使用 |
| export | /export/* | 3 | - | 全部未接入 |
| settings/sms | /settings/sms | 2 | - | 设置页面缺 SMS Tab |
| admin permissions | /admin/permissions | 3 | - | 权限管理页面仅有读取 |
| rule-sets performance | /rule-sets/performance | 3 | super_admin | 未接入 |
| audit-logs export | /audit-logs/export | 1 | - | 未接入 |

**用户端专属模块（排除）：**
- user_favorites：get_current_user 依赖，纯患者端收藏功能
- notification_preferences：get_current_user 依赖，用户通知偏好
- doctor_portal：医生端专属聚合路由
- points：用户端积分系统

**目标用户线索：**
- 平台管理员：platform_announcements、backup、tenant 迁移/密码策略、analytics
- 门店管理员：support_tickets、schedules 发布/撤回、data import/export、export
- 系统管理员：settings/sms、admin permissions、rule-sets performance、audit-logs export

---

### Designer — 用户视角

**页面清单与结构：**
- 22 个列表页、17 个列表+表单页、6 个详情页、2 个设置页、1 个仪表盘、13 个特殊页面
- ProComponents 使用频率：ProTable（最频繁）、PageContainer、ProForm 系列、ProDescriptions

**交互模式统计：**
- 标准列表页模式：PageContainer + ProTable + createListRequest + useListPage + OperationGroup
- 表单页模式：FormPage（封装 PageContainer + ProForm + FooterToolbar）
- 设置页模式：Tab 切换 + TAB_PATH_TO_KEY/TAB_KEY_TO_PATH 映射 + 独立 Tab 路由
- 详情页模式：Card + Tabs + 多个 ProTable
- 确认操作：轻量 Popconfirm vs 重量 ConfirmModal（需输入 CONFIRM）
- 导入导出：ImportExport 组件（Dropdown 菜单）

**现有参考页面：**
- platform-announcements 建议参考：content/notice.tsx（ProTable + FormPage）
- support-tickets 建议参考：feedback/index.tsx（ProTable + Drawer + ModalForm）
- SMS 配置建议参考：在 system/settings.tsx 添加新 Tab

**组件一致性事实：**
- 所有列表页使用 ProTable，columns 定义为 ProColumns 类型
- 操作列使用 valueType: 'option'，固定右侧 fixed: 'right'
- 状态列使用 valueEnum 映射
- 日期时间列使用 valueType: 'dateTime'
- 搜索条件 hideInTable: true，非搜索列 search: false

---

### Engineer — 技术视角

**存储层事实：**
- 后端使用 PostgreSQL 16 + SQLAlchemy 2.x (async)
- 前端无本地存储需求（除 auth token）

**核心引擎事实：**
- 后端 FastAPI，统一认证体系（get_current_account / get_current_account_with_role / get_optional_account）
- 两种权限守卫：require_platform_admin（平台管理员）、require_permission("module:action")（细粒度）

**API/协议事实：**
- packages/api 共 46 个模块文件，index.ts 导出约 40 个模块对象
- 标准 API 模块模式：import request -> 定义 Params/Data 接口 -> 导出 xxxApi 对象
- 参数约定：前端 camelCase -> API 层转 snake_case
- 分页参数：page + page_size（API 层），ProTable 传入 current + pageSize
- 统一响应格式：{ code: 0, message: "success", data: {...} }
- 分页响应自动转换为 ProTable 格式

**缺失 API 模块（需新建）：**
- platform_announcements（7 端点，含发布/撤回状态机）
- support_tickets（9 端点，含分配/解决/关闭/重开操作链）
- backup（3 端点，涉及文件上传 UploadFile + 流式下载 StreamingResponse）
- analytics（5 端点，含匿名埋点 POST /track + /batch 无需认证）

**安全机制事实：**
- backup 涉及文件上传（JSON），需校验文件类型和大小
- platform_announcements 含 target_tenant_ids 字段，需校验租户存在性
- support_tickets 含 attachments 字段，需文件上传支持

**依赖和模块耦合事实：**
- tenant 模块被几乎所有业务模块引用
- store -> department -> doctor -> schedule -> appointment 依赖链
- data import/export 依赖各业务模块的数据结构

**工作量估算参考：**
- 典型列表页：~166 行代码（feedback/index.tsx）
- 典型表单页：~490 行代码（doctor/form.tsx）
- 典型设置页：~1112 行代码（system/settings.tsx）
- 复杂权限管理页：~646 行代码（role-permissions.tsx）

---

## Round 2：辩论层

### 交叉评论投票矩阵

#### 简化投票矩阵（集中调度模式）

| 议题 | Team Lead 立场 | Critic 质询 | 最终裁决 |
|------|---------------|------------|---------|
| API 模块存在性 | PM 标记 export/websocket/analytics "无 API 模块" 有误 | 质询 1：export.ts/websocket.ts/statistics.ts 已存在 | 接受 Critic 纠正，修正分类 |
| 缺失模块数量 | PM 声称"8-10 个完全缺失" | 质询 2：实际分两类（完全缺失 4 个 + 部分缺失 8 个） | 接受，重新分类为 4+8 |
| 代码质量前提 | 三方均未检查 | 质询 3：已有代码质量是扩展前提 | 部分接受，列入待定项 |
| Designer 覆盖面 | 仅 2 个模块有参考建议 | 质询 4：backup/analytics/export/websocket 无设计指引 | 接受，补充设计指引 |
| 用户端模块排除 | PM 排除 4 个模块 | 质询 5：points 可能有 admin 管理需求 | 部分接受，points 归入待定 |
| 工作量估算 | Engineer 用行数估算 | 质询 6：非标准模式被低估 | 接受，重新估算 |
| 模块间依赖 | 三方均未分析 | 质询 7：依赖约束影响实施顺序 | 接受，补充依赖分析 |
| websocket 必要性 | PM 列为缺失 | 质询 8：admin 可能不需要实时通知 | 接受，降级为待定 |
| 前提假设（关键） | 假设所有端点都应有 admin 页面 | 质询 9：前提未论证 | 接受，修正范围：仅规划 admin 相关端点 |
| 已接入模块状态（关键） | 35 个模块"已接入" | 质询 10："已接入"不等于"可用" | 部分接受，export API 双轨问题列入待定 |

### 独到发现

1. **export API 双轨问题**：`packages/api/src/modules/export.ts`（3 个函数，admin 零使用）与 `ImportExport` 组件使用的 `dataApi`（`packages/api/src/modules/data.ts`）是两套独立的导出机制。前者是简单下载触发器，后者是完整的导入导出 URL 定义。需要明确两者关系。
2. **analytics 双模块问题**：后端 `analytics`（行为追踪）和 `statistics`（业务统计）是两个独立模块。statistics 已完全接入 admin dashboard，analytics 的追踪基础设施通过 `@hospital/shared` 的 tracker 已实现，但 /logs 和 /tenant-activity 管理端点未接入。
3. **platform_announcements 是唯一纯平台管理员模块**：所有 7 个端点均要求 `require_platform_admin`，与 tenant/store 无关，是最干净的独立模块。

### Critic 质询

**[Critic -> 全体] 质询 1：PM 的"无 API 模块"声明存在事实错误**
- 论据：export.ts、websocket.ts、statistics.ts 已存在于 packages/api/src/modules/
- 要求回应：PM
- 级别：普通
- Team Lead 裁决：**接受**。修正分类：export/websocket 属于"API 已有但 admin 未使用"，analytics 属于"部分已有（statistics 已接入，behavior logs 未接入）"

**[Critic -> 全体] 质询 2："8-10 个完全缺失模块"数字来源不明**
- 论据：实际应分两类——完全无页面的 4 个 + 已有页面但缺端点的 8 个
- 要求回应：PM
- 级别：普通
- Team Lead 裁决：**接受**。重新分类为：完全缺失 4 个（platform_announcements, support_tickets, backup, analytics behavior logs）+ 部分缺失 8 个

**[Critic -> 全体] 质询 3：三方都忽略了"已有代码质量"前提条件**
- 论据：行数不等于质量，技术债可能影响新模块实现
- 要求回应：Engineer
- 级别：普通
- Team Lead 裁决：**部分接受**。代码质量审计超出本次审查范围，但列入待定项供用户决策

**[Critic -> 全体] 质询 4：Designer 参考页面建议覆盖面严重不足**
- 论据：backup/analytics/export/websocket 无设计指引
- 要求回应：Designer
- 级别：普通
- Team Lead 裁决：**接受**。在行动计划中为每个模块补充设计指引

**[Critic -> 全体] 质询 5：排除用户端专属模块缺乏论证**
- 论据：points 可能有 admin 管理需求
- 要求回应：PM
- 级别：普通
- Team Lead 裁决：**部分接受**。user_favorites/notification_preferences/doctor_portal 确为用户端，排除合理。points 归入待定

**[Critic -> 全体] 质询 6：Engineer 工作量估算方法论有偏差**
- 论据：非标准 CRUD 模式被低估，安全工作未纳入
- 要求回应：Engineer
- 级别：普通
- Team Lead 裁决：**接受**。重新估算：标准列表页 4-6h，状态机工作流页 12-16h，文件操作页 8-12h，图表页 10-14h

**[Critic -> 全体] 质询 7：三方遗漏模块间依赖对实施顺序的约束**
- 论据：依赖链未分析，影响实施顺序
- 要求回应：Engineer / PM
- 级别：普通
- Team Lead 裁决：**接受**。在行动计划中标注依赖关系

**[Critic -> 全体] 质询 8：websocket 对 admin 的必要性未经论证**
- 论据：admin 工作流是"查看-操作-刷新"，非实时事件驱动
- 要求回应：PM
- 级别：普通
- Team Lead 裁决：**接受**。websocket 降级为待定，需用户确认 admin 是否有实时通知需求

**[Critic -> 全体] 质询 9（关键）：审查范围前提假设未被论证**
- 论据："所有端点都应有 admin 页面"未经验证
- 要求回应：PM / Designer / Engineer
- 级别：关键
- Team Lead 裁决：**接受**。修正范围：仅规划 admin 角色（平台管理员/门店管理员/系统管理员）实际需要的端点，排除纯用户端/医生端端点

**[Critic -> 全体] 质询 10（关键）：35 个已接入模块的真实状态未经验证**
- 论据："已接入"不等于"可用"，export API 双轨问题
- 要求回应：PM / Engineer
- 级别：关键
- Team Lead 裁决：**部分接受**。export API 双轨问题列入待定。已接入模块的全面质量审计超出本次范围，但建议作为独立任务

### Critic 关键质询追踪

| # | 关键质询内容 | 三方回应摘要 | 回应是否充分 | 处置 |
|---|------------|------------|------------|------|
| 1 | 审查范围前提假设未被论证 | Team Lead 修正范围：仅规划 admin 相关端点 | 是 | 纳入计划：已修正范围 |
| 2 | 35 个已接入模块真实状态未验证 | Team Lead 承认超出本次范围 | 部分 | 待定：需用户确认是否单独审计 |

---

## Round 3：共识层

### 共识项

1. **平台公告管理（platform_announcements）是最优先的新建模块**
   - 结论：7 个端点，纯平台管理员权限，独立无依赖，参考 content/notice.tsx 模式
   - 建议行动：新建 API 模块 + 页面 + 路由
   - 成本估算：API 模块 2h + 列表页 4h + 表单页 6h + 路由/权限 1h = **13h**
   - 负责：Engineer（API）+ Designer（页面）

2. **工单支持（support_tickets）是第二个优先的新建模块**
   - 结论：9 个端点，含状态机工作流（分配/解决/关闭/重开），参考 feedback/index.tsx 但需扩展
   - 建议行动：新建 API 模块 + 列表页 + 详情页 + 状态操作
   - 成本估算：API 模块 3h + 列表页 6h + 详情/状态操作 12h + 路由/权限 2h = **23h**
   - 负责：Engineer（API + 状态机）+ Designer（页面）

3. **排班发布/撤回应在已有排班页面上扩展**
   - 结论：4 个端点（publish/batch-publish/batch-withdraw/conflicts），已有排班日历页面
   - 建议行动：在排班日历页面添加发布/撤回按钮和冲突检测
   - 成本估算：8h
   - 负责：Engineer

4. **SMS 配置应在 settings.tsx 添加新 Tab**
   - 结论：2 个端点（GET/PUT），参考现有 Tab 模式
   - 建议行动：在 settings.tsx 添加 SMS Tab
   - 成本估算：4h
   - 负责：Engineer

5. **各列表页面的导入导出按钮应批量添加**
   - 结论：data.ts 已定义 14 个导入导出 URL，admin 页面仅排班使用
   - 建议行动：在医生、患者、科室、门店等列表页面添加 ImportExport 组件
   - 成本估算：每个页面 2h × 6 个页面 = **12h**
   - 负责：Engineer

6. **权限管理页面应补充 CRUD 功能**
   - 结论：3 个端点（create/batch-create/delete），已有权限管理页面仅有读取
   - 建议行动：在权限管理页面添加创建/删除功能
   - 成本估算：6h
   - 负责：Engineer

### 分歧项

1. **websocket 实时通知是否需要**
   - 各方立场：
     - PM：列为缺失模块
     - Engineer：技术可行但非必要
     - Critic：admin 工作流不需要实时通知
   - 裁决/建议：降级为"待定"，需用户确认。如果需要，轮询比 WebSocket 更简单
   - 决策依据：admin 典型工作流是"查看-操作-刷新"，无实时事件驱动场景

2. **points 积分系统是否有 admin 管理需求**
   - 各方立场：
     - PM：排除为用户端模块
     - Critic：可能有 admin 管理需求（查看/调整/配置）
   - 裁决/建议：归入"待定"，需用户确认
   - 决策依据：需要产品决策，非技术判断

3. **export API 双轨问题如何处理**
   - 各方立场：
     - Engineer：export.ts 和 data.ts 是两套机制
     - Critic：两者关系不明确
   - 裁决/建议：归入"待定"，建议统一为一套机制
   - 决策依据：避免维护两套导出逻辑

---

## 被低估的优势

1. **已有导入导出基础设施完备**：data.ts 定义了 14 个导入导出 URL，ImportExport 组件已封装好，添加到其他页面只需 2h/页面
2. **统一认证体系成熟**：require_platform_admin 和 require_permission 两种守卫已就绪，新模块接入权限零成本
3. **ProComponents 模式高度一致**：所有列表页使用相同模式，新页面可快速复制

---

## 行动计划（按 ROI 排序）

| 优先级 | 行动 | 成本 | 价值 | 负责 | 状态 |
|--------|------|------|------|------|------|
| P0 | 平台公告管理（新建 API + 页面） | 13h | 高 | Engineer + Designer | 待开始 |
| P0 | 排班发布/撤回（扩展已有页面） | 8h | 高 | Engineer | 待开始 |
| P0 | SMS 配置 Tab（扩展 settings.tsx） | 4h | 高 | Engineer | 待开始 |
| P1 | 工单支持（新建 API + 页面） | 23h | 高 | Engineer + Designer | 待开始 |
| P1 | 各列表页导入导出按钮（批量添加） | 12h | 中 | Engineer | 待开始 |
| P1 | 租户详细功能（标签/迁移/密码策略/使用趋势） | 16h | 中 | Engineer | 待开始 |
| P1 | 简单导出（预约/患者/排班，扩展已有页面） | 6h | 中 | Engineer | 待开始 |
| P2 | 权限管理 CRUD | 6h | 中 | Engineer | 待开始 |
| P2 | analytics 行为日志 + 租户活跃度 | 14h | 中 | Engineer + Designer | 待开始 |
| P2 | tenant 数据备份/恢复 | 12h | 中 | Engineer + Designer | 待开始 |
| P2 | 审计日志导出 | 2h | 低 | Engineer | 待开始 |
| P2 | rule-sets 性能监控 | 8h | 低 | Engineer | 待开始 |
| 待定 | websocket 实时通知 | 待评估 | 待定 | 待定 | 需用户确认 |
| 待定 | points 积分管理 | 待评估 | 待定 | 待定 | 需用户确认 |
| 待定 | export API 双轨统一 | 待评估 | 待定 | Engineer | 需用户确认 |
| 待定 | 已接入 35 个模块质量审计 | 待评估 | 待定 | Engineer | 需用户确认 |
| 待定 | unified-messages 管理端发送 | 4h | 低 | Engineer | 需用户确认 |

### P0：立即执行（高价值、低成本）

1. **平台公告管理** — 新建 `packages/api/src/modules/platform-announcement.ts` + `apps/admin/src/pages/platform/announcement.tsx` + 路由注册 + access.ts 权限。参考 content/notice.tsx 模式，含发布/撤回状态机。成本 13h。
2. **排班发布/撤回** — 在已有排班日历页面（schedule/calendar/）添加发布/撤回按钮和冲突检测弹窗。需要扩展 scheduleApi 模块。成本 8h。
3. **SMS 配置 Tab** — 在 settings.tsx 添加 SMS Tab，使用 TAB_PATH_TO_KEY 映射。需要扩展 settingsApi 模块。成本 4h。

### P1：本轮迭代（高价值、中等成本）

1. **工单支持** — 新建 `packages/api/src/modules/support-ticket.ts` + `apps/admin/src/pages/support/` 目录。含列表页（ProTable + 状态筛选）、详情页（Drawer + 状态操作按钮）、统计卡片。状态机：pending -> processing -> resolved -> closed，支持 reopen。成本 23h。
2. **各列表页导入导出** — 在医生、患者、科室、门店、系统用户、操作日志列表页面添加 ImportExport 组件。每个页面 2h × 6 = 12h。
3. **租户详细功能** — 在已有租户详情页添加标签管理、迁移预检/执行、密码策略配置、使用趋势图表。成本 16h。
4. **简单导出** — 在预约列表、患者列表页面添加导出按钮，使用 exportApi 已有函数。成本 6h。

### P2：下个周期规划（中等价值、较高成本）

1. **权限管理 CRUD** — 在已有权限管理页面添加创建/批量创建/删除功能。成本 6h。
2. **analytics 行为日志 + 租户活跃度** — 新建页面，含日志列表（ProTable）和统计图表（需引入图表库如 @ant-design/charts）。成本 14h。
3. **tenant 数据备份/恢复** — 在租户详情页添加备份导出（StreamingResponse 下载）和恢复导入（文件上传 + 预检）。成本 12h。
4. **审计日志导出** — 在审计日志页面添加导出按钮。成本 2h。
5. **rule-sets 性能监控** — 在规则组管理页面添加性能指标面板。成本 8h。

### 待定：需用户确认

1. **websocket 实时通知** — admin 是否有实时通知需求？如果需要，建议用轮询而非 WebSocket
2. **points 积分管理** — 积分系统是否有 admin 管理需求（查看/调整/配置）？
3. **export API 双轨统一** — export.ts 和 data.ts 两套导出机制是否需要统一？
4. **已接入模块质量审计** — 35 个已接入模块是否需要全面质量检查？
5. **unified-messages 管理端发送** — 管理端是否需要主动发送通知功能？

---

## 摘要

**使用模式：** 集中调度

**关键共识：**
- 6 项达成共识（P0 3 项 + P1 4 项中排班/SMS/导入导出/权限已明确）
- 3 项分歧（websocket/points/export 双轨）归入待定

**关键分歧：**
- websocket 对 admin 的必要性（Critic 质疑，PM 坚持）
- points 是否需要 admin 管理（Critic 质疑，PM 排除）
- export API 双轨问题（Engineer 发现，需产品决策）

**Top 3 P0 行动：**
1. 平台公告管理 — 新建 API + 页面，13h，平台管理员核心功能
2. 排班发布/撤回 — 扩展已有页面，8h，排班流程关键环节
3. SMS 配置 Tab — 扩展 settings.tsx，4h，系统设置完整性

**Critic 关键洞察：**
- 审查范围需修正：仅规划 admin 相关端点，排除纯用户端/医生端
- 已接入 35 个模块的真实状态未验证，export API 存在双轨问题
- 非标准 CRUD 模式（backup 文件操作、analytics 图表、support_tickets 状态机）的工作量被低估

---

## 已接入模块质量审计（2026-05-21）

审计范围：35 个已接入 admin 页面 + 共享 hooks/utils/components，共 60+ 文件。

### 统计摘要

| 问题类别 | 数量 | 严重度 |
|---------|------|--------|
| 潜在运行时崩溃 | 3 | Critical |
| 缺失错误处理（静默 catch） | 10 | High |
| `any` 类型泛滥 | 17 | Medium |
| 不一致的模式/风格 | 6 | Medium |
| 死代码/未使用导入 | 7 | Low |
| 重复代码 | 2 | Low |
| 硬编码值 | 3 | Low |
| 缺失加载状态 | 2 | Low |

### Critical — 潜在运行时崩溃

| # | 文件 | 行号 | 问题 |
|---|------|------|------|
| C1 | `system/log.tsx` | 283 | `JSON.parse(currentLog.params)` 无 try-catch，畸形 JSON 导致弹窗崩溃 |
| C2 | `message/index.tsx` | 104-107 | `TYPE_MAP[r.messageType]` 无 fallback，未知类型导致 `.color`/`.text` 访问 undefined |
| C3 | `examination-report/index.tsx` | 68-71 | 重复 `useModel('@@initialState')` + 误用 useState 初始化器 |

### High — 缺失错误处理（TOP 10）

| # | 文件 | 行号 | 说明 |
|---|------|------|------|
| H1 | `system/analytics.tsx` | 111, 311, 429 | 3 个 Tab 的 fetchData 均 `catch { // ignore }` |
| H2 | `system/rule-sets.tsx` | 178 | 性能数据加载静默失败 |
| H3 | `system/email-recipients.tsx` | 29, 34, 41 | 3 层 `.catch(() => {})` 链式静默吞错 |
| H4 | `platform/platform-announcement-form.tsx` | 35 | 编辑加载详情静默失败 |
| H5 | `system/checkin-audit-logs.tsx` | 107 | ProTable request 无 try-catch |
| H6 | `system/settings.tsx` | 266 | `!storeId` 分支缺少 try-catch |
| H7 | `patient/detail.tsx` | 109, 122 | loadPatient/loadDoctors 仅 console.error |
| H8 | `appointment/statistics.tsx` | 74 | loadData 仅 console.error |
| H9 | `message/form.tsx` | 32-38 | useEffect 两处 `.catch(() => {})` |
| H10 | `medical-record/index.tsx` | 204 | ProTable request 无 try-catch |

### Medium — `any` 类型（TOP 10）

| # | 文件 | 行号 | 说明 |
|---|------|------|------|
| M1 | `system/settings.tsx` | 138 | `stores` state 为 `any[]` |
| M2 | `system/settings.tsx` | 292-417 | 8 个 onFinish 均为 `(values: any)` |
| M3 | `system/rule-set-form.tsx` | 952-954 | 主表单状态全 `any` |
| M4 | `system/rule-sets.tsx` | 31-32 | perfStats/slowQueries 为 `any` |
| M5 | `message/form.tsx` | 27, 30 | recipientRules `any[]`、formRef `any` |
| M6 | `doctor/form.tsx` | 55, 154 | formRef `any`、handleSubmit `any` |
| M7 | `appointment/detail.tsx` | 59 | `data as any` 强转 |
| M8 | `store/form.tsx` | 93 | handleSubmit `values: any` |
| M9 | `blacklist.tsx` | 77, 240 | store filter/map 双重 `any` |
| M10 | `waitlist/index.tsx` | 129-191 | 4 处 store/doctor `any` |

### Medium — 不一致模式

| # | 文件 | 问题 |
|---|------|------|
| I1 | `notification-logs.tsx` | 直接 `import { message }` 而非 `App.useApp()` |
| I2 | `booking-notice.tsx` | 同上 + raw Modal 而非 ModalForm |
| I3 | `role-form.tsx` | 同上 |
| I4 | `store/fee-types.tsx` | 未使用 `useListPage()` hook |
| I5 | `store/index.tsx` | 同上 |
| I6 | `appointment/list.tsx` + `detail.tsx` | STATUS_MAP 重复定义 |

### Low — 死代码/重复/硬编码

| # | 文件 | 问题 |
|---|------|------|
| L1 | `settings.tsx:142` | `_wechatConfig` state 从未读取 |
| L2 | `rule-set-audit.tsx:97` | `_loading` state 从未使用 |
| L3 | `visit-type-config.tsx:16` | `_config` state 从未读取 |
| L4 | `suspension.tsx:55` | `useAccess()` 返回值未捕获 |
| L5 | `rest-day-form.tsx:34` | 同上 |
| L6 | `useRetry.ts:242` | `createRetryFunction` 空壳占位 |
| L7 | `useUniqueValidation.ts` + `useFormDraft.ts` | 重复自定义 debounce |
| L8 | `rule-set-form.tsx:1507-1692` | submitter.render 重复 ~77 行 |
| L9 | `user.tsx:34` | 密码 `'123456'` 硬编码 |
| L10 | `online-users.tsx:177` | 30s 刷新间隔硬编码 |
| L11 | `banner-form.tsx:44` | `(contentApi as any).getBannerDetail` 绕过类型 |
| L12 | `errorHandler.ts:257` | 访问私有静态字段 |

---
