# Change: 重构 Admin 端权限分类模型与角色分配交互

## Why
当前系统权限虽然已经具备 RBAC 基础能力，但权限元数据仍停留在 `menu/button` 两类，Admin 端“分配权限”页面也主要是原始树形勾选。这导致角色配置时存在三个明显问题：

- **控制类型表达不足**：很多权限实际控制的是页面入口、页内 Tab、按钮操作、接口能力或数据查看范围，但系统仅以 `menu/button` 展示，管理员难以理解“授予后到底能做什么”
- **交互认知成本高**：当前页面缺少搜索、类型筛选、模块快速勾选、风险提示与已选摘要，角色配置需要逐层展开树逐个判断
- **权限码语义和管理语义脱节**：同一权限码既用于前端显示控制，也用于后端接口拦截；现有分类对研发有用，但对配置角色的人不够友好

## What Changes
- 为 Admin 端权限分配建立新的**展示分类模型**，在不打破现有权限码与鉴权逻辑的前提下，将权限按“业务模块 + 控制类型”双维组织
- 在角色分配页中新增至少 4 类控制类型：`页面`、`Tab/视图`、`按钮/操作`、`接口/数据能力`
- 将当前单一树形勾选页重构为“概览 + 筛选 + 分组分配 + 已选摘要”的高可读交互
- 为角色配置增加快速操作能力，例如：按模块全选、按类型批量选择、仅查看已选、搜索权限码/权限名
- 明确哪些分类在第一阶段只作为 Admin 展示层能力，哪些字段在后续阶段需要升级为后端权限元数据

## Design Principles
- **兼容优先**：第一阶段不要求重建权限码体系，也不要求立即修改所有后端接口校验
- **解释优先**：角色管理员首先要知道“这个权限影响什么”，其次才是权限树结构
- **低风险演进**：先增加 Admin 端展示分类与交互，再评估是否将 `controlType` 下沉为后端正式字段
- **操作可回溯**：保存前应让管理员清楚知道本次新增/移除了哪些类型和模块的权限

## Scope

### In Scope
- `apps/admin/src/pages/system/role-permissions.tsx` 的信息架构与交互重构
- 新增一层 Admin 端权限分类规则，将权限映射为页面 / Tab / 按钮 / 接口等控制类型
- 新增模块统计、类型筛选、搜索、批量选择、已选摘要、保存前确认等交互
- 梳理当前权限码的语义规则，形成统一的展示映射策略

### Out of Scope
- 第一阶段不强制修改后端 `Permission.type` 字段的数据库结构
- 第一阶段不要求改写所有现有权限初始化脚本中的 `type`
- 第一阶段不重构整套 `access.ts` 路由权限实现
- 第一阶段不改变后端 `require_permission(...)` 的拦截行为

## Impact
- Affected specs: `admin-permission-management` (new)
- Affected code:
  - `apps/admin/src/pages/system/role-permissions.tsx`
  - `apps/admin/src/pages/system/role-permissions.less`
  - `apps/admin/src/access.ts`（如需补充分类映射辅助）
  - `packages/api/src/modules/admin.ts`（如需补充权限展示 DTO）
  - `apps/server/app/modules/admin/service_permissions.py`（仅在进入第二阶段后端元数据升级时）
  - `apps/server/scripts/init_permissions.py`（仅在进入第二阶段后端元数据升级时）

## Rollout Strategy
1. **阶段 1：Admin 展示层重构**
   - 基于现有权限树和权限码规则，在前端推导新的控制类型
   - 完成角色分配页重构与交互优化
2. **阶段 2：后端元数据补齐（可选）**
   - 若团队确认新分类稳定，再考虑为 `Permission` 增加正式 `control_type` 或同类字段
   - 逐步将初始化脚本与权限管理 API 对齐

## Open Questions
- `接口/数据能力` 是否仅用于表示“列表/详情/导出/查看”等接口级权限，还是未来扩展为更明确的 API Scope
- 当前部分权限同时具备“页面入口 + 接口能力”双重语义时，展示层是否采用“主类型 + 辅助标签”
- 是否需要在保存前显示“与当前角色相比的权限变更 diff”
