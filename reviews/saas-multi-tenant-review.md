# SaaS 多租户系统改造 — 自适应多智能体研究画布

> 协作模式：集中调度
> 日期：2026-03-25
> 审查目标：检查当前 SaaS 系统改造的完整性和逻辑自洽性

---

## 模式选择

**选定模式：** 集中调度

**选择理由：**
- 综合评审场景，需要跨模型层、API层、中间件、认证层等多个维度的全面审视
- 改造已大部分完成（约85%），需要快速识别遗漏点和逻辑漏洞
- 没有单一领域需要特别深入，集中调度可快速收敛且输出完整度最高

---

## Round 1：事实层（只写事实，不评价）

### PM — 产品视角

**租户业务模型：**
- Tenant 模型包含：tenant_code（全局唯一）、name、status（0-禁用/1-正常/2-欠费/3-试用）
- 订阅关联：subscription_plan_id、subscription_start_at、subscription_end_at、billing_cycle
- 配额覆盖字段：max_stores、max_admins、max_doctors、max_appointments_per_month、max_storage_mb
- 功能配置：features（JSON）、branding_config（JSON）
- 域名配置：custom_domain、subdomain

**订阅计划：**
- 三档预设计划：basic（299元/月）、pro（699元/月）、enterprise（1999元/月）
- 每档包含不同的门店、管理员、医生、预约配额和存储空间

**租户管理功能：**
- CRUD 操作：创建/查询/更新/删除租户
- 激活/暂停：POST /tenants/{id}/activate、/suspend
- 订阅管理：创建/查询订阅记录
- 用量统计：GET /tenants/{id}/usage、/usage/logs

**角色和权限：**
- SUPER_ADMIN：超级管理员（平台级，tenant_id=NULL）
- PLATFORM_ADMIN：平台管理员（tenant_id=NULL）
- TENANT_ADMIN：租户管理员
- STORE_ADMIN：门店管理员
- 权限存储在 role.permissions 字段（JSON格式）

**数据隔离范围：**
- 租户隔离：Store、Admin、Doctor、User、Patient、Department、Schedule、Appointment、Role
- 全局共享：SubscriptionPlan、AppTemplate、TemplateVersion
- 租户内唯一约束：phone、openid、unionid（User）；username、phone（Doctor）；card_no（Patient）；code（Store）

**迁移策略：**
- 创建默认订阅计划（basic，0元，100年有效期）
- 创建默认租户（tenant_code="default"）
- 将未关联租户的数据关联到默认租户

**缺失的功能：**
- 存储使用量统计（_get_storage_usage 返回固定值0）
- 用量警告通知发送（check_usage_limits 中标记为 TODO）
- 订阅到期提醒通知发送（check_subscription_expiry 中标记为 TODO）
- 创建门店/管理员/医生/预约时的配额检查

### Designer — 系统设计视角

**租户上下文传递：**
- 识别方式（按优先级）：X-Tenant-ID Header → X-Tenant-Code Header → 子域名 → 路径前缀
- 存储：Python ContextVar（_current_tenant_id, _current_tenant_code）
- 公开接口路径强制要求租户上下文
- 响应头添加 X-Tenant-ID 和 X-Tenant-Code 便于调试

**数据层隔离：**
- add_tenant_filter()：基础租户过滤
- add_tenant_filter_with_store_fallback()：支持门店间接关联
- TenantFilteredQuery：链式查询构建器
- get_tenant_id_for_create()：创建时推断租户ID

**模型关联设计：**
- 所有核心表添加 tenant_id 字段（String(36), FK → tenants.id, nullable=True）
- 所有模型都有 tenant relationship 反向关联
- 未定义级联删除（数据库默认 RESTRICT）

**认证授权流程：**
- get_current_user()：验证用户与租户上下文一致性
- get_current_doctor_by_token()：医生租户校验
- get_current_admin()：强制校验 admin.tenant_id == current_tenant_id（非超管）
- Token 本身不包含租户信息，通过数据库查询获取

