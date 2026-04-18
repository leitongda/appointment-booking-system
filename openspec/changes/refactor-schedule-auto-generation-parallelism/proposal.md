# Change: 并行化自动排班生成任务

## Why
当前 `auto_generate_schedules_task` 在单个 Celery 任务中串行遍历全部活跃租户，再在每个租户内串行处理模板。随着租户数量增长，任务总耗时线性上升，凌晨 2 点的调度窗口会被不断拉长；同时，一次重试会重新覆盖全部租户，失败域过大，也不利于定位单租户异常。

## What Changes
- 将每日自动排班生成重构为“调度器任务 + 租户级子任务 + 汇总回调”的并行执行模型
- 把现有租户内的排班生成逻辑下沉为独立的租户任务，继续保持租户内事务边界和模板级错误隔离
- 保留现有按模板手动生成能力，不改变 Admin 端和现有手动生成接口
- 为调度器输出结构化汇总结果，记录成功租户、失败租户、创建/跳过数量与错误摘要
- 明确定义并行执行下的重试、告警和幂等要求，避免重复生成和失败扩大化

## Impact
- Affected specs:
  - `schedule-auto-generation` (new)
- Affected code:
  - `apps/server/app/tasks/schedule_task.py`
  - `apps/server/app/celery_app.py`
  - `apps/server/tests/**`
