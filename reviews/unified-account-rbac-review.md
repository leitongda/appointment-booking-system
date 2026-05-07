# appointment-booking-system — 自适应多智能体研究画布

> 协作模式：对等协作
> 日期：2026-05-06
> 审查目标：评估将 Admin、Doctor、User 三张独立账号表统一为单用户表 + RBAC 角色架构的重构可行性及影响面

---

## 模式选择

**选定模式：** 对等协作

**选择理由：** 账号体系统一是一个跨职能复杂权衡决策，涉及产品（业务规则/用户流程）、设计（多端 UI 适配）、工程（数据模型/迁移/API）三个维度。无单一主导领域，三方视角同等重要，需要充分交叉碰撞发现盲点。

---

## Round 1：事实层（只写事实，不评价）

### PM — 产品视角

**当前账号体系：**
- 三张独立账号表：users（患者）、doctors（医生）、admins（管理员）
- Doctor.user_id 可选关联 User，允许医生独立存在或关联用户账号（`models/doctor.py:11`）
- Admin.tenant_id 为 NULL 表示平台管理员（`models/admin.py:83`）
- 唯一约束差异：Admin.username 全局唯一，Doctor/User 手机号租户内唯一

**注册/登录方式：**
- Admin：账号密码 / 手机号密码 / 短信验证码 / 微信扫码（`modules/admin/router_auth_login.py`）
- Doctor：手机号或账号 + 密码（`modules/doctors/router.py`）
- User：手机号密码 / 微信授权登录（`modules/auth/router.py`）

**权限控制：**
- 仅 Admin 使用 RBAC：roles 表 + role_permissions（`models/admin.py:10-15`）
- 四种角色：SUPER_ADMIN / PLATFORM_ADMIN / TENANT_ADMIN / STORE_ADMIN（`common/auth_deps.py:258-264`）
- Doctor 和 User 无细粒度权限控制，医生权限硬编码在业务逻辑中

**业务流程中的账号使用：**
- 预约：appointments 表关联 user_id（患者）+ doctor_id（医生）（`models/appointment.py`）
- 消息：messages 表用 user_id + user_type（patient/doctor）区分角色（`models/message.py`）
- 操作日志：operation_logs 记录 admin_id + admin_name（`models/admin.py:99-117`）
- 审计字段：所有业务表继承 AuditMixin（created_by/updated_by）（`utils/audit.py`）

**跨角色操作场景：**
- 管理员可代患者预约（created_by 字段记录）
- 医生通过 patient_id 查看就诊记录
- 同一人可同时拥有医生账号和用户账号（doctor.user_id 关联）
- 管理员不能直接登录患者端，需要单独的用户账号

**多租户：**
- 所有账号表包含 tenant_id，唯一约束均为 (tenant_id, field) 复合
- 同一手机号可在不同租户注册
- 微信用户可在不同租户分别绑定（tenant_id + openid/unionid）

**管理功能：**
- Admin 端用户管理（`apps/admin/src/pages/user/`）：列表、详情、禁用/启用、删除
- Admin 端医生管理（`apps/admin/src/pages/doctor/`）：列表、详情、编辑、排班、诊费
- Admin 端管理员管理（`apps/admin/src/pages/system/user.tsx`）：CRUD、角色分配、门店绑定

### Designer — 用户视角

**各端登录页面：**
- Patient-H5：手机号 + 密码，注册跳转，忘记密码联系客服（`patient-h5/src/pages/login/index.tsx`）
- Doctor：手机号或账号 + 密码，使用 authApi.doctorLogin()（`doctor/src/pages/login/index.tsx`）
- Admin：三种组件化登录方式（微信/手机号/账号），保存租户ID和门店信息（`admin/src/pages/login/`）

**用户信息展示：**
- Patient-H5：头像(72x72圆形)、昵称/姓名、手机号脱敏，手机号只读不可改（`patient-h5/src/pages/profile/`）
- Doctor：头像、姓名、职称灰色小字，从 localStorage 获取（`doctor/src/app.tsx:105-145`）
- Admin：头像、姓名/用户名，下拉菜单含个人设置/修改密码/退出（`admin/src/components/RightContent/`）

