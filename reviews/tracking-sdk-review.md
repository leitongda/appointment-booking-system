# appointment-booking-system — 自适应多智能体研究画布

> 协作模式：集中调度
> 日期：2026-05-22
> 审查目标：埋点/分析 SDK 体系完整性评审

---

## 模式选择

**选定模式：** 集中调度

**选择理由：** 三视角均衡（产品/交互/工程），无单一主导领域，需要快速产出可执行的分阶段落地方案。

---

## Round 1：事实层（只写事实，不评价）

### PM — 产品视角

**埋点事件覆盖度：**

- SDK 支持 5 种事件类型：`page_view`、`page_leave`、`click`、`search`、`custom`（tracker.ts:214-307）
- 后端 EventType 枚举与前端一致（behavior_log.py Schema:22-28）

各端接入状态：

| 前端端 | Tracker 初始化 | page_view | 自定义事件 | 状态 |
|---|---|---|---|---|
| admin | 已初始化 (platform='admin') | 已接入 (app.tsx:224) | 已接入（规则组预览 14 个事件） | 已接入 |
| patient-h5 | 已初始化 (platform='h5') | 已接入 (MainLayout:72) | 未发现 | 部分接入 |
| patient-miniapp | 已初始化 (platform='miniapp') | 已接入 (app.tsx:342) | 未发现 | 部分接入 |
| doctor | 未初始化 | 未接入 | 未接入 | 未接入 |
| website | 未初始化 | 未接入 | 未接入 | 未接入 |

- `trackClick()` 和 `trackSearch()` 在整个项目前端代码中零调用
- admin 端唯一业务级事件封装：`analytics.ts` 中 14 个规则组预览事件（冒号分隔命名：`rule_preview:live:open` 等）

**事件命名规范：**

- 两种命名风格混用：事件类型用 snake_case（`page_view`），自定义事件用冒号分隔（`rule_preview:live:open`）
- 字段命名跨层不一致：Tracker 层 snake_case（`session_id`），前端 API 模块 camelCase（`sessionId`），后端 Pydantic 用 `alias_generator=to_camel` 桥接
- 前端 Tracker 实际发送 snake_case 格式，后端 `populate_by_name=True` 同时接受两种格式

**数据分析能力：**

- 后端 3 个查询接口：日志列表（分页筛选）、行为概览（PV/UV/Top10/每日统计）、租户活跃度（DAU/WAU/MAU）
- 管理后台 3 个 Tab：行为概览（图表+表格）、租户活跃度（趋势+明细）、行为日志（可筛选列表）
- 筛选能力缺口：行为日志 Tab 后端支持 start_time/end_time 参数，但前端 UI 未暴露日期筛选

**业务场景覆盖：**

- 核心业务流程均无埋点：预约提交、挂号、登录、支付、审批 — 全部未追踪
- 关键转化路径缺失：从浏览到预约完成的全链路无追踪
- 异常场景：API 错误、JS 错误、表单验证失败均未追踪；仅规则预览失败有追踪（`rule_preview:modal:fail`）
- `user_id` 在 analytics router 中硬编码为 `None`（router.py:105），DAU/WAU/MAU 统计实际为 0

### Designer — 用户视角

**业务代码侵入性：**

- 调用方式：三端均通过 `import { getTracker } from '@hospital/shared'` 获取单例，命令式调用 `tracker.trackXxx()`
- 手动调用统计：页面访问 3 处（admin/h5/miniapp 各 1 处）+ 业务事件 14 处（仅 admin 规则组预览）
- 声明式埋点：不存在。无 `data-track-name`、HOC/Decorator、指令式等机制
- 侵入程度：admin 端埋点调用直接嵌入业务组件事件处理函数，`analytics.ts` 提供语义化封装但仍是命令式

**自动采集能力：**

- 页面访问：路由层手动调用，非框架级自动注入
- 自动点击采集：不存在。`trackClick()` API 已定义但无调用
- 自动错误采集：不存在。无 `window.onerror`、`unhandledrejection` 监听。`ShellErrorBoundary` 仅 console.error，未上报
- 自动性能采集：独立系统存在（Core Web Vitals + 路由耗时 + API 耗时），但 PerformanceReporter 仅 console.warn 输出，未实际上报到服务端

