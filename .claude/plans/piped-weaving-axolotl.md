# 订阅过期/欠费的全端处理方案

## Context

当前后端已实现「定时任务到期自动把 `tenant.status` 置为 2（欠费）+ 写 `tenant_notifications` 表」的能力，但前端基本无感：

- **Admin / Admin-v2**：欠费后登录被拦（HTTP 403 + detail 字符串），但**已登录的会话**和后续接口只会落到通用 toast，没有独立的"续费引导/全局横幅/到期前预警"。
- **患者小程序 / H5**：后端鉴权链（`get_current_user` / `get_current_user_or_admin`）和预约创建路径**完全没有 tenant 状态校验**，租户停服时患者侧照常下单。
- **`tenant_notifications` 表**已有写入逻辑（subscription_expiry / usage_warning / overdue），但**没有任何 router 暴露给前端**。
- 后端用 HTTPException + detail 字符串传递欠费/禁用，缺结构化错误码，前端只能字符串匹配。

目标：让"订阅到期/欠费"在四个前端都成为**可识别、可引导、不破坏只读体验**的一等状态——欠费时管理端能看到独立的提示页与续费引导，到期前 7/3/1 天能看到顶栏横幅，患者端禁止新预约但保留只读，并把已有的 `tenant_notifications` 通过 admin 顶栏铃铛展示。

---

## 一、后端改造（apps/server）

### 1.1 新增结构化错误码

**新文件** `apps/server/app/common/error_codes.py`

```python
class TenantErrorCode:
    TENANT_DISABLED = "TENANT_DISABLED"          # 租户被禁用
    TENANT_OVERDUE = "TENANT_OVERDUE"            # 租户欠费
    TENANT_TRIAL_EXPIRED = "TENANT_TRIAL_EXPIRED"# 试用期到期
    TENANT_SUSPENDED_WRITE = "TENANT_SUSPENDED_WRITE"  # 写操作被拒（患者侧）
```

**改造** `apps/server/app/middleware/exception.py:91-98`

让 `http_exception_handler` 识别 `HTTPException.detail` 为 dict 时透传 `code`/`message`，否则回落现状字符串行为。新增便捷构造函数 `raise_tenant_error(error_code, message)`，统一在登录/鉴权依赖处使用。

**复用**：`BusinessError` (`apps/server/app/middleware/exception.py:17-23`) 已支持自定义 code，无需新建异常类，仅扩展 handler。

### 1.2 鉴权依赖统一化

**改造** `apps/server/app/common/deps.py:264-269` `get_current_admin`

现行只校验 `tenant.status==0/2`。补充：

- `tenant.status==2` → 抛 `BusinessError(code=TENANT_OVERDUE, message="租户已欠费，请续费后继续使用", http_status=403)`
- `tenant.status==0` → `TENANT_DISABLED`
- 增加：当 `tenant.status==1` 但 `tenant.subscription_end_at and tenant.subscription_end_at < utcnow()` 时也按 `TENANT_OVERDUE` 拦截（防御定时任务尚未跑的窗口期）

**新增** 患者侧轻量校验依赖 `apps/server/app/common/deps.py`

```python
async def require_tenant_active_for_write(...) -> None:
    """供患者端写操作（预约/挂号/支付）使用。
    禁用/欠费时抛 TENANT_SUSPENDED_WRITE。只读接口不调用。"""
```

**挂载点**（仅写操作，保留只读）：
- `apps/server/app/modules/appointments/router_booking.py:35-67` 创建预约
- `apps/server/app/modules/appointments/router.py` 取消/改约
- `apps/server/app/modules/payments/router.py` 发起支付

### 1.3 新增"当前租户/通知"接口

**新增** `apps/server/app/modules/tenants/router.py`

```
GET  /api/v1/tenants/me                      # 返回当前租户精简信息（admin 用）
GET  /api/v1/tenants/me/public               # 返回 status/subscription_end_at（患者端可匿名获取，按 X-Tenant-ID 解析）
GET  /api/v1/tenants/me/notifications        # 站内信列表 + 未读数（admin 用）
POST /api/v1/tenants/me/notifications/{id}/read
POST /api/v1/tenants/me/notifications/read-all
```

返回字段（`schemas.py` 新增 `CurrentTenantResponse`）：

```
status, subscription_plan_name, subscription_end_at,
is_subscription_active, days_until_expiry,
billing_cycle, contact_phone(用于续费联系)
```

**复用**：`Tenant.is_subscription_active` (`models/tenant.py:139-148`) 直接序列化；`TenantNotification` 模型 (`models/tenant.py:232-261`) 已含 `is_read/priority/notification_type`；查询逻辑参考 `tenants/service.py` 现有分页模式。

### 1.4 `/admin/me` 扩展

**改造** `apps/server/app/modules/admin/helpers.py:37-86` `build_admin_response`