**信息架构差异：**
- Patient-H5：扁平化路由，底部 Tab 导航，无复杂权限
- Doctor：ProLayout 左侧菜单，菜单固定无细粒度权限
- Admin：ProLayout 多级折叠菜单，40+ 种权限细粒度控制（`admin/src/access.ts`）

**交互流程差异：**
- 修改密码：仅 Admin 端有此功能（弹窗形式），Doctor/Patient-H5 缺失
- 忘记密码：Patient-H5 仅弹窗显示客服电话，无自助重置
- 手机号换绑：三端均无此功能
- 头像上传：Patient-H5 手动保存，Admin 自动保存（含裁剪），Doctor 缺失
- 退出登录：三端各自独立实现，清理策略不同

**消息通知：**
- Patient-H5 消息类型：appointment/consultation/stop_clinic/system
- Doctor 消息类型：schedule/appointment/consultation/stop_clinic/system
- 消息 API 用 userId + userType 区分（`packages/api/src/modules/message.ts`）
- Doctor 端支持 WebSocket 实时推送

### Engineer — 技术视角

**数据模型字段对比：**
- 共同字段：id(UUID), tenant_id, phone, password_hash, avatar, status, created_at, updated_at
- Admin 独有：username(全局唯一), email, role_id, current_store_id, admin_stores(多对多)
- Doctor 独有：user_id(可选→users), username(租户唯一), 医疗资质字段(title/education/license等), 排班设置(max_daily_appointments等), 展示设置(page_style/promo_video等), banner, deleted_at
- User 独有：openid, unionid, wechat_nickname, wechat_avatar, wechat_synced_at, points, nickname

**外键引用统计：**
- Admin 被引用：4 处（OperationLog, AdminLoginHistory, admin_stores, ScheduleGenerationLog）
- Doctor 被引用：9 处（Appointment, Schedule, MedicalRecord, ConsultationFee, DoctorBookingSetting, ScheduleTemplate, ScheduleSuspension, RuleSet, Doctor→User）
- User 被引用：6 处（Patient, Appointment, PointLog, Blacklist, UserFavorite, Doctor.user_id）

**Token 结构差异：**
- Admin: `{sub: id, type: "admin", tenant_id: ...}`
- Doctor: `{sub: id, type: "doctor"}`
- User: `{sub: id}`（无 type 字段）

**认证依赖注入函数（7个）：**
- `get_current_user`（`auth_deps.py:35-96`）：Token→User表，含医生检查
- `get_current_doctor`（`auth_deps.py:99-129`）：依赖 get_current_user，检查 is_doctor
- `get_current_doctor_by_token`（`auth_deps.py:132-199`）：直接 Doctor Token 认证
- `get_current_admin`（`auth_deps.py:202-430`）：Admin Token 认证，含租户/门店/权限解析
- `get_current_super_admin`（`auth_deps.py:433-442`）：验证超管
- `get_optional_user`（`auth_deps.py:445-453`）：可选认证
- `get_current_user_or_admin`（`auth_deps.py:456-596`）：同时支持 User 和 Admin

**租户隔离：**
- ContextVar 存储 tenant_id/tenant_code（`middleware/tenant_context.py:28-29`）
- 三种识别方式：Header > 子域名 > 路径前缀
- 所有认证函数强制校验 tenant_id 一致性

**迁移现状：**
- 75 个 Alembic 版本文件，命名 `{num}_{description}.py`
- 数据迁移脚本：init_roles.py, init_data.py, migrate_tenant_data.py 等

**Celery 任务引用：**
- operation_log_task, tenant_usage_task, blacklist_task, notification_task, behavior_log_task 均引用账号模型
- 任务通过参数传递 admin_id/doctor_id/user_id

**测试 Fixtures：**
- conftest.py 中 10 个账号相关 fixtures（test_tenant, test_store, test_doctor, test_user, test_patient, test_super_admin 等）
- Token 生成 fixtures：super_admin_token, store_admin_token

