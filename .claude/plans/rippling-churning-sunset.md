# 订阅计划详情 Drawer

## Context

订阅计划列表页（`plans.tsx`）只有编辑和删除操作，无法查看计划详情。后端 `GET /tenants/plans/{plan_id}` 和前端 `tenantApi.getPlan(planId)` 已经存在，只需要加前端展示。

计划数据字段简单（名称/价格/限制数等），无需独立页面，用 Drawer 侧边抽屉即可。

## 方案：Drawer 侧边抽屉

### 修改文件

#### 1. `apps/admin/src/pages/tenant/plans.tsx`

- 引入 `Drawer`, `Descriptions`, `Tag`, `Spin` 等组件
- 新增 state: `detailId` (当前查看的计划 ID) / `detailData` / `detailLoading`
- 添加 `handleView(planId)` 函数：调用 `tenantApi.getPlan(planId)` 获取详情
- 在 `createOperationColumn` 中加入 `viewUrl` 配置（或使用 `moreActions` 添加"查看详情"菜单项）
- 渲染 `<Drawer>` 组件，内容为 `<Descriptions>` 展示所有字段：
  - 基本信息：计划编码、名称、描述、状态、是否默认、排序
  - 价格：月付价格、年付价格、货币单位
  - 资源限制：门店上限、管理员上限、医生上限、月预约上限、存储空间上限
  - 时间：创建时间、更新时间

#### 2. `apps/admin/config/routes.ts` — 无需修改（Drawer 不需要路由）

### 复用清单

- `tenantApi.getPlan(planId)` — `packages/api/src/modules/tenant.ts`
- `createOperationColumn` 的 `viewUrl` 参数 — `apps/admin/src/components/ListOperations/createOperationColumn.tsx`
- `useListPage` hook 的 `reload` — `apps/admin/src/hooks/useListPage.ts`
- `Descriptions` 组件 — Ant Design，租户详情页 `detail.tsx` 中已大量使用

### 验证

1. `pnpm dev:admin` 启动后进入 订阅计划列表
2. 操作列应出现"查看"按钮，点击后右侧滑出 Drawer
3. Drawer 展示计划完整信息，关闭后列表不受影响
4. 刷新页面正常，无控制台报错
