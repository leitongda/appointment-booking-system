# 修复: 登录页出现"登录已过期"弹框

## Context

用户在登录页看到了不该出现的"登录已过期"弹框。根因是 `getInitialState` 中的 `fetchUserInfo` 遇到 401 时，拦截器已经通过 `Modal.confirm`（命令式，渲染在独立 React root）弹了框，但 catch 块又执行 `history.push('/login')` 软导航。软导航不会销毁命令式 Modal，导致弹框在登录页仍然可见。

触发条件: 用户在任意受保护页面（如 `/dashboard`），token 过期后刷新页面（F5）或首次打开应用。

## 修改方案

### 1. `apps/admin/src/app.tsx` — getInitialState 中的 fetchUserInfo (行 323-331)

在 catch 中判断: 如果是 401（已被拦截器处理），跳过导航，因为拦截器的 Modal `onOk` 已经会 `window.location.href = '/login'` 硬跳转。

```typescript
const fetchUserInfo = async () => {
  try {
    const currentUser = await adminApi.getCurrentAdmin();
    return currentUser as API.CurrentUser;
  } catch (error: any) {
    // 401 已由响应拦截器处理（弹框 + 清 token），不再重复操作
    if (error?.isUnauthorized?.()) return undefined;
    removeToken();
    history.push(loginPath);
  }
  return undefined;
};
```

需要顶部增加 import: `import { ApiError } from '@hospital/api';`（用于类型判断）。但实际上 `error` 可能是 `ApiError` 实例，直接用 `error?.isUnauthorized?.()` 即可，不需要额外 import（鸭子类型判断）。

### 2. `apps/admin/src/pages/login/index.tsx` — handleLoginSuccess 中的 fetchUserInfo (行 75-84)

同样的模式，同样修复:

```typescript
const fetchUserInfo = async () => {
  try {
    const user = await adminApi.getCurrentAdmin();
    return user as any;
  } catch (error: any) {
    if (error?.isUnauthorized?.()) return undefined;
    removeToken();
    history.push('/login');
    return undefined;
  }
};
```

### 3. `apps/admin/src/utils/errorHandler.ts` — handleApiError 对 401 的处理 (行 100-105)

当前代码对 401 额外 `message.error` toast，与拦截器的 `Modal.confirm` 形成双重提示:

```typescript
if (error.isUnauthorized()) {
  messageApi.error(error.message || '登录已过期，请重新登录');
  return;
}
```

修复: 移除 401 的 toast，因为拦截器已经弹框处理了。

```typescript
if (error.isUnauthorized()) {
  return; // 401 已由响应拦截器统一处理
}
```

## 修改文件清单

| 文件 | 改动 |
|---|---|
| `apps/admin/src/app.tsx:323-331` | fetchUserInfo catch 中 401 跳过导航 |
| `apps/admin/src/pages/login/index.tsx:75-84` | fetchUserInfo catch 中 401 跳过导航 |
| `apps/admin/src/utils/errorHandler.ts:100-105` | 移除 401 的多余 toast |

## 验证

1. 手动测试: 设置一个短过期 token → 刷新受保护页面 → 确认弹框出现但不会带到登录页
2. 手动测试: 在登录页 → 确认不会出现"登录已过期"弹框
3. 手动测试: 正常登录 → 正常使用 → token 自然过期 → 确认弹框正常，点击重新登录跳转正常
4. 跑后端测试确认无回归: `cd apps/server && pytest tests/ -v`
