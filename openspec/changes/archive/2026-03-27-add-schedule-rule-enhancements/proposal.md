# Change: 排班规则功能增强

## Why
当前排班规则模块缺少以下关键功能：
1. 无法对已生成的排班进行批量管理（一键删除、一键停诊）
2. 重复生成排班时没有提醒确认机制，可能导致意外覆盖
3. 缺少生成历史记录，无法追溯操作
4. 排班列表缺少日期范围搜索功能

## What Changes

### 1. 排班规则页面新增操作功能
- 添加"一键删除排班"按钮，删除该规则生成的所有排班
- 添加"一键停诊"按钮，将该规则生成的所有排班标记为停诊状态
- 生成排班时增加确认弹窗，提示是否已存在生成的排班

### 2. 重复生成排班确认机制
- 生成排班前检查规则是否已经生成过排班
- 如果存在已生成的排班，弹出确认对话框
- 用户确认后覆盖原有规则生成的排班

### 3. 生成排班历史记录
- 新增数据表 `schedule_generation_logs` 记录生成历史
- 记录操作人、操作时间、生成/删除/停诊的记录数等
- 在排班规则页面添加"查看历史"功能

### 4. 排班列表日期范围搜索
- 添加日期范围选择器
- 支持按开始日期和结束日期筛选排班

## Impact
- 新增表: `schedule_generation_logs`
- 后端 API:
  - `POST /schedule-templates/{id}/batch-delete` - 批量删除排班
  - `POST /schedule-templates/{id}/batch-suspend` - 批量停诊
  - `GET /schedule-templates/{id}/check-generated` - 检查是否已生成
  - `GET /schedule-templates/{id}/logs` - 获取生成历史
- 前端页面:
  - `apps/admin/src/pages/schedule/rule/index.tsx` - 规则列表页
  - `apps/admin/src/pages/schedule/list.tsx` - 排班列表页