在 `AdminResponse` (`packages/api/src/modules/admin.ts:52-83` 同步类型) 中新增嵌套：

```
tenant: {
  status, subscriptionPlanName, subscriptionEndAt,
  isSubscriptionActive, daysUntilExpiry
}
```

避免前端登录后再发一次 `/tenants/me`。

---

## 二、共享层改造

### 2.1 packages/api

**改造** `packages/api/src/modules/tenant.ts`

新增方法 `getCurrentTenant()`、`getCurrentTenantPublic()`、`getMyNotifications(query)`、`markNotificationRead(id)`、`markAllNotificationsRead()`，并新增 TS 类型 `CurrentTenant`、`TenantNotification`、`TenantStatusInfo`。

**改造** `packages/api/src/modules/admin.ts:52-83`

`Admin` 类型新增 `tenant?: TenantStatusInfo` 字段。

### 2.2 packages/shared

**新增** `packages/shared/src/utils/tenantStatus.ts`

```ts
export type TenantSuspendReason = 'overdue' | 'disabled' | 'trial_expired';
export interface TenantStatusInfo { ... }

export function deriveTenantBannerLevel(t): 'none'|'warning'|'critical';
// 规则：days_until_expiry <= 7 → warning；<=1 critical；status!=1 → critical
export function isTenantSuspended(t): boolean;
export function shouldBlockWrite(t): boolean;
```

**新增** `packages/shared/src/utils/tenantSuspend.ts`

仿 `authFeedback.ts` 模式提供 `markTenantSuspended()` / `clearTenantSuspended()` / `subscribeTenantSuspended()`，借由 `crossTabSync`（已存在）跨标签广播。

### 2.3 三端响应拦截器复用同一识别函数

**新增** `packages/shared/src/utils/parseTenantError.ts`

```ts
export function parseTenantError(err): TenantSuspendReason | null;
// 同时识别 BusinessError code 与历史 detail 字符串包含「欠费/禁用」
```

被以下三处复用：
- `apps/admin/src/utils/request.ts:144-148`
- `apps/admin-v2/src/api/interceptors.ts:107-110`
- `apps/patient-miniapp/src/app.tsx:178-189`
- （patient-h5 同小程序 request 拦截器）

---

## 三、Admin 端（apps/admin）

### 3.1 全局响应拦截器扩展

**改造** `apps/admin/src/utils/request.ts:144-148`

403 分支增加：调用 `parseTenantError(err)`，命中则：
1. `markTenantSuspended(reason)` 记录全局状态
2. 路由跳转到新页面 `/tenant-suspended`（替代原 toast）
3. 调用 `clearAuthSession`（保留 token 但禁用 layout）

### 3.2 顶栏 Banner

**新增** `apps/admin/src/components/TenantStatusBanner/index.tsx`

基于 antd `Alert`，常驻 layout 顶部。读取 `initialState.currentAdmin.tenant`，按 `deriveTenantBannerLevel`：

- `warning`（≤7 天）：黄条「订阅将于 X 天后到期」+ 联系续费按钮
- `critical`（≤1 天 / 已过期 / status!=1）：红条 + 续费指引

**接入点** `apps/admin/src/app.tsx:399-523` `layout.childrenRender`（`:517-519`）—— 在 `children` 上方插入 `<TenantStatusBanner/>`，所有页面共享。

### 3.3 顶栏通知铃铛对接

**改造** `apps/admin/src/components/HeaderActions/index.tsx`

`NotificationButton` 现状（推断仅 UI 占位或对接其他通知）改为读取 `tenantApi.getMyNotifications({ unread: true })`，含未读红点。点击下拉显示最近 10 条 + 跳转「我的通知」全列表页（新页面 `pages/account/notifications.tsx`）。

### 3.4 续费引导页

**新增** `apps/admin/src/pages/tenant-suspended/index.tsx`

- 路由 `/tenant-suspended`（`apps/admin/config/routes.ts` 新增，`layout: false`）
- 内容：状态原因 + 到期时间 + 联系销售（取 tenant.contact_phone / 配置中心电话）+ 退出登录按钮
- 不复用菜单/侧边栏，禁止用户继续操作业务

### 3.5 initialState 扩展

**改造** `apps/admin/src/app.tsx:333-393`

`getInitialState` 中 `currentAdmin` 已含新增 `tenant` 字段（来自 1.4），无需多发请求。增加每 5 分钟轮询 `/tenants/me` 刷新（用 `setInterval`，配合 `unmount` 清理）。

### 3.6 跨标签同步

复用 `apps/admin/src/app.tsx:154-231` `handleCrossTabEvent`，新增 `tenant-suspended` 事件类型，一个标签收到 403 后，其它标签同步跳转。

---

