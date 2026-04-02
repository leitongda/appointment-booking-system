# Token 黑名单多租户架构审查

**日期**: 2026-04-02
**审查人**: 后端架构师
**项目**: SaaS 多租户医院预约挂号系统

---

## 1. 现状分析

### 1.1 Token payload 包含哪些字段？

**结论**: Token payload 包含 `tenant_id` 字段（对于有租户的管理员）

**代码证据**:

`apps/server/app/modules/admin/router_auth_login.py:110-116`:
```python
# 创建 JWT Token，包含租户信息
token_data = {"sub": admin.id, "type": "admin"}
if admin.tenant_id:
    token_data["tenant_id"] = admin.tenant_id

access_token = create_access_token(data=token_data)
```

**说明**:
- 超管（SUPER_ADMIN）的 `admin.tenant_id` 为 `NULL`，Token 中**不含** `tenant_id` 字段
- 租户管理员的 Token 中包含 `tenant_id` 字段

---

### 1.2 超管 logout 时的黑名单 key 是什么？

**结论**: 超管 logout 时生成的黑名单 key 是 `token:blacklist:{hash}`（不含租户前缀）

**代码证据**:

`apps/server/app/core/redis.py:590-605`:
```python
@staticmethod
def _build_token_blacklist_key(token_hash: str, tenant_id: Optional[str] = None) -> str:
    """构建 Token 黑名单的 Redis 键（支持多租户隔离）

    Returns:
        包含租户维度的键，格式: token:blacklist:{tenant_id}:{token_hash}
        如果没有租户上下文（平台管理员），则返回: token:blacklist:{token_hash}
    """
    effective_tenant_id = tenant_id or get_current_tenant_id()
    if effective_tenant_id:
        return f"{RedisCache.PREFIX_TOKEN_BLACKLIST}{effective_tenant_id}:{token_hash}"
    return f"{RedisCache.PREFIX_TOKEN_BLACKLIST}{token_hash}"
```

`apps/server/app/modules/admin/router_auth_token.py:54-93`:
```python
@router.post("/logout", summary="退出登录")
async def admin_logout(...):
    admin_tenant_id = current_admin.get("tenant_id")
    token_hash = __import__("hashlib").sha256(token.encode()).hexdigest()[:32]
    # 传递 tenant_id 实现多租户会话隔离
    session = await RedisCache.get_admin_session(admin_id, tenant_id=admin_tenant_id)
    # ...
    if ttl > 0:
        # 传递 tenant_id 实现多租户 Token 黑名单隔离
        await RedisCache.add_token_to_blacklist(token_hash, ttl, tenant_id=admin_tenant_id)
```

**说明**:
- 超管的 `admin_tenant_id` 为 `None`，生成的黑名单 key = `token:blacklist:{hash}`
- 租户管理员的黑名单 key = `token:blacklist:{tenant_id}:{hash}`

---

### 1.3 超管切换租户后 token 是否变化？

**结论**: **Token 不会变化**，但数据库中 `admin.tenant_id` 会被更新。

**代码证据**:

`apps/server/app/modules/admin/router_auth_token.py:147-187`:
```python
@router.put("/me/current-tenant", summary="切换当前租户")
async def switch_current_tenant(...):
    # 权限校验：仅平台管理员可切换租户
    if not current_admin.get("is_platform_admin"):
        raise HTTPException(status_code=status.HTTP_403_FORAUTHORIZED, detail="此操作仅限平台管理员")

    # 更新管理员的租户关联
    admin.tenant_id = target_tenant_id
    await db.commit()
    # 注意：这里没有刷新 Token！
```

**说明**:
1. 超管登录时 Token 不含 `tenant_id`（因为 `admin.tenant_id` 为 NULL）
2. 切换租户后，数据库 `admin.tenant_id` 被更新为新的租户 ID
3. **但 Token 本身不会刷新**，客户端继续使用同一个 Token
4. 下次请求时，`get_current_admin` 会从数据库重新加载 admin，获取新的 `tenant_id`

---

### 1.4 多 Tab 场景分析

**场景**: 超管在 Tab A 操作租户 X、Tab B 操作租户 Y，Tab A logout

**结论**: **Tab B 也会被拦截（这是 BUG）**

**代码证据**:

`apps/server/app/common/deps.py:223-227`:
```python
# 检查 Token 是否在黑名单中（优先使用 payload 中的 tenant_id，确保多租户隔离）
token_hash = hashlib.sha256(token.encode()).hexdigest()[:32]
token_tenant_id = payload.get("tenant_id")  # 超管的 Token 这里是 None
if await RedisCache.is_token_blacklisted(token_hash, tenant_id=token_tenant_id):
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="登录已失效，请重新登录")
```

**执行流程**:
1. 超管在 Tab A 切换到租户 X，`admin.tenant_id` = X
2. 超管在 Tab B 切换到租户 Y，`admin.tenant_id` = Y（数据库已更新）
3. Tab A logout 时，生成黑名单 key = `token:blacklist:{hash}`（因为 `token_tenant_id` = None）
4. Tab B 发起请求，检查黑名单时使用 `tenant_id=None`，检查 key = `token:blacklist:{hash}`
5. **发现 Token 已在黑名单，Tab B 被拦截**

