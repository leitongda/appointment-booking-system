# 租户管理模块架构分析与线框图

## Context

用户要求排查租户（Tenant）相关逻辑如何与其他业务模块关联，以及 admin 端如何操作租户。本文件产出为**纯分析文档**（不涉及代码修改），包含：
1. 多租户架构全景
2. 数据关联关系
3. Admin 端各页面线框图（ASCII）
4. 关键文件索引

---

## 1. 多租户架构全景

### 1.1 租户识别链路

```
用户登录
  │
  ▼
Login Response 包含 admin.tenantId
  │
  ▼
localStorage.setItem('hospital_current_tenant_id', tenantId)
  │
  ▼
Axios 请求拦截器 → 自动注入 X-Tenant-ID Header
  │
  ▼
TenantContextMiddleware (后端中间件)
  │
  ├─ 优先级1: X-Tenant-ID Header (直接 UUID)
  ├─ 优先级2: X-Tenant-Code Header (需 DB 查询)
  ├─ 优先级3: 子域名 (tenant1.example.com)
  └─ 优先级4: 路径前缀 (/t/tenant1/...)
  │
  ▼
ContextVar (异步安全上下文变量)
  │
  ▼
Service 层所有查询自动 WHERE tenant_id = ?
```

### 1.2 数据隔离层级

| 层级 | 机制 | 文件 |
|------|------|------|
| 数据库 | 28+ 表有 `tenant_id` FK + 索引 | `apps/server/app/models/*.py` |
| 中间件 | ContextVar 注入 tenant 上下文 | `apps/server/app/middleware/tenant_context.py` |
| 服务层 | `add_tenant_filter()` 查询过滤 | `apps/server/app/common/tenant_filter.py` |
| 缓存层 | Redis key 前缀含 `tenant:{id}:` | `apps/server/app/core/redis.py` |
| 安全校验 | 跨租户操作抛 403 | `apps/server/app/common/deps.py:286-293` |
| 前端 | `X-Tenant-ID` Header + localStorage | `apps/admin/src/utils/request.ts:76-81` |

---

## 2. 租户与业务模块关联

### 2.1 核心关联模型图

```
                        ┌─────────────────────┐
                        │    SubscriptionPlan  │
                        │  (定价/配额/功能开关)  │
                        └──────────┬──────────┘
                                   │ 1:N
                        ┌──────────▼──────────┐
                        │       Tenant        │
                        │ (租户核心表)          │
                        │ status: 0禁/1常/2欠/3试│
                        └──┬──┬──┬──┬──┬──┬──┬┘
                           │  │  │  │  │  │  │
              ┌────────────┘  │  │  │  │  │  └──────────┐
              ▼               ▼  ▼  ▼  ▼  ▼             ▼
         ┌────────┐    ┌─────┐┌───┐┌──┐┌──────┐  ┌──────────┐
         │ Store  │    │Admin││Doc││Dep││Role  │  │User/Patient│
         │(门店)  │    │管理员││医 ││科 ││(角色)│  │(用户/患者) │
         └───┬────┘    └─────┘└──┬┘└──┘└──────┘  └──────────┘
             │                 │
     ┌───────┼───────┐        │
     ▼       ▼       ▼        ▼
┌────────┐┌──────┐┌──────┐┌───────────┐
│Schedule││Appnt ││Dept  ││SchTemplate│
│(排班)  ││(预约)││(科室)││(排班模板)  │
└────────┘└──────┘└──────┘└───────────┘
```

### 2.2 28+ 含 tenant_id 的模型清单

