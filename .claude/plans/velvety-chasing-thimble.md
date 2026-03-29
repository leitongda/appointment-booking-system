# 跨 Tab 状态同步方案（storage 事件监听）

## Context

当前系统的认证和上下文状态（token、租户、门店）存储在 localStorage 中，各 Tab 独立运行。当用户在 Tab B 登录/登出/切换租户/切换门店后，Tab A 无法感知变化，仍然使用旧的 token 和上下文发请求，导致：
- 数据串租户/串门店
- 旧 token 请求报 401，触发刚做好的弹框（但用户困惑）
- 显示的用户名/权限/菜单与实际不一致

## 覆盖场景

| 场景 | 触发动作 | 期望行为 |
|------|---------|---------|
| Tab B 登录新用户 | token 变化 | Tab A 弹框"登录账号已变更"，确认后 reload |
| Tab B 登录同用户 | token 更新 | Tab A 静默更新 token 快照，不弹框 |
| Tab B 登出 | token 被移除 | Tab A 弹框"已在其他页面退出登录"，确认后跳 login |
| Tab B 切换租户 | tenant_id 变化 | Tab A 弹框"租户已切换为 XXX"，确认后 reload |
| Tab B 切换门店 | currentStore 变化 | Tab A 弹框"门店已切换为 XXX"，确认后 reload |

## 实施方案

### 第 1 步：新增 `packages/shared/src/utils/crossTabSync.ts`

核心模块，提供发布-订阅式的跨 Tab 监听。

```typescript
// 关键设计：
// 1. 监听 window 'storage' 事件（仅跨 Tab 触发，同 Tab 不触发）
// 2. 对比关键字段的新旧值，生成变更事件
// 3. 通过订阅者回调通知各端
// 4. 提供判断"是否为同一用户换 token"的逻辑（解码 JWT 的 sub 字段对比）

export type CrossTabEvent =
  | { type: 'auth-change'; action: 'login' | 'logout' | 'switch-user'; newUserId?: string }
  | { type: 'tenant-change'; newTenantId: string; newTenantName?: string }
  | { type: 'store-change'; newStoreId: string; newStoreName?: string };

type EventHandler = (event: CrossTabEvent) => void;

// 监听的 localStorage keys
const WATCHED_KEYS = [
  'hospital_token',            // token
  'hospital_current_tenant_id', // 租户 ID
  'currentStore',              // 门店信息 JSON
];

export function initCrossTabSync(handler: EventHandler): () => void;
// 返回 unsubscribe 函数

export function destroyCrossTabSync(): void;
```

**内部逻辑**：
1. `initCrossTabSync` 注册 `window.addEventListener('storage', onStorageChange)`
2. `onStorageChange` 中判断 `event.key` 是否在 `WATCHED_KEYS` 中
3. 根据 key 类型解析事件：
   - `hospital_token`：对比旧 token 和新 token 的 JWT sub（用户 ID），判断是 login/logout/switch-user
   - `hospital_current_tenant_id`：读取新值生成 tenant-change
   - `currentStore`：解析 JSON 读取 store id/name 生成 store-change
4. 调用 handler 通知订阅者
5. 同步更新本地快照（防止重复触发）

### 第 2 步：导出新模块

**`packages/shared/src/utils/index.ts`** 添加：
```typescript
export * from './crossTabSync';
```

### 第 3 步：Admin 端集成 `apps/admin/src/app.tsx`

在 `rootContainer` 函数中初始化监听（应用最早的生命周期点）：

```typescript
import { initCrossTabSync, destroyCrossTabSync, CrossTabEvent } from '@hospital/shared';

export function rootContainer(container: any) {
  // ... 现有主题逻辑 ...

  // 初始化跨 Tab 状态同步
  initCrossTabSync((event: CrossTabEvent) => {
    handleCrossTabEvent(event);
  });

  return (
    <ConfigProvider ...>
      <App>{container}</App>
    </ConfigProvider>
  );
}
```

新增 `handleCrossTabEvent` 函数（放在 app.tsx 顶层或单独文件）：