**根本原因**:
- 超管的 Token 不含 `tenant_id`
- 黑名单 key 也不含租户前缀
- 所有 Tab 共用同一个 Token，logout 会影响所有 Tab

---

### 1.5 超管会话隔离机制分析

**会话 key 格式**:
- 超管: `session:admin:{admin_id}`
- 租户管理员: `session:admin:{tenant_id}:{admin_id}`

**代码证据**:

`apps/server/app/core/redis.py:479-494`:
```python
@staticmethod
def _build_admin_session_key(admin_id: str, tenant_id: Optional[str] = None) -> str:
    """构建管理员会话的 Redis 键（支持多租户隔离）

    Returns:
        包含租户维度的键，格式: session:admin:{tenant_id}:{admin_id}
        如果没有租户上下文（平台管理员），则返回: session:admin:{admin_id}
    """
    effective_tenant_id = tenant_id or get_current_tenant_id()
    if effective_tenant_id:
        return f"{RedisCache.PREFIX_ADMIN_SESSION}{effective_tenant_id}:{admin_id}"
    return f"{RedisCache.PREFIX_ADMIN_SESSION}{admin_id}"
```

**切换租户时的行为**:
- 切换租户会更新数据库 `admin.tenant_id`
- 但**不会创建新的会话记录**
- 下次登录时，会使用新的 `tenant_id` 创建会话

**当前设计的局限性**:
- 同一个超管在不同租户切换时，只有一个会话记录
- 无法区分超管在哪个租户上下文中登录

---

## 2. 风险矩阵

| 场景 | 风险等级 | 影响 | 触发条件 |
|------|---------|------|---------|
| 超管多 Tab logout | **高** | 所有 Tab 同时失效，用户体验差 | 超管在多 Tab 操作不同租户 |
| 超管切换租户后 Token 不变 | **中** | Token payload 与数据库不一致 | 切换租户后继续使用旧 Token |
| 超管 Token 不含 tenant_id | **低** | 审计日志难以追溯原始租户 | 超管操作时的审计 |
| 租户管理员多 Tab logout | **无** | 正常隔离，每个租户独立 Token | 租户管理员（含 tenant_id 的 Token） |

---

## 3. 推荐方案

### 方案 A: 为超管生成带租户标识的 Token（推荐）

**思路**: 超管切换租户后，返回新的 Token（含 `tenant_id`）

**实现**:
1. 修改 `/me/current-tenant` 接口，切换租户后刷新 Token
2. 新 Token 包含 `tenant_id` 字段
3. 前端收到新 Token 后，更新本地存储

**优点**:
- 每个 Tab 可以有独立的 Token
- logout 只影响当前租户上下文的 Tab
- Token payload 与数据库一致

**缺点**:
- 需要前端配合更新 Token
- 旧 Token 仍可用直到过期（需要加入旧 Token 黑名单）

**成本估算**: 2-3 小时

### 方案 B: 保持现状，前端处理多 Tab 提示（快速）

**思路**: 在前端检测到 401 时，提示用户"登录已失效，请重新登录"

**优点**:
- 无需后端改动
- 实现简单

**缺点**:
- 用户体验不佳
- 无法区分是否因为其他 Tab logout 导致

**成本估算**: 0.5 小时（前端）

### 方案 C: 引入会话 ID 机制（长期）

**思路**: 每次登录/切换租户生成新的 session_id，Token 和黑名单都基于 session_id

**优点**:
- 彻底解决多 Tab 问题
- 支持更细粒度的会话管理

**缺点**:
- 需要修改 Token 结构
- 需要数据库 schema 变更

**成本估算**: 1-2 天

---

## 4. 结论

### 4.1 当前设计是否可以接受？

**部分可以接受**，但存在以下问题：

1. **租户管理员**: 设计合理，`tenant_id` 包含在 Token 中，黑名单隔离正确
2. **超管**: 存在多 Tab logout 互相影响的问题，需要优化

### 4.2 是否需要立即修改？

**建议**: **不是紧急问题，但应该在中期优化**

**理由**:
- 超管数量通常很少，多 Tab 操作场景不常见
- 租户管理员（大多数用户）不受影响
- 影响的是用户体验，不是安全性问题

**优先级**: P2（中期优化）

### 4.3 临时缓解措施

1. 在前端添加 401 处理，提示用户重新登录
2. 文档说明超管避免在多 Tab 同时操作不同租户

---

## 5. 附录：代码引用索引

| 文件 | 行号 | 说明 |
|------|-----|------|
| `apps/server/app/modules/admin/router_auth_login.py` | 110-116 | Token 创建，包含 tenant_id |
| `apps/server/app/modules/admin/router_auth_token.py` | 54-93 | Logout 实现，黑名单添加 |
| `apps/server/app/modules/admin/router_auth_token.py` | 147-187 | 切换租户实现 |
| `apps/server/app/common/deps.py` | 223-227 | 黑名单检查 |
| `apps/server/app/core/redis.py` | 590-605 | 黑名单 key 构建 |
| `apps/server/app/core/redis.py` | 479-494 | 会话 key 构建 |
