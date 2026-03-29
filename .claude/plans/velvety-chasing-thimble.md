# 登录页排除 + 401 弹框不可取消

## Context

两个问题：
1. 登录过期弹框在登录页也会弹出（getInitialState 或拦截器在路由切换期间触发 401）
2. 401 弹框有"留在当前页"按钮，但 token 已被清除，留下看到的是僵尸页面，所有操作都会失败

## 改动方案

### 核心原则

- **登录页不弹框**：所有弹登录过期/身份变更弹框的地方，先判断当前路由是否为 `/login`，是则跳过弹框
- **401 弹框强制跳转**：取消"留在当前页"按钮和关闭按钮，只保留"重新登录"

### 改动清单

#### 1. `apps/admin/src/utils/request.ts` — 2 处 401 弹框

**第 107 行（ApiError 401）和第 165 行（原始 Axios 401）**：

- 加 `history.location.pathname !== '/login'` 判断
- 移除 `cancelText: '留在当前页'`、`closable: true` → `closable: false`
- 加 `cancelButtonProps: { style: { display: 'none' } }`
- `onOk` 改用 `window.location.href = '/login'` 而非 `history.push`（确保完全重置状态）

#### 2. `apps/admin/src/app.tsx` — 1 处 UmiJS 拦截器 401

**第 508 行**：

- 同样加登录页排除判断
- 同样移除"留在当前页"和关闭按钮

#### 3. `apps/admin/src/app.tsx` — handleCrossTabEvent

**第 154 行**：

- `auth-change` 的 `logout` 分支加登录页排除（在登录页不需要弹"已在其他页面退出"）
- `auth-change` 的 `switch-user` 分支同理

#### 4. `apps/doctor/src/app.tsx` — 2 处

- 401 UmiJS 拦截器（第 ~172 行）：加登录页排除，移除关闭按钮
- 跨 Tab sync（第 18 行）：加登录页排除

### 修改文件清单

| 文件 | 改动点 |
|------|--------|
| `apps/admin/src/utils/request.ts` | 2 处 401 弹框：加登录页排除 + 移除关闭/取消按钮 |
| `apps/admin/src/app.tsx` | 1 处 UmiJS 401 + handleCrossTabEvent：加登录页排除 |
| `apps/doctor/src/app.tsx` | 1 处 UmiJS 401 + 跨 Tab 回调：加登录页排除 |

### 统一弹框配置模板

401 登录过期弹框统一为：

```typescript
// 登录页不弹框
if (window.location.pathname === '/login') return;

Modal.confirm({
  title: '登录已过期',
  content: '您的登录已失效，请重新登录。',
  okText: '重新登录',
  cancelButtonProps: { style: { display: 'none' } },
  closable: false,
  maskClosable: false,
  onOk: () => { window.location.href = '/login'; },
});
```

## 验证

1. 在登录页，即使后端返回 401（如旧 token 残留），不应弹框
2. 非登录页 401 → 弹框只有一个"重新登录"按钮，不可关闭
3. 点击"重新登录" → 跳转到 /login 并完全刷新状态