**路由注册：**
- 62 个 API 模块（`api/v1/__init__.py`）
- 账号相关：/auth, /users, /doctors, /admin

---

## Round 2：辩论层

### 交叉评论投票矩阵

#### 完整投票矩阵（对等协作模式）

| 议题 | PM | Designer | Engineer | Critic 质询 | 共识？ |
|------|-----|----------|----------|-------------|--------|
| 统一账号表（主表+扩展表模式） | ✅ +1 | ✅ +1 | ✅ +1（但明确：统一≠单表） | ⚡ 当前可选关联已支持一人多角色，强制统一反而失去灵活性？ | 🤝 共识（3/3） |
| 一人多角色业务价值 | ✅ +1（强烈） | ✅ +1（强烈） | ✅ +1 | ⚡ 缺少触发频率数据支撑 | 🤝 共识（3/3） |
| RBAC 扩展到所有角色 | ✅ +1 | ✅ +1 | ✅ +1 | ⚡ 将 RBAC 扩展到 Doctor/User 的成本是否低于合并表？ | 🤝 共识（3/3） |
| 消息/通知/审计系统统一 | ✅ +1 | ✅ +1 | ✅ +1 | — | 🤝 共识（3/3） |
| 多租户唯一约束策略 | ✅ +1 | ✅ +1 | ✅ +1（推荐租户内唯一） | ⚡ Admin 全局唯一 vs 租户内唯一是有意设计 | ⚠️ 分歧（Critic 质疑） |
| 数据迁移策略（大爆炸 vs 渐进） | 反驳 Engineer 的渐进方案 | — | ✅ 大爆炸切换 | 🚨 迁移方案完全缺失，无回滚策略 | ⚠️ 分歧 |
| 统一登录页面 | ✅ +1 | ✅ +1 | ✅ +1（28h 成本） | ⚡ 统一后端表≠统一前端登录页，真正需要的是 SSO | 🤝 共识（3/3，但 Critic 指出边界） |
| Doctor 40+ 字段拆为扩展表 | ✅ +1 | — | ✅ +1（反对 JSON 字段） | — | 🤝 共识（2/2，Designer 未投票） |
| 软删除策略统一 | — | — | ✅ +1（发现 Doctor 有软删除，其他表无） | — | 仅 Engineer 发现 |
| Token 兼容性处理 | — | ✅ +1 | ✅ +1（需强制重新登录） | 🚨 强制重新登录的用户影响未评估 | ⚠️ 分歧 |
| 前端适配成本 | — | ✅ +1 | ✅ +1（48h 前端成本） | — | 🤝 共识（2/2，PM 未投票） |

### 独到发现

1. **PM 交叉发现 — 产品定位冲突**：当前三表硬编码角色架构与"可配置多租户 SaaS 平台"定位根本冲突。每次新增角色（如护士、药剂师）需建新表+新认证逻辑+新 API，违背平台化目标。

2. **PM 交叉发现 — 一人多角色价值被低估**：医生需预约其他医生、管理员需测试患者流程、客服需以用户身份操作——这些是真实业务场景，当前架构下需多账号多端登录，体验极差。

3. **Designer 交叉发现 — 无障碍风险**：Patient-H5 面向含老年患者群体，统一后 UI 复杂度可能向患者端渗透。三端错误处理风格不一致，跨端操作错误反馈缺失标准。

4. **Engineer 交叉发现 — 软删除策略不一致**：Doctor 表有 deleted_at 软删除，Admin 和 User 直接物理删除。统一后需决定统一策略，否则级联删除逻辑冲突。

5. **Engineer 交叉发现 — 性能回归风险**：统一后所有账号查询需 JOIN 扩展表，当前 9 处 Doctor 外键引用查询变慢。需引入 Redis 缓存层+读写分离。

6. **Engineer 交叉发现 — 总成本 216 小时**：数据模型 48h + 认证重写 40h + 数据迁移 24h + API 路由 32h + Celery 24h + 前端 48h ≈ 27 个工作日。

### Critic 质询