| 模型 | 文件 | nullable | 特殊约束 |
|------|------|----------|----------|
| Store | `models/store.py:13` | Yes (平台级门店) | `(tenant_id, code)` unique |
| Admin | `models/admin.py:82` | Yes (平台管理员) | — |
| Role | `models/admin.py:52` | Yes (平台角色) | — |
| Doctor | `models/doctor.py:13` | Yes | `(tenant_id, username)`, `(tenant_id, phone)` unique |
| User | `models/user.py:11` | Yes | `(tenant_id, phone)`, `(tenant_id, openid)` unique |
| Patient | `models/user.py:46` | Yes | `(tenant_id, card_no)` unique |
| Department | `models/department.py:19` | Yes | — |
| Schedule | `models/schedule.py:22` | Yes | — |
| ScheduleTemplate | `models/schedule_template.py:15` | Yes | — |
| ScheduleSuspension | `models/schedule_suspension.py:13` | Yes | — |
| Appointment | `models/appointment.py:18` | Yes | — |
| MedicalRecord | `models/medical_record.py:13` | Yes | — |
| Message | `models/message.py:23` | Yes | — |
| LeaveRequest | `models/leave_request.py:26` | Yes | — |
| RestDay | `models/rest_day.py:12` | Yes | — |
| RuleSet (x3) | `models/rule_set.py:30,45,209` | Yes (null=全局) | — |
| MiniappCompany | `models/miniapp_platform.py:14` | No | — |
| MiniappInstance | `models/miniapp_platform.py:70` | No | — |
| PaymentProfile | `models/miniapp_platform.py:113` | No | — |
| MiniappConfig | `models/miniapp_platform.py:143` | No | — |
| MiniappTemplate | `models/miniapp_platform.py:178` | No | — |
| TenantSubscription | `models/tenant.py:160` | No | — |
| TenantUsageLog | `models/tenant.py:197` | No | — |
| TenantNotification | `models/tenant.py:237` | No | — |

### 2.3 配额层级（覆盖优先级）

```
有效配额 = Tenant.max_stores  (租户级覆盖)
           ?? SubscriptionPlan.max_stores  (计划默认值)
           ?? 1  (硬编码兜底)
```

方法: `Tenant.get_effective_max_stores()` (`models/tenant.py:107-137`)

---

## 3. Admin 端租户操作流程与线框图

### 3.1 路由结构

```
/platform/tenant                → 重定向到 /platform/tenant/list
/platform/tenant/list           → 租户列表页
/platform/tenant/create         → 新增租户
/platform/tenant/:id            → 租户详情
/platform/tenant/:id/edit       → 编辑租户
/platform/tenant/plans          → 订阅计划列表
/platform/tenant/plans/create   → 新增订阅计划
/platform/tenant/plans/:id/edit → 编辑订阅计划
```

权限控制: `canTenant`, `canTenantPlans`

### 3.2 租户列表页线框图

```
┌──────────────────────────────────────────────────────────────────────────┐
│  PageContainer: 租户管理                                                  │
├──────────────────────────────────────────────────────────────────────────┤
│                                                          ┌──────────┐    │
│                                                          │+ 新增租户 │    │
│                                                          │ 订阅计划  │    │
│  搜索: [名称/标识/联系人___] [状态 ▼] [计划 ▼] [查询]     └──────────┘    │
├──────┬──────────┬─────┬────────┬────────┬──────┬─────┬─────────┬────────┤
│ 租户  │ 租户名称  │ 状态 │订阅计划 │订阅到期 │门店/管理│联系人   │创建时间  │操作│
│ 标识  │          │     │        │        │员数   │         │         │    │
├──────┼──────────┼─────┼────────┼────────┼──────┼─────┼─────────┼────────┤
│copyable│ <a>名称   │Tag  │Tag     │日期    │ 3/5  │张三     │2025-.. │编辑│
│ clinic│ → 详情页  │正常  │基础版  │        │      │         │        │删除│
│       │          │绿标  │蓝标    │        │      │         │        │激活│
├──────┼──────────┼─────┼────────┼────────┼──────┼─────┼─────────┼────────┤
│ ...  │ ...      │已禁用│ 未订阅  │  -     │0/0   │-       │...     │... │
│      │          │灰色  │ 灰标   │        │      │        │        │    │
└──────┴──────────┴─────┴────────┴────────┴──────┴─────┴─────────┴────────┘
                                          分页: < 1 2 3 ... >
```