**跨模块数据流（预约创建）：**
1. 获取当前租户ID
2. 验证 schedule.tenant_id == current_tenant_id
3. 验证 user.tenant_id == current_tenant_id
4. 验证 patient.tenant_id == current_tenant_id
5. 创建预约时 appointment.tenant_id = schedule.tenant_id

**边界场景：**
- 超级管理员：tenant_id=NULL，可跨租户操作
- NULL tenant_id 语义：平台级数据（stores/admins/roles）或历史数据（users/doctors/patients）
- 租户状态：0-禁用（拒绝访问）、1-正常、2-欠费（拒绝访问）、3-试用

**缺失的设计：**
- 无 ORM 层全局租户过滤拦截器
- 无级联删除定义
- 无租户切换审计日志
- 无租户级别软删除机制
- 无复合索引优化（tenant_id + 常用字段）

### Engineer — 技术实现视角

**租户过滤覆盖：**
- 已应用：doctors/service_query.py、stores/service_query.py、patients/service_manage.py、patients/service_users.py、appointments/service_booking.py、import_export/router_export.py
- 未显式应用：admin/service_admins.py（依赖认证层）、import_export/service_import.py

**异常处理：**
- 400：缺少租户上下文
- 403：租户已禁用/欠费/不属于当前租户/无权访问
- 404：租户不存在或未识别

**异步任务（Celery）：**
- 每天凌晨1点：租户用量统计
- 每天凌晨2点：订阅到期检查
- 每天凌晨4点：用量限制检查
- 任务通过 tenant_id 参数传入，不使用请求上下文

**缓存和性能：**
- Redis 缓存键未包含 tenant_id 维度
- 短信验证码：sms:{phone}:{type}（未隔离租户）
- 微信Token：wechat:token:{app_id}（未隔离租户）
- 用户会话：session:{admin_id}（未隔离租户）

**测试覆盖：**
- 已覆盖：同一手机号多租户注册、跨租户访问拒绝、token 租户校验、黑名单隔离、数据查询租户过滤、公开接口租户要求
- Fixture：tenant_a, tenant_b, store_a, store_b 等

**日志和可观测性：**
- 日志记录：Tenant context: id={tenant_id}, code={tenant_code}
- 响应头添加租户信息
- 日志中未包含 tenant_id 作为结构化字段

**并发和事务：**
- 预约创建使用分布式锁：appointment:create:{schedule_id}
- 锁粒度按排班ID，未按租户隔离
- 未发现租户级别的数据库连接池隔离

**配置和密钥：**
- resolve_secret_ref() 仅支持 env:VAR_NAME 格式
- 未发现租户级别的密钥隔离

**缺失的实现：**
- Redis 缓存键未包含租户维度（跨租户缓存污染风险）
- 管理员服务层未显式应用租户过滤
- 导入服务未显式处理租户隔离
- 分布式锁键未包含租户维度
- 错误追踪系统未集成租户上下文

---

## Round 2：辩论层

### 交叉评论投票矩阵

#### 简化投票矩阵（集中调度模式）

| 议题 | 裁决者立场 | Critic 质询 | 最终裁决 |
|------|-----------|------------|---------|
| 管理员服务租户过滤 | 需补充 | 🚨 关键 | P0 修复 |
| 缓存键租户隔离 | 需补充 | 🚨 关键 | P0 修复 |
| 配额实时检查 | 需补充 | 🚨 关键 | P1 功能完善 |
| 分布式锁租户维度 | 可选优化 | 普通 | P2 优化 |
| NULL tenant_id 语义 | 需明确文档 | 普通 | P1 文档补充 |
| 导入服务租户隔离 | 需补充 | 普通 | P1 修复 |
| 租户删除策略 | 需定义 | 普通 | 待定（业务决策） |
| 缓存隔离测试 | 需补充 | 普通 | P1 测试补充 |

### 独到发现

1. **缓存层成为多租户隔离的盲区**：PM 和 Designer 视角都未关注缓存层，但 Engineer 发现缓存键未含 tenant_id，这是严重的安全隐患
2. **配额定义与执行脱节**：订阅计划定义了配额，定时任务统计了用量，但创建资源时没有实时检查，导致配额限制形同虚设
3. **NULL tenant_id 语义模糊**：同时表示"平台级数据"和"历史数据"，在 add_tenant_filter 中被跳过，可能导致数据泄露

