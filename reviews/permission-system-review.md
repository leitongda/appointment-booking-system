# appointment-booking-system — 自适应多智能体研究画布

> 协作模式：领域主导（Engineer 主导）
> 日期：2026-04-13
> 审查目标：权限精细化管理企业级拆分方案

---

## 模式选择

**选定模式：** 领域主导（Engineer 主导）

**选择理由：** 权限体系设计的核心是技术架构问题（数据库模型、API鉴权、中间件、前端控制），需要 Engineer 维度最深入的分析。PM 和 Designer 作为辅助提供业务权限需求和前端交互视角。

---

## Round 1：事实层（只写事实，不评价）

### PM — 产品视角（精简版）

**业务角色事实：**

1. 系统定义 5 种角色层级（来源：`apps/server/scripts/init_roles.py`）：
   - `SUPER_ADMIN`：超级管理员，平台级（tenant_id=NULL），权限为 `["*"]`
   - `PLATFORM_ADMIN`：平台管理员，平台级，与 SUPER_ADMIN 等同处理
   - `TENANT_ADMIN`：租户管理员，租户级
   - `STORE_ADMIN`：门店管理员，租户级，仅限绑定门店
   - `STORE_USER`：门店用户，租户级，自定义权限，仅限绑定门店

2. 角色判断逻辑在 `apps/server/app/common/deps.py:257-260`，通过 role_code 和 role_name 双重判断

3. 角色保护机制：SUPER_ADMIN 不可修改 code、不可删除；系统至少保留一个启用的超级管理员（`apps/server/app/modules/admin/service_roles.py:102-144`）

4. 医生角色独立于 RBAC 体系，通过 Doctor 模型的 username/password 认证（`apps/server/app/models/doctor.py:19-21`）

5. 患者无 RBAC，User 表存储账号，Patient 表存储就诊人，一对多关系（`apps/server/app/models/user.py:6-78`）

**业务模块功能清单：**

6. 后端 30+ 业务模块，覆盖：认证、管理员、租户、门店、科室、医生、排班、预约、患者、病历、消息、反馈、内容、诊费、统计、审计、设置、班次、规则组、小程序平台、支付、上传、导入导出、WebSocket、候补、积分、医生端等

7. 前端 Admin 端 40+ 路由，按一级菜单分组：
   - 仪表盘（canDashboard）
   - 平台管理（canPlatformManagement）
   - 组织与权限（canOrganizationManagement）
   - 医疗业务（canMedicalServices）
   - 经营配置（canOperationsConfig）
   - 内容与触达（canContentOperations）

8. 医生端 10+ 路由：工作台、排班、停诊调班、预约管理、就诊管理、病历、统计、消息

9. 患者端 H5/小程序：首页、科室、医生、预约、记录、消息、个人中心、反馈

**数据敏感度事实：**

10. 高敏感字段：password_hash（bcrypt）、phone（明文）、id_card（明文）、openid/unionid（明文）

11. 中敏感字段：license_number、patient_name、patient_phone、symptom_description、chief_complaint、diagnosis、prescription、allergy_history、payment_transaction_id

12. 日志脱敏：operation_log 中间件自动将 password/token/secret 等字段替换为 `***`（`apps/server/app/middleware/operation_log.py:79-150`）

13. API 响应未对手机号、身份证号做脱敏处理（`apps/server/app/schemas/user.py:230,315`）

**功能权限控制现状：**

14. 前端菜单/路由：通过 routes.ts 的 `access` 字段声明权限标识

15. 前端按钮：通过 AuthButton 组件 + access.hasPermission() 判断

16. 前端 Tab：通过页面组件内条件渲染，无独立权限组件

17. 权限配置混合模式：角色-权限关联在数据库（JSON）；菜单-权限映射硬编码在前端

### Designer — 用户视角（精简版）

**前端路由与菜单事实：**

1. Admin 端路由配置在 `apps/admin/config/routes.ts`，所有业务路由通过 `access` 字段做权限守卫

2. Doctor 端路由在 `apps/doctor/src/.umi/core/route.tsx`，仅检查 currentDoctor 是否存在，无细粒度权限

3. Patient-H5 路由无权限守卫，通过门店上下文验证访问

4. 无权限时重定向到 `/dashboard`（`apps/admin/src/app.tsx:487-490`）；无 token 跳转登录页（`apps/admin/src/app.tsx:454-460`）

**UI 元素权限控制事实：**

5. AuthButton 组件（`apps/admin/src/components/AuthButton/index.tsx`）：
   - 支持单个/多个权限检查（任一满足）
   - fallback 模式：hidden（隐藏）、disabled（禁用）、tooltip（提示）
   - 包含 usePermission Hook

6. OperationButton 组件（`apps/admin/src/components/ListOperations/OperationButton.tsx`）：统一操作按钮，支持 permission 属性

7. CreateButton 组件（`apps/admin/src/components/ListOperations/CreateButton.tsx`）：新增按钮，支持 permission 属性

8. createOperationColumn 函数（`apps/admin/src/components/ListOperations/createOperationColumn.tsx`）：支持 viewPermission/editPermission/deletePermission

9. Tab 级别无独立权限控制组件，通过页面内 access.hasPermission() 条件渲染

10. 字段脱敏：maskName()、maskPhone() 函数仅在排班日历详情抽屉中使用（`apps/admin/src/pages/schedule/calendar/components/DayDetailDrawer.tsx:63-72`），未全局统一

**前端权限数据流：**

