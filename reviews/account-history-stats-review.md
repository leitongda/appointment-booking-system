# 账号历史记录与使用统计 - 自适应评审画布

> 协作模式：集中调度
> 执行深度：标准
> 风险升级因子：无
> 日期：2026-06-25
> 审查目标：添加账号历史记录、账号使用情况统计（使用时长、次数、设备情况）

---

## Phase 0 审批记录

**基础复杂度：** 标准（8-12 文件，跨 2-3 模块）
**风险升级因子：** 无（读取型统计，不涉及认证变更/支付/数据删除）
**最终深度：** 标准
**协作模式：** 集中调度
**选定 Agent：**
- PM 标准版
- Designer 标准版
- Engineer 标准版
- 评审组：挑战者A + 挑战者B + 审计者

**预估 Token：** ~120K
**执行轮次：** Round 1-3
**跳过轮次：** 无
**用户批准：** 已批准

---

## Round 1：事实层（只写事实，不评价）

### PM - 产品视角

**产品定位：**
- 项目为"全栈医院预约挂号系统，SaaS 多租户架构" | 来源: CLAUDE.md:1-4 | 证据级别: E2 | 置信度: High

**功能完成度（账号历史/统计相关）：**

| 功能 | 状态 | 来源 |
|------|------|------|
| Admin 登录历史记录（写入） | 已实现 | helpers.py:177-225 |
| Admin 登录历史查询 API | 已实现 | router_monitoring.py:187-235 |
| Admin 在线用户列表 | 已实现 | router_monitoring.py:59-80 |
| Admin 强制下线 | 已实现 | router_monitoring.py:83-127 |
| Admin 用户状态（在线/离线） | 已实现 | router_monitoring.py:130-184 |
| Admin 超时退出自动记录 | 未实现（枚举存在但无写入逻辑） | models/admin.py:141 |
| Doctor 登录历史记录 | 未实现（仅有 last_login_at/ip） | doctors/router.py:174-220 |
| User/Patient 登录历史记录 | 未实现（连 last_login_at/ip 都无） | models/user.py |
| 登录失败记录 | 未实现 | - |
| 账号使用统计（登录次数/频率/时段） | 未实现 | - |
| 登录历史导出 | 未实现 | - |
| 登录地理位置 | 未实现 | - |
| 多设备同时登录检测/限制 | 未实现 | - |
| 异常登录告警 | 未实现 | - |

**竞品功能对比（SaaS 管理后台常见功能）：**

| 功能 | 本项目 | 行业常见 |
|------|--------|---------|
| 登录历史记录 | 仅 Admin | 全角色 |
| 在线用户列表 | 仅 Admin | 全角色 |
| 登录失败记录 | 无 | 有 |
| 使用频率统计 | 无 | 有 |
| 登录时段分布 | 无 | 有 |
| 异常登录告警 | 无 | 有 |
| 登录历史导出 | 无 | 有 |

**目标用户：**
- 使用角色：平台超管 + 拥有 `system:log` 权限的租户管理员
- 权限控制：`access: 'canOnlineUsers'` 等价于 `isSuperAdmin || hasPermission('system:log')`
- 来源: apps/admin/src/access.ts:98-100 | E1 | High

### Designer - 用户视角

**页面清单与结构（系统管理相关）：**

| 页面 | 路由 | 用途 |
|------|------|------|
| online-users.tsx | /system/monitoring/online-users | 在线用户 |
| log.tsx | /system/monitoring/log | 操作日志 |
| checkin-audit-logs.tsx | /system/monitoring/checkin-audit-logs | 签到审计 |
| notification-logs.tsx | /system/monitoring/notification-logs | 通知日志 |
| analytics.tsx | 无独立路由 | 行为分析 |
| account/settings.tsx | /account/settings | 个人设置 |

来源: apps/admin/config/routes/system.ts:13-107 | E1 | High

**交互模式统计：**

| 模式 | 组件 | 使用场景 |
|------|------|---------|
| 表格 | ProTable + createListRequest | 列表数据（checkin-audit-logs, log, notification-logs） |
| 表格 | antd Table 手动管理 | 在线用户（全量加载 pagination=false） |
| 统计卡片 | Row/Col + Card + Statistic | 概览数字（notification-logs: 6个, analytics: 4个） |
| 图表 | @ant-design/charts (lazy+Suspense) | 趋势/排行/分布 |
| 时间线 | Timeline | 登录历史（online-users Drawer 内） |
| 抽屉 | Drawer | 详情展示（online-users, notification-logs） |
| 标签 | Tag | 状态/分类/设备标识 |

来源: 多个系统管理页面 | E1 | High