1. [Critic → PM] 产品定位自洽性：当前 Doctor.user_id 可选关联已支持一人多角色灵活性，强制统一为单表+角色反而失去"医生账号可独立于患者账号存在"的灵活性。级别：🚨 关键

2. [Critic → Engineer] 40+ 字段迁移查询性能：扩展表 JOIN 后 Doctor 9 处外键查询性能下降未被量化，缺少基准测试。级别：普通

3. [Critic → Designer] 统一账号 UX 收益被夸大：三端完全独立应用，统一后端表≠统一前端登录体验，真正需要的是 SSO 而非表合并。级别：普通

4. [Critic → Engineer] 数据迁移方案完全缺失：无迁移步骤、无停机时间评估、无数据验证方案、无回滚策略。级别：🚨 关键

5. [Critic → PM] 缺少"不统一也能解决"的折中方案评估：跨角色操作可通过角色切换功能解决，修改密码缺失可独立补全，RBAC 可独立扩展到其他表——投入产出比未比较。级别：普通

6. [Critic → Engineer] 独立表设计的优势被忽略：职责清晰隔离、权限安全隔离、新增角色灵活（如药剂师直接建表）——统一后的代价未讨论。级别：普通

7. [Critic → 全体] 触发频率/影响范围数据缺失：无跨角色操作频率、无 UI 差异投诉数据、无代码修改 bug 引入风险量化。级别：普通

8. [Critic → 全体] 独立表设计优势未讨论：职责隔离、安全隔离、扩展灵活（新增角色直接建表）。级别：普通

9. [Critic → Engineer] Token 兼容性：统一后 Token 结构变化需强制所有用户重新登录，三端在线用户全部受影响，用户影响和支持成本未评估。级别：🚨 关键

10. [Critic → Engineer] Celery 任务和测试 Fixtures 迁移成本被低估：5+ 任务参数类型需修改，10 个 fixtures 需重写，回归测试成本未充分评估。级别：普通

### 🚨 Critic 关键质询追踪

| # | 关键质询内容 | 三方回应摘要 | 回应是否充分 | 处置 |
|---|------------|------------|------------|------|
| 1 | 当前可选关联已支持一人多角色，强制统一反而失去灵活性 | PM: 统一是为了平台化可配置，不仅是一人多角色；Engineer: 扩展表模式保留独立性 | 部分 | 纳入计划（需保留角色独立性设计约束） |
| 2 | 数据迁移方案完全缺失（无步骤/停机/验证/回滚） | Engineer: 建议双写+分阶段切换，但未提供具体方案 | 否 | 待定：需用户确认迁移策略 |
| 3 | Token 变更需强制所有用户重新登录，影响未评估 | Engineer: 明确需要强制重新登录，但未评估用户影响 | 否 | 待定：需用户确认 Token 策略 |

---

## Round 3：共识层

### ✅ 共识项

1. **议题：统一账号表（主表+扩展表模式）**
   **结论：** 采用主表 `unified_accounts` + 三张扩展表 `account_doctors`/`account_admins`/`account_users` 的模式。共同字段（约 8 个）放主表，业务特有字段放扩展表。不使用 JSON 字段存储扩展属性（外键约束和索引需求）。
   **建议行动：** 设计统一数据模型，创建迁移脚本
   **成本估算：** 48h（数据模型）+ 24h（迁移脚本）= 72h
   **优先级：** P1

2. **议题：RBAC 扩展到所有角色**
   **结论：** 将当前 Admin 专属的 RBAC 系统扩展为统一权限系统，支持 Doctor 和 User 的细粒度权限控制。权限不再硬编码在业务逻辑中。
   **建议行动：** 重构权限系统，增加角色-权限-资源三层模型
   **成本估算：** 40h
   **优先级：** P1

3. **议题：消息/通知/审计系统统一**
   **结论：** 统一 operation_logs 和 messages 表的角色引用方式，审计字段 created_by/updated_by 增加角色标识，满足医疗合规要求。
   **建议行动：** 重构审计日志和消息系统
   **成本估算：** 24h（审计）+ 12h（消息）= 36h
   **优先级：** P1

