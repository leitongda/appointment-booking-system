# 登录重试 "1/3" 无限循环问题修复

## Context

用户在浏览器控制台看到 `[API Retry] 请求重试 (1/3): GET /admin/public-key` 反复出现。

**根因**：后端开发环境**没有配置** `RSA_PRIVATE_KEY`/`RSA_PUBLIC_KEY` 环境变量（`config.py:86-87` 默认为 `None`），导致 `uvicorn --reload` 每次重启都生成新密钥对。而前端 localStorage 缓存了旧公钥（有效期 24h），造成：

1. 前端用旧公钥加密密码 -> 后端新私钥解密失败 -> 400 "密码解密失败"
2. `admin.ts:login()` 捕获解密错误 -> `clearPublicKey()` + 递归调用 `login(data, true)`
3. 内部重试时调用 `getPublicKey()`（GET 请求）-> API 重试拦截器分配新 `_retryId`，count 从 0 开始
4. 如果公钥请求本身也失败（网络抖动/后端重启中），每次都从 `1/3` 开始重试
5. 用户多次点击登录 -> 每次都重复上述链路，看起来像无限循环

## 修复方案

### 修改 1: 后端 - 开发环境密钥对持久化到文件（核心修复）

**文件**: `apps/server/app/core/security.py` (第 41-69 行 `load_rsa_keys` 函数)

当环境变量未配置时，将密钥对缓存到本地文件，重启时优先从文件加载。

加载优先级：
1. 环境变量（生产环境）
2. 本地文件 `.keys/rsa.json`（开发环境，重启复用）
3. 首次生成并保存到文件

同时将 `.keys/` 添加到 `.gitignore`。

### 修改 2: 前端 - 公钥请求降低重试次数

**文件**: `packages/api/src/modules/admin.ts` (第 246 行 `getPublicKey` 函数)

`getPublicKey()` 在登录流程中被调用，其重试与登录层自身的解密错误重试叠加，导致用户看到反复的 `1/3`。降低到 `maxRetries: 1`（而非完全禁用），保留网络抖动的容错能力。

```typescript
const result = await request.get<PublicKeyResponse>(
  `${PREFIX}/public-key`,
  withRetry({ maxRetries: 1 })
);
```

## 涉及文件

| 文件 | 改动要点 |
|------|---------|
| `apps/server/app/core/security.py` | `load_rsa_keys` 增加文件缓存（环境变量 > 文件 > 生成） |
| `.gitignore` | 添加 `.keys/` |
| `packages/api/src/modules/admin.ts` | `getPublicKey` 加 `withRetry({ maxRetries: 1 })` |

## 验证

1. 删除 `.keys/rsa.json`（如果存在），启动后端确认文件自动生成
2. 重启后端，确认 `.keys/rsa.json` 内容不变（密钥对固定）
3. 前端登录，确认控制台不再出现 `[API Retry]` 日志
4. 清除 localStorage 中公钥缓存后登录，确认正常获取新公钥并成功
