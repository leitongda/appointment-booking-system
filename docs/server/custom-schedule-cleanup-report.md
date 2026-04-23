# CustomSchedule 废弃清理影响范围报告

## 背景

`CustomSchedule` 模型已在 Alembic 迁移 `021_merge_custom_schedules` 中被废弃，数据已合并到 `schedules` 表（通过 `template_id IS NULL` 区分原自定义排班）。

**模型状态**: `apps/server/app/models/custom_schedule.py` 标记为 `[已废弃]`，但文件仍保留。

## 引用情况分析

### 后端 (`apps/server/`)

#### 1. 模型定义
- ✅ **已废弃**: `app/models/custom_schedule.py` - 包含废弃注释

#### 2. Schema 定义
- ⚠️ **仍在使用**: `app/schemas/custom_schedule.py` - 定义了 `CustomScheduleCreate`、`CustomScheduleResponse` 等 schema

#### 3. 路由和服务
- ⚠️ **仍在使用**: `app/modules/custom_schedules/router.py` - 提供 4 个端点：
  - `GET /custom-schedules` - 获取列表（查询 `schedules` 表中 `template_id IS NULL`）
  - `GET /custom-schedules/effective` - 获取生效排班
  - `POST /custom-schedules` - 创建排班（插入到 `schedules` 表）
  - `DELETE /custom-schedules/{id}` - 删除排班

**重要**: 此路由**不再**使用 `CustomSchedule` 模型，而是查询 `Schedule` 模型并筛选 `template_id IS NULL`。

#### 4. API 注册
- ⚠️ **仍在使用**: `app/api/v1/__init__.py` - 包含 `custom_schedules_router`

### 前端 API 层 (`packages/api/`)

- ⚠️ **仍在使用**: `packages/api/src/modules/custom-schedule.ts` - 导出 `customScheduleApi`
- ⚠️ **仍在导出**: `packages/api/src/index.ts:64` - `export { customScheduleApi }`
- ⚠️ **仍在使用**: `packages/shared/src/types/schedule.ts` - 导出 `CustomSchedule` 类型

### 管理端前端 (`apps/admin/`)

- ⚠️ **仍在使用**: `apps/admin/src/pages/schedule/custom.tsx` - 自定义排班列表页
- ⚠️ **仍在使用**: `apps/admin/src/pages/schedule/custom-form.tsx` - 自定义排班创建表单

### 数据库迁移

- ✅ **已完成**: `migrations/versions/021_merge_custom_schedules.py` - 数据合并迁移
- ✅ **已完成**: `migrations/versions/2fc10ef02888_remove_weekday_column_from_schedule_.py` - 清理旧列

## 清理影响范围

### 可安全删除（低风险）

1. **模型文件**: `apps/server/app/models/custom_schedule.py`
   - 后端代码已不再直接使用此模型
   - 数据库表已废弃（数据已迁移）

2. **数据库表**: `custom_schedules` 表
   - 数据已合并到 `schedules` 表
   - 可在确认后 DROP

### 需要重构（中风险）

1. **Schema 重命名**:
   - `app/schemas/custom_schedule.py` 中的 schema 应合并到 `app/schemas/schedule.py`
   - 或重命名为 `schedule_custom.py` 以反映其实际操作 `Schedule` 模型

2. **路由端点**:
   - `app/modules/custom_schedules/router.py` 可以合并到 `app/modules/schedules/router.py`
   - 端点路径保持 `/custom-schedules` 不变以维持前端兼容性

3. **前端 API**:
   - `packages/api/src/modules/custom-schedule.ts` 可以合并到 `packages/api/src/modules/schedule.ts`
   - 保持导出名称 `customScheduleApi` 不变

### 需要同步修改（高风险）

1. **管理端页面**:
   - `apps/admin/src/pages/schedule/custom.tsx`
   - `apps/admin/src/pages/schedule/custom-form.tsx`
   - 这些页面使用的 API 调用 (`customScheduleApi`) 需要保持可用

2. **类型定义**:
   - `packages/shared/src/types/schedule.ts` 中的 `CustomSchedule` 接口被多个页面引用
   - 清理时需要同步更新引用

## 清理建议方案

### 方案 A：渐进式清理（推荐）

**阶段 1**：后端重构
1. 将 `app/schemas/custom_schedule.py` 合并到 `app/schemas/schedule.py`
2. 将 `app/modules/custom_schedules/router.py` 合并到 `app/modules/schedules/router.py`
3. 删除 `app/models/custom_schedule.py`
4. 运行测试验证

**阶段 2**：前端重构
1. 将 `packages/api/src/modules/custom-schedule.ts` 合并到 `packages/api/src/modules/schedule.ts`
2. 更新 `packages/api/src/index.ts` 导出
3. 验证管理端页面仍能正常工作

**阶段 3**：数据库清理
1. 确认所有功能正常后，执行 `DROP TABLE custom_schedules CASCADE;`
2. 删除相关迁移文件中的表创建代码

### 方案 B：保持现状

**理由**:
- 当前代码虽然有多余的文件，但功能正常
- "自定义排班" 作为业务概念仍然存在（`template_id IS NULL` 的排班）
- 清理工作量 vs 收益不成正比

**建议**: 如果选择此方案，至少更新文件顶部的注释，明确说明架构设计意图。

## service_admins.py 未提交改动分析

```diff
+from app.models.tenant import Tenant
...
-selectinload(Admin.tenant),
+selectinload(Admin.tenant).selectinload(Tenant.subscription_plan),
```

### 改动意图

在加载 Admin 用户时，同时预加载（eager load）其所属租户的订阅计划信息。

### 合理性评估

✅ **合理，建议提交**

1. **性能优化**: 避免 N+1 查询问题，当需要访问 `admin.tenant.subscription_plan` 时不会触发额外查询
2. **业务场景**: 订阅计划信息常用于前端展示（如"专业版"/"企业版"标识）或权限判断
3. **一致性**: 所有查询方法都已统一添加此预加载

### 建议

提交前添加注释说明加载意图：

```python
selectinload(Admin.tenant).selectinload(Tenant.subscription_plan),  # 预加载订阅计划用于前端展示
```

## 总结

| 项目 | 状态 | 建议 |
|------|------|------|
| `CustomSchedule` 模型 | 已废弃，可删除 | ✅ 删除文件 |
| `custom_schedule` schema | 仍在使用 | ⚠️ 合并到 `schedule.py` |
| `custom_schedules` router | 仍在使用 | ⚠️ 合并到 `schedules/router.py` |
| 前端 API `customScheduleApi` | 仍在使用 | ⚠️ 合并到 `schedule.ts` |
| 管理端页面 | 仍在使用 | ⚠️ 保持可用 |
| `service_admins.py` 改动 | 合理 | ✅ 提交 |