### Critic 质询

1. [Critic → Engineer] 管理员服务缺失租户过滤导致跨租户访问风险
   - 论据：service_admins.py 中 get_list、get_by_id 等方法完全没有租户过滤逻辑
   - 要求回应：确认 AdminService 是否应受租户约束
   - 级别：🚨 关键

2. [Critic → Engineer] 缓存键缺失租户维度导致跨租户数据泄露风险
   - 论据：短信验证码、会话缓存、微信Token 都未包含 tenant_id
   - 要求回应：确认缓存隔离策略
   - 级别：🚨 关键

3. [Critic → Engineer] 分布式锁键缺失租户维度导致跨租户预约阻塞
   - 论据：锁键为 appointment:create:{schedule_id}，理论上存在 UUID 冲突
   - 要求回应：评估是否需要改为含 tenant_id 的格式
   - 级别：普通

4. [Critic → PM/Engineer] 配额检查缺失导致订阅限制无效
   - 论据：创建资源时没有实时检查配额，配额限制形同虚设
   - 要求回应：确认是否应添加实时配额检查
   - 级别：🚨 关键

5. [Critic → Designer] NULL tenant_id 语义不一致导致查询歧义
   - 论据：add_tenant_filter 在 tenant_id 为空时返回原查询，可能泄露数据
   - 要求回应：明确 NULL tenant_id 数据的可见性规则
   - 级别：普通

6. [Critic → Engineer] 导入服务缺失租户隔离逻辑
   - 论据：ImportService 没有租户相关逻辑
   - 要求回应：说明导入数据的 tenant_id 来源和校验机制
   - 级别：普通

7. [Critic → Designer] 租户删除时关联数据处理策略缺失
   - 论据：未定义级联删除，关联数据处理不明确
   - 要求回应：明确删除租户时关联数据的处理策略
   - 级别：普通

8. [Critic → Engineer] 缓存隔离测试缺失
   - 论据：测试覆盖缺失缓存隔离场景
   - 要求回应：确认是否补充缓存隔离测试
   - 级别：普通

### 🚨 Critic 关键质询追踪

| # | 关键质询内容 | Team Lead 回应 | 回应是否充分 | 处置 |
|---|------------|---------------|------------|------|
| 1 | 管理员服务缺失租户过滤 | 确认需要修复，AdminService 应受租户约束（非平台管理员） | 是 | P0 纳入计划 |
| 2 | 缓存键缺失租户维度 | 确认需要修复，短信验证码和会话缓存必须隔离 | 是 | P0 纳入计划 |
| 3 | 配额实时检查缺失 | 确认需要实现，创建资源时检查配额 | 是 | P1 纳入计划 |

---

## Round 3：共识层

### ✅ 共识项

1. **管理员服务需添加租户过滤**
   - **结论**：AdminService 的查询方法（非平台管理员场景）需添加 tenant_id 过滤
   - **建议行动**：在 service_admins.py 中为 get_list、get_by_id、get_by_username 等方法添加租户过滤
   - **成本估算**：2h
   - **优先级**：P0

2. **缓存键需包含租户维度**
   - **结论**：短信验证码、会话缓存必须包含 tenant_id，微信 Token 按场景处理
   - **建议行动**：
     - 短信验证码：sms:{tenant_id}:{phone}:{type}
     - 会话缓存：session:{tenant_id}:admin:{admin_id}
     - 微信 Token：保持现状（与 app_id 绑定，多租户共享场景需单独配置）
   - **成本估算**：4h
   - **优先级**：P0

3. **配额实时检查需实现**
   - **结论**：创建门店/管理员/医生/预约时需检查配额，超配额拒绝创建
   - **建议行动**：
     - 在 StoreService、AdminService、DoctorService、AppointmentService 的 create 方法中添加配额检查
     - 创建通用配额检查工具函数 check_quota(tenant_id, resource_type)
   - **成本估算**：8h
   - **优先级**：P1

