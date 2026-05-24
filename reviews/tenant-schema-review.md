# appointment-booking-system — 自适应多智能体研究画布

> 协作模式：领域主导（Engineer Lead）
> 日期：2026-05-24
> 审查目标：租户 Schema/字段分层补全 — 涉及 server schemas、router、service、admin 前端表单

---

## 模式选择

**选定模式：** 领域主导（Engineer Lead）

**选择理由：** 核心任务是 Schema 设计与字段级权限控制，属于技术实现任务。Engineer 主导确保 schema 分层设计与现有代码模式一致，PM 和 Designer 辅助提供业务语义和表单交互上下文。

---

## Round 1：事实层（只写事实，不评价）

### PM — 产品视角

**产品定位：**
- 全栈医院预约挂号系统，SaaS 多租户架构，支持多门店/分院、多科室、多医生排班预约
- 三端：机构端(Admin)、患者端(H5+小程序)、医生端(Doctor)
- 后端 49+ 业务模块

**租户字段按业务语义分类：**

| 类别 | 字段 | 行号 |
|------|------|------|
| 用户注册填写 | tenant_code, name, contact_name, contact_phone, contact_email, address, custom_domain, subdomain | :54,:55,:92-:95,:98-:99 |
| 系统管理 | id, status, deleted_at, deleted_by, tags, log_retention_days, rate_limit_per_minute, rate_limit_per_second | :53,:56,:59-:60,:84-:85,:88-:89 |
| 订阅相关 | subscription_plan_id, subscription_start_at, subscription_end_at, billing_cycle | :63-:66 |
| 配置覆盖 | max_stores, max_admins, max_doctors, max_appointments_per_month, features, branding_config, password_policy | :69-:72,:75,:78,:81 |

**功能完成度：**
- 自助注册流程存在：`POST /tenants/register` (router.py:86-100)，使用 `TenantSelfRegisterRequest` schema
- 平台管理员创建流程存在：`POST /tenants` (router.py:606-684)，使用 `TenantCreate` schema
- Admin 前端路由存在：`/platform/tenant/list|create|:id|:id/edit` + 订阅计划管理
- 前端页面文件存在：index.tsx(列表), form.tsx(表单), detail.tsx(详情), plans.tsx, plan-form.tsx

### Designer — 用户视角

**页面清单：**
- Admin 端平台管理路由（platform.ts）：租户列表/新增/详情/编辑 + 订阅计划管理
- 门店管理（organization.ts）：列表/新增/编辑 + 就诊类型配置
- 科室管理（organization.ts）：列表/新增/编辑
- 医生管理（medical-services.ts）：列表/新增/详情/编辑/预约设置

**表单模式（4 个典型 CRUD 表单对比）：**

| 特征 | store/form | department/form | doctor/form | tenant/form |
|------|-----------|----------------|-------------|-------------|
| 容器 | FormPage | FormPage | FormPage | 原生 ProForm |
| 布局 | FormPage 内置 | FormPage 内置 | FormPage 内置 | Card + Row/Col 手动 |
| 验证 | formValidators + useFieldUnique | formValidators + useFormInitialValues | formValidators + useFieldUnique + useDict | 内联规则 + checkTenantCode |
| JSON 组装 | 无 | 无 | 无 | 手动组装 features/branding/passwordPolicy |

**验证模式 3 种并存：**
- 模式 A：formValidators.ts 工具函数（requiredRules, stringLengthRules, phoneRules 等）
- 模式 B：useFieldUnique hook（异步唯一性校验）
- 模式 C：内联规则 + 自定义 validator（tenant/form 独有）

**列表页联动方式：** 跳转编辑（所有 CRUD 实体统一模式），新增和编辑共用同一 form 组件，通过 useParams 区分模式。

### Engineer — 技术视角

**现有 Pydantic Schema 模式：**
- schemas/ 目录共 31 个文件
- ~60% 模块采用 Base → Create/Update → Response 三层分离
- 无通用基类/mixin，每个模块独立定义，重复代码较多
- 通用配置模式：`ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)`

**Tenant 模块 Schema 现状（已有完整三层分离）：**
- TenantBase (line 206-225): tenant_code, name, contact_name/phone/email, address, custom_domain, subdomain
- TenantCreate (line 227-263): 继承 Base + subscription_plan_id, billing_cycle, max_stores/admins/doctors/appointments, features, branding_config, password_policy, tags, log_retention_days, is_trial
- TenantUpdate (line 265-306): 独立定义，所有字段 Optional，含 rate_limit_per_minute/second，移除 subscription_plan_id/billing_cycle/is_trial
- TenantResponse (line 309-340): 完整字段 + 计算字段 is_subscription_active
- TenantListResponse (line 343-362): 简化版
- TenantSelfRegisterRequest (line 641-654): 注册专用，必填 tenant_code/name/contact_name/phone/admin_username/admin_password