**组件一致性：**
- UI 库：Ant Design 6 + @ant-design/pro-components + @ant-design/charts
- 页面容器：统一使用 PageContainer
- 消息反馈：统一使用 App.useApp() 获取 message
- Loading：ProTable 内置 / useState 手动管理 / useRequest 自动 / Spin
- 空状态：locale={{ emptyText }} 或条件渲染

来源: apps/admin/package.json, 各页面 import | E1 | High

**数据可视化：**
- 已安装 @ant-design/charts v2.6.6
- 图表类型：Line（趋势）、Column（排行）、Pie（分布）、WordCloud（词云）
- 加载模式：lazy + Suspense + ChartLoading 自定义占位
- 统计页面结构：过滤器 Card -> Statistic Card 行 -> 图表 Card -> 表格 Card

来源: analytics.tsx:17-32, dashboard/index.tsx:35-44 | E1 | High

### Engineer - 技术视角

**存储层事实：**

| 事实 | 来源 | 证据 | 置信度 |
|------|------|------|--------|
| AdminLoginHistory 有 11 个字段（含 browser/os/device_type/duration） | models/admin.py:133-151 | E1 | High |
| admin_id 无显式 index=True | models/admin.py:138 | E1 | High |
| 无 tenant_id 字段，租户隔离依赖 JOIN admins 表 | models/admin.py:133-151 | E1 | High |
| Account 主表有 last_login_at/ip 但无独立历史表 | models/account.py:58-60 | E1 | High |
| Doctor 模型有 last_login_at/ip | models/doctor.py:54-55 | E1 | High |
| User 模型无 last_login_at/ip | models/user.py | E1 | High |
| 无任何 Celery 任务清理 admin_login_history | tasks/cleanup_task.py | E1 | High |

**核心引擎事实：**

| 事实 | 来源 | 证据 | 置信度 |
|------|------|------|--------|
| store_admin_session() 同时写 Redis + AdminLoginHistory | helpers.py:177-224 | E1 | High |
| 登出时更新 logout_time/logout_type/duration | router_auth_token.py:112-151 | E1 | High |
| logout_type="timeout" 枚举存在但无写入逻辑 | models/admin.py:141 | E1 | High |
| parse_user_agent() 使用 user_agents 库解析 browser/os/device_type | redis.py:1094-1140 | E1 | High |
| Redis 键格式: session:admin:{tenant_id}:{admin_id} | redis.py:568-664 | E1 | High |

**API/协议事实：**

| 事实 | 来源 | 证据 | 置信度 |
|------|------|------|--------|
| login-history API 返回格式为 dict（非 PageResponse） | router_monitoring.py:235 | E1 | High |
| login-history API 无时间范围筛选参数 | router_monitoring.py:187-235 | E1 | High |
| 所有 monitoring API 使用 require_permission("system:log","log:list") | router_monitoring.py | E1 | High |
| 超管可跨租户查看，非超管仅限本租户 | router_monitoring.py:200-205 | E1 | High |

**安全机制事实：**

| 事实 | 来源 | 证据 | 置信度 |
|------|------|------|--------|
| router_monitoring 使用 get_current_admin（旧接口） | router_monitoring.py | E1 | High |
| accounts 模块使用 get_current_account（新统一接口） | accounts/router.py | E1 | High |
| AdminLoginHistory 无 tenant_id，隔离依赖显式代码检查 | router_monitoring.py:200-205 | E1 | High |

**模块耦合事实：**

| 事实 | 来源 | 证据 | 置信度 |
|------|------|------|--------|
| login-history/online-users/user-status 均在 router_monitoring.py | modules/admin/ | E1 | High |
| modules/accounts/ 仅有 router.py（头像/改密/邮箱） | modules/accounts/ | E1 | High |
| 新统计功能建议归属 router_monitoring.py（已有监控语义） | 模块结构推理 | E3 | Medium |

### Round 1 质量门禁

- [x] 每条事实包含来源（文件路径:行号）
- [x] 每条事实标注证据级别（E1-E4）
- [x] 零评价性词汇
- [x] 覆盖所有调研维度
- [x] 三个视角交集度：**高**（均确认 Admin 已实现、Doctor/User 缺失、统计功能完全缺失）

**结果：** 通过
**争议密度评估：** 低（<20%）— 三个视角事实高度一致
**Round 2 决策：** 降级为仅评审组（跳过三方交叉评论）

---

## Round 2：辩论层（评审组）

### 评审组质询

#### 挑战者 A（反对角度 + 误报抑制）