11. 登录后流程：setToken → localStorage 保存租户/门店/用户信息 → setInitialState 更新全局状态（currentUser 包含 permissions 数组）

12. 权限存储：localStorage（token、tenant_id、store）+ Umi InitialState（currentUser.permissions、roleCode、isSuperAdmin）

13. access.ts 权限计算（`apps/admin/src/access.ts:5-211`）：
    - 基础函数：hasPermission、hasAnyPermission、hasAllPermissions、hasModuleAccess
    - 预定义标识：canDashboard、canPlatformManagement、canOrganizationManagement 等 ~30 个
    - 超级管理员和通配符 `*` 自动通过所有检查

### Engineer — 技术视角（加深版）

**认证机制事实：**

1. JWT Token 机制（`apps/server/app/core/security.py:173-201`）：
   - HS256 算法，密钥来自 settings.SECRET_KEY
   - access_token：30 分钟有效期
   - refresh_token：7 天有效期
   - 支持 4 种 token 类型：access、refresh、admin、doctor
   - Token 撤销：Redis 黑名单 `token:blacklist:{tenant_id}:{token_hash}`

2. 密码存储：bcrypt + 自动 salt（`apps/server/app/core/security.py:159-171`）

3. RSA-2048 加密传输（`apps/server/app/core/security.py:25-157`）：前端加密密码，后端私钥解密

4. 登录端点：
   - `POST /api/v1/auth/login`：用户登录（手机号+密码）
   - `POST /api/v1/admin/login`：管理员登录（RSA 加密传输）
   - `POST /api/v1/auth/wechat/login`：微信登录（code 换 openid）
   - `POST /api/v1/admin/logout`：登出（Token 加入黑名单）

**授权/权限模型事实：**

5. RBAC 模型（`apps/server/app/models/admin.py`）：
   - Permission 表（29-40行）：code、name、type(menu/button)、parent_code
   - Role 表（42-67行）：name、code、description、status、tenant_id、permissions(JSON)
   - Admin 表（69-96行）：username、password_hash、role_id、tenant_id、current_store_id
   - admin_stores 关联表：管理员-门店多对多

6. 权限存储：Role.permissions 字段为 JSON 数组，存储权限码列表（如 `["doctor:create", "doctor:update"]`）

7. 权限检查依赖注入（`apps/server/app/api/deps.py:642-732`）：
   - `require_permission(*permissions)`：任一权限
   - `require_all_permissions(*permissions)`：所有权限
   - 超级管理员和通配符 `*` 自动通过

8. 权限类型：当前仅支持 menu 和 button 两种 type

**API 端点鉴权事实：**

9. 鉴权依赖函数：
   - `get_current_user`（deps.py:32-94）：JWT 解析 + 多租户校验
   - `get_current_admin`（deps.py:199-393）：验证 admin token + 黑名单检查 + 角色加载
   - `get_current_doctor_by_token`（deps.py:129-196）：验证 doctor token + 租户校验
   - `get_current_super_admin`：要求超级管理员权限
   - `require_platform_admin`：要求平台管理员权限
   - `check_store_access`：检查门店访问权限

10. API 鉴权方式混合：部分使用依赖注入，部分使用函数内 if 判断 + HTTPException(403)

**中间件权限拦截事实：**

11. TenantContextMiddleware（`apps/server/app/middleware/tenant_context.py:91-232`）：
    - 识别优先级：X-Tenant-ID Header > X-Tenant-Code Header > 子域名 > 路径前缀
    - 设置 ContextVar：_current_tenant_id、_current_tenant_code
    - 跳过路径：/health、/docs、/redoc、/api/v1/platform

12. 请求日志中间件记录租户上下文（`apps/server/app/middleware/request_log.py`）

**数据库权限模型事实：**

13. 所有业务表包含 tenant_id 字段做数据隔离

14. 唯一约束包含 tenant_id：（tenant_id, code）、（tenant_id, phone）等

15. Permission 表仅定义 code/name/type/parent_code，未定义 resource_type、action、scope 等细粒度字段

**前端权限控制事实：**

16. access.ts 定义 ~30 个模块级权限标识（canDashboard、canDoctor 等），未细化到按钮/Tab/字段级别

17. AuthButton 组件已实现按钮级控制框架，但实际使用覆盖面有限

18. 前端 permission 码与后端不完全对齐（前端使用 canXxx 布尔值，后端使用 module:action 字符串）

**多租户权限隔离事实：**

19. 数据库层：tenant_id 外键 + 唯一约束
20. API 层：get_tenant_filter() 自动添加 WHERE 条件
21. 缓存层：Redis 键包含 tenant_id 前缀
22. 上下文层：TenantContextMiddleware 设置 ContextVar

23. SubscriptionPlan 功能限制（`apps/server/app/models/tenant.py:16-46`）：
    - max_stores、max_admins、max_doctors、max_appointments_per_month
    - features 字段（JSON）控制高级功能可用性

**Celery 任务权限事实：**

24. 异步任务中显式调用 set_tenant_context(tenant_id, tenant_code)，结束后 clear_tenant_context()（`apps/server/app/tasks/notification_task.py:133`）

25. 定时任务遍历所有活跃租户执行，无鉴权要求（`apps/server/app/celery_app.py:64-135`）

---

## Round 2：辩论层

### 交叉评论投票矩阵

#### 简化投票矩阵（领域主导模式）