**Router 字段过滤逻辑：**
- 创建端 (router.py:606-684): `require_platform_admin()` + 直接使用 TenantCreate，无字段过滤
- 更新端 (router.py:734-792): `get_current_admin` + 根据角色过滤字段
  - 平台管理员：全字段
  - 租户管理员：仅 allowed_fields = {"name", "contact_name", "contact_phone", "contact_email", "address", "branding_config"}

**Service 层字段处理：**
- create (service.py:210-264): 手动逐字段映射 TenantCreate → Tenant ORM 对象，无系统字段保护
- update (service.py:318-350): `model_dump(exclude_unset=True)` 直接 setattr，依赖 Router 层已过滤

**前端 API 层 (packages/api/src/modules/tenant.ts)：**
- TenantCreateData / TenantUpdateData 类型定义，features/branding/passwordPolicy 为 JSON 字符串
- 前端 form.tsx 手动扁平化 → 组装 JSON 字符串的提交逻辑

**权限实现：**
- require_platform_admin (tenant_deps.py): 检查 is_super_admin 字段
- Router 更新路由内部判断角色，租户管理员硬编码 allowed_fields 白名单

---

## Round 2：辩论层（Engineer Lead）

### 交叉评论

#### [Engineer -> PM] 租户字段按业务语义分类

**+1**，两处修正：
1. `custom_domain` 和 `subdomain` 业务上更接近"基础设施配置"而非"用户注册填写"。`TenantSelfRegisterRequest` 中不存在这两个字段，佐证了这一判断。
2. `password_policy` 应归入"安全策略"子类，与 `rate_limit` 一样需平台管理员授权，而非普通"配置覆盖"。

关联性：直接影响 Schema 分层设计和 Router 层字段白名单的边界划分 | 影响程度：中

#### [Engineer -> PM] 功能完成度

**+1**，补充关键遗漏：`TenantCreate` schema 有 `is_trial` 字段（schemas.py:240），`service.create` 据此设置 `status=3`（试用），但**前端表单完全没有对应的 UI 控件**，前端 `TenantCreateData` 类型定义（tenant.ts:103-123）也没有这个字段。平台管理员无法通过表单创建试用租户。

关联性：Schema 分层完整性 | 影响程度：高 | 成本：0.5h

#### [Engineer -> Designer] tenant/form 独有的 Card+Row/Col 手动布局

**+1**。更深层的问题是 **JSON 字段的手动组装/拆解**。form.tsx 的 `handleSubmit`（行 148-203）和 `loadTenant`（行 41-106）各约 50 行代码在手动做 `features`/`branding`/`passwordPolicy` 三个 JSON 字段的扁平化 <-> 序列化。这是维护成本的主要来源。

关联性：前端表单与 Schema 的对应关系 | 影响程度：高

#### [Engineer -> Designer] 验证模式 3 种并存

**+1**。补充：`checkTenantCode` 验证器存在时序隐患 — 如果用户在 `loadTenant` 完成前触发验证，会发起不必要的唯一性检查请求。

关联性：代码质量 | 影响程度：低

### 简化投票矩阵（领域主导模式）

| 议题 | 裁决者（Engineer）立场 | 优先级 | 成本 |
|------|----------------------|--------|------|
| PM: 租户字段四类分层 | +1（2 处修正） | P2 | 0h |
| PM: 功能完成度（is_trial 遗漏） | +1（补充） | P1 | 0.5h |
| Designer: Card+Row/Col 手动布局 | +1 | P2 | 4-5h |
| Designer: 验证模式 3 种并存 | +1（补充时序 bug） | P3 | 0.5h |

### 独到发现

#### E-1: Service.create 遗漏 password_policy 字段 [Critical]

`TenantService.create()`（service.py:231-252）手动逐字段映射 TenantCreate 到 ORM 对象，但**遗漏了 `password_policy` 字段**。平台管理员创建租户时设置的密码策略会被静默丢弃。

对比：`TenantService.update()` 使用 `model_dump(exclude_unset=True)` + `setattr` 通用模式，不会遗漏。

**优先级：P0 | 成本：0.5h**

#### E-2: TenantUpdate 缺少 extra="forbid"，存在权限提升风险 [Critical]

