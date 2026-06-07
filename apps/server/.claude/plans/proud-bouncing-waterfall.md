# P3: Schedule Module Technical Debt Cleanup

## Context

P0/P1/P2 全部完成（1422 passed, 0 failed）。剩余技术债不影响正确性/安全性，但影响可维护性和一致性。按依赖关系分组，常量层最先（其他任务依赖它），类型安全最后（纯代码质量）。

## Execution Order

### Phase 1: 常量统一（基础层，其他任务依赖）

#### 1.1 时段边界统一
- **问题**: 4 处定义冲突（afternoon end 17:30 vs 18:00, morning start 06:00 vs 08:00）
- **权威来源**: `packages/shared/src/constants/schedule.ts:19-23` 的 `TIME_SLOT_RANGE`
- **修改**:
  - `packages/shared/src/constants/schedule.ts:192-195` — `DEFAULT_TIME_PERIODS` 对齐 `TIME_SLOT_RANGE` 的时间边界
  - `apps/admin/src/pages/doctor/components/ScheduleEditModal.tsx:36-40` — 删除本地定义，import from `@hospital/shared`
  - `apps/admin/src/pages/schedule/calendar/components/WeekView.tsx:57-61` — `inferTimeSlotType` 对齐 `TIME_SLOT_RANGE`（afternoon end 改为 `< 18` 即 18:00）
- **影响**: `@hospital/shared` 已导出 `TIME_SLOT_RANGE`，下游直接 import

#### 1.2 WINDOW_COLORS 统一
- **问题**: HorizontalTimeline 和 GanttTimeline 各自定义 WINDOW_COLORS，颜色值不同（antd vs tailwind）
- **修改**:
  - `apps/admin/src/themes/scheduleColors.ts` — 新增 `WINDOW_ACTION_COLORS` (BOOK/CHECKIN/CANCEL/HOLD_RELEASE)
  - `apps/admin/src/components/rule-set-visualization/HorizontalTimeline.tsx:47-80` — 删除本地 WINDOW_COLORS，import from scheduleColors
  - `apps/admin/src/components/rule-set-visualization/GanttTimeline.tsx:35-70` — 同上
- **权威值**: 使用 antd 色值（#1890ff, #52c41a, #fa8c16, #722ed1）保持与全局主题一致

#### 1.3 TIME_SLOT_LABELS 去重
- **问题**: 7 个文件各自定义 `morning->上午, afternoon->下午, evening->晚上`
- **已有**: `packages/shared/src/constants/schedule.ts` 已导出 `TIME_SLOT_LABELS`
- **修改**: 7 个文件删除本地定义，改为 import from `@hospital/shared`:
  - `calendar/components/CreateAppointmentModal.tsx:16`
  - `calendar/components/MonthView.tsx:15`
  - `calendar/components/DragConfirmModal.tsx:26`
  - `calendar/components/DayDetailDrawer.tsx:24`
  - `calendar/components/ExtraQuotaModal.tsx:20`
  - `doctor/components/ScheduleEditModal.tsx:30`
  - `doctor/components/ScheduleCalendar.tsx:18`

### Phase 2: 共享 Hooks

#### 2.1 创建 useDepartments + useDoctors
- **问题**: 10 文件重复 `loadDepartments`，12 文件重复 `loadDoctors/loadDoctorsByDept/loadDoctorsByStore`
- **已有全局模型**: `apps/admin/src/models/globalData.ts` 有 `loadDepartments` 但 schedule 模块未使用
- **新建**:
  - `apps/admin/src/hooks/useDepartments.ts` — 封装 departmentApi.list + 缓存
  - `apps/admin/src/hooks/useDoctors.ts` — 封装 doctorApi.list / doctorApi.listByDept / doctorApi.listByStore + 缓存
- **替换**: 22 处本地函数 → import hook（逐文件替换，每替换一个文件跑 tsc 验证）
- **代表文件**: `schedule/rule/index.tsx`, `schedule/gantt/index.tsx`, `schedule/custom-form.tsx`

### Phase 3: Server 端修复

#### 3.1 时区统一
- **问题**: `datetime.utcnow()` 3 处（deprecated），`datetime.now()` 9 处（naive）
- **新建**: `apps/server/app/utils/datetime.py`
  ```python
  from datetime import datetime, timezone
  def utc_now() -> datetime:
      return datetime.now(timezone.utc)
  ```
- **替换**:
  - `service_extra_quota.py:82,126,162` — `utcnow()` → `utc_now()`
  - `appointments/service_flow.py:173,250,304` — `datetime.now()` → `utc_now()`
  - `appointments/service_booking.py:91,473,508,635` — `datetime.now()` → `utc_now()`
- **注意**: `service_booking.py:216` (strftime ID 生成) 和 `:401` (Blacklist 过期比较) 需确认时区语义

#### 3.2 N+1 查询修复
- **问题**: `router_custom.py:370-375` 每条 custom schedule 3-4 次 db.refresh
- **修改**: 创建后用单次 eager-loaded 查询重新加载
  ```python
  # 替代循环 refresh
  ids = [s.id for s in created_schedules]
  result = await db.execute(
      select(Schedule)
      .where(Schedule.id.in_(ids))
      .options(selectinload(Schedule.doctor).selectinload(Doctor.department))
  )
  created_schedules = list(result.scalars().all())
  ```

### Phase 4: 类型安全（最高工作量，分批执行）

#### 4.1 高优先级 — 数据结构类型
- **问题**: 75 处 `: any`，15 个文件
- **先修数据结构类**（非 catch 块）:
  - `statistics.tsx:271,295,318,286` — 为 trendData/workloadData/heatmap 定义接口
  - `rule/form.tsx:61` — breakTimes 改为 `{ startTime: string; endTime: string }[]`
  - `rule/form.tsx:171,221` — handleSubmit/handleValuesChange 使用 FormValues 类型
  - `suspension.tsx:196` — handleSubmit 使用 FormValues 类型
  - `detail/index.tsx:68` — handleSubmit 使用 FormValues 类型
  - `CopyRuleModal.tsx:22` — breakTimes 改为 typed array
  - `gantt/index.tsx:207` — baseParams 使用具体类型

#### 4.2 低优先级 — catch 块 + 表单回调
- 剩余 `catch(e: any)` 和 antd 回调类型保持现状或改为 `unknown`

## Verification

每个 Phase 完成后:
1. **Phase 1**: `cd apps/admin && npx tsc --noEmit` 验证无类型错误
2. **Phase 2**: `npx tsc --noEmit` + 手动检查 hook 导入无循环依赖
3. **Phase 3**: `cd apps/server && python -m pytest tests/ -q` 全量通过
4. **Phase 4**: `npx tsc --noEmit` 验证

最终: `cd apps/server && python -m pytest tests/ -q` 全量通过
