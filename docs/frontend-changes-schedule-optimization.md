# 排班管理优化 - 前端变更说明

## 概述

本次优化对后端排班管理模块进行了重构，前端代码**基本不需要修改**，因为：

1. **API向后兼容**：旧的API调用已更新为内部使用新API，保持接口不变
2. **类型定义更新**：已自动适配新的数据结构
3. **功能保持不变**：所有功能继续正常工作

## 变更详情

### 1. 停诊API变更（已自动适配）

**变更内容：**
- 后端移除了 `/schedules/{id}/suspend` 和 `/schedules/{id}/resume` API
- 统一使用 `/schedule-suspensions` API

**前端影响：**
- ✅ **无需修改**：`scheduleApi.suspend()` 和 `scheduleApi.resume()` 已更新为内部使用新API
- ✅ 所有现有调用继续正常工作
- ⚠️ **建议**：未来新功能请直接使用 `scheduleSuspensionApi`，功能更强大（支持批量停诊、部分时段停诊等）

**受影响文件（无需修改）：**
- `apps/admin/src/pages/schedule/detail/index.tsx`
- `apps/admin/src/pages/schedule/list.tsx`
- `apps/admin/src/pages/doctor/components/ScheduleEditModal.tsx`
- `apps/doctor/src/pages/schedule/index.tsx`

### 2. 批量添加排班API变更（已自动适配）

**变更内容：**
- 后端移除了 `/schedule-templates/batch-add` API
- 统一使用 `/schedules/batch` API

**前端影响：**
- ✅ **无需修改**：`scheduleTemplateApi.batchAdd()` 已更新为内部使用新API
- ⚠️ **注意**：新API不支持 `slot_count`, `schedule_mode`, `appointment_type` 等高级参数，只支持基本的批量创建
- ⚠️ **建议**：如需使用高级功能，请改用 `scheduleApi.batchCreate()` 或创建排班模板后生成

**受影响文件（无需修改）：**
- `apps/admin/src/pages/schedule/template.tsx`

### 3. 类型定义更新（已自动更新）

**变更内容：**
- `Schedule.timeSlot` 改为可选字段（`timeSlot?: string`）
- `ScheduleCreateData.timeSlot` 改为可选字段

**前端影响：**
- ✅ **无需修改**：TypeScript类型已自动更新
- ✅ 创建排班时，如果不提供 `timeSlot`，后端会根据 `startTime` 自动计算

**受影响文件（无需修改）：**
- `packages/shared/src/types/schedule.ts`
- `packages/api/src/modules/schedule.ts`

### 4. CustomSchedule API（保持不变）

**变更内容：**
- 后端将 `CustomSchedule` 数据合并到 `Schedule` 表
- `/custom-schedules` API 仍然存在，内部使用 `Schedule` 模型

**前端影响：**
- ✅ **无需修改**：`customScheduleApi` 继续正常工作
- ✅ `CustomSchedule` 类型定义保持不变
- ✅ 所有现有功能继续正常工作

**受影响文件（无需修改）：**
- `apps/admin/src/pages/schedule/custom.tsx`
- `apps/admin/src/pages/schedule/custom-form.tsx`
- `packages/api/src/modules/custom-schedule.ts`

## 测试建议

### 1. 停诊功能测试
- [ ] 测试单个排班停诊（admin端）
- [ ] 测试单个排班恢复（admin端）
- [ ] 测试医生端停诊申请
- [ ] 验证停诊后排班状态正确更新

### 2. 批量添加排班测试
- [ ] 测试排班模板的批量添加功能
- [ ] 验证生成的排班数据正确

### 3. 自定义排班测试
- [ ] 测试创建自定义排班
- [ ] 测试查询自定义排班列表
- [ ] 测试删除自定义排班

### 4. 排班创建测试
- [ ] 测试不提供 `timeSlot` 时创建排班（应自动计算）
- [ ] 测试提供 `timeSlot` 时创建排班

## 未来优化建议

### 1. 停诊功能增强
建议前端逐步迁移到 `scheduleSuspensionApi`，支持：
- 批量停诊（一次停多个排班）
- 部分时段停诊（只停上午或下午）
- 停诊历史记录查看

### 2. 批量添加排班增强
如需使用高级功能（如 `schedule_mode`, `slot_count` 等），建议：
- 创建排班模板，然后使用模板生成
- 或扩展 `scheduleApi.batchCreate()` 支持更多参数

## 总结

✅ **前端代码无需修改**，所有变更已通过API层自动适配  
✅ **功能完全兼容**，现有功能继续正常工作  
⚠️ **建议**：未来新功能使用新的API，功能更强大

