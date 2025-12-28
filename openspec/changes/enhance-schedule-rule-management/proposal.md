# Change: 增强排班规则管理功能

## Why
当前排班规则设置页面功能较为基础，缺少对已生成排班的管理能力。用户无法追踪规则生成的历史记录，也无法批量删除或停诊由规则生成的排班。同时排班列表缺少日期范围筛选，不便于查找特定时间段的排班。

## What Changes
- 排班规则页面新增"一键删除"功能：删除由该规则生成的所有排班
- 排班规则页面新增"一键停诊"功能：将由该规则生成的所有排班设为停诊状态
- 规则重新生成时检测冲突：如果已生成过排班，弹窗提醒用户确认后覆盖
- 新增规则生成历史记录功能：记录操作人、操作时间、生成数量等信息
- 排班列表页面新增日期范围搜索条件

## Impact
- Affected specs: schedule-rule-management (新建)
- Affected code:
  - `apps/admin/src/pages/schedule/rule/index.tsx` - 规则列表页面
  - `apps/admin/src/pages/schedule/list.tsx` - 排班列表页面
  - `packages/api/src/modules/schedule-template.ts` - 排班模板 API
  - `packages/api/src/modules/schedule.ts` - 排班 API
  - `apps/server/app/` - 后端服务（新增历史记录表、相关接口）
