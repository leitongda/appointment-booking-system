# Change: 重构审批流执行为连线驱动

## Why

当前审批流设计器已经支持节点、连线、条件分支、BPMN 导入和实例流程图展示，但运行时推进仍主要依赖 `sort_order` 和条件节点内的 `target_node_key`。这会造成三个问题：

- 设计器画出的连线不一定等于运行时实际路径，复杂分支、回路、跳转和 BPMN 导入后尤其容易失真
- `edges` 已经被前端、导入、校验和流程图依赖，但后端执行没有把它作为权威拓扑，维护成本高
- 条件节点默认分支、条件分支、不可达节点校验和实例进度展示缺少统一的图语义

审批流应以“流程定义快照中的节点和边”为运行时事实来源，使设计、导入、校验、执行和展示保持一致。

## What Changes

- 将审批实例运行时的下一节点查找从 `sort_order` 推进重构为 `edges` 驱动
- 激活流程时将 `edges` 写入 `snapshot_json`，运行中实例始终使用快照边执行
- 条件节点根据条件规则匹配目标节点，并要求匹配目标必须存在对应出边；条件不命中时走默认边
- 普通节点、抄送节点、开始节点使用出边查找下一个节点；结束节点终止流程
- 流程校验增强为图校验：单开始节点、至少一个结束节点、边端点存在、开始可达、非结束节点出边约束、条件节点分支约束
- 保留兼容回退：历史快照没有 `edges` 时仍可使用现有 `sort_order` 逻辑，并记录日志

## Scope

### In Scope

- `apps/server/app/modules/approval_flows/engine.py`
- `apps/server/app/modules/approval_flows/service_definitions.py`
- `apps/server/app/modules/approval_flows/bpmn_parser.py`
- `apps/server/app/modules/approval_flows/schemas.py`（如需补充 edge 结构）
- 审批流相关单元测试与 BPMN 解析测试
- Admin 设计器中与条件边/默认边保存相关的必要兼容修复

### Out of Scope

- 不引入并行网关的真正并行执行语义
- 不新增数据库表保存运行轨迹，运行轨迹增强另行设计
- 不重构审批实例高级操作的权限模型
- 不改变已有业务回调注册方式

## Impact

- Affected specs: `approval-flow-execution` (new)
- Affected code:
  - `apps/server/app/modules/approval_flows/engine.py`
  - `apps/server/app/modules/approval_flows/service_definitions.py`
  - `apps/server/app/modules/approval_flows/bpmn_parser.py`
  - `apps/admin/src/pages/approval/designer/*`
  - `apps/server/tests/unit/test_approval_flows_engine.py`
  - `apps/server/tests/unit/test_bpmn_parser.py`

## Rollout Strategy

1. 先实现快照 edge-driven 执行，并保留无 edges 快照的 `sort_order` 回退
2. 对新激活流程强制通过图校验，阻止不完整拓扑进入 active 状态
3. 用单元测试覆盖线性流程、条件命中、默认分支、抄送跳过、BPMN 条件边导入
4. 线上存量运行中实例继续使用已有快照；没有 `edges` 的历史快照走兼容回退

## Open Questions

- 条件节点是否允许没有默认边；建议第一阶段允许，但条件不命中时流程应报错并停留当前节点，避免误通过
- 并行网关在 BPMN 导入后是否只作为普通审批占位；建议本变更不实现并行语义
- 设计器是否需要显式展示“默认边”句柄；建议第一阶段保留现有 `sourceHandle=default` 约定