| 议题 | Engineer 立场 | Critic 质询 | 最终裁决 |
|------|-------------|------------|---------|
| 5 种角色是否满足精细化需求 | +1（部分），角色体系可行但权限类型仅 2 种 | 质询 2：Permission 表仅 menu/button，是根本瓶颈 | 裁决：角色层级可保留，Permission 表需重构 |
| 30+ 模块 CRUD 权限映射 | 反驳：前后端映射未文档化，hasModuleAccess 是关键 | 质询 1：权限矩阵 500+ 码，JSON 性能未验证 | 裁决：需统一权限码规范 + 分层存储 |
| 数据敏感度与脱敏 | +1：API 响应明文返回，无全局脱敏 | 质询 6（关键）：医疗系统合规漏洞 | 裁决：P0 优先修复，API 响应脱敏 |
| 医生端/患者端无权限控制 | 交叉发现 3：Doctor 表无 role_id，完全脱离 RBAC | 质询 5：三方都低估了安全风险 | 裁决：P1 分阶段实施医生端权限 |
| 列级权限完全未实现 | 交叉发现 4：Permission 无 resource_type/scope 字段 | 质询 7：3 种列级操作技术路径未分析 | 裁决：P1 引入 FieldPermission 机制 |
| 前后端权限码不对齐 | 交叉发现 2：canXxx 聚合 vs module:action 精确匹配 | 质询 4：500 码时错误率指数级上升 | 裁决：P0 统一权限码枚举 |
| Role.permissions JSON vs role_permissions 表 | 交叉发现 5：关联表已定义但未使用，架构债务 | 无直接质询 | 裁决：P2 技术债务偿还 |
| Tab 级权限无独立组件 | +1：AuthContainer 已存在可复用，成本 8-12h | 无直接质询 | 裁决：P0 低成本高价值 |

### 独到发现

1. **Permission.type 字段完全未使用**：表定义了 type(menu/button) 但代码中无任何 `Permission.type` 引用，权限检查仅依赖 code 字符串匹配。扩展 type 枚举是所有细分权限的前置条件。（成本：48-64h）

2. **role_permissions 关联表已定义但从未使用**：`admin.py:10-15` 定义了关联表，但实际权限存储在 `Role.permissions` JSON 字段。这是未完成的重构遗留问题。（成本：24-32h）

3. **AuthButton/AuthContainer 组件框架完善但覆盖面低**：组件设计支持 hidden/disabled/tooltip 三种 fallback，但 111 个页面组件中仅少数使用。根因是缺少权限脚手架生成工具。（成本：24-32h）

4. **数据权限仅有 tenant_id + store_id 双层**：无科室级别、患者组级别、数据所有者级别的隔离。`check_store_access` 是唯一的数据权限函数。（成本：64-96h）

### Critic 质询

1. [Critic → 全体] **权限矩阵规模失控风险**（关键）
   - 论据：30 模块 × 4 操作 × 3 层级 ≈ 360 权限点，加 Tab/字段级可突破 500
   - 要求回应：PM（业务维度）、Engineer（JSON 方案性能）
   - 级别：关键

2. [Critic → 全体] **Permission 表架构瓶颈**（关键）
   - 论据：仅 menu/button 两种 type，无法承载 7 种资源维度 + 3 种字段操作
   - 要求回应：Engineer（表结构重构）、PM（资源维度优先级）
   - 级别：关键

3. [Critic → PM] **数据权限维度缺失**
   - 论据：仅有 tenant_id + store_id 双层，无科室/患者组/病历状态等细粒度数据权限
   - 要求回应：PM（数据权限需求）、Engineer（技术方案）
   - 级别：普通

4. [Critic → Designer + Engineer] **前后端权限码不对齐的企业级风险**
   - 论据：canXxx 布尔值 vs module:action 字符串，500 码时维护 3 处同步
   - 要求回应：Designer（前端规范）、Engineer（后端规范）
   - 级别：普通

5. [Critic → 全体] **医生端/患者端权限真空被低估**
   - 论据：医生端仅检查 currentDoctor 存在，患者端无权限守卫
   - 要求回应：PM（需求清单）、Engineer（实现成本）
   - 级别：普通

6. [Critic → 全体] **字段脱敏合规风险**（关键）
   - 论据：日志/前端有脱敏但 API 响应无脱敏，医疗系统合规漏洞
   - 要求回应：Engineer（脱敏中间件方案）、PM（脱敏字段优先级）
   - 级别：关键

7. [Critic → Engineer] **列级权限实现路径缺失**
   - 论据：不可见/脱敏/只读 3 种操作的技术实现完全不同，三方未分析
   - 要求回应：Engineer（列级权限架构）、Designer（前端组件）
   - 级别：普通

### 🚨 Critic 关键质询追踪

| # | 关键质询内容 | 回应摘要 | 回应是否充分 | 处置 |
|---|------------|---------|------------|------|
| 1 | 权限矩阵 500+ 码，JSON 性能未验证 | 裁决：引入分层存储（Permission 表 + 关联表 + 缓存），JSON 仅做序列化格式 | 是 | 纳入 P1 行动 |
| 2 | Permission 表仅 2 种 type | 裁决：扩展为 7 种资源类型 + 操作/数据/列级三维度 | 是 | 纳入 P0 行动 |
| 3 | API 响应无脱敏，合规漏洞 | 裁决：P0 优先实现 Pydantic field_serializer + Response 脱敏中间件 | 是 | 纳入 P0 行动 |

---

## Round 3：共识层

### ✅ 共识项