## 四、Admin-v2 端（apps/admin-v2）

### 4.1 拦截器扩展

**改造** `apps/admin-v2/src/api/interceptors.ts:107-110`

403 分支调用 `parseTenantError`；命中则 `useAuthStore.getState().markTenantSuspended(reason)` + `navigate('/tenant-suspended')`。

### 4.2 auth-store 扩展

**改造** `apps/admin-v2/src/auth/auth-store.ts:25-108`

- state 新增 `tenantStatus: TenantStatusInfo | null`、`suspendReason: TenantSuspendReason | null`
- `fetchCurrentUser` (`:71-90`) 同时取 `admin.tenant` 写入
- 新增 action `markTenantSuspended(reason)` / `clearTenantSuspended()`

### 4.3 Banner 组件

**新增** `apps/admin-v2/src/components/tenant-status-banner.tsx`

基于 shadcn `Alert`，逻辑同 admin 端。

**接入** `apps/admin-v2/src/layout/AdminLayout.tsx:6-18`

```
<SidebarInset>
  <AppHeader/>
  <TenantStatusBanner/>  {/* 新增 */}
  <main>{children}</main>
</SidebarInset>
```

### 4.4 续费引导页 + Guard

**新增** `apps/admin-v2/src/pages/tenant-suspended.tsx`

**改造** `apps/admin-v2/src/auth/auth-guard.tsx`

新增分支：`suspendReason != null && pathname !== '/tenant-suspended'` → `<Navigate to="/tenant-suspended"/>`。

### 4.5 通知铃铛

**新增** `apps/admin-v2/src/components/notification-bell.tsx`（shadcn DropdownMenu + Badge）

**接入** `apps/admin-v2/src/layout/AppHeader.tsx:31-58`，放在用户头像左侧。

---

## 五、患者小程序（apps/patient-miniapp）

### 5.1 启动注入租户状态

**改造** `apps/patient-miniapp/src/app.tsx:262-292` `bootstrap()`

`storeApi.getByCode(storeCode)` 后，并行调 `tenantApi.getCurrentTenantPublic()`，把结果写入全局（新建 `apps/patient-miniapp/src/store/tenant.ts` 简单 zustand 或 valtio store）。

### 5.2 写操作前置检查

**新增** `apps/patient-miniapp/src/hooks/useTenantGuard.ts`

```ts
export function useTenantGuard() {
  return {
    requireWritable: () => {
      if (isTenantSuspended(tenant)) {
        Taro.showModal({ title: '该机构暂停服务', content: '...', showCancel: false });
        throw new TenantSuspendedError();
      }
    }
  };
}
```

**接入点**：
- `apps/patient-miniapp/src/packageBooking/pages/booking/index.tsx` `handleSubmit` 入口
- 取消/改约页面同理
- 收藏/反馈等次要写操作不强拦，由后端兜底

### 5.3 全局拦截器扩展

**改造** `apps/patient-miniapp/src/app.tsx:178-189`

`response` 拦截：识别 `TENANT_SUSPENDED_WRITE` / `TENANT_OVERDUE` 错误码，弹模态「机构已暂停服务，请联系机构续费」，不跳转（保留只读浏览）。

### 5.4 顶部静默 Banner（可选）

**改造** `apps/patient-miniapp/src/components/PageContainer.tsx:21-59`

可选：当 `isTenantSuspended` 时，在顶部插入一条只读 Banner「该机构暂停服务，新预约不可下单」。**不做强遮罩**，保持只读体验。

---

## 六、患者 H5（apps/patient-h5）

与小程序对称：

- **改造** `apps/patient-h5/src/utils/request.ts`（或类似入口）：复用 `parseTenantError`
- **新增** `apps/patient-h5/src/hooks/useTenantGuard.ts`
- **接入** `apps/patient-h5/src/pages/appointment/detail.tsx` 等写操作页面
- 登录/启动时调 `tenantApi.getCurrentTenantPublic()`

H5 端结构与小程序非常相似，可在小程序方案落地后简单复刻。

---

## 七、关键文件清单

### 新增
- `apps/server/app/common/error_codes.py`
- `packages/shared/src/utils/tenantStatus.ts`
- `packages/shared/src/utils/tenantSuspend.ts`
- `packages/shared/src/utils/parseTenantError.ts`
- `apps/admin/src/components/TenantStatusBanner/index.tsx`
- `apps/admin/src/pages/tenant-suspended/index.tsx`
- `apps/admin/src/pages/account/notifications.tsx`
- `apps/admin-v2/src/components/tenant-status-banner.tsx`
- `apps/admin-v2/src/components/notification-bell.tsx`
- `apps/admin-v2/src/pages/tenant-suspended.tsx`
- `apps/patient-miniapp/src/hooks/useTenantGuard.ts`
- `apps/patient-miniapp/src/store/tenant.ts`
- `apps/patient-h5/src/hooks/useTenantGuard.ts`

