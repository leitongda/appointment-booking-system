# appointment-booking-system — SaaS 多租户改造进度审查画布

> 协作模式：领域主导（Engineer 领域主导）
> 日期：2026-03-27
> 审查目标：逐模块分析 SaaS 多租户架构改造进度，检查是否符合常理

---

## 模式选择

**选定模式：** 领域主导 — Engineer 领域主导

**选择理由：** SaaS 多租户改造本质上是工程架构任务，需要深入审查中间件、数据隔离、缓存策略、权限模型等技术细节。PM 和 Designer 角色贡献有限，Engineer 领域主导可让技术审查更深入。

---

## Round 1：事实层（只写事实，不评价）

### PM — 产品视角

**产品定位：**
- 自我定位：全栈医院预约挂号系统，SaaS 多租户架构，支持多门店/分院、多科室、多医生排班预约（CLAUDE.md:14）

**功能完成度：**

| 功能 | 状态 | 证据 |
|------|------|------|
| 多租户识别（Header/子域名/路径前缀） | 已实现 | middleware/tenant_context.py 支持 4 种识别方式 |
| 租户数据隔离（tenant_id 字段覆盖） | 部分实现 | 约 10 个核心表有 tenant_id，30+ 表未完全检查 |
| 租户缓存隔离（Redis key 前缀） | 部分实现 | 短信验证码和分布式锁有隔离，微信Token/会话等未隔离 |
| 订阅计划/用量限制 | 已实现 | SubscriptionPlan 模型 + TenantUsageLog + 用量统计服务 |
| 租户级权限系统 | 部分实现 | Role 有 tenant_id，但权限管理路由未隔离 |
| 租户级配置 | 已实现 | features/branding_config/custom_domain/subdomain 字段 |
| 租户管理后台 | 已实现 | 前端 5 个页面 + 后端完整 CRUD API |
| 租户自助注册 | 未实现 | 创建接口仅平台管理员可访问 |

**目标用户线索：**
- 部署方式：单实例多租户（单一 DB + Redis）
- 无租户自助注册，需平台管理员创建
- 有 Swagger/ReDoc API 文档，但无独立 SDK
- 前端共享包 packages/api 为 HTTP 请求封装

### Designer — 用户视角

**页面清单与结构：**
- 租户管理路由 7 条：/tenant/list, /tenant/create, /tenant/:id, /tenant/:id/edit, /tenant/plans, /tenant/plans/create, /tenant/plans/:id/edit
- 租户页面文件 5 个：index.tsx(167行), form.tsx(266行), detail.tsx(270行), plans.tsx(126行), plan-form.tsx
- 登录流程：保存 stores 数组到 localStorage，支持多门店场景
- 仅有 StoreSwitcher 组件，无 TenantSwitcher 组件

**交互模式统计：**
- 租户选择/切换：前端未实现租户切换 UI
- 跨租户操作 UI 提示：未发现
- 请求拦截器（utils/request.ts:65-82）：未添加 X-Tenant-ID 或 X-Tenant-Code Header
- 权限控制：access.ts 定义了 canTenant、canTenantPlans

**响应式设计事实：**
- 有响应式配置文件 constants/responsive.ts（160行）和 useResponsive hook
- 租户管理页面使用固定栅格布局（Col span={12}），未使用响应式 Hook
- 全局 18 个文件 221 处使用响应式栅格

### Engineer — 技术视角

#### 1. 多租户中间件和上下文
- **租户识别**：4 种方式，优先级 X-Tenant-ID > X-Tenant-Code > 子域名 > 路径前缀（tenant_context.py:6-10,166-197）
- **ContextVar**：_current_tenant_id + _current_tenant_code（tenant_context.py:27-29）
- **中间件顺序**：CORS -> RateLimit -> RequestLog -> OperationLog -> UnifiedResponse -> TenantContext（main.py:398-416）
- **错误处理**：公开接口定义 PUBLIC_TENANT_REQUIRED_PATHS（12个路径前缀），缺失返回 400

#### 2. 数据隔离 — 逐模块检查