4. **导入服务需添加租户隔离**
   - **结论**：导入数据时 tenant_id 从当前上下文获取，不接受导入文件中的 tenant_id
   - **建议行动**：
     - 修改 service_import.py，在创建数据时调用 get_tenant_id_for_create()
     - 添加校验：导入文件中的 tenant_id（如有）必须与当前上下文一致
   - **成本估算**：4h
   - **优先级**：P1

5. **分布式锁键需包含租户维度**
   - **结论**：为避免理论上的 UUID 冲突，锁键应包含 tenant_id
   - **建议行动**：将 appointment:create:{schedule_id} 改为 appointment:create:{tenant_id}:{schedule_id}
   - **成本估算**：1h
   - **优先级**：P2

6. **NULL tenant_id 语义需明确**
   - **结论**：需文档化 NULL tenant_id 的处理规则
   - **建议行动**：
     - 历史数据迁移后，所有业务数据的 tenant_id 应为非空
     - 平台级数据（如平台角色）tenant_id 保持 NULL
     - add_tenant_filter 对 NULL tenant_id 的处理：平台管理员可见全部，租户管理员仅可见本租户
   - **成本估算**：2h（文档）
   - **优先级**：P1

7. **缓存隔离测试需补充**
   - **结论**：需添加缓存隔离的单元测试和集成测试
   - **建议行动**：
     - 测试同一手机号在两租户同时发验证码
     - 测试会话缓存的租户隔离
   - **成本估算**：4h
   - **优先级**：P1

### ⚡ 分歧项/待决策项 → 已推荐方案

1. **租户删除策略** → **推荐：软删除 + 90天保留期**
   - **推荐方案**：添加 `deleted_at` 字段，保留所有关联数据，90天后物理删除
   - **理由**：医疗行业数据合规要求，支持误删恢复，与现有 `status=0` 兼容
   - **成本**：4h
   - **优先级**：P1

2. **存储配额统计实现** → **推荐：Phase 1 本地存储（可延后）**
   - **推荐方案**：遍历 `uploads/{tenant_id}` 目录计算大小，暂不实现 OSS/MinIO
   - **理由**：当前上传场景少，存储非核心限制，按需投入
   - **成本**：4h
   - **优先级**：P2（可延后至用户反馈）

3. **用量警告和订阅到期通知** → **推荐：站内信优先，短信按需**
   - **推荐方案**：创建 `TenantNotification` 表，站内信 + 日志，短信可选
   - **理由**：站内信成本低无费用，短信需服务商对接，管理后台可展示历史
   - **成本**：8h
   - **优先级**：P1

---

## 被低估的优势

1. **租户上下文中间件设计完善**：支持多种识别方式（Header/子域名/路径），使用 ContextVar 实现异步安全，设计成熟度高
2. **测试覆盖基础扎实**：已覆盖核心隔离场景（跨租户访问拒绝、token 校验等），为后续测试补充提供了良好基础
3. **迁移策略合理**：通过默认租户和 NULL 语义兼容历史数据，降低了迁移风险

---

## 行动计划（按 ROI 排序）

| 优先级 | 行动 | 成本 | 价值 | 负责 | 状态 |
|--------|------|------|------|------|------|
| P0 | 管理员服务添加租户过滤 | 2h | 高 | Engineer | 待执行 |
| P0 | 缓存键添加租户维度 | 4h | 高 | Engineer | 待执行 |
| P1 | 配额实时检查实现 | 8h | 高 | Engineer | 待执行 |
| P1 | 导入服务租户隔离 | 4h | 高 | Engineer | 待执行 |
| P1 | 租户删除策略（软删除） | 4h | 高 | Engineer | 待执行 |
| P1 | 用量/到期通知（站内信） | 8h | 高 | Engineer | 待执行 |
| P1 | NULL tenant_id 语义文档化 | 2h | 中 | Designer | 待执行 |
| P1 | 缓存隔离测试补充 | 4h | 中 | Engineer | 待执行 |
| P2 | 分布式锁键添加租户维度 | 1h | 中 | Engineer | 待执行 |
| P2 | 存储配额统计（本地） | 4h | 中 | Engineer | 可延后 |