前端 `TenantUpdateData`（tenant.ts:125-147）定义了 `status` 和 `subscriptionPlanId` 两个字段，但后端 `TenantUpdate` 不包含这两个字段。然而 `TenantUpdate` 未设置 `extra="forbid"`，导致 `model_dump(exclude_unset=True)` 会包含传入的任意 key，`setattr` 到 ORM 对象时直接生效。

**攻击路径**：租户管理员通过 PUT `/{tenant_id}` 传入 `status: 1` 可重新激活被暂停的租户，绕过平台管理员审批。

**优先级：P0 | 成本：1h**（TenantUpdate 加 `extra="forbid"` + 移除前端多余类型字段）

#### E-3: 前端 passwordPolicy 字段集合与后端 PasswordPolicy Schema 不一致

后端 `PasswordPolicy`（schemas.py:13-36）定义 11 个字段。前端 form.tsx 只映射 5 个，其中 `maxLoginAttempts` 在后端不存在。后端有 7 个字段（`require_lowercase`, `special_chars`, `disallow_username`, `disallow_phone`, `max_repeated_chars`, `history_count`, `expiry_days`）在前端没有 UI 控件。

**优先级：P1 | 成本：2-3h**

#### E-4: 前后端功能开关定义分裂

后端 `TenantFeatures`（schemas.py:41-76）定义 15 个字段。前端 form.tsx 硬编码 11 个开关，其中 4 个（`evaluation`, `waiting_queue`, `online_service`, `miniapp_live`）后端不存在，8 个后端字段前端未展示。没有单一真相来源。

**优先级：P1 | 成本：4-5h**（后端新增功能开关元数据 API + 前端动态渲染）

#### E-5: Router allowed_fields 硬编码

`allowed_fields`（router.py:765）写死在 Router 层，与 Schema 定义分离。建议在 Schema 字段上声明 `json_schema_extra={"tenant_admin_editable": True}`，Router 动态生成白名单。

**优先级：P2 | 成本：2h**

#### E-6: TenantSelfRegisterRequest 缺少注册场景扩展字段

注册端点只靠 IP 级限流保护，缺少人机验证（captcha）。`TenantSelfRegisterRequest` 缺少 `source`, `referral_code`, `captcha_token` 等常见注册字段。

**优先级：P2 | 成本：3-4h**

#### E-7: service.create 手动映射 vs service.update 通用模式不一致

`service.create` 手动逐字段赋值容易遗漏（已证实），`service.update` 用通用 `model_dump + setattr`。建议统一为通用模式。

**优先级：P1 | 成本：1-2h**

### Critic 质询（外部 Critic）

1. **[Critic -> 全体] branding_config 字段归属三方说法矛盾**
   - PM 归入"配置覆盖"，Router 允许租户管理员编辑，无独立 UI 入口
   - 要求回应：PM / Engineer | 级别：关键

2. **[Critic -> 全体] Router allowed_fields 硬编码安全性风险**
   - 字段过滤在 Router 运行时而非 Schema 类型系统层，内部调用绕过保护
   - 要求回应：Engineer | 级别：关键

3. **[Critic -> 全体] 前端 features 字段与后端 TenantFeatures 不同步**
   - 前端 4 个独有字段后端不存在，后端 8 个字段前端未展示
   - 要求回应：PM / Designer / Engineer | 级别：关键

4. **[Critic -> 全体] TenantSelfRegisterRequest 密码校验与密码策略脱节**
   - 注册时 min_length=6，但注册后默认策略可能更严格
   - 要求回应：PM / Engineer | 级别：普通

5. **[Critic -> 全体] 前端 JSON 手动组装边界问题**
   - features 空对象覆盖计划默认值、passwordPolicy 始终提交导致 exclude_unset 失效、处理逻辑不一致
   - 要求回应：Designer / Engineer | 级别：普通

6. **[Critic -> 全体] 租户管理员自助修改信息的完整场景被忽略**
   - 编辑表单不区分角色，租户管理员看到全字段但提交被静默过滤
   - 要求回应：PM / Designer | 级别：普通

### Critic 关键质询追踪

| # | 关键质询内容 | 回应摘要 | 回应是否充分 | 处置 |
|---|------------|---------|------------|------|
| 1 | branding_config 归属矛盾 | 承认分类不精确，实际允许租户管理员编辑是正确的产品决策（品牌自助化） | 充分 | 纳入 P1 行动 |
| 2 | Router allowed_fields 安全风险 | 接受，改用独立 Schema（TenantSelfUpdateRequest）做类型级隔离 | 充分 | 纳入 P0 行动 |
| 3 | 前后端功能开关不同步 | 接受，P1 统一定义 | 充分 | 纳入 P1 行动 |

---

## Round 3：共识层

### Critic 关键质询回应