| 模块 | 文件 | tenant_id 过滤 | 说明 |
|------|------|:---:|------|
| Admin 服务 | service_admins.py | 部分 | get_list/get_by_id 有过滤，update/delete 无显式校验 |
| Doctor 服务 | doctors/service_mutation.py | 无 | 仅配额检查使用 tenant_id，数据操作无隔离 |
| Schedule 服务 | schedules/service_mutation.py | 无 | 所有排班操作无租户隔离 |
| Store 服务 | stores/service_mutation.py | 无 | 仅配额检查使用 tenant_id |
| Appointment | appointments/router*.py | 间接 | 通过门店过滤间接实现 |
| Import/Export | router_export.py | 有 | 双重过滤（门店+租户） |
| Admin 角色 | router_roles.py | 无 | 角色管理路由未隔离 |
| Admin 权限 | router_permissions.py | 无 | 权限管理路由未隔离 |

#### 3. 数据库模型层
- **有 tenant_id 的表**（10个）：Admin, Role, User, Doctor, Store, Department, ScheduleTemplate, Schedule, Appointment, TenantSubscription/TenantUsageLog/TenantNotification
- **无全局过滤机制**：未发现 SQLAlchemy event listener 或全局 query filter
- **租户模型**：SubscriptionPlan 和 Tenant 本身无 tenant_id（根表）
- **UniqueConstraint**：Doctor 表有 tenant_id + username/phone 的租户内唯一约束

#### 4. 缓存隔离
- **已隔离**：短信验证码（sms:{tenant_id}:{phone}）、分布式锁 API（tenant:{tenant_id}:{lock_name}）
- **未隔离**：微信 Token（按 app_id）、扫码登录（按 scan_id）、管理员会话（按 admin_id）、Token 黑名单（按 token_hash）
- **锁 API 已实现但未推广使用**：schedules/service_mutation.py 使用 distributed_lock 而非 tenant_distributed_lock

#### 5. 认证和权限
- **JWT Token**：包含 tenant_id（router_auth_login.py:113,161,227,295）
- **登录验证**：get_current_admin 强制校验租户一致性（deps.py:276-293）
- **依赖注入完善**：get_current_tenant, get_tenant_filter, check_tenant_access, validate_tenant_consistency 等 7+ 个函数

#### 6. Celery 任务
- **schedule_task.py**：排班生成任务未实现租户隔离
- **tenant_usage_task.py**：用量统计任务已正确实现租户隔离（遍历所有 tenant 并按 tenant_id 统计）
- **其他任务**（behavior_log, notification, cleanup, blacklist, operation_log）：需逐一检查

#### 7. 前端多租户支持
- **tenantApi 存在**：getPlans, createTenant, updateTenant 等
- **请求头传递未确认**：前端请求拦截器未添加 X-Tenant-ID
- **子域名/路径前缀方案**：后端已支持，前端需配置 Nginx 或路由重写

#### 8. 测试覆盖
- 7 个测试文件，覆盖缓存隔离、分布式锁隔离、数据隔离、配额、导入隔离等
- 使用内存 SQLite + mock Redis（conftest.py）

---

## Round 2：辩论层

### 交叉评论投票矩阵

#### 简化投票矩阵（领域主导模式）

| 议题 | Lead(Engineer)立场 | Critic 质询 | 最终裁决 |
|------|:---:|:---:|:---:|
| 数据隔离覆盖不足（Doctor/Schedule/Store 无过滤） | P0 阻断性 | 质疑"部分实现"标签，实为核心缺失 | **P0 确认** |
| Celery 任务完全未隔离 | P1 高优先级 | 缺少影响频率数据，tenant_usage_task 已隔离 | **P1 降级为部分任务** |
| 前端未传递 X-Tenant-ID | P1 非阻断 | 证据不足，可通过子域名/路径前缀绕过 | **P1 降级** |
| 缓存部分未隔离（会话/Token） | P1 中-高风险 | 锁 API 已实现但未使用，优先级需调整 | **P1 确认** |
| 无全局 tenant_id 过滤机制 | P2 建议引入 | UniqueConstraint 已提供数据完整性兜底 | **P2 确认** |
| 权限/角色管理路由未隔离 | P0 阻断性 | 未直接质询 | **P0 确认** |
| RateLimit 未按租户隔离 | 未提及 | 🚨 关键质询：共享资源竞争 | **P1 确认** |
| 数据库索引策略 | 未提及 | 🚨 关键质询：查询效率 | **P2 确认** |
| Alembic 迁移策略 | 未提及 | 🚨 关键质询：升级可行性 | **待定** |
| 认证授权链路完善 | 确认 | 未被充分认可为第一道防线 | **共识** |
| 测试覆盖 | 确认 | 有效性需验证（SQLite vs PostgreSQL） | **共识，需补充** |