**数据脱敏情况：**

- 前端 Tracker：无任何数据过滤/脱敏逻辑。`trackSearch` 直接存原文，`extraData` 直接透传
- 后端 router：无脱敏处理，直接存库
- `extra_data` 字段：前端 `Record<string, any>` 无限制，后端 Schema 无 `max_length`，数据库 `Text` 无长度限制
- 搜索关键词：无脱敏，直接存储原始输入（Schema 限制 max_length=200）
- IP/User-Agent：后端直接存储，无脱敏

**初始化和配置模式：**

- 三端初始化位置：admin 在 `initApp.ts:13`，h5 在 `MainLayout/index.tsx:20`，miniapp 在 `app.tsx:232`（均为模块顶层执行）
- `enableInDev`：三端均设为 `true`，开发环境也启用
- 采样率：不存在。无 `sampleRate` 配置
- 动态开关：`setEnabled()` 方法存在但无业务代码调用，无远程配置/feature flag 集成
- 性能监控与行为追踪是两套独立系统，无数据关联（session_id 未打通）

### Engineer — 技术视角

**SDK 核心架构：**

- Tracker 类 9 个公共方法：`trackPageView`、`trackPageLeave`、`trackClick`、`trackSearch`、`trackEvent`、`forceFlush`、`destroy`、`setEnabled`、`getSessionId`
- 事件队列：数组无限增长，无容量上限，无丢弃策略（tracker.ts:156）
- 上报通道优先级：sendBeacon（同步）→ fetch（异步，keepalive）→ wx.request（小程序）
- 失败重试：catch 块中 `unshift` 回队列头部，无退避策略，无死信队列，无最大重试次数
- 插件化：不存在。analytics 目录仅 tracker.ts、types.ts、index.ts 三个文件

**数据模型和格式：**

- TrackEvent 12 个字段，全部 snake_case（types.ts:32-45）
- 后端 UserBehaviorLog 21 个字段（behavior_log.py:10-33），8 个索引
- 前后端字段名完全一致（均为 snake_case），Pydantic alias_generator 做 camelCase 桥接
- PerformanceReport 接口用 camelCase（`pageUrl`、`userAgent`），与 Tracker 的 snake_case 不一致
- `extra_data` 前端 `Record<string, any>` → 后端 `Text`（JSON 字符串），无大小限制

**性能监控子系统：**

- MetricsCollector 采集 7 种指标：FCP/LCP/CLS/FID/INP/TTFB/ROUTE_CHANGE（metrics.ts:42-50）
- 内存上限 100 条 PerformanceMetric（metrics.ts:308-310）
- PerformanceReporter.sendReport() 是 `console.warn`，fetch 调用被注释（reporter.ts:262-276）
- 后端无 `/api/v1/performance/report` 端点
- API 性能监控：PerformanceMonitor 内存上限 1000 条，`sendToAnalytics()` 依赖不存在的 `window.analytics` 对象
- `flushToStorage()` 每 60 秒写 localStorage（performance.ts:227-234）

**后端接收和存储：**

- 上报 API 无需认证（router.py:88-89, 144）
- `tenant_id` 在 track/batch 端点中未设置，始终为 None（router.py:103-122, 158-179）
- `user_id` 硬编码为 None，未从 token 提取（router.py:105）
- Celery task：autoretry_for=Exception, max_retries=3, 指数退避（behavior_log_task.py:16-25）
- 降级行为不一致：`/track` Celery 不可用时直接写库；`/batch` 仅记录 warning，数据丢失（router.py:129-139 vs 186-188）
- UA 解析：纯字符串匹配，不用 ua-parser 库（router.py:40-85）
- 统计查询性能问题：`get_behavior_overview` 当 days=90 时执行 367 条 SQL；`get_tenant_activity_stats` 执行 273 条 SQL（router.py:364-398, 434-474）

**跨平台适配：**

- 浏览器：sessionStorage + sendBeacon/fetch + PerformanceObserver
- 微信小程序：wx.getStorageSync + wx.request，但 `data` 直接传对象（未 JSON.stringify），与浏览器环境行为不一致（tracker.ts:182 vs 192-195）
- `getPageTitle()` 和 `getReferrer()` 在小程序环境返回空字符串
- Taro 适配：仅 HTTP 请求层有 TaroAdapter，Tracker 不使用
- uni-app：不存在适配

