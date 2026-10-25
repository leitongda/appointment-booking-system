> 状态说明（2026-10-23 核对）：实现已于 2026-04-18 随提交 `572cc43c`
> （feat(admin): 租户状态拦截 + 暂停页 + 权限管理页重构）落地，
> 本文件长期未回填。今日按 `role-permissions.tsx` / `role-permissions.utils.ts` /
> `role-permissions.less` 逐项核对后勾选；未勾选项均为确实未做或需人工验证，
> 不是待办遗漏。

## 阶段 0：权限语义梳理

- [x] 0.1 盘点现有权限码与页面/接口使用关系（`docs/modules/permission-codes.md`，由 `apps/server/scripts/gen_permission_matrix.py` 静态生成、可再生；盘点发现 48 个目录外守卫码缺口，已在 permission.md「已知缺口」登记，待产品定名补目录）
- [x] 0.2 定义展示层控制类型映射规则（`role-permissions.utils.ts`：`ACTION_SEGMENTS` / `PermissionControlType` 推导）
- [x] 0.3 明确模块分组与类型标签文案（`CONTROL_TYPE_LABELS`：页面 / Tab·视图 / 按钮·操作 / 接口·数据）

## 阶段 1：Admin 端权限分配页重构

- [x] 1.1 提取权限分类与统计工具函数（`role-permissions.utils.ts`；注意：该 utils 尚无配套单测，与 4.3 一并补）
- [x] 1.2 将原始树形数据转换为“模块卡片 + 分组节点”展示结构（`permission-module-card` 逐模块渲染）
- [x] 1.3 增加顶部权限概览区
  - [x] 已选权限数（`已选权限 N / 总数` Statistic）
  - [x] 模块覆盖数（"覆盖 N 个业务模块"）
  - [x] 页面 / Tab / 按钮 / 接口类型分布（四张类型卡 + 当前结果计数）
- [x] 1.4 增加筛选与查找能力
  - [x] 关键词搜索（权限名 / 权限码）
  - [x] 控制类型筛选（`Tag.CheckableTag` 按控制类型多选）
  - [x] 仅看已选
  - [x] 展开 / 收起全部
- [x] 1.5 增加批量操作能力
  - [x] 模块全选 / 清空（2026-10-24 补：模块卡片标题右侧模块级全选/清空，随当前筛选结果生效）
  - [x] 按类型批量选择（类型筛选 + 全选当前结果组合达成；2026-10-24 再补一键「仅选页面级 / 仅选操作级」）
  - [x] 仅选择页面级 / 仅选择操作级（`handleSelectOnlyByTypes` + `codesByControlTypes`，重置为全树该类型权限码）
- [x] 1.6 增加已选摘要与保存提示
  - [x] 保存前展示本次选择概况（确认 Modal 内含新增/移除数量与影响说明）
  - [x] 明确高风险权限类型提示（`高风险` Tag + 保存确认文案）

## 阶段 2：样式与交互优化

- [x] 2.1 重做 `role-permissions.less`，形成信息密度更合理的双栏或卡片布局（模块卡 + 概览卡 + 摘要卡）
- [x] 2.2 为不同控制类型增加统一视觉标签（`summary-card-{page,tab,action,api}` 与类型 pill）
- [x] 2.3 优化树节点 hover、选中、批量操作反馈（less `:hover` 态 + 变更徽标）
- [x] 2.4 优化空状态、无搜索结果、加载态、保存态反馈（`Empty` / `Spin` / `saving` 态 + 离开确认）

## 阶段 3：验证

- [ ] 3.1 验证超级管理员以外角色的权限编辑流程（需人工 QA）
- [ ] 3.2 验证搜索、筛选、批量选择与实际保存结果一致（需人工 QA）
- [x] 3.3 验证保存后权限码提交格式未变化（静态核对：`adminApi.updateRolePermissions(id, checkedKeys)` 仍提交权限码数组）
- [x] 3.4 验证现有后端 `updateRolePermissions` 接口无需兼容性改造即可工作（静态核对：`PUT /roles/{role_id}/permissions` 契约未变，仅新增租户过滤参数）

## 阶段 4：后续演进（可选，不在首期强制）

- [x] 4.1 评估为后端 `Permission` 模型增加正式展示分类字段（2026-10 评估结论：`control_type` 列已存在且 `Permission` 模型已声明；前端 utils 以该字段优先、缺失时按码推断，暂无需再扩字段。相关：读端点已按 system:*:list 收口）
- [ ] 4.2 如后端升级分类字段，补充初始化脚本与 API 返回（现状满足，暂无升级项；保留待后续目录补 48 码时一并处理）
- [x] 4.3 为权限分类规则补充文档与测试（`role-permissions.utils.test.ts` 21 用例；`docs/modules/permission-codes.md` + permission.md 现行模型文档）