### 独到发现

1. **前端-后端租户传递断裂**：后端支持 4 种租户识别方式，但前端请求拦截器未传递 X-Tenant-ID
2. **门店级隔离掩盖租户级缺陷**：Appointment 通过门店过滤间接实现租户隔离，依赖门店数据正确性
3. **get_tenant_from_admin 的兼容性 hack**：deps.py:892-903 从门店推断租户是临时方案
4. **排班分布式锁不含租户维度**：锁 API 已存在（tenant_distributed_lock）但未被使用
5. **RateLimit 中间件在 TenantContext 之后执行**：限流键可能不包含租户维度，一个租户高流量影响其他租户

### Critic 质询

1. [Critic → 全体] 质询 1：产品定位自洽性 — "SaaS 多租户"定义被滥用，核心数据隔离层缺失
   - 论据：mutation 服务无 tenant_id 过滤，不是"部分实现"而是"核心缺失"
   - 要求回应：PM / Engineer
   - 级别：🚨 关键

2. [Critic → Engineer] 质询 2：前端未传 X-Tenant-ID 证据不足
   - 论据：子域名/路径前缀识别可绕过 Header 传递问题
   - 要求回应：Engineer
   - 级别：普通

3. [Critic → Engineer] 质询 3：Celery 任务隔离缺少影响频率数据
   - 论据：tenant_usage_task.py 已正确实现租户隔离
   - 要求回应：Engineer
   - 级别：普通

4. [Critic → Engineer] 质询 4：缓存隔离评估遗漏
   - 论据：锁 API 已实现但未推广使用，优先级需调整
   - 要求回应：Engineer
   - 级别：普通

5. [Critic → Engineer] 质询 5：中间件顺序安全性影响
   - 论据：RateLimit 在 TenantContext 之后执行，限流可能不按租户隔离
   - 要求回应：Engineer
   - 级别：🚨 关键

6. [Critic → Engineer] 质询 6：UniqueConstraint 作用被忽略
   - 论据：Doctor 表已有租户内唯一约束，数据完整性有兜底
   - 要求回应：Engineer
   - 级别：普通

7. [Critic → 全体] 质询 7：认证授权链路未被充分认可
   - 论据：get_current_user 强制租户一致性校验是第一道防线
   - 要求回应：全体
   - 级别：普通

8. [Critic → Engineer] 质询 8：测试覆盖有效性未评估
   - 论据：使用 SQLite 而非 PostgreSQL，对多租户验证价值有限
   - 要求回应：Engineer
   - 级别：普通

9. [Critic → Engineer] 质询 9：数据库索引策略缺失
   - 论据：多租户系统所有查询应包含 tenant_id，索引策略直接影响性能
   - 要求回应：Engineer
   - 级别：🚨 关键

10. [Critic → Engineer/PM] 质询 10：Alembic 迁移策略未定义
    - 论据：单租户升级到多租户的数据迁移策略完全缺失
    - 要求回应：Engineer / PM
    - 级别：🚨 关键

### Critic 关键质询追踪

| # | 关键质询内容 | Lead 回应 | 回应是否充分 | 处置 |
|---|------------|---------|:---:|:---:|
| 1 | 产品定位自洽性 — 核心数据隔离层缺失 | 确认事实，数据隔离确实是核心缺失而非"部分实现" | 是 | 纳入 P0 |
| 5 | RateLimit 未按租户隔离 | 确认事实，rate_limit.py 未检查租户维度 | 是 | 纳入 P1 |
| 9 | 数据库索引策略 | 确认事实，tenant_id 字段已有 index=True，但复合索引策略未评估 | 部分 | 纳入 P2 |
| 10 | Alembic 迁移策略 | 确认事实，三方均未检查迁移脚本，无法评估 | 否 | 待定：需用户确认 |

---

## Round 3：共识层

### ✅ 共识项

1. **数据隔离是当前最大风险**
   **结论：** Doctor/Schedule/Store 服务的 mutation 操作缺少 tenant_id 过滤，是安全漏洞而非功能缺失
   **建议行动：** 在所有 service_mutation 方法中添加租户校验，优先修复 update/delete 操作
   **成本估算：** 30-40h
   **优先级：** P0

2. **权限/角色管理路由必须隔离**
   **结论：** router_roles.py 和 router_permissions.py 允许跨租户操作角色和权限，权限系统完全失控
   **建议行动：** 添加 get_tenant_filter 依赖，所有角色/权限操作限定租户范围
   **成本估算：** 20-30h
   **优先级：** P0