### 修改
- `apps/server/app/middleware/exception.py:91-98`
- `apps/server/app/common/deps.py:264-269`（admin 拦截扩展 + 新增写操作依赖）
- `apps/server/app/modules/admin/router_auth_login.py:99-287`（四个登录入口改用结构化错误）
- `apps/server/app/modules/admin/helpers.py:37-86`（`/admin/me` 扩展）
- `apps/server/app/modules/tenants/router.py`（5 个新端点）
- `apps/server/app/modules/tenants/schemas.py`
- `apps/server/app/modules/tenants/service.py`（通知查询/已读）
- `apps/server/app/modules/appointments/router_booking.py:35-67`、`router.py`、`payments/router.py`（挂 `require_tenant_active_for_write`）
- `packages/api/src/modules/tenant.ts`、`admin.ts`
- `apps/admin/src/utils/request.ts:144-148`
- `apps/admin/src/app.tsx:154-231,333-393,399-523`
- `apps/admin/src/components/HeaderActions/index.tsx`
- `apps/admin/config/routes.ts`
- `apps/admin-v2/src/api/interceptors.ts:107-110`
- `apps/admin-v2/src/auth/auth-store.ts:25-108`
- `apps/admin-v2/src/auth/auth-guard.tsx`
- `apps/admin-v2/src/layout/AdminLayout.tsx`、`AppHeader.tsx`
- `apps/patient-miniapp/src/app.tsx:178-189,262-292`
- `apps/patient-miniapp/src/components/PageContainer.tsx`
- `apps/patient-miniapp/src/packageBooking/pages/booking/index.tsx`
- `apps/patient-h5/src/utils/request.ts`、写操作页面

---

## 八、验证方案

### 8.1 后端单元测试

- `apps/server/tests/unit/test_tenant_suspend.py`（新增）
  - 测 `BusinessError` 扩展 handler 的 dict detail 透传
  - 测 `get_current_admin` 在 `tenant.status=2` / `subscription_end_at < now` 两种场景下的拦截
  - 测 `require_tenant_active_for_write` 依赖
  - 测 `/tenants/me`、`/tenants/me/notifications` 含已读/分页
- 复用 `apps/server/tests/conftest.py` 已有 fixtures（内存 SQLite + mock Redis）

### 8.2 后端集成测试

- `apps/server/tests/integration/test_tenant_suspend_flow.py`（新增）
  - 预约创建在 status=2 时 → 403 + `TENANT_SUSPENDED_WRITE`
  - 列表查询在 status=2 时 → 200（只读放行）

### 8.3 前端手动验证

执行步骤（按顺序）：

1. **造数据**：`pnpm dev:server` 启动后端，用 SQL 把测试租户 `tenants.status=2`（或 `subscription_end_at` 改为昨天）。
2. **Admin（`pnpm dev:admin` → :8005）**：
   - 已登录态：刷新页面 → 自动跳 `/tenant-suspended`
   - 未登录态：登录 → 报 "租户已欠费"
   - 改为 status=1 + `subscription_end_at` 7 天后 → 顶栏出现黄色 Banner
   - 改为 1 天后 → 红色 Banner
   - 触发 `tenant_notifications` 写入 → 顶栏铃铛红点
3. **Admin-v2（`pnpm dev:admin-v2`）**：同 admin 流程
4. **小程序（`pnpm dev:patient-miniapp`）**：
   - status=2：进入首页可浏览，点「立即预约」→ 弹模态拦截
   - 列表/医生详情仍可查看
5. **Patient-H5（`pnpm dev:patient-h5` → :8002）**：同小程序

### 8.4 回归

- `pnpm lint`
- `cd apps/server && pytest tests/unit/test_tenant_suspend.py tests/integration/test_tenant_suspend_flow.py -v`
- `cd apps/server && pytest tests/tenants/ -v`（确保未破坏现有租户测试）
- `pnpm test`（admin 端 vitest）

---

## 九、风险与回滚

- **风险 1**：`/admin/me` 扩展增字段，若旧前端未升级到新 packages/api 版本，TS 类型不会报错但不会显示 banner。**缓解**：新增字段全 optional。
- **风险 2**：写操作依赖加得过多，可能误伤平台管理员。**缓解**：`require_tenant_active_for_write` 内部跳过 `is_super_admin`。
- **风险 3**：定时任务尚未跑、`subscription_end_at < now` 但 `status=1` 的"窗口期"，新增的 deps 防御逻辑会提前拦截，**这是预期行为**，无需回滚。
- **回滚**：本方案后端改动以"新增拦截 + 新错误码 + 新 router"为主，回滚只需移除 deps 中新增分支与 `error_codes.py`，前端组件未挂载即不生效。