**Critic Q1 回应（branding_config 归属）：**
- `branding_config` 允许租户管理员编辑是正确的产品设计（品牌自助化），PM 的"配置覆盖"分类不精确
- 裁决：`branding_config` 归入"租户可编辑"类别，与 contact 信息同级
- 行动：更新 PM 字段分类表，form.tsx 需根据角色显示/隐藏字段组

**Critic Q2 回应（Router allowed_fields 安全风险）：**
- 接受 Critic 观点，运行时白名单不如类型系统隔离
- 裁决：新增 `TenantSelfUpdateRequest` schema，仅包含租户管理员可编辑字段，Router 根据角色选择使用哪个 schema
- 替代方案：在 TenantUpdate 字段上加 `Field(json_schema_extra={"admin_only": True})` 元数据标记，运行时动态过滤 — 成本更低但不如独立 schema 安全
- 最终选择：独立 schema 方案

**Critic Q3 回应（功能开关不同步）：**
- 接受。`TenantFeatures` 的 `extra="allow"` 本身就是开放式的，前端硬编码必然不同步
- 裁决：后端 `TenantFeatures` 改为 `extra="forbid"` + 明确枚举所有合法字段；前端从后端 schema 派生
- 行动：P1 范围内统一定义

**Critic Q4 回应（注册密码校验）：**
- 承认差异存在。注册时无租户策略，使用全局最低标准
- 裁决：`TenantSelfRegisterRequest.admin_password` 使用独立验证规则（与 `PasswordPolicy` 默认值对齐），注册成功后创建的 Admin 账号密码已满足默认策略
- 行动：纳入 P2

**Critic Q5 回应（JSON 组装边界）：**
- 接受。三个 JSON 字段处理逻辑不一致是 Bug
- 裁决：统一处理 — 空对象不提交（不覆盖计划默认值）；passwordPolicy 仅在用户实际修改时提交
- 行动：纳入 P1

**Critic Q6 回应（租户管理员编辑场景）：**
- 接受。当前 form.tsx 不区分角色，租户管理员看到无权字段
- 裁决：根据角色（通过 access 权限判断或 API 返回）动态显示表单字段组；或为租户管理员提供独立的"机构信息"设置页
- 行动：纳入 P1

### 共识项

1. **TenantUpdate 必须加 `extra="forbid"`** — 安全修复，阻止任意字段注入
   - 结论：立即修复
   - 成本：0.5h | 优先级：P0 | 负责：Engineer

2. **service.create 遗漏 password_policy** — 数据丢失 Bug
   - 结论：立即修复，同时统一为通用映射模式
   - 成本：1h | 优先级：P0 | 负责：Engineer

3. **新增 TenantSelfUpdateRequest schema** — 类型级字段隔离
   - 结论：独立 schema，Router 根据角色路由
   - 成本：1.5h | 优先级：P0 | 负责：Engineer

4. **前端 TenantUpdateData 清理多余字段** — 配合后端 extra="forbid"
   - 结论：移除 status, subscriptionPlanId, billingCycle
   - 成本：0.5h | 优先级：P0 | 负责：Engineer

5. **前端 passwordPolicy 字段与后端对齐** — 移除虚构字段，补充缺失字段
   - 结论：P1 修复
   - 成本：2-3h | 优先级：P1 | 负责：Engineer + Designer

6. **前后端功能开关统一定义** — 后端改 extra="forbid"，前端同步
   - 结论：P1 修复
   - 成本：4-5h | 优先级：P1 | 负责：Engineer

7. **前端 JSON 组装逻辑统一** — 空对象不提交，仅修改时提交
   - 结论：P1 修复
   - 成本：1h | 优先级：P1 | 负责：Designer

8. **租户管理员编辑场景** — 根据角色动态显示字段组
   - 结论：P1 修复
   - 成本：2-3h | 优先级：P1 | 负责：Designer + PM

### 分歧项

1. **功能开关是否需要动态渲染（API 驱动）**
   - Engineer：最小化方案，JSON schema 导出
   - Critic：独立 API 更可靠
   - 裁决：本轮不做动态渲染，先统一定义消除不同步。P2 再考虑 API 化

---

## 行动计划（按 ROI 排序）