3. **认证授权链路是有效的第一道防线**
   **结论：** get_current_admin/get_current_user 强制校验租户一致性，即使数据层缺少全局过滤，已认证用户无法访问其他租户数据
   **建议行动：** 确保所有业务路由都使用认证依赖，补充未认证的公开接口的租户校验
   **成本估算：** 10-15h
   **优先级：** P0

4. **中间件和依赖注入层架构完善**
   **结论：** TenantContextMiddleware 4 种识别方式、TenantContext 上下文管理器、7+ 个租户相关依赖函数，基础设施到位
   **建议行动：** 无需重构，持续维护
   **成本估算：** 0h
   **优先级：** 已完成

5. **缓存隔离需要补全**
   **结论：** 管理员会话和 Token 黑名单未按租户隔离；分布式锁 API 已存在但 service_mutation 未使用
   **建议行动：** 会话和 Token 黑名单添加 tenant_id 维度；排班锁改用 tenant_distributed_lock
   **成本估算：** 20-25h
   **优先级：** P1

6. **RateLimit 需按租户隔离**
   **结论：** 限流中间件在 TenantContext 之后执行，但限流键未包含租户维度
   **建议行动：** 在 rate_limit.py 中获取当前租户 ID，限流键加入 tenant_id
   **成本估算：** 4-8h
   **优先级：** P1

7. **Celery 排班任务需要租户隔离**
   **结论：** schedule_task.py 的 auto_generate_schedules_task 未按租户过滤模板，但 tenant_usage_task 已正确隔离
   **建议行动：** 排班生成任务添加租户遍历逻辑（参考 tenant_usage_task 模式）
   **成本估算：** 15-20h
   **优先级：** P1

8. **前端租户切换 UI 缺失**
   **结论：** 仅有 StoreSwitcher，无 TenantSwitcher；请求拦截器未传 X-Tenant-ID，但可通过子域名/路径前缀方案绕过
   **建议行动：** 添加 TenantSwitcher 组件 + X-Tenant-ID Header 传递（推荐方案，运维成本低）
   **成本估算：** 16-24h
   **优先级：** P1

### ⚡ 分歧项

1. **全局 tenant_id 过滤机制（SQLAlchemy event listener）**
   **各方立场：**
   - Engineer Lead：强烈建议引入，防御性编程
   - Critic：UniqueConstraint 已提供数据完整性兜底，需评估 ROI
   **裁决/建议：** P2 级别，成本高（40-50h），在完成 P0/P1 手动过滤后再评估自动化的必要性
   **决策依据：** 手动过滤 + 认证层防线 + UniqueConstraint 已构成三层防护，自动化是锦上添花

2. **前端传递方案选择**
   **各方立场：**
   - Engineer Lead：添加 X-Tenant-ID Header
   - Critic：子域名/路径前缀方案也可行
   **裁决/建议：** 两种方案并行实施，Header 传递为首选（运维成本低），子域名/路径前缀作为备选
   **决策依据：** Header 方案对前端改动最小，子域名方案需要 DNS 配置

---

## 被低估的优势

1. **认证层租户校验完善**：get_current_admin/get_current_user 的强制租户一致性校验是有效的第一道防线，即使数据层有漏洞，已认证用户也无法跨租户访问
2. **依赖注入层设计完善**：7+ 个租户相关依赖函数（get_tenant_filter, validate_tenant_consistency 等）提供了良好的扩展基础
3. **租户用量任务已正确隔离**：tenant_usage_task.py 的 record_daily_usage 任务展示了正确的多租户 Celery 任务模式（遍历 tenant + 按 tenant_id 统计），可作为其他任务的参考
4. **数据库层面有租户内唯一约束**：Doctor 表的 UniqueConstraint(tenant_id, username) 等约束防止了跨租户数据冲突
5. **测试覆盖较全面**：7 个测试文件覆盖了缓存、锁、数据隔离、配额等关键场景

---

## 行动计划（按 ROI 排序）

