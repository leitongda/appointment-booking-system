# 🔐 权限管理模块

> 2026-10-24 按现行实现重写（原版为早期 PRD，已过时）。
> 权限码与后端守卫/前端引用的逐码对照见 [permission-codes.md](./permission-codes.md)
> （由 `apps/server/scripts/gen_permission_matrix.py` 生成，可再生）。

## 一、模型总览

RBAC + 多租户双层控制：

```
Admin（管理员，属某租户或平台）
  └─ N:1 Role（角色，租户内唯一 code；平台角色 tenant_id=NULL）
        └─ permissions: JSON 数组（权限码，如 ["doctor:list", "system:user"]）

Permission（权限目录表，全平台共享，无租户维度）
  code / name / type(menu|button) / control_type(page|tab|action|api) / parent_code
```

要点：

- **权限目录是平台级的**：所有租户共用同一套权限码定义（种子见 `apps/server/scripts/init_permissions.py`）；
- **授权存储在 `Role.permissions` JSON 列**，模型里的 `role_permissions` 关联表是无读写的遗留结构（D20 待删，删前需全环境核对行数=0）；
- **角色按租户隔离**：`(tenant_id, code)` 复合唯一（迁移 p3a2）；租户管理员只能管理本租户角色；
- **提权防护**：租户角色禁止授予 `*` 通配权限；`SUPER_ADMIN` 角色权限不可修改；平台特权判定锚定平台级角色（`role.tenant_id IS NULL`），租户内自建 `code="SUPER_ADMIN"` 无效。

## 二、权限检查依赖（后端）

`apps/server/app/common/permission_deps.py`：

| 依赖 | 适用 | 语义 |
|---|---|---|
| `require_permission(*codes)` | Admin | 满足其一即过；支持 `*` 与 `prefix:*` 通配 |
| `require_all_permissions(*codes)` | Admin | 必须全部满足 |
| `require_account_permission(*codes)` | admin/doctor/user/operator 统一 | 按角色类型取权限集（doctor/user 为硬编码集，`role_permissions.py`） |

通配规则：`*` 匹配一切；`doctor:*` 匹配 `doctor:` 前缀全部。超级管理员天然全过。

**读端点收口（2026-10）**：`GET /admin/admins*` 挂 `("system:user:list", "system:user")`、`GET /admin/roles*` 挂 `("system:role:list", "system:role")`——OR 父码兼容存量授权。全量「路由 ↔ 守卫」约束由 `tests/architecture/test_admin_route_permission_matrix.py` 固化：新增无守卫的管理端点会直接测试失败。

## 三、数据权限（行级）

- **租户维度**：管理端经 `require_admin_tenant_anchor` 显式锚点（query > header/子域/路径），租户管理员恒为本租户，平台管理员须显式指定；
- **门店维度**：`get_store_filter` / `check_store_access`（绑定门店 + 当前门店）；`DataScopeFilter` 为预留结构，当前恒走 fallback（D20 处置中）；
- **功能维度**：`require_feature("online_payment" | "basic_statistics" | "export_data")` 受 `FEATURE_ENFORCEMENT_ENABLED` 总开关（默认 False）与租户 features 覆盖控制。

## 四、Admin 端权限分配页

`apps/admin/src/pages/system/role-permissions.tsx`（2026-04 重构，2026-10 补模块级批量）：

- 模块卡片 + 页面/Tab/操作/接口四类控制类型标签（`role-permissions.utils.ts` 推断，`controlType` 字段优先）；
- 顶部概览（已选数 / 模块覆盖数 / 四类分布）、关键词搜索、类型筛选、仅看已选；
- 批量：全选/清空当前结果、**模块级全选/清空**、**仅选页面级 / 仅选操作级**；
- 高风险权限（delete/refund/reset-password/permission/kick/status）标红，保存前确认弹窗含变更摘要。

## 五、已知缺口

1. **目录外守卫码 48 个**（审批流/联系人/兼职/低代码/积分/排班加额等模块）：后端守卫在用但权限目录（种子与库）均无这些码，非 `*` 角色无法获得授权——清单见 permission-codes.md 漂移段；补目录需产品定名与分组（进行中）。
2. `consultation_fees` 查询侧尚未按租户过滤（p3a8 只落了数据维度与写入锚点）。
3. doctor/user 角色权限为硬编码集，租户不可自定义。
