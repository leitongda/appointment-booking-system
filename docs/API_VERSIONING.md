# API 版本控制与废弃机制

## 版本策略

### 版本号格式

API 使用 URL 路径版本控制：`/api/v1/...`、`/api/v2/...`。

当前版本：**v1**（配置在 `settings.API_VERSION`）。

### 何时创建 v2

当满足以下任一条件时，应创建新的主版本（v2）：

1. **破坏性变更**：无法保持向后兼容的接口变更（删除必填字段、改变响应结构、修改语义）
2. **大规模重构**：多个模块需要统一调整接口契约
3. **认证体系变更**：切换认证方案（如从 JWT 切换到 OAuth2）

**不需要创建新版本的变更**：

- 新增可选字段
- 新增端点
- 新增响应字段
- 修复 bug（行为修正）

### 版本共存规则

- 新版本发布后，旧版本至少维护 6 个月
- 过渡期内两个版本同时可用
- 过渡期结束后，旧版本端点标记为废弃（deprecated）
- 废弃后保留 3 个月，之后移除

## 废弃机制

### 标记端点废弃

在 `apps/server/app/api/v1/__init__.py` 的 `ROUTER_REGISTRATIONS` 中，为废弃模块设置 `deprecated=True` 和 `sunset_date`：

```python
RouterRegistration(
    module="app.modules.old_feature.router",
    prefix="/old-feature",
    tags=["旧功能"],
    deprecated=True,
    sunset_date="2025-12-31",
)
```

### 废弃端点的响应头

当请求匹配废弃端点时，`DeprecationMiddleware` 自动添加以下响应头：

| 响应头 | 值 | 说明 |
|--------|-----|------|
| `Deprecation` | `true` | 标记端点已废弃 |
| `Sunset` | `2025-12-31` | 废弃日期（ISO 8601） |
| `X-API-Deprecated-Version` | `v1` | 被废弃的 API 版本 |
| `X-API-Replacement` | `/api/v2/xxx` | 可选的替代路径 |

### 中间件配置

`DeprecationMiddleware` 在 `_configure_middlewares()` 中注册，默认不配置任何废弃端点。

要激活废弃检测，需要传入端点列表：

```python
from app.middleware.deprecation import DeprecationMiddleware, DeprecatedEndpoint

deprecation_endpoints = [
    DeprecatedEndpoint(
        path_prefix="/api/v1/old-feature",
        sunset_date="2025-12-31",
        deprecated_version="v1",
        replacement="/api/v2/new-feature",
    ),
]

app.add_middleware(DeprecationMiddleware, deprecated_endpoints=deprecation_endpoints)
```

## 客户端迁移指南

### 检测废弃端点

客户端应检查响应头中的 `Deprecation: true`，并在 `console` 中输出警告：

```typescript
// packages/api 中可添加拦截器
if (response.headers.get('Deprecation') === 'true') {
  const sunset = response.headers.get('Sunset');
  const replacement = response.headers.get('X-API-Replacement');
  console.warn(
    `[API Deprecation] 端点已废弃，Sunset: ${sunset}` +
    (replacement ? `，替代: ${replacement}` : '')
  );
}
```

### 迁移步骤

1. **识别依赖**：搜索项目中所有调用废弃端点的代码
2. **确认替代**：查看 `X-API-Replacement` 响应头或 API 文档
3. **逐步替换**：先在测试环境验证新端点，再切换生产环境
4. **移除旧代码**：确认迁移完成后清理旧端点调用

### 时间线

| 阶段 | 时长 | 说明 |
|------|------|------|
| 发布新版本 | - | 新端点可用 |
| 共存期 | 6 个月 | 新旧版本同时可用 |
| 废弃期 | 3 个月 | 旧端点返回 `Deprecation` 头 |
| 移除 | - | 旧端点从路由中删除 |

## 路由结构

废弃端点和正常端点注册在同一 API 前缀（`/api/v1`）下，但在路由层面分离：

```
/api/v1/
  ├── (正常端点) main_router 包含的模块
  └── (废弃端点) deprecated_router 包含的模块
```

两个路由器都挂载到同一个前缀下，客户端无需区分。废弃信息通过响应头传递。

## 现有端点标记废弃示例

假设要废弃 `/auth` 模块：

```python
# apps/server/app/api/v1/__init__.py
RouterRegistration("app.modules.auth.router", "/auth", ["认证"],
                   deprecated=True, sunset_date="2025-12-31"),
```

同时在 `_configure_middlewares()` 中配置中间件：

```python
app.add_middleware(
    DeprecationMiddleware,
    deprecated_endpoints=[
        DeprecatedEndpoint(
            path_prefix=f"{settings.API_V1_STR}/auth",
            sunset_date="2025-12-31",
            deprecated_version="v1",
        ),
    ],
)
```

这样所有 `/api/v1/auth/*` 的请求都会在响应头中包含废弃信息。