**质询 1：AdminLoginHistory 无 tenant_id 字段是否构成安全风险？**
- 论据：当前租户隔离依赖 JOIN admins 表做权限校验（router_monitoring.py:200-205），而非在 LoginHistory 表本身存储 tenant_id。如果未来需要按租户维度统计登录数据（如"本租户本月登录次数 Top10"），每次都需要 JOIN admins 表，性能和复杂度都会增加。
- 误报验证：
  1. 用户能否遇到？— 当前 API 已有跨租户检查，普通用户不会遇到跨租户数据泄露
  2. 触发条件？— 需要绕过 API 直接查询数据库
  3. 发生频率？— 极低（仅数据库管理员直接查询时）
  4. 是否有防护？— 有，API 层已做权限校验
  5. 修复成本 vs 风险？— 添加 tenant_id 字段成本 Low，但当前风险也 Low
- 级别：普通（P2 级，建议在扩展时一并处理）

**质询 2：Doctor/User 登录历史是否为必要功能？**
- 论据：Doctor 端通过小程序/H5 登录，User 端通过微信小程序登录，这两个角色的"账号安全审计"需求远低于 Admin 角色。投入产出比需要评估。
- 误报验证：
  1. 用户能否遇到？— 管理员确实可能需要查看医生登录情况
  2. 触发条件？— 医生账号异常时需要审计
  3. 发生频率？— 低频（异常排查场景）
  4. 是否有防护？— Doctor 有 last_login_at/ip，基础信息已有
  5. 修复成本 vs 风险？— 新增 DoctorLoginHistory 模型 + 写入逻辑成本 Medium
- 级别：普通（P2 级，可作为后续迭代）

#### 挑战者 B（替代方案角度 + 证据验证）

**质询 1：统计功能的数据源选择**
- 论据：账号使用统计有两种数据源方案：
  - 方案 A：基于 AdminLoginHistory 表做 SQL 聚合查询
  - 方案 B：新建独立的统计汇总表，通过 Celery 定时任务预计算
- 证据验证：AdminLoginHistory 表当前无 tenant_id（E1），无索引优化（E1），数据量随时间增长无清理机制（E1）。如果选择方案 A，需要先解决索引和清理问题。
- 级别：关键（影响架构决策）

**质询 2：前端页面放置位置**
- 论据：统计数据展示有两个候选位置：
  - 位置 A：/system/monitoring/ 下新增子页面（与 online-users 同级）
  - 位置 B：/account/ 下新增"使用统计"页面（个人维度）
- 证据验证：现有 /system/monitoring/ 已有 online-users 和 log（E1），/account/ 仅有 settings.tsx（E1）。如果是"管理员看所有人的统计"放 monitoring，如果是"个人看自己的使用情况"放 account。
- 级别：普通（需确认需求意图）

#### 审计者（一致性检查 + 格式验证）

**一致性检查 1：login-history API 返回格式不一致**
- 发现的矛盾：login-history API 直接构造 dict 返回 `{"list":..., "total":..., "page":..., "pageSize":...}`，而其他 API 使用 `PageResponse` 模型（含 code/message/data 包装）。新增统计 API 应统一使用 PageResponse。
- 级别：普通

**一致性检查 2：认证接口不统一**
- 发现的矛盾：router_monitoring.py 使用 `get_current_admin`（旧接口返回 dict），accounts 模块使用 `get_current_account`（新接口返回 AccountInfo）。新增端点应考虑使用统一接口。
- 级别：普通

### 关键质询追踪

| # | 来源 | 关键质询内容 | 回应摘要 | 充分？ | 处置 |
|---|------|------------|---------|-------|------|
| 1 | 挑战者B | 统计功能数据源选择（SQL聚合 vs 预计算汇总表） | 需根据数据量和查询频率决定 | 待确认 | 纳入计划 |
| 2 | 挑战者B | 前端页面放置位置（monitoring vs account） | 取决于"看所有人"还是"看自己" | 待确认 | 纳入计划 |
| 3 | 审计者 | login-history API 返回格式不一致 | 新增 API 应统一使用 PageResponse | 是 | 纳入计划 |

### Round 2 质量门禁

- [x] 每个反驳附带理由
- [x] 评审组完成误报抑制检查（5问验证）
- [x] 评审组标记了关键质询（2 条）
- [x] 交叉评论覆盖主要发现
- [x] 争议密度已计算：低（<20%）

**结果：** 通过
**争议密度：** 低
**Round 3 决策：** 直接裁决（争议密度 < 20%）

---

## Round 3：共识层

### 共识项