---

## Round 2：辩论层

### 交叉评论投票矩阵（集中调度简化版）

| 议题 | 裁决者立场 | Critic 质询 | 最终裁决 |
|------|-----------|------------|---------|
| 事件模型统一性 | 前后端字段名一致但非真正统一管道 | 普通：12 字段 vs 21 字段，后端单方面填充 | 采纳 Critic：需在文档中明确前后端职责边界 |
| 索引数量 | 8 个索引在迁移文件中 | 暴涨 2（Critical）：Critic 仅查模型未查迁移 | 驳回 Critic：迁移文件确认 9 个索引（8+tenant_id），Engineer 正确 |
| /batch 数据丢失 | 降级行为不一致 | 暴涨 3（Critical）：主上报路径无降级保护 | 采纳 Critic：P0 修复 |
| 业务埋点覆盖不足 | PM 列为缺陷 | 普通：MVP 阶段先验证管道是合理策略 | 部分采纳：当前阶段合理，但应制定铺开计划 |
| 声明式埋点缺失 | Designer 列为缺陷 | 普通：项目体量下命令式+封装层已足够 | 驳回：当前 analytics.ts 封装模式适合项目规模 |
| 上报接口安全风险 | 三方均遗漏 | 暴涨 6（Critical）：无认证+无限速+无大小限制 | 采纳 Critic：P0 修复 |
| 队列无限增长 | Engineer 列为缺陷 | 普通：正常使用下队列不超 10，风险极低 | 采纳 Critic：当前不构成实际风险 |
| 数据生命周期 | 三方均遗漏 | 普通：无 TTL/清理/归档机制 | 采纳：P2 规划 |

### 独到发现

1. **三套监控系统互相孤立**：行为追踪（Tracker）、性能监控（MetricsCollector/Reporter）、API 性能（PerformanceMonitor）是三个独立系统，无 session_id 打通，无法关联分析
2. **PerformanceReporter 是空壳**：sendReport() 仅 console.warn，后端无对应端点，整个性能监控子系统采集了数据但从未上报
3. **user_id 始终为 None 导致 DAU/WAU/MAU 全部为 0**：analytics router 中 user_id 硬编码为 None，租户活跃度统计的核心指标实际无意义
4. **小程序 wx.request 未 JSON.stringify**：浏览器环境传字符串，小程序传对象，行为不一致可能导致后端解析异常

### Critic 质询

1. [Critic → 全体] 质询 1：PM 声称"事件类型前后端一致"是误导性结论 — 前端 12 字段 vs 后端 21 字段，后端单方面填充。级别：普通
2. [Critic → 全体] 质询 2：Engineer 对"8 个索引"的描述与代码不符 — **Team Lead 验证：迁移文件确认 8 个索引存在，Critic 仅检查了模型定义。级别：普通（Critic 事实错误）**
3. [Critic → 全体] 质询 3：/batch 端点数据丢失 — 正常使用流程中主上报路径无降级保护。级别：🚨 关键
4. [Critic → 全体] 质询 4：PM 缺少优先级判断依据 — MVP 阶段先验证管道是合理策略。级别：普通
5. [Critic → 全体] 质询 5：Designer 侵入性评估缺少基线对比 — analytics.ts 封装模式已足够解耦。级别：普通
6. [Critic → 全体] 质询 6：上报接口安全风险 — 无认证+无限速+无大小限制。级别：🚨 关键
7. [Critic → 全体] 质询 7：队列无限增长描述需量化 — 正常使用下不构成风险。级别：普通
8. [Critic → 全体] 质询 8：数据生命周期管理缺失 — 无 TTL/清理/归档。级别：普通

### 🚨 Critic 关键质询追踪

| # | 关键质询内容 | 三方回应摘要 | 回应是否充分 | 处置 |
|---|------------|------------|------------|------|
| 2 | 索引数量与代码不符 | Team Lead 验证迁移文件确认 9 个索引 | Critic 事实错误 | 驳回，不进入行动计划 |
| 3 | /batch 端点数据丢失 | Engineer 承认降级行为不一致 | 是 | 纳入 P0 |
| 6 | 上报接口安全风险 | 三方均未考虑此攻击面 | 是 | 纳入 P0 |