**总成本估算：** P0 (6h) + P1 (30h) + P2 (5h) = **41h**

### P0：立即执行（高价值、低成本）

1. **管理员服务添加租户过滤**（2h）
   - 文件：`apps/server/app/modules/admin/service_admins.py`
   - 修改：为 get_list、get_by_id、get_by_username、get_by_phone 添加 tenant_id 过滤
   - 条件：非平台管理员场景

2. **缓存键添加租户维度**（4h）
   - 文件：`apps/server/app/infrastructure/sms/service.py`、`apps/server/app/core/redis.py`
   - 修改：
     - 短信验证码：`sms:{tenant_id}:{phone}:{type}`
     - 会话缓存：`session:{tenant_id}:admin:{admin_id}`

### P1：本轮迭代（高价值、中等成本）

1. **配额实时检查实现**（8h）
   - 创建：`apps/server/app/common/quota.py`
   - 修改：StoreService、AdminService、DoctorService、AppointmentService 的 create 方法
   - 功能：创建资源前检查配额，超配额抛出 403 错误

2. **导入服务租户隔离**（4h）
   - 文件：`apps/server/app/modules/import_export/service_import.py`
   - 修改：创建数据时调用 get_tenant_id_for_create()，校验导入文件中的 tenant_id

3. **租户删除策略（软删除）**（4h）
   - 修改：`apps/server/app/models/tenant.py` 添加 deleted_at、deleted_by 字段
   - 创建：软删除接口、恢复接口
   - 保留期：90天

4. **用量/到期通知（站内信）**（8h）
   - 创建：`apps/server/app/infrastructure/notifications/service.py`
   - 创建：`apps/server/app/models/tenant.py` 添加 TenantNotification 表
   - 集成：定时任务调用通知服务
   - 模板：订阅到期提醒、用量警告、欠费通知

5. **NULL tenant_id 语义文档化**（2h）
   - 创建：`docs/multi-tenant.md`
   - 内容：NULL tenant_id 的处理规则、历史数据迁移说明

6. **缓存隔离测试补充**（4h）
   - 文件：`apps/server/tests/tenants/test_cache_isolation.py`
   - 场景：验证码隔离、会话隔离

### P2：下个周期规划（中等价值、较高成本）

1. **分布式锁键添加租户维度**（1h）
   - 文件：`apps/server/app/modules/appointments/service_booking.py`
   - 修改：锁键改为 `appointment:create:{tenant_id}:{schedule_id}`

2. **存储配额统计（本地）**（4h）
   - 实现遍历 `uploads/{tenant_id}` 目录计算大小
   - 可延后至用户反馈后实现

---

## 摘要

**使用模式：** 集中调度

**关键共识：**
- 10 项达成共识（P0: 2项，P1: 6项，P2: 2项）
- 3 项待决策项已给出推荐方案

**推荐方案汇总：**
| 决策项 | 推荐方案 | 优先级 | 成本 |
|--------|---------|--------|------|
| 租户删除策略 | 软删除 + 90天保留期 | P1 | 4h |
| 存储配额统计 | 本地存储（可延后） | P2 | 4h |
| 用量/到期通知 | 站内信优先 | P1 | 8h |

**Top 3 P0 行动：**
1. 管理员服务添加租户过滤（2h）— 修复跨租户访问漏洞
2. 缓存键添加租户维度（4h）— 修复缓存数据泄露风险

**总成本估算：** P0 (6h) + P1 (30h) + P2 (5h) = **41h**

**Critic 关键洞察：**
- 缓存层是多租户隔离的最大盲区，短信验证码和会话缓存未隔离会导致严重的安全问题
- 配额定义与执行脱节，没有实时检查使订阅限制形同虚设
- NULL tenant_id 的双重语义（平台数据 vs 历史数据）在代码层面处理不一致

---

## 附录：模式切换日志

| 时间 | 从 | 到 | 原因 |
|------|-----|-----|------|
| - | - | - | 未切换 |