### 3.3 新增/编辑租户表单线框图

```
┌──────────────────────────────────────────────────────────────────────────┐
│  PageContainer: 新增租户 / 编辑租户                                       │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌─ 基本信息未分组 ────────────────────────────────────────────────────┐  │
│  │                                                                     │  │
│  │  租户标识 [clinic-one____]     租户名称 [XX诊所__________]          │  │
│  │  (仅创建时可编辑,               (必填)                              │  │
│  │   实时唯一性校验)                                                    │  │
│  │                                                                     │  │
│  │  订阅计划 [基础版 ▼]            计费周期 [月付 ▼]                    │  │
│  │                                                                     │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  ┌─ 配额设置 (Card) ──────────────────────────────────────────────────┐  │
│  │                                                                     │  │
│  │  最大门店数 [___]  最大管理员数 [___]  最大医生数 [___]  月预约上限  │  │
│  │                                                           [___]    │  │
│  │  (留空 = 使用订阅计划默认值)                                         │  │
│  │                                                                     │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  ┌─ 联系信息 (Card) ──────────────────────────────────────────────────┐  │
│  │                                                                     │  │
│  │  联系人 [张三___]    联系电话 [138___________]    联系邮箱 [a@b.c_]  │  │
│  │                                                                     │  │
│  │  详细地址 [_____________________________________________]            │  │
│  │           [_____________________________________________]            │  │
│  │                                                                     │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  ┌─ 域名配置 (Card) ──────────────────────────────────────────────────┐  │
│  │                                                                     │  │
│  │  子域名前缀 [clinic1__]    自定义域名 [www.example.com_]            │  │
│  │  (→ clinic1.yourdomain.com)                                        │  │
│  │                                                                     │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│                                    [ 取消 ]              [ 保存 ]         │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

### 3.4 租户详情页线框图

```
┌──────────────────────────────────────────────────────────────────────────┐
│  PageContainer: XX诊所                  [激活租户] [暂停租户] [编辑] [返回] │
├──────────────────────────────────────┬───────────────────────────────────┤
│  左栏 (Col 16)                       │  右栏 (Col 8)                     │
│                                      │                                   │
│  ┌─ Tabs ──────────────────────┐     │  ┌─ 用量概览 (Card) ──────────┐  │
│  │ [租户概览] [订阅记录] [用量日志]│    │  │                           │  │
│  ├─────────────────────────────┤     │  │  门店数      管理员数       │  │
│  │                             │     │  │  ┌────┐     ┌────┐        │  │
│  │  === 租户概览 Tab ===       │     │  │  │3/10│     │5/20│        │  │
│  │                             │     │  │  └────┘     └────┘        │  │
│  │  租户标识: clinic-one       │     │  │                           │  │
│  │  状态:      [正常] Tag      │     │  │  医生数      本月预约       │  │
│  │  订阅计划:  [基础版] Tag    │     │  │  ┌────┐     ┌────┐        │  │
│  │  计费周期:  月付            │     │  │  │50  │     │200 │        │  │
│  │  订阅到期:  2025-12-31     │     │  │  └────┘     └────┘        │  │
│  │  创建时间:  2025-01-01     │     │  │                           │  │
│  │  联系人:    张三            │     │  │  本月完成    本月取消       │  │
│  │  联系电话:  138xxxx         │     │  │  ┌────┐     ┌────┐        │  │
│  │  联系邮箱:  a@b.c          │     │  │  │180 │     │ 20 │        │  │
│  │  详细地址:  XX市XX路...     │     │  │  └─绿──┘     └─红──┘        │  │
│  │  子域名:    clinic1        │     │  │                           │  │
│  │  自定义域名: www.xx.com    │     │  │  存储空间                  │  │
│  │                             │     │  │  ┌──────────────┐        │  │
│  ├─────────────────────────────┤     │  │  │ 256.00 MB /  │        │  │
│  │                             │     │  │  │ 1024 MB      │        │  │
│  │  === 订阅记录 Tab ===       │     │  │  └──────────────┘        │  │
│  │                             │     │  └───────────────────────────┘  │
│  │  ┌──────┬───┬──────┬──────┬───┬───┬─────┐                         │
│  │  │ 计划  │周期│开始   │结束  │金额│状态│自动续│                         │
│  │  ├──────┼───┼──────┼──────┼───┼───┼─────┤                         │
│  │  │基础版 │月付│01-01 │02-01 │99  │已付│ 是  │                         │
│  │  └──────┴───┴──────┴──────┴───┴───┴─────┘                         │
│  │                             │     │  ┌─ 配额限制 (Card) ─────────┐  │
│  ├─────────────────────────────┤     │  │                           │  │
│  │                             │     │  │  最大门店数:  使用计划默认值│  │
│  │  === 用量日志 Tab ===       │     │  │  最大管理员数: 使用计划默认值│  │
│  │                             │     │  │  最大医生数:  使用计划默认值 │  │
│  │  ┌──────┬───┬───┬───┬───┬───┬───┐ │  │  月预约上限:  使用计划默认值│  │
│  │  │ 日期  │预约│完成│取消│新用│活医│存储│ │  │                           │  │
│  │  ├──────┼───┼───┼───┼───┼───┼───┤ │  └───────────────────────────┘  │
│  │  │04-01 │ 15│ 12│  3│ 5 │ 8│1.2│ │                                   │
│  │  └──────┴───┴───┴───┴───┴───┴───┘ │                                   │
│  │                             │     │                                   │
│  └─────────────────────────────┘     └───────────────────────────────────┘
└──────────────────────────────────────────────────────────────────────────┘
```

### 3.5 订阅计划列表页线框图

```
┌──────────────────────────────────────────────────────────────────────────┐
│  PageContainer: 订阅计划列表                             [+ 新增计划] [返回]│
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
├──────┬──────┬──────┬──────┬──────┬──────┬──────┬──────┬─────┬────┬──────┤
│计划编码│计划名│月付价│年付价│门店上│管理员│医生上│月预约│状态  │默认│排序│操作│
│      │称    │格    │格    │限    │上限  │限    │上限  │     │    │    │    │
├──────┼──────┼──────┼──────┼──────┼──────┼──────┼──────┼─────┼────┼──────┤
│basic │基础版│¥99   │¥999  │5     │20    │50    │1000  │启用  │默认│ 1 │编辑│
│      │      │      │      │      │      │      │      │绿标  │蓝标│   │删除│
├──────┼──────┼──────┼──────┼──────┼──────┼──────┼──────┼─────┼────┼──────┤
│pro   │专业版│¥299  │¥2999 │20    │50    │200   │5000  │启用  │ -  │ 2 │... │
├──────┼──────┼──────┼──────┼──────┼──────┼──────┼──────┼─────┼────┼──────┤
│...   │...   │...   │...   │...   │...   │...   │...   │...  │... │...│... │
└──────┴──────┴──────┴──────┴──────┴──────┴──────┴──────┴─────┴────┴──────┘