---

## Round 3：共识层

### ✅ 共识项

1. **/batch 端点需补充降级写入**
   - 结论：`/batch` Celery 不可用时应与 `/track` 一致，降级为直接数据库写入
   - 建议行动：在 `/batch` 的 except 块中添加 `db.add_all()` + `await db.commit()` 降级逻辑
   - 成本估算：1h
   - 优先级：P0

2. **上报接口需添加基础安全防护**
   - 结论：`/track` 和 `/batch` 端点无认证、无限速、无大小限制，可被外部利用
   - 建议行动：(a) 添加 API Key 或简单 token 校验；(b) 对 `extra_data` 添加 max_length 限制（如 4096 字符）；(c) 使用 slowapi 或自定义中间件添加 IP 级速率限制
   - 成本估算：4h
   - 优先级：P0

3. **user_id 需从请求中提取**
   - 结论：当前硬编码为 None，导致 DAU/WAU/MAU 统计全部为 0，租户活跃度面板无意义
   - 建议行动：在 track/batch 端点中尝试从 Authorization header 解析 user_id（可选，匿名用户仍允许）
   - 成本估算：2h
   - 优先级：P0

4. **PerformanceReporter 需接通真实上报**
   - 结论：当前仅 console.warn，后端无对应端点，整个性能监控子系统是空壳
   - 建议行动：(a) 后端新增 `/api/v1/performance/report` 端点；(b) PerformanceReporter.sendReport() 替换为真实 fetch 调用
   - 成本估算：4h
   - 优先级：P1

5. **三套监控系统需打通 session_id**
   - 结论：行为追踪、性能监控、API 性能三个系统独立运行，无法关联分析
   - 建议行动：PerformanceReporter 和 PerformanceMonitor 在构建报告时注入当前 Tracker 的 session_id
   - 成本估算：2h
   - 优先级：P1

6. **统计查询需优化**
   - 结论：`get_behavior_overview` days=90 时 367 条 SQL，`get_tenant_activity_stats` 273 条 SQL
   - 建议行动：将 Python 循环 N 天的查询改为单条 GROUP BY 按日期聚合的 SQL
   - 成本估算：4h
   - 优先级：P1

7. **tenant_id 需在写入时注入**
   - 结论：track/batch 端点未设置 tenant_id，多租户数据隔离失效
   - 建议行动：在端点中调用 `get_current_tenant_id()` 注入 tenant_id（从请求上下文或 token 中获取）
   - 成本估算：1h
   - 优先级：P1

8. **小程序 wx.request 数据格式不一致**
   - 结论：浏览器环境传 JSON.stringify 字符串，小程序传原始对象
   - 建议行动：统一为 JSON.stringify 后传入
   - 成本估算：0.5h
   - 优先级：P1

### ⚡ 分歧项

1. **事件命名规范是否需要统一**
   - 各方立场：
     - PM：两种风格混用（snake_case + 冒号分隔）会导致数据分析混乱
     - Designer：当前冒号分隔命名（`rule_preview:live:open`）语义清晰，层级分明
     - Engineer：字段名已统一 snake_case，事件名的冒号分隔是业务语义，不影响存储
   - 裁决：事件类型枚举值保持 snake_case，自定义事件名允许冒号分隔（作为命名空间），但需在 SDK 文档中明确规范
   - 决策依据：冒号分隔在业界（如 GA4 的 `screen_view`、Mixpanel 的 `$identify`）是常见模式，关键是统一而非强制一种风格

2. **是否需要声明式埋点**
   - 各方立场：
     - Designer：当前无声明式机制，全部命令式
     - Critic：项目体量下 analytics.ts 封装模式已足够
   - 裁决：当前阶段不需要。analytics.ts 的封装模式（独立文件、语义化函数、节流控制）已实现业务与埋点解耦。若后续业务模块扩展到 10+ 个埋点场景，再考虑引入 `data-track-*` 属性 + 全局 click 监听
   - 决策依据：声明式埋点在 React+TS 中的工程成本（类型定义、编译校验、运行时解析）高于当前项目体量的收益

---

## 被低估的优势