1. **Permission 表需要扩展资源类型**
   **结论：** 从 menu/button 扩展为 menu/route/button/tab/api/field/component 七种类型
   **建议行动：** 重构 Permission 模型，添加 resource_type + action + scope 字段
   **成本估算：** 48-64h（Engineer）
   **优先级：** P0

2. **前后端权限码需要统一**
   **结论：** 统一为 `{module}:{action}:{target}` 三段式命名规范，前后端共享枚举
   **建议行动：** 创建共享权限码常量文件，替换前端 canXxx 和后端硬编码字符串
   **成本估算：** 40-56h（Engineer 32h + Designer 24h）
   **优先级：** P0

3. **API 响应脱敏必须修复**
   **结论：** 在 Pydantic Schema 层添加 field_serializer，或 Response Middleware 统一处理
   **建议行动：** 实现基于权限的响应脱敏（高敏感字段按角色/权限决定是否脱敏）
   **成本估算：** 16-24h（Engineer）
   **优先级：** P0

4. **Tab 级权限控制需独立组件**
   **结论：** 基于 AuthContainer 创建 AuthTabPane 组件
   **建议行动：** 封装 AuthTabPane 组件，在 Permission 表添加 tab 类型权限码
   **成本估算：** 8-12h（Designer）
   **优先级：** P0

5. **列级权限机制需要引入**
   **结论：** 引入 FieldPermission 模型，支持 invisible/masked/readonly 三种列级操作
   **建议行动：** 分三阶段实施：只读 → 脱敏 → 不可见
   **成本估算：** 64-96h（Engineer 48-72h + Designer 16-24h）
   **优先级：** P1

6. **医生端需要接入 RBAC 体系**
   **结论：** 为 Doctor 模型添加 role_id 关联，复用 Role-Permission 机制
   **建议行动：** 创建医生专用角色（如 CHIEF_DOCTOR、DOCTOR、INTERN），权限覆盖排班/预约/病历等
   **成本估算：** 80-120h（Engineer 56-80h + PM 8h + Designer 16h）
   **优先级：** P1

7. **数据权限需要扩展科室维度**
   **结论：** 在现有 tenant_id + store_id 基础上，添加 department_id 数据隔离维度
   **建议行动：** 引入 DataScope 概念（all_tenant/all_store/own_department/own_only）
   **成本估算：** 64-96h（Engineer）
   **优先级：** P2

### ⚡ 分歧项

1. **Role.permissions JSON 存储是否需要迁移到关联表**
   **各方立场：**
   - Engineer：role_permissions 关联表已定义但未使用，应迁移以支持复杂查询
   - PM：当前 JSON 方案在 <200 权限码时可接受，迁移风险较高
   - Critic：500+ 权限码场景下 JSON 查询性能未验证
   **裁决：** 分阶段 — P0 先在 Permission 表补充结构化字段，P2 再将 JSON 迁移到关联表
   **决策依据：** 降低一次性变更风险，先验证权限码规模增长速度

2. **患者端是否需要权限控制**
   **各方立场：**
   - PM：患者端主要是只读操作，权限需求较低
   - Designer：患者端通过门店上下文验证访问即可
   - Critic：家庭就诊人管理涉及跨患者数据访问，需要控制
   **裁决：** 仅在"家庭成员就诊记录访问"和"敏感操作（如取消预约）"两个场景引入轻量权限检查
   **决策依据：** 患者端面向 C 端用户，过度权限控制影响体验

---

## 被低估的优势

1. **AuthButton/AuthContainer 组件框架已相当完善**：支持 3 种 fallback 模式、usePermission Hook、多权限检查。扩展到 Tab/字段级只需少量封装，无需从零设计。

2. **require_permission 依赖注入机制可扩展**：当前仅支持字符串匹配，但架构上支持扩展为类型判断 + scope 过滤，无需重写整个鉴权链路。

3. **多租户隔离机制已覆盖完整**：tenant_id 贯穿数据库/API/缓存/上下文四层，是数据权限扩展的坚实基础。

---

## 行动计划（按 ROI 排序）

| 优先级 | 行动 | 成本 | 价值 | 负责 | 状态 |
|--------|------|------|------|------|------|
| P0 | Permission 表扩展 7 种资源类型 | 48-64h | 极高 | Engineer | 待实施 |
| P0 | 前后端统一权限码枚举 | 40-56h | 高 | Engineer + Designer | 待实施 |
| P0 | API 响应脱敏（Pydantic field_serializer） | 16-24h | 极高（合规） | Engineer | 待实施 |
| P0 | AuthTabPane 组件封装 | 8-12h | 高 | Designer | 待实施 |
| P1 | 列级权限机制（只读 → 脱敏 → 不可见） | 64-96h | 高 | Engineer + Designer | 待实施 |
| P1 | 医生端接入 RBAC | 80-120h | 高 | Engineer + PM + Designer | 待实施 |
| P1 | 权限管理 UI（角色权限树配置） | 32-48h | 高 | Designer + Engineer | 待实施 |
| P2 | 数据权限扩展科室维度（DataScope） | 64-96h | 中 | Engineer | 待实施 |
| P2 | Role.permissions JSON → 关联表迁移 | 24-32h | 中 | Engineer | 待实施 |
| P2 | 权限脚手架生成工具 | 24-32h | 中 | Engineer | 待实施 |
| 待定 | 患者端轻量权限控制 | 16-24h | 待定 | Engineer + PM | 需用户确认 |

### P0：立即执行（高价值、低成本）

