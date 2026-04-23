> 状态说明（2026-04-16）：
> 本 change 与已归档的 `add-schedule-rule-enhancements` 功能重复。
> 该任务清单保留为历史记录，不再作为当前实现依据，也不应继续勾选执行。
> 如需继续演进排班规则能力，请基于现状创建新的 change，而不是恢复本任务清单。

## 1. 后端实现

### 1.1 数据库模型
- [ ] 1.1.1 创建 `schedule_generation_history` 表（记录生成历史）
  - id, template_ids, start_date, end_date, generated_count, operation_type, operator_id, operator_name, created_at

### 1.2 API 接口
- [ ] 1.2.1 新增 `POST /schedule-templates/batch-delete` - 批量删除规则生成的排班
- [ ] 1.2.2 新增 `POST /schedule-templates/batch-suspend` - 批量停诊规则生成的排班
- [ ] 1.2.3 新增 `GET /schedule-templates/check-conflict` - 检查生成冲突
- [ ] 1.2.4 修改 `POST /schedule-templates/generate` - 支持覆盖模式，记录历史
- [ ] 1.2.5 新增 `GET /schedule-templates/generation-history` - 获取生成历史列表

### 1.3 数据库迁移
- [ ] 1.3.1 创建 Alembic 迁移脚本

## 2. 前端 API 封装

- [ ] 2.1 在 `packages/api/src/modules/schedule-template.ts` 中添加新接口
  - batchDeleteSchedules
  - batchSuspendSchedules
  - checkGenerateConflict
  - getGenerationHistory

## 3. 前端页面实现

### 3.1 排班规则页面 (`apps/admin/src/pages/schedule/rule/index.tsx`)
- [ ] 3.1.1 添加"一键删除"按钮和弹窗
- [ ] 3.1.2 添加"一键停诊"按钮和弹窗
- [ ] 3.1.3 修改生成排班逻辑，增加冲突检测和确认
- [ ] 3.1.4 添加"生成历史"按钮和弹窗/抽屉

### 3.2 排班列表页面 (`apps/admin/src/pages/schedule/list.tsx`)
- [ ] 3.2.1 添加日期范围搜索条件

## 4. 测试验证

- [ ] 4.1 测试一键删除功能
- [ ] 4.2 测试一键停诊功能
- [ ] 4.3 测试冲突检测和覆盖生成
- [ ] 4.4 测试生成历史记录
- [ ] 4.5 测试日期范围搜索