注: 默认计划不可删除; isDefault=true 的计划标记蓝标
```

### 3.6 租户切换器组件（Header 内）

```
┌──────────────────────────────────────────────────────┐
│  HEADER                                    [🏥 当前租户 ▼] │
├──────────────────────────────────────────────────────┤
│                                                      │
│              点击后弹出 Popover:                       │
│              ┌─────────────────────┐                  │
│              │ 切换租户              │                  │
│              ├─────────────────────┤                  │
│              │ ✓ [🏥] XX诊所       │                  │
│              │        clinic-one   │  ← 当前选中      │
│              │                      │                  │
│              │   [🏥] YY医院       │                  │
│              │        hospital-yy  │                  │
│              │                      │                  │
│              │   [🏥] ZZ康复中心   │                  │
│              │        zz-rehab     │                  │
│              └─────────────────────┘                  │
│                                                      │
│  仅超级管理员可见 (roleCode === 'SUPER_ADMIN')         │
│  切换流程:                                            │
│  1. 保存 tenantId → localStorage                     │
│  2. 清除 currentStore 缓存                           │
│  3. window.location.reload() 全页刷新                 │
└──────────────────────────────────────────────────────┘
```

### 3.7 登录流程中租户处理

```
用户输入账号密码 → POST /admin/login
                        │
                        ▼
              Response: { admin: { tenantId, ... }, stores: [...] }
                        │
           ┌────────────┼────────────────────┐
           ▼            ▼                    ▼
    localStorage   localStorage         resetTokenExpired
  .tenant_id    .currentStore          State()
                        │
                        ▼
              Axios 拦截器自动注入
              X-Tenant-ID Header
                        │
                        ▼
              所有后续 API 请求自动携带租户上下文