| 优先级 | 行动 | 成本 | 价值 | 负责 | 状态 |
|--------|------|------|------|------|------|
| P0 | Doctor/Schedule/Store 服务添加 tenant_id 过滤 | 30-40h | 高（安全） | Engineer | |
| P0 | 权限/角色管理路由添加租户隔离 | 20-30h | 高（安全） | Engineer | |
| P0 | 确保所有业务路由使用认证依赖 | 10-15h | 高（安全） | Engineer | |
| P1 | RateLimit 按租户隔离 | 4-8h | 高（稳定性） | Engineer | |
| P1 | 排班锁改用 tenant_distributed_lock | 4-6h | 中（并发安全） | Engineer | |
| P1 | 会话和 Token 黑名单添加租户维度 | 20-25h | 中（安全） | Engineer | |
| P1 | Celery 排班任务添加租户隔离 | 15-20h | 中（数据正确性） | Engineer | |
| P1 | 前端添加 TenantSwitcher + X-Tenant-ID Header | 16-24h | 高（用户体验） | Designer + Engineer | |
| P1 | get_tenant_from_admin hack 清理 | 8-12h | 中（技术债务） | Engineer | |
| P2 | 全局 tenant_id 过滤机制评估 | 40-50h | 中（防御性） | Engineer | |
| P2 | 数据库复合索引策略优化 | 15-20h | 中（性能） | Engineer | |
| P2 | 测试补充（PostgreSQL 集成测试） | 20-30h | 中（质量） | Engineer | |
| 待定 | Alembic 迁移策略（单租户→多租户数据迁移） | 待评估 | 高 | Engineer + PM | |

### P0：立即执行（高价值、安全关键）

1. **Doctor/Schedule/Store 服务添加 tenant_id 过滤** [成本：30-40h] [负责：Engineer]
   - 在 service_mutation.py 的 create/update/delete 方法中添加租户校验
   - 使用 get_tenant_filter() 或从上下文获取 tenant_id
   - 添加 validate_tenant_consistency() 验证关联数据

2. **权限/角色管理路由添加租户隔离** [成本：20-30h] [负责：Engineer]
   - router_roles.py 和 router_permissions.py 添加 get_tenant_filter 依赖
   - 角色查询限定 tenant_id 范围
   - 权限创建/修改校验租户一致性

3. **确保所有业务路由使用认证依赖** [成本：10-15h] [负责：Engineer]
   - 审计所有公开接口，确保有租户上下文校验
   - 公开预约接口添加 require_tenant_context()

### P1：本轮迭代（高价值、中等成本）

1. **RateLimit 按租户隔离** [成本：4-8h] [负责：Engineer]
2. **排班锁改用 tenant_distributed_lock** [成本：4-6h] [负责：Engineer]
3. **会话和 Token 黑名单添加租户维度** [成本：20-25h] [负责：Engineer]
4. **Celery 排班任务添加租户隔离** [成本：15-20h] [负责：Engineer]
5. **前端添加 TenantSwitcher + X-Tenant-ID Header** [成本：16-24h] [负责：Designer + Engineer]
6. **get_tenant_from_admin hack 清理** [成本：8-12h] [负责：Engineer]

### P2：下个周期规划（中等价值、较高成本）

1. **全局 tenant_id 过滤机制评估** [成本：40-50h] [负责：Engineer]
2. **数据库复合索引策略优化** [成本：15-20h] [负责：Engineer]
3. **测试补充（PostgreSQL 集成测试）** [成本：20-30h] [负责：Engineer]

### 待定：需用户确认

1. **Alembic 迁移策略（单租户→多租户数据迁移）** [成本：待评估] [负责：Engineer + PM]
   - 当前系统是否已有生产数据？
   - 历史数据如何分配 tenant_id？
   - 是否需要数据迁移脚本？

---

## 摘要

**使用模式：** 领域主导 — Engineer 领域主导

**关键共识：**
- 8 项达成共识

**关键分歧：**
- 2 项需要决策者介入（全局过滤机制、前端传递方案）

**Top 3 P0 行动：**
1. Doctor/Schedule/Store 服务添加 tenant_id 过滤（30-40h，安全关键）
2. 权限/角色管理路由添加租户隔离（20-30h，安全关键）
3. 确保所有业务路由使用认证依赖（10-15h，安全关键）

**Critic 关键洞察：**
- 认证授权链路是有效的第一道防线，数据层漏洞的实际可利用性需结合认证层评估
- 租户用量任务（tenant_usage_task.py）已展示正确的多租户 Celery 任务模式，可作为其他任务的参考
- Alembic 迁移策略是三方都遗漏的关键问题，直接影响系统从单租户升级到多租户的可行性

---

## 附录：模式切换日志

| 时间 | 从 | 到 | 原因 |
|------|-----|-----|------|
| | | | |