1. **规则组预览埋点是高质量试点**：14 个事件覆盖完整 CRUD + 预览生命周期，包含节流机制（3 秒去重）和语义化封装，说明团队有能力做好埋点，只是还没铺开
2. **Celery 异步写入 + 指数退避重试**：后端写入路径已有成熟的异步化方案，max_retries=3 + retry_backoff + retry_jitter 是生产级配置
3. **前端重试机制完备**：packages/api/src/utils/retry.ts 实现了端点级熔断（连续 5 次失败后熔断 30 秒）、全局重试预算（30 秒内最多 50 次）、429 Retry-After 解析，这是企业级的重试策略
4. **多环境适配已到位**：enableInDev 配置、开发环境 debug 模式、浏览器/小程序双通道上报，基础设施层面考虑周全

---

## 行动计划（按 ROI 排序）

| 优先级 | 行动 | 成本 | 价值 | 负责 | 状态 |
|--------|------|------|------|------|------|
| P0 | /batch 端点补充降级写入（与 /track 一致） | 1h | 高 — 修复主上报路径的数据丢失 | Engineer | 待执行 |
| P0 | 上报接口添加 API Key + extra_data max_length + IP 限速 | 4h | 高 — 关闭外部攻击面 | Engineer | 待执行 |
| P0 | user_id 从请求中提取（可选认证） | 2h | 高 — 恢复 DAU/WAU/MAU 统计能力 | Engineer | 待执行 |
| P1 | 统计查询优化（Python 循环 → GROUP BY 聚合） | 4h | 高 — 防止数据量增长后接口超时 | Engineer | 待执行 |
| P1 | tenant_id 写入时注入 | 1h | 高 — 恢复多租户数据隔离 | Engineer | 待执行 |
| P1 | PerformanceReporter 接通真实上报 + 后端新增端点 | 4h | 中 — 性能监控从空壳变为可用 | Engineer | 待执行 |
| P1 | 三套监控系统打通 session_id | 2h | 中 — 支持关联分析 | Engineer | 待执行 |
| P1 | 小程序 wx.request 统一 JSON.stringify | 0.5h | 中 — 消除跨平台行为不一致 | Engineer | 待执行 |
| P1 | 行为日志 Tab 前端暴露日期筛选 | 1h | 低 — 提升管理员使用体验 | Engineer | 待执行 |
| P2 | 核心业务埋点铺开（预约/挂号/登录/支付） | 8h | 高 — 关键转化路径追踪 | PM + Engineer | 待规划 |
| P2 | JS Error + API Error 自动采集 | 4h | 中 — 异常场景追踪 | Engineer | 待规划 |
| P2 | 数据生命周期管理（TTL/清理/归档） | 4h | 中 — 防止存储无限增长 | Engineer | 待规划 |
| P2 | doctor 端 + website 端接入 Tracker | 2h | 中 — 全端覆盖 | Engineer | 待规划 |
| P2 | SDK 文档编写（事件命名规范、接入指南） | 4h | 中 — 降低后续接入成本 | PM + Engineer | 待规划 |

---

## 摘要

**使用模式：** 集中调度

**关键共识：**
- 8 项达成共识（/batch 降级、安全防护、user_id 提取、性能上报打通、session_id 关联、查询优化、tenant_id 注入、小程序格式统一）

**关键分歧：**
- 2 项需要决策者介入（事件命名规范、声明式埋点），均已裁决

**Top 3 P0 行动：**
1. /batch 端点补充降级写入（1h） — 修复主上报路径数据丢失
2. 上报接口添加 API Key + extra_data 限制 + IP 限速（4h） — 关闭外部攻击面
3. user_id 从请求中提取（2h） — 恢复 DAU/WAU/MAU 统计

**Critic 关键洞察：**
- /batch 端点数据丢失是最隐蔽的 bug：正常使用中绝大多数事件走 /batch，而该路径 Celery 不可用时静默丢数据
- 上报接口安全风险是三方都遗漏的攻击面：无认证+无限速+无大小限制 = 可被外部利用的数据注入入口
- 索引数量质疑经验证不成立：迁移文件确认 9 个索引，Critic 仅查了模型定义

---

## 附录：模式切换日志

| 时间 | 从 | 到 | 原因 |
|------|-----|-----|------|
| 无切换 | - | - | - |