1. **Permission 表扩展 7 种资源类型**（48-64h）
   - 扩展 Permission.type 枚举：menu/route/button/tab/api/field/component
   - 添加 action 字段（read/create/update/delete/export/approve 等）
   - 添加 scope 字段（all/own/department/store/tenant）
   - 数据迁移脚本为现有权限码补充 type/action/scope
   - 负责：Engineer

2. **前后端统一权限码枚举**（40-56h）
   - 定义三段式命名规范：`{module}:{action}:{target}`
   - 后端创建 `app/core/permissions.py` 权限码常量类
   - 前端创建 `src/constants/permissions.ts` 共享枚举
   - 替换前端 access.ts 中的 canXxx 为统一权限码
   - 负责：Engineer + Designer

3. **API 响应脱敏**（16-24h）
   - Pydantic Schema 层添加 `@field_serializer` 装饰器
   - 高敏感字段（phone/id_card）按权限决定脱敏方式
   - 创建 Response 脱敏中间件兜底
   - 负责：Engineer

4. **AuthTabPane 组件封装**（8-12h）
   - 基于 AuthContainer 封装 Tab 权限组件
   - 在 Permission 表为现有 Tab 补充权限码
   - 负责：Designer

### P1：本轮迭代（高价值、中等成本）

1. **列级权限机制**（64-96h）— 分三阶段：
   - 阶段 1（只读）：前端表单禁用 + API 写操作拦截（24h）
   - 阶段 2（脱敏）：Pydantic field_serializer + 前端二次校验（20-32h）
   - 阶段 3（不可见）：SQL 排除字段 + 前端不渲染（20-40h）
   - 负责：Engineer + Designer

2. **医生端接入 RBAC**（80-120h）
   - Doctor 模型添加 role_id 字段
   - 创建医生角色：CHIEF_DOCTOR、DOCTOR、INTERN
   - 医生端前端接入 access.ts 权限机制
   - 负责：Engineer + PM + Designer

3. **权限管理 UI**（32-48h）
   - 角色权限树配置页面
   - 权限按 7 种资源类型分类展示
   - 支持批量勾选/继承
   - 负责：Designer + Engineer

### P2：下个周期规划（中等价值、较高成本）

1. **数据权限扩展科室维度**（64-96h）— 引入 DataScope 概念
2. **Role.permissions JSON → 关联表迁移**（24-32h）— 技术债务偿还
3. **权限脚手架生成工具**（24-32h）— 自动生成带权限的 CRUD 页面

### 待定：需用户确认

1. **患者端轻量权限控制**（16-24h）— 是否需要在家庭成员就诊记录访问场景引入权限检查

---

## 企业级权限拆分方案

### 一、权限分类体系

```
权限体系（Permission System）
├── A. 资源权限（Resource Permission）
│   ├── A1. 菜单权限（Menu） — 控制侧边栏菜单可见性
│   ├── A2. 路由权限（Route） — 控制页面直接 URL 访问
│   ├── A3. 按钮权限（Button） — 控制操作按钮可见性/可用性
│   ├── A4. Tab 权限（Tab） — 控制页面内 Tab 面板可见性
│   ├── A5. 接口权限（API） — 控制 API 端点访问
│   ├── A6. 组件权限（Component） — 控制页面组件可见性
│   └── A7. 页面元素权限（Element） — 控制页面级元素可见性
│
├── B. 操作权限（Operation Permission）
│   ├── B1. 创建（Create）
│   ├── B2. 查看/列表（Read/List/Detail）
│   ├── B3. 更新（Update）
│   ├── B4. 删除（Delete）
│   └── B5. 特殊操作（Export/Import/Approve/Refund/Audit 等）
│
├── C. 数据权限（Data Permission）
│   ├── C1. 行级权限（Row Level）
│   │   ├── 全租户（All Tenant） — 平台管理员
│   │   ├── 全门店（All Store） — 租户管理员
│   │   ├── 本科室（Own Department） — 科室管理员
│   │   └── 仅本人（Own Only） — 普通医生
│   │
│   └── C2. 列级权限（Column Level）
│       ├── 不可见（Invisible） — 字段不返回/不渲染
│       ├── 脱敏（Masked） — 字段部分遮蔽显示
│       │   ├── 手机号：138****1234
│       │   ├── 身份证：310***********1234
│       │   ├── 姓名：张*
│       │   └── 工资/收入：***
│       └── 只读（Readonly） — 可看不可改
│
└── D. 业务维度权限（Business Context）
    ├── D1. 租户隔离 — tenant_id（已实现）
    ├── D2. 门店隔离 — store_id（已实现）
    ├── D3. 科室隔离 — department_id（待实现）
    └── D4. 订阅计划限制 — SubscriptionPlan.features（已实现）
```

### 二、权限码命名规范

**三段式：`{module}:{action}:{target}`**

```
模块（module）：业务模块名，如 doctor/schedule/appointment/patient/medical_record
操作（action）：CRUD + 特殊操作，如 list/detail/create/update/delete/export/approve
目标（target，可选）：具体资源，如 tab/basic_info/field/phone
```

**示例：**
```
doctor:list                          # 医生列表
doctor:create                        # 新增医生
doctor:update                        # 编辑医生
doctor:delete                        # 删除医生
doctor:tab:schedule                  # 医生详情-排班 Tab
doctor:tab:booking_setting           # 医生详情-预约设置 Tab
doctor:field:salary:read             # 工资字段-可见
doctor:field:salary:invisible        # 工资字段-不可见
doctor:export                        # 导出医生数据
schedule:create                      # 创建排班
schedule:template:manage             # 排班模板管理
appointment:refund                   # 预约退款
appointment:field:phone:mask         # 手机号脱敏
patient:field:id_card:read           # 身份证可见
medical_record:create                # 填写病历
medical_record:field:diagnosis:edit  # 诊断字段可编辑
```

