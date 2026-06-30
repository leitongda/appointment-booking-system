# Design: 审批流 Edge-Driven 执行

## Current State

审批流定义已保存 `nodes` 和 `edges`，实例激活时也会把节点和边写入 `snapshot_json`。但是运行时 `_find_next_node` 的核心逻辑仍是：

1. 当前节点有条件规则时，按条件规则返回 `target_node_key`
2. 否则按 `sort_order` 找下一个节点

这意味着画布连线只参与展示和部分校验，不是执行权威。BPMN 导入、条件分支、回路和手工连线都可能与运行时路径不一致。

## Target Model

运行时以 `snapshot_json` 为唯一事实来源：

```text
snapshot_json = {
  nodes: [...],
  edges: [
    { id, source, target, sourceHandle, targetHandle }
  ],
  global_listeners: [...]
}
```

节点推进不再根据 `sort_order` 猜路径，而是从当前节点出边中选择目标。

## Execution Rules

### 普通节点

- 读取当前节点的出边
- 如果只有一条出边，进入该目标节点
- 如果没有出边且当前节点不是结束节点，则完成流程前必须由校验阻止；历史数据回退到 `sort_order`
- 如果多条非条件出边，校验失败，避免运行时歧义

### 条件节点

- 读取当前条件节点的所有出边
- 使用 `ConditionEvaluator.evaluate_condition_groups(...)` 得到匹配的 `target_node_key`
- 匹配成功时，目标必须存在对应出边，否则运行时报错并记录日志
- 匹配失败时，选择 `sourceHandle == "default"` 的默认边
- 如果没有默认边，运行时报错，不自动通过

### 抄送节点

- 抄送通知后继续根据出边推进
- 抄送节点可以连接到审批、条件或结束节点

### 开始/结束节点

- 开始节点使用出边进入第一个业务节点
- 结束节点终止流程并标记通过

## Compatibility

历史快照可能没有 `edges`。兼容策略：

- 如果 snapshot 中有 edges，则使用 edge-driven 执行
- 如果 snapshot 中没有 edges，则记录 `approval_flow_edges_missing_fallback` 日志，并继续使用现有 `sort_order` 逻辑
- 新激活流程必须包含合法 edges，否则不能激活

## Validation

`FlowDefinitionService.validate` 应增加图校验：

- 只能有一个开始节点
- 至少有一个结束节点
- 所有边的 source/target 必须存在
- 从开始节点必须能到达所有非孤立业务节点
- 非结束节点至少有一条出边
- 结束节点不允许有出边
- 普通节点不允许多条无条件出边
- 条件节点的每个条件目标必须存在对应出边
- 条件节点最多一条默认边

## Tests

需要覆盖：

- 线性审批：start -> approval -> end
- 条件命中：condition 根据 form_data 进入匹配边
- 条件默认：不命中时走 default 边
- 条件缺默认：运行时报错
- 抄送节点：通知后继续按边推进
- 历史快照无 edges：使用 sort_order 回退
- BPMN 条件网关导入：条件边进入 edges，运行路径可匹配