```typescript
function handleCrossTabEvent(event: CrossTabEvent) {
  switch (event.type) {
    case 'auth-change':
      if (event.action === 'logout') {
        Modal.confirm({
          title: '登录状态变更',
          content: '您已在其他页面退出登录，请重新登录。',
          okText: '重新登录',
          cancelButtonProps: { style: { display: 'none' } }, // 不允许关闭
          closable: false,
          maskClosable: false,
          onOk: () => window.location.href = '/login',
        });
      } else if (event.action === 'switch-user') {
        Modal.confirm({
          title: '登录账号已变更',
          content: '检测到您在其他页面切换了登录账号，当前页面需要刷新以保持一致。',
          okText: '刷新页面',
          cancelButtonProps: { style: { display: 'none' } },
          closable: false,
          maskClosable: false,
          onOk: () => window.location.reload(),
        });
      } else {
        // login（同用户换 token）— 静默更新快照，不弹框
      }
      break;

    case 'tenant-change':
      Modal.confirm({
        title: '租户已切换',
        content: `租户已切换为「${event.newTenantName || event.newTenantId}」，当前页面需要刷新以保持一致。`,
        okText: '刷新页面',
        cancelButtonProps: { style: { display: 'none' } },
        closable: false,
        maskClosable: false,
        onOk: () => window.location.reload(),
      });
      break;

    case 'store-change':
      Modal.confirm({
        title: '门店已切换',
        content: `门店已切换为「${event.newStoreName || event.newStoreId}」，当前页面需要刷新以保持一致。`,
        okText: '刷新页面',
        cancelButtonProps: { style: { display: 'none' } },
        closable: false,
        maskClosable: false,
        onOk: () => window.location.reload(),
      });
      break;
  }
}
```

### 第 4 步：Doctor 端集成 `apps/doctor/src/app.tsx`

Doctor 端没有 `rootContainer`，在文件顶层（模块初始化阶段）注册监听：

```typescript
import { initCrossTabSync, destroyCrossTabSync } from '@hospital/shared';

// 初始化跨 Tab 状态同步
initCrossTabSync((event) => {
  // doctor 端只关心 auth-change
  if (event.type === 'auth-change') {
    if (event.action === 'logout') {
      Modal.confirm({
        title: '登录状态变更',
        content: '您已在其他页面退出登录，请重新登录。',
        okText: '重新登录',
        cancelButtonProps: { style: { display: 'none' } },
        closable: false,
        maskClosable: false,
        onOk: () => window.location.href = '/login',
      });
    } else if (event.action === 'switch-user') {
      Modal.confirm({
        title: '登录账号已变更',
        content: '检测到您在其他页面切换了登录账号，当前页面需要刷新。',
        okText: '刷新页面',
        cancelButtonProps: { style: { display: 'none' } },
        closable: false,
        maskClosable: false,
        onOk: () => window.location.reload(),
      });
    }
  }
});
```

## 修改文件清单

| # | 文件 | 改动 |
|---|------|------|
| 1 | `packages/shared/src/utils/crossTabSync.ts` | **新建**。核心监听模块，约 120 行 |
| 2 | `packages/shared/src/utils/index.ts` | 添加一行导出 |
| 3 | `apps/admin/src/app.tsx` | rootContainer 中 initCrossTabSync + handleCrossTabEvent 函数 |
| 4 | `apps/doctor/src/app.tsx` | 模块顶层 initCrossTabSync + 处理函数 |

## 设计要点

1. **同用户换 token 不弹框**：解析 JWT sub 字段对比用户 ID，一致则静默更新快照
2. **登出不可取消**：`cancelButtonProps: { display: 'none' }` + `closable: false`，强制用户操作
3. **租户/门店变更不可取消**：同上，数据一致性优先
4. **防抖**：利用已有 `handleTokenExpired` 的防抖模式，crossTabSync 内部同样需要防重复弹框（storage 事件短时间内可能连续触发多次）
5. **cleanup**：`initCrossTabSync` 返回 unsubscribe 函数，`destroyCrossTabSync` 在 SPA 销毁时调用

## 验证方式

1. 打开两个 Tab 都登录用户 A → Tab B 登出 → Tab A 应弹出"已退出登录"
2. 打开两个 Tab 登录用户 A → Tab B 登录用户 B → Tab A 应弹出"账号已变更"
3. 打开两个 Tab → Tab B 切换租户 → Tab A 应弹出"租户已切换"
4. 打开两个 Tab → Tab B 切换门店 → Tab A 应弹出"门店已切换"
5. 同用户重新登录（token 刷新）→ Tab A 不应弹框