### 三、当前系统权限矩阵（30+ 模块）

#### 平台管理模块

| 权限码 | 资源类型 | 操作 | 适用角色 | 说明 |
|--------|---------|------|---------|------|
| `platform:menu` | menu | read | PLATFORM_ADMIN | 平台管理菜单可见 |
| `tenant:list` | route | read | PLATFORM_ADMIN | 租户列表 |
| `tenant:create` | button+api | create | PLATFORM_ADMIN | 新增租户 |
| `tenant:update` | button+api | update | PLATFORM_ADMIN | 编辑租户 |
| `tenant:delete` | button+api | delete | SUPER_ADMIN | 删除租户 |
| `tenant:tab:subscription` | tab | read | PLATFORM_ADMIN | 租户订阅信息 Tab |
| `tenant:field:payment_info:read` | field | read | SUPER_ADMIN | 支付信息可见 |
| `tenant:export` | button+api | export | PLATFORM_ADMIN | 导出租户数据 |
| `subscription_plan:list` | route | read | SUPER_ADMIN | 订阅计划列表 |
| `subscription_plan:create` | button+api | create | SUPER_ADMIN | 创建订阅计划 |
| `subscription_plan:update` | button+api | update | SUPER_ADMIN | 编辑订阅计划 |
| `miniapp_platform:menu` | menu | read | SUPER_ADMIN | 小程序平台菜单 |
| `miniapp_company:list` | route | read | SUPER_ADMIN | 公司管理 |
| `miniapp_company:create` | button+api | create | SUPER_ADMIN | 新增公司 |
| `miniapp_payment:list` | route | read | SUPER_ADMIN | 支付配置 |
| `miniapp_instance:list` | route | read | SUPER_ADMIN | 小程序实例 |

#### 组织与权限模块

| 权限码 | 资源类型 | 操作 | 适用角色 | 说明 |
|--------|---------|------|---------|------|
| `organization:menu` | menu | read | TENANT_ADMIN+ | 组织与权限菜单 |
| `store:list` | route | read | STORE_ADMIN+ | 门店列表 |
| `store:create` | button+api | create | TENANT_ADMIN+ | 新增门店 |
| `store:update` | button+api | update | TENANT_ADMIN+ | 编辑门店 |
| `store:delete` | button+api | delete | SUPER_ADMIN | 删除门店 |
| `store:disable` | button+api | update | SUPER_ADMIN | 禁用门店 |
| `store:field:contact_phone:read` | field | read | TENANT_ADMIN+ | 联系电话可见 |
| `department:list` | route | read | STORE_ADMIN+ | 科室列表 |
| `department:create` | button+api | create | TENANT_ADMIN+ | 新增科室 |
| `department:update` | button+api | update | TENANT_ADMIN+ | 编辑科室 |
| `department:delete` | button+api | delete | TENANT_ADMIN+ | 删除科室 |
| `role:list` | route | read | TENANT_ADMIN+ | 角色列表 |
| `role:create` | button+api | create | TENANT_ADMIN+ | 创建角色 |
| `role:update` | button+api | update | TENANT_ADMIN+ | 编辑角色权限 |
| `role:delete` | button+api | delete | TENANT_ADMIN+ | 删除角色 |
| `admin_user:list` | route | read | TENANT_ADMIN+ | 后台用户列表 |
| `admin_user:create` | button+api | create | TENANT_ADMIN+ | 新增后台用户 |
| `admin_user:update` | button+api | update | TENANT_ADMIN+ | 编辑后台用户 |
| `admin_user:reset_password` | button+api | update | TENANT_ADMIN+ | 重置密码 |
| `audit_log:list` | route | read | TENANT_ADMIN+ | 操作日志 |
| `audit_log:export` | button+api | export | TENANT_ADMIN+ | 导出日志 |
| `checkin_audit:list` | route | read | TENANT_ADMIN+ | 签到审计 |
| `online_user:list` | route | read | TENANT_ADMIN+ | 在线用户 |
| `online_user:force_logout` | button+api | update | TENANT_ADMIN+ | 强制下线 |
| `analytics:view` | route | read | TENANT_ADMIN+ | 行为分析 |

#### 医疗业务模块