4. **议题：Doctor 40+ 字段拆分为扩展表**
   **结论：** 医疗资质、排班设置、展示设置等业务字段拆入 `account_doctors` 扩展表，主表保持精简。外键字段（department_id, store_id）必须在扩展表中保留。
   **建议行动：** 拆分 Doctor 模型为扩展表
   **成本估算：** 包含在 P1 数据模型重构中
   **优先级：** P1

5. **议题：认证函数统一**
   **结论：** 7 个认证依赖注入函数合并为 2-3 个统一函数（`get_current_account`, `get_current_account_with_role`, `get_optional_account`），内部根据 Token 中的角色信息路由到对应扩展表。
   **建议行动：** 重写认证系统
   **成本估算：** 40h
   **优先级：** P0

### ⚡ 分歧项

1. **议题：数据迁移策略（大爆炸 vs 渐进式）**
   **各方立场：**
   - PM：建议分阶段迁移（先新用户后旧用户）+ 双写期 1-2 个月
   - Engineer：建议统一切换（大爆炸），避免双重认证逻辑维护
   - Critic：🚨 迁移方案完全缺失，无法评估
   **裁决/建议：** 采用 **双写过渡期** 方案——先建新表，双写 2-4 周，验证一致性后统一切换读取源，最后下线旧表。兼顾 Engineer 的代码简洁性和 PM 的风险控制。
   **决策依据：** 医疗预约系统不能承受长时间停机，双写期可在线上验证。

2. **议题：Token 兼容性与强制重新登录**
   **各方立场：**
   - Engineer：明确需要强制重新登录
   - Critic：🚨 用户影响和支持成本未评估
   - Designer：未直接回应
   **裁决/建议：** 采用 **渐进式 Token 迁移**——新 Token 格式同时包含 `account_id` 和旧格式字段，认证函数优先读取新字段。旧 Token 自然过期（ACCESS_TOKEN_EXPIRE_MINUTES）后自动切换，无需强制登出。过渡期 1-2 天。
   **决策依据：** 减少用户感知，避免大规模支持工单。

3. **议题：多租户唯一约束策略**
   **各方立场：**
   - Engineer：统一为租户内唯一 `(tenant_id, phone)`
   - Critic：Admin 全局唯一是有意设计（平台管理员跨租户）
   **裁决/建议：** 保留 **混合策略**——统一账号表中 `phone` 和 `username` 采用 `(tenant_id, field)` 租户内唯一约束，`tenant_id = NULL` 的平台管理员天然不受约束影响（NULL 不参与唯一索引）。这与当前行为完全一致。
   **决策依据：** PostgreSQL 中 NULL 值不参与 UNIQUE 约束，混合策略无需额外代码。

---

## 被低估的优势（Critic 提醒）

1. **职责清晰隔离**：当前三表独立，修改 Doctor 认证逻辑不影响 Admin/User。统一后任何认证变更影响所有角色，需更严格的测试覆盖。

2. **安全隔离**：即使 Doctor 表被攻破，攻击者无法直接获取 Admin 或 User 的密码哈希。统一后主表成为单点风险，需加强安全防护。

3. **扩展灵活性**：新增角色（如药剂师、技师）当前可独立建表，不影响现有结构。统一后需在扩展表框架内新增，灵活度降低但可控。

4. **Doctor.user_id 可选关联的优雅设计**：当前医生可独立存在或关联患者账号，是一种灵活的渐进式一人多角色方案。统一后需通过角色表模拟，复杂度不降反升。

---

## 行动计划（按 ROI 排序）

