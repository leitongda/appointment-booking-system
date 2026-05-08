# 修复方案：双写同步前缺少 flush 导致新表数据丢失

## Context

双写过渡期中，`AccountSyncService` 通过 `db.get(OldModel, id)` 查旧表记录再同步到新表。但如果旧表的修改尚未 flush，查询会返回旧数据或 None，导致新表数据不完整或跳过。

实际影响已在 PostgreSQL 上验证：创建医生时 `db.add(doctor)` 后没 flush 就调 sync，导致 `accounts` / `account_doctors` 表无记录。

## 问题清单

### 模式
所有调用点都遵循同一模式：
```
修改旧表对象 → 调 AccountSyncService.sync_xxx() → db.commit()
```
应在 sync 调用前加 `await self.db.flush()` / `await db.flush()`。

### A. admin/service_admins.py（4 处）

| 行号 | 方法 | 当前状态 |
|------|------|----------|
| 316 | `update` | 修改 admin 字段后直接 sync，无 flush |
| 344 | `reset_password` | 修改 password_hash 后直接 sync，无 flush |
| 358 | `update_login_info` | 修改 last_login_at/ip 后直接 sync，无 flush |
| 382 | `delete` | 删除 admin 前无 flush（需确认是否先 commit） |

### B. users/service.py（5 处）

| 行号 | 方法 | 当前状态 |
|------|------|----------|
| 77 | `update_wechat_info` | 修改 user 字段后直接 sync，无 flush |
| 106 | `create` | `db.add(user)` 后直接 sync，无 flush；**且 User 缺少 tenant_id** |
| 126 | `update` | 修改 user 字段后直接 sync，无 flush |
| 157 | `change_password` | 修改 password_hash 后直接 sync，无 flush |
| 179 | `bind_phone` | 修改 phone 后直接 sync，无 flush |

### C. doctors/service_mutation.py（2 处）

| 行号 | 方法 | 当前状态 |
|------|------|----------|
| 88 | `create` | **已修复**（上一轮 commit） |
| 115 | `update` | 修改 doctor 字段后直接 sync，无 flush |
| 155 | `delete` (soft) | 修改 deleted_at/status 后直接 sync，无 flush |

### D. auth/router.py（4 处）

| 行号 | 方法 | 当前状态 |
|------|------|----------|
| 242 | `change_password` | 修改 password_hash 后直接 sync，无 flush |
| 365 | `forgot_password` | 修改 password_hash 后直接 sync，无 flush |
| 465 | `wechat_get_phone` | 修改 openid 后直接 sync，无 flush |
| 524 | `wechat_bind_phone` | 修改 openid 后直接 sync，无 flush |

## 修复步骤

### 1. admin/service_admins.py — 4 处加 flush

在每个 `await AccountSyncService.sync_admin_to_account(...)` 调用前加 `await self.db.flush()`：

- L316 `update`: 在 `set_update_audit` 后、sync 前加 flush
- L344 `reset_password`: 在 `password_hash = ...` 后、sync 前加 flush
- L358 `update_login_info`: 在 `last_login_ip = ip` 后、sync 前加 flush
- L382 `delete`: 在 `await self.db.delete(admin)` 后、sync 前加 flush（如存在）

### 2. users/service.py — 5 处加 flush + 1 处补 tenant_id

- L77 `update_wechat_info`: `set_update_audit` 后加 flush
- L106 `create`: `db.add(user)` 后加 flush；**User 构造函数加 `tenant_id=tenant_id`**
- L126 `update`: `set_update_audit` 后加 flush
- L157 `change_password`: `password_hash = ...` 后加 flush
- L179 `bind_phone`: `user.phone = phone` 后加 flush

`create` 方法需要从 `get_current_tenant_id()` 获取 tenant_id，与 doctors/service_mutation.py 保持一致。

### 3. doctors/service_mutation.py — 2 处加 flush

- L115 `update`: `set_update_audit` 后加 flush
- L155 `delete` (soft): `doctor.status = 0` 后加 flush

### 4. auth/router.py — 4 处加 flush

每个 `await AccountSyncService.sync_user_to_account(...)` 调用前加 `await db.flush()`：

- L242 `change_password`: `password_hash = ...` 后加 flush
- L365 `forgot_password`: `password_hash = ...` 后加 flush
- L465 `wechat_get_phone`: `user.openid = data.openid` 后加 flush
- L524 `wechat_bind_phone`: `user.openid = data.openid` 后加 flush

## 验证

- `python -m pytest tests/unit/ tests/integration/ -v --tb=short` 全量测试
- 在真实 PostgreSQL 上重复医生创建双写验证
- 可选：创建用户/管理员，验证新表同步