**1. 使用统计功能的数据源方案**
- 结论：采用方案 A（基于 AdminLoginHistory 表 SQL 聚合），同时补充索引和清理机制
- 严重度：P2
- 证据级别：E3（架构推理）
- 理由：当前数据量级（单租户管理员数量有限）下 SQL 聚合足够；预计算方案增加复杂度但收益有限
- 建议行动：为 admin_login_history.admin_id 添加索引；新增按时间范围清理的 Celery 任务
- 工程成本：Low（2-4h）
- 风险降低：Medium
- 杠杆率：高
- 负责：Engineer

**2. 前端页面放置位置**
- 结论：新增 /system/monitoring/account-stats 页面（管理员看所有人的统计），同时在 /account/settings 中增加个人使用概览
- 严重度：P2
- 证据级别：E3
- 理由：管理员审计需求（看所有人）和个人查看需求（看自己）是两个不同场景
- 建议行动：在 system/monitoring 下新增统计页面；在 account/settings 中添加个人使用概览 Tab
- 工程成本：Medium（8-12h）
- 风险降低：Medium
- 杠杆率：中
- 负责：Designer + Engineer

**3. Doctor/User 角色登录历史覆盖**
- 结论：本轮仅覆盖 Admin 角色统计，Doctor/User 登录历史作为后续迭代
- 严重度：P3
- 证据级别：E1（Doctor 有 last_login_at/ip，User 完全无）
- 理由：Admin 是安全审计的主要需求方；Doctor/User 的审计需求优先级较低
- 建议行动：后续迭代新增统一的 account_login_history 表（基于 Account 模型，覆盖全角色）
- 工程成本：Low（当前不实施）
- 风险降低：Low
- 杠杆率：低
- 负责：Engineer

**4. login-history API 返回格式统一**
- 结论：新增统计 API 统一使用 PageResponse 格式
- 严重度：P3
- 证据级别：E1
- 建议行动：新增 API 使用 PageResponse；旧 API 保持不变（向后兼容）
- 工程成本：Low
- 风险降低：Low
- 杠杆率：低
- 负责：Engineer

### Open Risks

1. **风险描述：** AdminLoginHistory 表无清理机制，数据持续增长
   **分歧方：** 挑战者A（需清理） vs 当前代码（无清理任务）
   **争议核心：** 数据增长对查询性能的影响
   **已有证据：** E1（cleanup_task.py 中无 login_history 清理）
   **建议：** 新增 Celery 定时任务，按可配置的保留天数清理（默认 180 天）

2. **风险描述：** logout_type="timeout" 无写入逻辑，导致部分登出记录缺失
   **分歧方：** PM（枚举存在暗示需要） vs Engineer（无实现代码）
   **争议核心：** 是否需要实现超时退出自动记录
   **已有证据：** E1（枚举定义存在，写入逻辑缺失）
   **建议：** 后续迭代通过 Celery 任务扫描过期 Redis 会话并更新历史记录

---

## 被低估的优势

1. 已有的 `store_admin_session()` 函数在登录时同时写入 Redis 和数据库，架构设计良好，扩展统计功能无需改动写入逻辑。
2. 已有 `@ant-design/charts` 图表库和成熟的 lazy+Suspense 加载模式，新增统计图表有成熟的技术基础。
3. 已有 `notification-logs.tsx` 的 Statistic Card + ProTable 组合模式，可直接复用于账号统计页面。

---

## 行动计划（按杠杆率排序）

| 优先级 | 行动 | 严重度 | 杠杆率 | 工程成本 | 风险降低 | 负责 | 状态 |
|--------|------|--------|--------|---------|---------|------|------|
| P1 | 新增账号使用统计 API（登录次数/时长/设备聚合） | P1 | 高 | Medium (6-8h) | High | Engineer | 待开发 |
| P1 | 新增账号统计前端页面（/system/monitoring/account-stats） | P1 | 高 | Medium (8-12h) | High | Designer+Engineer | 待开发 |
| P2 | 为 admin_login_history.admin_id 添加数据库索引 | P2 | 高 | Low (1h) | Medium | Engineer | 待开发 |
| P2 | 新增 admin_login_history 清理 Celery 任务 | P2 | 高 | Low (2h) | Medium | Engineer | 待开发 |
| P2 | 在 account/settings 中添加个人使用概览 | P2 | 中 | Medium (4-6h) | Medium | Designer+Engineer | 待开发 |
| P3 | login-history API 添加时间范围筛选参数 | P3 | 中 | Low (1h) | Low | Engineer | 待开发 |
| P3 | 新增 API 统一使用 PageResponse 格式 | P3 | 低 | Low (1h) | Low | Engineer | 待开发 |
| P3 | 后续迭代：统一 account_login_history 表覆盖全角色 | P3 | 低 | - | Low | Engineer | 后续迭代 |
| Open Risk | logout_type="timeout" 自动记录机制 | - | - | - | - | Engineer | 需确认 |
| Open Risk | 登录失败记录功能 | - | - | - | - | PM+Engineer | 需确认 |