```

---

## 4. 关键文件索引

### 后端

| 文件 | 用途 |
|------|------|
| `apps/server/app/models/tenant.py` | Tenant, SubscriptionPlan, TenantSubscription, TenantUsageLog, TenantNotification 模型 |
| `apps/server/app/modules/tenants/router.py` | 租户 CRUD + 订阅计划 + 用量统计路由 |
| `apps/server/app/modules/tenants/service.py` | 租户/计划/订阅/用量业务逻辑 |
| `apps/server/app/modules/tenants/schemas.py` | 请求/响应 Pydantic Schema |
| `apps/server/app/middleware/tenant_context.py` | 多租户中间件 (Header/子域名/路径识别) |
| `apps/server/app/common/tenant_filter.py` | 查询过滤工具 (add_tenant_filter 等) |
| `apps/server/app/common/deps.py` | 依赖注入 (租户一致性校验, 第 277-293 行) |
| `apps/server/app/tasks/tenant_usage_task.py` | Celery 定时任务 (用量记录/过期检测/配额告警) |

### 前端 Admin

| 文件 | 用途 |
|------|------|
| `apps/admin/src/pages/tenant/index.tsx` | 租户列表页 |
| `apps/admin/src/pages/tenant/form.tsx` | 新增/编辑租户表单 |
| `apps/admin/src/pages/tenant/detail.tsx` | 租户详情页 (概览+订阅+用量) |
| `apps/admin/src/pages/tenant/plans.tsx` | 订阅计划列表页 |
| `apps/admin/src/pages/tenant/plan-form.tsx` | 新增/编辑订阅计划表单 |
| `apps/admin/src/components/TenantSwitcher/index.tsx` | 超级管理员租户切换器 |
| `apps/admin/src/utils/request.ts` | 请求拦截器 (注入 X-Tenant-ID) |
| `apps/admin/src/pages/login/index.tsx` | 登录 (存储 tenantId) |
| `apps/admin/config/routes.ts` | 路由配置 (/platform/tenant/*) |

### 共享包

| 文件 | 用途 |
|------|------|
| `packages/api/src/modules/admin.ts` | Admin API (AdminLoginResult 含 tenantId) |
| `packages/api/src/modules/tenant.ts` | Tenant API (14 个租户接口 + 5 个计划接口) |

---

## 5. 总结

- **租户是系统核心维度**：28+ 张业务表通过 `tenant_id` FK 关联，所有查询自动按租户过滤
- **Admin 端操作路径**：`/platform/tenant/*` — 租户 CRUD、订阅计划管理、用量监控
- **租户上下文传播**：登录存 localStorage → 请求拦截器注入 Header → 中间件解析 → ContextVar → Service 过滤
- **超级管理员特权**：TenantSwitcher 组件可跨租户切换
- **配额三级覆盖**：租户覆盖 > 计划默认 > 硬编码兜底
- **软删除策略**：租户禁用后保留 90 天数据