| 优先级 | 行动 | 成本 | 价值 | 负责 | 状态 |
|--------|------|------|------|------|------|
| P0 | 统一认证函数（7→3个） | 40h | 高：降低维护复杂度 | Engineer | 规划中 |
| P0 | 补全基础功能（修改密码/忘记密码） | 16h | 高：用户体验+安全 | Designer+Engineer | 规划中 |
| P0 | 审计日志统一（增加角色标识） | 24h | 高：医疗合规要求 | Engineer | 规划中 |
| P1 | 设计统一数据模型（主表+扩展表） | 48h | 高：架构基础 | Engineer | 规划中 |
| P1 | RBAC 扩展到所有角色 | 40h | 高：企业客户必需 | PM+Engineer | 规划中 |
| P1 | 数据迁移（双写过渡方案） | 24h | 高：风险控制 | Engineer | 规划中 |
| P1 | 前端适配（Token/API/登录） | 48h | 高：三端联调 | Designer+Engineer | 规划中 |
| P2 | 消息/通知系统统一 | 12h | 中：数据一致性 | Engineer | 规划中 |
| P2 | Celery 任务和测试改造 | 24h | 中：回归测试 | Engineer | 规划中 |
| P2 | 手机号换绑功能 | 36h | 中：功能增强 | Designer+Engineer | 规划中 |
| P2 | 头像上传统一（含 Doctor 端补全） | 20h | 中：一致性 | Designer+Engineer | 规划中 |
| 待定 | 数据迁移完整方案（含回滚） | TBD | 高：生产安全 | Engineer | 需用户确认 |
| 待定 | Token 渐进式迁移验证 | TBD | 高：用户影响 | Engineer | 需用户确认 |

### P0：立即执行（高价值、低成本）

1. **统一认证函数**（40h）：将 7 个认证函数合并为 2-3 个，使用渐进式 Token 迁移避免强制登出。这是所有后续工作的基础。
2. **补全修改密码/忘记密码功能**（16h）：Doctor 和 Patient-H5 缺失的修改密码功能，Patient-H5 的忘记密码自助重置。无需统一账号即可独立完成。
3. **审计日志增加角色标识**（24h）：operation_logs 表增加 account_role 字段，created_by/updated_by 增加角色类型。医疗合规要求。

### P1：本轮迭代（高价值、中等成本）

1. **统一数据模型设计**（48h）：创建 `unified_accounts` 主表 + 三张扩展表，编写迁移脚本。
2. **RBAC 扩展**（40h）：将权限系统从 Admin 扩展到 Doctor/User，支持角色-权限-资源三层模型。
3. **双写过渡数据迁移**（24h）：创建新表，双写 2-4 周，验证一致性后切换读取源。
4. **前端三端适配**（48h）：Token 逻辑、API 路由、登录流程统一。

### P2：下个周期规划（中等价值、较高成本）

1. **消息/通知系统统一**（12h）
2. **Celery 任务和测试改造**（24h）
3. **手机号换绑功能**（36h）
4. **头像上传统一**（20h）

### 待定：需用户确认

1. **数据迁移完整方案**：双写过渡期的具体时长、停机窗口、数据验证脚本、回滚操作手册。需用户确认可接受的停机时间和风险等级。
2. **Token 渐进式迁移验证**：旧 Token 自然过期方案是否可接受，是否需要额外的用户通知（弹窗/短信提示重新登录）。

---

## 摘要

**使用模式：** 对等协作

**关键共识：**
- 5 项达成共识（统一主表+扩展表、RBAC 扩展、审计统一、Doctor 字段拆分、认证函数统一）

**关键分歧：**
- 3 项需要决策者介入（数据迁移策略、Token 兼容性、多租户唯一约束）

**Top 3 P0 行动：**
1. 统一认证函数（7→3个），成本 40h，降低维护复杂度
2. 补全修改密码/忘记密码功能，成本 16h，用户体验+安全
3. 审计日志增加角色标识，成本 24h，医疗合规要求

**Critic 关键洞察：**
- 当前 Doctor.user_id 可选关联已是一种优雅的一人多角色方案，统一后需确保不丢失这种灵活性
- 三端独立应用（不同技术栈/不同设备），统一后端表≠统一前端体验，真正的体验统一需要 SSO
- 独立表设计的安全隔离优势（单表攻破不影响其他角色）在统一后需通过其他手段补偿

**总成本估算：** 约 216h（27 个工作日），分 3 个阶段（P0: 80h / P1: 160h / P2: 92h）

---

## 附录：模式切换日志

| 时间 | 从 | 到 | 原因 |
|------|-----|-----|------|
| 无切换 | - | - | - |