| 优先级 | 行动 | 成本 | 价值 | 负责 | 涉及文件 |
|--------|------|------|------|------|---------|
| P0 | TenantUpdate 加 extra="forbid" | 0.5h | 安全 | Engineer | schemas.py |
| P0 | service.create 补 password_policy + 统一映射 | 1h | 数据完整性 | Engineer | service.py |
| P0 | 新增 TenantSelfUpdateRequest schema | 1.5h | 安全 | Engineer | schemas.py, router.py |
| P0 | 前端 TenantUpdateData 清理 | 0.5h | 配合后端 | Engineer | packages/api tenant.ts |
| P1 | 前端 passwordPolicy 字段对齐 | 2-3h | 一致性 | Engineer+Designer | form.tsx |
| P1 | 前后端功能开关统一定义 | 4-5h | 一致性 | Engineer | schemas.py, form.tsx, shared |
| P1 | JSON 组装逻辑统一 | 1h | 可靠性 | Designer | form.tsx |
| P1 | 租户管理员编辑场景 | 2-3h | 体验 | Designer | form.tsx 或新页面 |
| P1 | 前端 TenantCreateData 补 isTrial | 0.5h | 功能完整 | Engineer | tenant.ts, form.tsx |
| P2 | Router 字段过滤改为 Schema 元数据驱动 | 2h | 可维护性 | Engineer | schemas.py, router.py |
| P2 | TenantSelfRegisterRequest 扩展 | 3-4h | 安全 | Engineer | schemas.py, router.py, service.py |
| P2 | form.tsx 统一为 FormPage 容器 | 2h | 一致性 | Designer | form.tsx |
| 待定 | 功能开关动态渲染 | 4-5h | 可维护性 | Engineer | 多文件 |

### P0：立即执行（高价值、低成本）

1. `schemas.py`: TenantUpdate 加 `model_config = ConfigDict(extra="forbid")`
2. `service.py`: 补充 password_policy 字段映射，统一为 model_dump + 系统字段过滤
3. `schemas.py`: 新增 `TenantSelfUpdateRequest`，仅含 name/contact/branding 字段
4. `router.py`: update 路由根据角色使用不同 schema
5. `packages/api/src/modules/tenant.ts`: TenantUpdateData 移除多余字段

**P0 总成本：约 3.5h**

### P1：本轮迭代（高价值、中等成本）

6. `form.tsx`: passwordPolicy 字段与后端 PasswordPolicy 对齐
7. `schemas.py` + `form.tsx`: 功能开关统一定义（TenantFeatures 改 extra="forbid"）
8. `form.tsx`: JSON 组装逻辑统一（空对象不提交、条件化提交）
9. `form.tsx`: 根据角色动态显示/隐藏字段组
10. `tenant.ts` + `form.tsx`: 补充 isTrial 字段

**P1 总成本：约 10-13h**

### P2：下个周期规划

11. Router 字段过滤改为 Schema 元数据驱动
12. TenantSelfRegisterRequest 扩展（captcha 等）
13. form.tsx 统一为 FormPage 容器

**P2 总成本：约 7-8h**

### 待定：需用户确认

14. 功能开关动态渲染（API 驱动） — 本轮先不做

---

## 被低估的优势

1. Tenant 模块已有完整的 Schema 三层分离（Base/Create/Update/Response），只需修补而非重写
2. Router 层已有角色判断逻辑，只需拆分 schema 而非新增权限框架
3. 前端 form.tsx 虽有手动 JSON 组装，但表单结构清晰，重构风险可控

---

## 摘要

**使用模式：** 领域主导（Engineer Lead）

**关键共识：**
- 5 项达成共识（P0）
- 5 项达成共识（P1）

**关键分歧：**
- 1 项需要决策者介入（功能开关是否 API 驱动 → 裁决：本轮不做）

**Top 3 P0 行动：**
1. TenantUpdate 加 `extra="forbid"` — 阻止权限提升攻击（0.5h）
2. service.create 补 password_policy + 统一映射模式（1h）
3. 新增 TenantSelfUpdateRequest schema — 类型级字段隔离（1.5h）

**Critic 关键洞察：**
- branding_config 的"配置覆盖"分类与实际代码行为矛盾，需重新归类为"租户可编辑"
- Router 层运行时字段过滤是安全隐患，必须在 Schema 类型系统层面隔离
- 前后端功能开关定义已严重分裂（4+8），需立即统一

---

## 附录：完整修改文件清单

| 文件 | 修改类型 | 优先级 |
|------|---------|--------|
| `apps/server/app/modules/tenants/schemas.py` | 修改 + 新增 | P0+P1 |
| `apps/server/app/modules/tenants/service.py` | 修改 | P0 |
| `apps/server/app/modules/tenants/router.py` | 修改 | P0+P1 |
| `packages/api/src/modules/tenant.ts` | 修改 | P0+P1 |
| `apps/admin/src/pages/tenant/form.tsx` | 修改 | P1 |
| `packages/shared/` (可能) | 新增功能开关常量 | P1 |