| 权限码 | 资源类型 | 操作 | 适用角色 | 说明 |
|--------|---------|------|---------|------|
| `medical_services:menu` | menu | read | STORE_ADMIN+ | 医疗业务菜单 |
| `doctor:list` | route | read | STORE_ADMIN+ | 医生列表 |
| `doctor:create` | button+api | create | TENANT_ADMIN+ | 新增医生 |
| `doctor:update` | button+api | update | TENANT_ADMIN+ | 编辑医生 |
| `doctor:delete` | button+api | delete | TENANT_ADMIN+ | 删除医生 |
| `doctor:detail` | route | read | STORE_ADMIN+ | 医生详情 |
| `doctor:tab:schedule` | tab | read | STORE_ADMIN+ | 排班 Tab |
| `doctor:tab:booking_setting` | tab | read | TENANT_ADMIN+ | 预约设置 Tab |
| `doctor:tab:consultation_fee` | tab | read | TENANT_ADMIN+ | 诊费 Tab |
| `doctor:field:salary:invisible` | field | — | 仅 TENANT_ADMIN+ | 工资字段不可见 |
| `doctor:field:license_number:read` | field | read | STORE_ADMIN+ | 执业证号可见 |
| `doctor:export` | button+api | export | TENANT_ADMIN+ | 导出医生 |
| `schedule:list` | route | read | STORE_ADMIN+ | 排班管理 |
| `schedule:create` | button+api | create | TENANT_ADMIN+ | 创建排班 |
| `schedule:update` | button+api | update | TENANT_ADMIN+ | 编辑排班 |
| `schedule:delete` | button+api | delete | TENANT_ADMIN+ | 删除排班 |
| `schedule:tab:calendar` | tab | read | STORE_ADMIN+ | 日历视图 |
| `schedule:tab:list` | tab | read | STORE_ADMIN+ | 列表视图 |
| `schedule:tab:template` | tab | read | TENANT_ADMIN+ | 排班模板 |
| `schedule:tab:suspension` | tab | read | TENANT_ADMIN+ | 停诊管理 |
| `appointment:list` | route | read | STORE_ADMIN+ | 预约列表 |
| `appointment:detail` | route | read | STORE_ADMIN+ | 预约详情 |
| `appointment:create` | button+api | create | STORE_ADMIN+ | 代客预约 |
| `appointment:cancel` | button+api | update | STORE_ADMIN+ | 取消预约 |
| `appointment:refund` | button+api | update | TENANT_ADMIN+ | 退款 |
| `appointment:checkin` | button+api | update | STORE_ADMIN+ | 签到 |
| `appointment:noshow` | button+api | update | STORE_ADMIN+ | 标记爽约 |
| `appointment:field:phone:mask` | field | — | STORE_USER | 手机号脱敏 |
| `appointment:field:id_card:invisible` | field | — | STORE_USER | 身份证不可见 |
| `appointment:field:symptom:read` | field | read | STORE_ADMIN+ | 病情描述可见 |
| `appointment:export` | button+api | export | TENANT_ADMIN+ | 导出预约 |
| `patient:list` | route | read | STORE_ADMIN+ | 患者列表 |
| `patient:detail` | route | read | STORE_ADMIN+ | 患者详情 |
| `patient:create` | button+api | create | STORE_ADMIN+ | 新增患者 |
| `patient:update` | button+api | update | STORE_ADMIN+ | 编辑患者 |
| `patient:field:phone:mask` | field | — | STORE_USER | 手机号脱敏 |
| `patient:field:id_card:invisible` | field | — | STORE_USER | 身份证不可见 |
| `patient:field:address:readonly` | field | — | STORE_USER | 地址只读 |
| `patient:blacklist` | button+api | update | TENANT_ADMIN+ | 黑名单管理 |
| `patient:export` | button+api | export | TENANT_ADMIN+ | 导出患者 |
| `medical_record:list` | route | read | STORE_ADMIN+ | 病历列表 |
| `medical_record:detail` | route | read | STORE_ADMIN+ | 病历详情 |
| `medical_record:create` | button+api | create | STORE_ADMIN+ | 填写病历 |
| `medical_record:update` | button+api | update | STORE_ADMIN+ | 编辑病历 |
| `medical_record:field:diagnosis:edit` | field | — | 仅主治+ | 诊断字段可编辑 |
| `medical_record:field:prescription:edit` | field | — | 仅主治+ | 处方字段可编辑 |
| `medical_record:field:allergy_history:readonly` | field | — | STORE_USER | 过敏史只读 |
| `medical_record:export` | button+api | export | TENANT_ADMIN+ | 导出病历 |
| `leave_request:list` | route | read | TENANT_ADMIN+ | 停诊审核列表 |
| `leave_request:approve` | button+api | approve | TENANT_ADMIN+ | 审批停诊 |
| `leave_request:reject` | button+api | approve | TENANT_ADMIN+ | 驳回停诊 |

#### 经营配置模块

| 权限码 | 资源类型 | 操作 | 适用角色 | 说明 |
|--------|---------|------|---------|------|
| `operations:menu` | menu | read | TENANT_ADMIN+ | 经营配置菜单 |
| `booking_rules:update` | button+api | update | TENANT_ADMIN+ | 预约规则配置 |
| `blacklist_settings:update` | button+api | update | TENANT_ADMIN+ | 爽约黑名单配置 |
| `wechat_settings:update` | button+api | update | TENANT_ADMIN+ | 微信配置 |
| `basic_settings:update` | button+api | update | TENANT_ADMIN+ | 基础设置 |
| `shift_type:list` | route | read | TENANT_ADMIN+ | 班次类型列表 |
| `shift_type:create` | button+api | create | TENANT_ADMIN+ | 新增班次类型 |
| `rule_set:list` | route | read | SUPER_ADMIN | 规则组列表 |
| `rule_set:create` | button+api | create | SUPER_ADMIN | 新增规则组 |
| `consultation_fee:list` | route | read | TENANT_ADMIN+ | 诊费类型列表 |
| `consultation_fee:create` | button+api | create | TENANT_ADMIN+ | 新增诊费类型 |
| `consultation_fee_template:list` | route | read | TENANT_ADMIN+ | 诊费模板列表 |
| `consultation_fee_template:create` | button+api | create | TENANT_ADMIN+ | 新增诊费模板 |
| `booking_notice:update` | button+api | update | TENANT_ADMIN+ | 预约须知 |
| `email_template:list` | route | read | TENANT_ADMIN+ | 邮件模板 |
| `email_template:create` | button+api | create | TENANT_ADMIN+ | 新增邮件模板 |

