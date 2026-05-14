# SaaS 多租户架构文档

## 概述

本系统采用 SaaS 多租户架构，支持多个医院/诊所/医疗集团在同一个平台上独立运营，实现数据隔离和资源配额管理。

## 租户模型

### Tenant 模型

租户（Tenant）是系统的核心隔离单元，代表一个独立的医疗机构（医院、诊所、医疗集团）。

**核心字段：**
- `id`: 租户唯一标识（UUID）
- `tenant_code`: 租户编码（全局唯一，用于域名/路由识别）
- `name`: 租户名称
- `status`: 租户状态（0-禁用、1-正常、2-欠费、3-试用）
- `subscription_plan_id`: 关联的订阅计划
- `subscription_start_at`: 订阅开始时间
- `subscription_end_at`: 订阅结束时间
- `deleted_at`: 软删除时间（NULL 表示未删除）
- `deleted_by`: 删除操作人ID

**配额字段（覆盖订阅计划）：**
- `max_stores`: 最大门店数
- `max_admins`: 最大管理员数
- `max_doctors`: 最大医生数
- `max_appointments_per_month`: 月预约上限

**配置字段：**
- `features`: 功能开关配置（JSON 格式）
- `branding_config`: 品牌配置（JSON 格式）
- `custom_domain`: 自定义域名
- `subdomain`: 子域名前缀

## NULL tenant_id 语义

### 定义

`tenant_id` 为 `NULL` 的数据在系统中有两种可能的语义：

1. **平台级数据**：由平台管理员创建，不属于任何特定租户
   - 例如：平台角色（SUPER_ADMIN、PLATFORM_ADMIN）
   - 特征：由系统初始化脚本创建，由平台管理员管理

2. **历史数据**：在多租户改造前创建的数据
   - 例如：早期创建的用户、医生、患者记录
   - 处理方式：通过数据迁移脚本关联到默认租户

### 处理规则

#### 查询时的处理

在 `add_tenant_filter()` 函数中：

```python
def add_tenant_filter(query, model, tenant_id=None):
    if tenant_id is None:
        tenant_id = get_current_tenant_id()

    if not tenant_id:
        return query  # 超级管理员场景，不过滤

    return query.where(model.tenant_id == tenant_id)
```

**规则：**
- **平台管理员**（tenant_id = NULL）：可以查询所有数据（包括 NULL 和非 NULL）
- **租户管理员**（tenant_id != NULL）：只能查询本租户的数据（tenant_id 匹配）
- **未认证请求**：拒绝访问（要求提供租户上下文）

#### 数据可见性矩阵

| 数据类型 | tenant_id | 平台管理员 | 租户管理员 | 说明 |
|---------|-----------|-----------|-----------|------|
| 平台级数据 | NULL | ✅ 可见 | ❌ 不可见 | 超管专属 |
| 租户A数据 | tenant-a-id | ✅ 可见 | ✅ 可见（仅租户A） | 租户隔离 |
| 历史数据 | NULL | ✅ 可见 | ❌ 不可见 | 待迁移 |
| 已软删除租户数据 | tenant-b-id, deleted_at!=NULL | ✅ 可见 | ❌ 不可见 | 已删除 |

### 历史数据迁移

系统通过以下脚本处理历史数据：

1. **创建默认租户**（tenant_code = "default"）
2. **将未关联租户的数据关联到默认租户**
   - Stores → default tenant
   - Admins → default tenant
   - Doctors → default tenant
   - Users/Patients → default tenant

迁移脚本位置：
- `scripts/migrate_tenant_data.py`
- `scripts/migrate_core_tenant_data.py`

**迁移后状态：**
- 所有业务数据的 `tenant_id` 应为非空
- 平台级数据（如平台角色）的 `tenant_id` 保持 NULL
- NULL `tenant_id` 不再表示历史数据，而是明确表示平台级数据

## 租户上下文传递

### 识别方式（按优先级）

1. **X-Tenant-ID Header**：直接指定租户ID
2. **X-Tenant-Code Header**：通过租户编码识别
3. **子域名**：从 `subdomain.example.com` 中提取租户编码
4. **路径前缀**：从 `/api/tenants/{tenant_code}/...` 中提取

### 存储机制

使用 Python 的 `ContextVar` 实现异步安全的租户上下文存储：

```python
_current_tenant_id: ContextVar[Optional[str]] = ContextVar("_current_tenant_id", default=None)
_current_tenant_code: ContextVar[Optional[str]] = ContextVar("_current_tenant_code", default=None)
```

### 响应头

为便于调试，API 响应头包含租户信息：
- `X-Tenant-ID`: 当前租户ID
- `X-Tenant-Code`: 当前租户编码

## 数据隔离策略

### 数据库层面

1. **字段级隔离**：所有核心表添加 `tenant_id` 字段
   - Stores, Admins, Doctors, Users, Patients
   - Departments, Schedules, Appointments
   - Roles

2. **查询过滤**：使用 `add_tenant_filter()` 统一添加租户条件

3. **创建时推断**：使用 `get_tenant_id_for_create()` 获取租户ID

### 应用层面

1. **认证层**：验证用户与租户上下文一致性
2. **服务层**：业务逻辑中显式应用租户过滤
3. **导入导出**：强制使用当前租户上下文，拒绝外部 `tenant_id`

### 缓存层面

**关键隔离策略：**
- 短信验证码：`sms:{tenant_id}:{phone}:{type}`
- 会话缓存：`session:{tenant_id}:admin:{admin_id}`
- 微信 Token：`wechat:token:{app_id}`（按 app_id 隔离）

**风险：** 缓存键未包含租户维度会导致跨租户数据泄露。

## 软删除策略

### 租户软删除