### P1：本轮迭代

**1. 新增账号使用统计 API**
- 影响声明：管理员无法查看账号使用情况，缺乏安全审计数据支撑
- 证据：E1（代码中无任何统计聚合 API）
- 杠杆率：高（Medium 成本，High 风险降低）
- 预估工时：6-8 小时
- 负责：Engineer
- 具体内容：
  - 新增 `GET /monitoring/account-stats` 端点
  - 支持按时间范围（start_date/end_date）筛选
  - 返回：总登录次数、总使用时长、设备分布（desktop/mobile/tablet）、浏览器分布、常用登录时段
  - 支持按单个账号或全部账号查询
  - 租户隔离：非超管仅查本租户

**2. 新增账号统计前端页面**
- 影响声明：管理员无法直观查看账号使用统计
- 证据：E1（前端无统计页面）
- 杠杆率：高
- 预估工时：8-12 小时
- 负责：Designer + Engineer
- 具体内容：
  - 路由：/system/monitoring/account-stats
  - 顶部：Statistic Card 行（总登录次数、活跃账号数、平均使用时长）
  - 中部：设备分布饼图 + 登录时段柱状图 + 登录趋势折线图
  - 底部：账号使用明细表格（ProTable，含登录次数/总时长/最后登录/常用设备）
  - 复用 notification-logs.tsx 的 Statistic Card + ProTable 模式
  - 复用 analytics.tsx 的 @ant-design/charts lazy 加载模式

### P2：下个周期规划

**3. admin_login_history 索引优化**
- 证据：E1（admin_id 无 index=True）
- 预估工时：1 小时
- 负责：Engineer

**4. login_history 清理任务**
- 证据：E1（cleanup_task.py 无 login_history 清理）
- 预估工时：2 小时
- 负责：Engineer

**5. 个人使用概览**
- 证据：E1（account/settings.tsx 无使用统计 Tab）
- 预估工时：4-6 小时
- 负责：Designer + Engineer

### P3：仅记录（不生成 Issue）

1. login-history API 添加时间范围筛选参数
2. 新增 API 统一使用 PageResponse 格式
3. 后续迭代：统一 account_login_history 表覆盖 Doctor/User 角色

### Open Risks

1. **logout_type="timeout" 自动记录** — Redis 会话 TTL 到期时不更新数据库记录，导致部分登出记录缺失。需要 Celery 任务扫描过期会话。
2. **登录失败记录** — 当前无登录失败记录功能，无法审计暴力破解等安全事件。需要在登录端点添加失败记录逻辑。

---

## 输出格式

### GitHub Issue 生成规则

**自动生成：** P1（2 个 Issue）
**按需生成：** P2（用户请求时）
**不生成：** P3

---

## 摘要

**使用模式：** 集中调度
**执行深度：** 标准
**风险升级：** 无

**关键共识：** 5 项
**关键分歧：** 0 项（2 个待确认的设计决策）
**Open Risks：** 2 项

**Top 3 P1/P2 行动（按杠杆率）：**
1. 新增账号使用统计 API（Medium 成本，High 收益）
2. 新增账号统计前端页面（Medium 成本，High 收益）
3. admin_login_history 索引 + 清理任务（Low 成本，Medium 收益）

**评审组关键洞察：**
- 现有 AdminLoginHistory 模型和 store_admin_session() 架构设计良好，扩展统计功能无需改动写入逻辑
- 统计功能建议基于 SQL 聚合（方案 A），当前数据量级下足够，无需引入预计算方案
- Doctor/User 角色登录历史覆盖建议作为后续迭代，本轮聚焦 Admin 角色

---

## 附录

### LEARNED_RULES 注入记录

| 规则 | 来源 | 置信度 | 适用上下文 | 是否注入 | 原因 |
|------|------|--------|-----------|---------|------|
| 无 | - | - | - | - | 首次评审该功能域，无历史规则 |

### 模式切换日志

| 时间 | 从 | 到 | 触发条件 | 原因 |
|------|-----|-----|---------|------|
| Round 2 | 三方交叉 | 仅评审组 | 争议密度 < 20% | 三个视角事实高度一致，无需交叉辩论 |

### 门禁恢复记录

| 轮次 | 失败原因 | 恢复路径 | 执行动作 | 结果 |
|------|---------|---------|---------|------|
| 无 | - | - | - | - |