#### 内容与触达模块

| 权限码 | 资源类型 | 操作 | 适用角色 | 说明 |
|--------|---------|------|---------|------|
| `content_center:menu` | menu | read | TENANT_ADMIN+ | 内容中心菜单 |
| `content:list` | route | read | TENANT_ADMIN+ | 内容管理 |
| `content:create` | button+api | create | TENANT_ADMIN+ | 新增内容 |
| `content:update` | button+api | update | TENANT_ADMIN+ | 编辑内容 |
| `content:delete` | button+api | delete | TENANT_ADMIN+ | 删除内容 |
| `message:list` | route | read | TENANT_ADMIN+ | 消息管理 |
| `message:send` | button+api | create | TENANT_ADMIN+ | 发送消息 |
| `feedback:list` | route | read | TENANT_ADMIN+ | 用户反馈 |
| `feedback:reply` | button+api | update | TENANT_ADMIN+ | 回复反馈 |

#### 医生端模块（新增，待实施）

| 权限码 | 资源类型 | 操作 | 适用角色 | 说明 |
|--------|---------|------|---------|------|
| `doctor_portal:dashboard` | route | read | DOCTOR+ | 工作台 |
| `doctor_portal:schedule:view` | route | read | DOCTOR+ | 排班查看 |
| `doctor_portal:appointment:today` | route | read | DOCTOR+ | 今日预约 |
| `doctor_portal:appointment:history` | route | read | DOCTOR+ | 历史预约 |
| `doctor_portal:appointment:call` | button+api | update | CHIEF_DOCTOR+ | 叫号 |
| `doctor_portal:appointment:noshow` | button+api | update | DOCTOR+ | 标记爽约 |
| `doctor_portal:consultation:start` | button+api | create | DOCTOR+ | 开始就诊 |
| `doctor_portal:medical_record:create` | button+api | create | DOCTOR+ | 填写病历 |
| `doctor_portal:medical_record:update` | button+api | update | DOCTOR+ | 编辑病历 |
| `doctor_portal:medical_record:field:diagnosis:edit` | field | — | CHIEF_DOCTOR | 诊断字段可编辑 |
| `doctor_portal:medical_record:field:prescription:edit` | field | — | CHIEF_DOCTOR | 处方字段可编辑 |
| `doctor_portal:leave_request:create` | button+api | create | DOCTOR+ | 申请停诊 |
| `doctor_portal:statistics:view` | route | read | DOCTOR+ | 数据统计 |
| `doctor_portal:patient:field:phone:mask` | field | — | DOCTOR | 手机号脱敏 |
| `doctor_portal:patient:field:id_card:invisible` | field | — | DOCTOR | 身份证不可见 |

### 四、数据库模型设计方案

```python
# 1. Permission 表（重构）
class Permission(Base):
    __tablename__ = "permissions"

    id: Mapped[int]
    code: Mapped[str]           # "doctor:create"
    name: Mapped[str]           # "新增医生"
    resource_type: Mapped[str]  # menu/route/button/tab/api/field/component
    module: Mapped[str]         # "doctor"
    action: Mapped[str]         # read/create/update/delete/export/approve
    target: Mapped[str | None]  # "phone" / "schedule" / None
    scope: Mapped[str]          # all/own/department/store/tenant
    parent_id: Mapped[int | None]
    status: Mapped[int]         # 1=启用, 0=禁用
    sort_order: Mapped[int]
    description: Mapped[str | None]

# 2. 列级权限配置表（新增）
class FieldPermission(Base):
    __tablename__ = "field_permissions"

    id: Mapped[int]
    permission_id: Mapped[int]       # 关联 Permission
    table_name: Mapped[str]          # "patients"
    column_name: Mapped[str]         # "phone"
    access_mode: Mapped[str]         # invisible/masked/readonly
    mask_pattern: Mapped[str | None] # "138****1234" 的正则模式

# 3. 数据权限配置表（新增）
class DataScope(Base):
    __tablename__ = "data_scopes"

    id: Mapped[int]
    role_id: Mapped[int]             # 关联 Role
    module: Mapped[str]              # "appointment"
    scope_type: Mapped[str]          # all_tenant/all_store/own_department/own_only
    scope_config: Mapped[dict]       # JSON: 额外配置（如特定科室 ID 列表）

# 4. Role-Permission 关联表（已有但未使用，激活）
class RolePermission(Base):
    __tablename__ = "role_permissions"

    role_id: Mapped[int]
    permission_id: Mapped[int]
```

---

## 摘要

**使用模式：** 领域主导（Engineer 主导）

**关键共识：**
- 7 项达成共识

**关键分歧：**
- 2 项需要决策者介入（JSON 迁移时机、患者端权限范围）

**Top 3 P0 行动：**
1. Permission 表扩展 7 种资源类型（48-64h）— 所有细分权限的前置条件
2. API 响应脱敏（16-24h）— 医疗系统合规必要条件
3. 前后端统一权限码枚举（40-56h）— 消除维护同步成本

**Critic 关键洞察：**
- 权限矩阵在 500+ 码规模下的 JSON 存储性能问题需要提前验证
- API 响应无脱敏是合规漏洞，即使前端做了脱敏也不够
- Permission 表架构瓶颈是精细化管理的根本阻碍

---

## 附录：模式切换日志

| 时间 | 从 | 到 | 原因 |
|------|-----|-----|------|
| 无 | — | — | 未切换模式 |