当删除租户时，系统采用软删除策略：

**执行操作：**
1. 设置 `deleted_at` 为当前时间
2. 设置 `deleted_by` 为操作人ID
3. 设置 `status` 为 0（禁用）
4. 保留所有关联数据

**保留期：90天**

90天后可通过定时任务物理删除：
- 级联删除所有关联数据（Stores, Admins, Doctors, 等）
- 删除租户记录

**恢复机制：**
- 提供 `restore(tenant_id)` 方法恢复已软删除的租户
- 清除 `deleted_at` 和 `deleted_by`
- 设置 `status` 为 1（正常）

### 查询过滤

默认查询过滤已软删除的租户：
```python
query = query.where(Tenant.deleted_at.is_(None))
```

如需包含已删除租户，使用：
```python
tenant_service.get_list(query, include_deleted=True)
```

## 配额管理

### 配额类型

1. **资源配额**
   - 门店数量：`max_stores`
   - 管理员数量：`max_admins`
   - 医生数量：`max_doctors`

2. **用量配额**
   - 月预约数量：`max_appointments_per_month`
   - 存储空间：`max_storage_mb`

### 实时检查

在创建资源时进行配额检查：

```python
from app.common.quota import check_quota

# 创建门店前检查配额
await check_quota(tenant_id, "stores", db)

# 创建管理员前检查配额
await check_quota(tenant_id, "admins", db)

# 创建医生前检查配额
await check_quota(tenant_id, "doctors", db)

# 创建预约前检查配额
await check_quota(tenant_id, "appointments", db)
```

**超配额处理：**
- 抛出 `QuotaCheckError`（HTTP 403）
- 错误消息包含当前用量和上限
- 前端显示友好的提示信息

### 配额继承

租户配额的优先级：
1. 租户自定义配额（Tenant 字段）
2. 订阅计划配额（SubscriptionPlan 字段）
3. 系统默认值

通过 `get_effective_max_*()` 方法获取有效配额。

## 通知机制

### 通知类型

1. **订阅到期提醒**（subscription_expiry）
   - 提前 7 天：普通提醒
   - 提前 3 天：重要提醒
   - 提前 1 天：紧急提醒
   - 已到期：紧急提醒

2. **用量警告**（usage_warning）
   - 80% 配额：普通警告
   - 90% 配额：重要警告
   - 100% 配额：紧急警告

3. **欠费通知**（overdue）
   - 订阅到期自动标记欠费时发送

### 通知存储

通知存储在 `TenantNotification` 表中：
- `tenant_id`: 租户ID
- `notification_type`: 通知类型
- `title`: 通知标题
- `content`: 通知内容
- `priority`: 优先级（0-普通、1-重要、2-紧急）
- `is_read`: 是否已读
- `read_at`: 阅读时间

### 通知发送

**当前实现：**
- 站内信（存储在数据库）
- 日志记录

**扩展方向：**
- 邮件通知（需配置 SMTP）
- 短信通知（需对接短信服务商）

### 定时任务

1. **每日凌晨1点**：租户用量统计
2. **每日凌晨2点**：订阅到期检查
3. **每日凌晨4点**：用量限制检查

## 最佳实践

### 开发指南

1. **查询数据时**：始终使用 `add_tenant_filter()` 添加租户过滤
2. **创建数据时**：使用 `get_tenant_id_for_create()` 获取租户ID
3. **缓存数据时**：确保缓存键包含 `tenant_id` 维度
4. **导入导出时**：强制使用当前租户上下文

### 安全检查清单

- [ ] 所有查询都添加了租户过滤
- [ ] 所有创建都使用了正确的租户ID
- [ ] 缓存键包含租户维度
- [ ] 导入文件不包含 `tenant_id` 字段
- [ ] NULL `tenant_id` 数据的处理符合预期

### 常见问题

**Q: 如何处理跨租户的数据统计？**
A: 使用平台管理员身份（tenant_id = NULL），查询所有租户的数据。

**Q: 如何支持租户级别的自定义配置？**
A: 使用 `Tenant.features` 和 `Tenant.branding_config` 字段存储 JSON 格式的配置。

**Q: 如何测试租户隔离？**
A: 参考 `apps/server/tests/tenants/` 目录下的测试用例，特别是跨租户访问拒绝的测试。

## 附录

### 相关文件

**模型层：**
- `app/models/tenant.py`：租户相关模型
- `app/models/*/`：各业务模型（包含 tenant_id 字段）

**服务层：**
- `app/modules/tenants/service.py`：租户管理服务
- `app/modules/tenants/service_usage.py`：租户用量统计服务
- `app/common/quota.py`：配额检查工具
- `app/common/tenant_filter.py`：租户过滤工具

**中间件：**
- `app/middleware/tenant_context.py`：租户上下文管理
- `app/middleware/tenant_middleware.py`：租户识别中间件

**通知：**
- `app/infrastructure/notifications/service.py`：租户通知服务
- `app/tasks/tenant_usage_task.py`：租户定时任务

**测试：**
- `apps/server/tests/tenants/`：租户相关测试

### 迁移脚本

- `scripts/init_subscription_plans.py`：初始化订阅计划
- `scripts/migrate_tenant_data.py`：迁移租户数据
- `scripts/migrate_core_tenant_data.py`：迁移核心数据

### 数据库迁移

- `migrations/versions/039_add_tenant_support.py`：添加租户支持
- `migrations/versions/040_add_tenant_to_core_tables.py`：核心表添加租户字段
- `migrations/versions/041_add_template_driven_miniapp_platform.py`：添加模板驱动的小程序平台

---

**文档版本：** v1.0
**更新日期：** 2026-03-25
**维护者：** 开发团队
